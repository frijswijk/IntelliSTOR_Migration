// papyrus_rpt_info.cpp - Standalone RPT metadata collector
//
// Reads Papyrus RPT spool files and outputs a CSV summary with:
//   RPT_FILE, REPORT_SPECIES_ID, SECTION_COUNT, PAGES, BINARY
//
// Usage:
//   papyrus_rpt_info.exe <file.rpt>                    - Single file info
//   papyrus_rpt_info.exe <directory>                    - All .RPT files in directory
//   papyrus_rpt_info.exe <file_or_dir> [OUTPUT <path>]  - Write CSV to file
//
// Dependencies: zlib only (no QPDF, no AFP parser)
//
// Compile:
//   g++ -std=c++17 -O2 -static -o papyrus_rpt_info.exe papyrus_rpt_info.cpp -lz -s

#include <algorithm>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#include <zlib.h>

namespace fs = std::filesystem;

// ============================================================================
// Constants
// ============================================================================

static constexpr uint32_t RPTINSTHDR_OFFSET = 0xF0;

// ============================================================================
// Data Structures
// ============================================================================

struct RptHeader {
    int         domain_id           = 0;
    int         report_species_id   = 0;
    std::string timestamp;
    uint32_t    page_count          = 0;
    uint32_t    section_count       = 0;
    uint32_t    binary_object_count = 0;
};

struct BinaryObjectEntry {
    uint32_t page_offset       = 0;
    uint32_t uncompressed_size = 0;
    uint32_t compressed_size   = 0;

    uint32_t absolute_offset() const {
        return page_offset + RPTINSTHDR_OFFSET;
    }
};

// ============================================================================
// Utility Functions
// ============================================================================

static uint16_t read_u16(const uint8_t* p) {
    uint16_t v;
    std::memcpy(&v, p, sizeof(v));
    return v;
}

static uint32_t read_u32(const uint8_t* p) {
    uint32_t v;
    std::memcpy(&v, p, sizeof(v));
    return v;
}

static std::vector<uint8_t> read_file(const std::string& path) {
    std::ifstream f(path, std::ios::binary | std::ios::ate);
    if (!f) return {};
    auto sz = f.tellg();
    if (sz <= 0) return {};
    std::vector<uint8_t> buf(static_cast<size_t>(sz));
    f.seekg(0);
    f.read(reinterpret_cast<char*>(buf.data()), sz);
    return buf;
}

static const uint8_t* find_marker(const uint8_t* haystack, size_t haystack_len,
                                  const char* needle, size_t needle_len) {
    if (haystack_len < needle_len) return nullptr;
    const uint8_t* end = haystack + haystack_len - needle_len + 1;
    for (const uint8_t* p = haystack; p < end; ++p) {
        if (std::memcmp(p, needle, needle_len) == 0) return p;
    }
    return nullptr;
}

// ============================================================================
// RPT Parsing
// ============================================================================

static bool parse_rpt_header(const uint8_t* data, size_t data_len, RptHeader& hdr) {
    if (data_len < 0x1F0) return false;
    if (std::memcmp(data, "RPTFILEHDR", 10) != 0) return false;

    size_t header_end = 0;
    for (size_t i = 0; i < std::min(data_len, (size_t)192); ++i) {
        if (data[i] == 0x1A || data[i] == 0x00) {
            header_end = i;
            break;
        }
    }
    if (header_end == 0) header_end = 192;

    std::string header_line(reinterpret_cast<const char*>(data), header_end);
    std::vector<std::string> parts;
    {
        std::istringstream ss(header_line);
        std::string token;
        while (std::getline(ss, token, '\t')) {
            parts.push_back(token);
        }
    }

    if (parts.size() >= 2) {
        const std::string& id_part = parts[1];
        auto colon = id_part.find(':');
        if (colon != std::string::npos) {
            try {
                hdr.domain_id = std::stoi(id_part.substr(0, colon));
                hdr.report_species_id = std::stoi(id_part.substr(colon + 1));
            } catch (...) {}
        }
    }
    if (parts.size() >= 3) {
        hdr.timestamp = parts[2];
        while (!hdr.timestamp.empty() &&
               (hdr.timestamp.back() == ' ' || hdr.timestamp.back() == '\r' ||
                hdr.timestamp.back() == '\n')) {
            hdr.timestamp.pop_back();
        }
    }
    hdr.page_count      = read_u32(data + 0x1D4);
    hdr.section_count   = read_u32(data + 0x1E4);
    if (data_len >= 0x200) {
        hdr.binary_object_count = read_u32(data + 0x1F4);
    }

    return true;
}

static std::vector<BinaryObjectEntry> read_binary_table(const uint8_t* data, size_t data_len,
                                                         uint32_t count) {
    std::vector<BinaryObjectEntry> entries;
    if (count == 0) return entries;

    const uint8_t* mp = find_marker(data, data_len, "BPAGETBLHDR", 11);
    if (!mp) return entries;

    size_t entry_start = (mp - data) + 13;
    constexpr size_t entry_size = 16;

    entries.reserve(count);
    for (uint32_t i = 0; i < count; ++i) {
        size_t offset = entry_start + i * entry_size;
        if (offset + entry_size > data_len) break;

        const uint8_t* p = data + offset;
        BinaryObjectEntry e;
        e.page_offset       = read_u32(p);
        e.uncompressed_size = read_u32(p + 8);
        e.compressed_size   = read_u32(p + 12);
        entries.push_back(e);
    }

    return entries;
}

// ============================================================================
// Binary Format Detection
// ============================================================================

static std::string detect_binary_format(const std::string& rpt_path,
                                         const std::vector<BinaryObjectEntry>& binary_entries) {
    if (binary_entries.empty()) return "";

    const auto& first = binary_entries[0];

    // Read compressed data
    std::ifstream f(rpt_path, std::ios::binary);
    if (!f) return "";

    std::vector<uint8_t> compressed(first.compressed_size);
    f.seekg(first.absolute_offset());
    f.read(reinterpret_cast<char*>(compressed.data()), first.compressed_size);

    // Decompress
    uLongf dest_len = first.uncompressed_size;
    std::vector<uint8_t> decompressed(dest_len);
    int ret = uncompress(decompressed.data(), &dest_len,
                         compressed.data(), static_cast<uLong>(first.compressed_size));
    if (ret != Z_OK || dest_len < 8) return "";

    // Check magic bytes
    if (dest_len >= 4 && std::strncmp(reinterpret_cast<char*>(decompressed.data()), "%PDF", 4) == 0) {
        return "PDF";
    }
    // AFP: first byte 0x5A (structured field introducer), reasonable length
    if (decompressed[0] == 0x5A) {
        uint16_t sf_len = (static_cast<uint16_t>(decompressed[1]) << 8) | decompressed[2];
        if (sf_len >= 8 && sf_len <= dest_len) {
            return "AFP";
        }
    }
    return "";
}

// ============================================================================
// Process a single RPT file
// ============================================================================

struct RptInfo {
    std::string filename;
    int         species_id    = 0;
    uint32_t    section_count = 0;
    uint32_t    pages         = 0;
    std::string binary_format;
    bool        valid         = false;
};

static RptInfo collect_rpt_info(const std::string& rpt_path) {
    RptInfo info;
    info.filename = fs::path(rpt_path).filename().string();

    auto file_data = read_file(rpt_path);
    if (file_data.size() < 0x200) {
        std::cerr << "WARNING: File too small or cannot read: " << info.filename << "\n";
        return info;
    }

    RptHeader hdr;
    if (!parse_rpt_header(file_data.data(), file_data.size(), hdr)) {
        std::cerr << "WARNING: Not a valid RPT file: " << info.filename << "\n";
        return info;
    }

    info.species_id    = hdr.report_species_id;
    info.section_count = hdr.section_count;
    info.pages         = hdr.page_count;

    // Detect binary format
    auto binary_entries = read_binary_table(file_data.data(), file_data.size(),
                                            hdr.binary_object_count);
    info.binary_format = detect_binary_format(rpt_path, binary_entries);
    info.valid = true;

    return info;
}

// ============================================================================
// Main
// ============================================================================

static void print_usage(const char* prog) {
    std::cerr << "Usage:\n";
    std::cerr << "  " << prog << " <file.rpt>                      - Single file info\n";
    std::cerr << "  " << prog << " <directory>                      - All .RPT files in directory\n";
    std::cerr << "  " << prog << " <file_or_dir> OUTPUT <path.csv>  - Write CSV to file\n";
    std::cerr << "\nOutput CSV columns:\n";
    std::cerr << "  RPT_FILE, REPORT_SPECIES_ID, SECTION_COUNT, PAGES, BINARY\n";
}

int main(int argc, char* argv[]) {
    if (argc < 2) {
        print_usage(argv[0]);
        return 1;
    }

    std::string input = argv[1];
    std::string output_file;

    // Check for OUTPUT <path> option
    for (int i = 2; i < argc; ++i) {
        std::string arg = argv[i];
        std::transform(arg.begin(), arg.end(), arg.begin(), ::tolower);
        if (arg == "output" && i + 1 < argc) {
            output_file = argv[++i];
        }
    }

    // Collect RPT files
    std::vector<std::string> rpt_files;
    if (fs::is_directory(input)) {
        for (const auto& entry : fs::directory_iterator(input)) {
            if (!entry.is_regular_file()) continue;
            std::string ext = entry.path().extension().string();
            std::transform(ext.begin(), ext.end(), ext.begin(), ::tolower);
            if (ext == ".rpt") {
                rpt_files.push_back(entry.path().string());
            }
        }
        std::sort(rpt_files.begin(), rpt_files.end());
    } else if (fs::exists(input)) {
        rpt_files.push_back(input);
    } else {
        std::cerr << "ERROR: Not found: " << input << "\n";
        return 2;
    }

    if (rpt_files.empty()) {
        std::cerr << "ERROR: No .RPT files found\n";
        return 2;
    }

    // Collect info from all RPT files
    std::vector<RptInfo> results;
    for (const auto& rpt : rpt_files) {
        results.push_back(collect_rpt_info(rpt));
    }

    // Build CSV output
    std::ostringstream csv;
    csv << "RPT_FILE,REPORT_SPECIES_ID,SECTION_COUNT,PAGES,BINARY\n";
    for (const auto& r : results) {
        if (!r.valid) continue;
        csv << r.filename << ","
            << r.species_id << ","
            << r.section_count << ","
            << r.pages << ","
            << r.binary_format << "\n";
    }

    // Output
    std::string csv_str = csv.str();

    if (!output_file.empty()) {
        // Create parent directory if needed
        fs::path parent = fs::path(output_file).parent_path();
        if (!parent.empty() && !fs::exists(parent)) {
            fs::create_directories(parent);
        }
        std::ofstream out(output_file);
        if (!out) {
            std::cerr << "ERROR: Cannot write to: " << output_file << "\n";
            return 5;
        }
        out << csv_str;
        out.close();
        std::cout << "Written " << results.size() << " entries to " << output_file << "\n";
    } else {
        // Print to stdout
        std::cout << csv_str;
    }

    // Print summary to stderr (so it doesn't mix with CSV on stdout)
    int valid_count = 0;
    for (const auto& r : results) {
        if (r.valid) valid_count++;
    }
    std::cerr << "Processed " << rpt_files.size() << " files, "
              << valid_count << " valid RPT files\n";

    return 0;
}
