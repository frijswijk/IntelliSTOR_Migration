// papyrus_rpt_page_extractor.cpp - RPT extractor with PDF page extraction & watermarking
//
// Standalone C++17 CLI tool for Papyrus shell method calls (4 positional arguments).
// Based on rpt_page_extractor.cpp with simplified command-line interface.
// Includes PDF page extraction and watermarking support via QPDF.
//
// Compile: g++ -std=c++17 -O2 -static -o papyrus_rpt_page_extractor.exe papyrus_rpt_page_extractor.cpp -lz -s
// Compile (MSVC): cl /EHsc /O2 /MT papyrus_rpt_page_extractor.cpp /Fe:papyrus_rpt_page_extractor.exe
//
// Usage: papyrus_rpt_page_extractor.exe <input_rpt> <selection_rule> <output_txt> <output_binary>
//
// Selection rule formats:
//   - "all": All pages
//   - "pages:1-5": Pages 1-5
//   - "pages:1-5,10-20": Multiple page ranges
//   - "sections:14259": Single section
//   - "sections:14259,14260,14261": Multiple sections
//   - "14259,14260": Shorthand for sections (comma-separated numbers without prefix)
//
// PDF Features:
//   - Automatically extracts selected pages from PDF binaries (requires QPDF)
//   - Applies watermark if image found at ./tools/watermarks/confidential.png (requires ImageMagick)
//   - Falls back to full PDF extraction if QPDF not available
//   - Preserves page orientation (portrait/landscape)
//
// Dependencies (Optional):
//   - QPDF: For PDF page extraction (https://github.com/qpdf/qpdf/releases)
//   - ImageMagick: For watermarking (https://imagemagick.org/)
//   Place executables in ./tools/ or ensure they're in PATH
//
// Exit codes:
//   0  - Success
//   1  - Invalid arguments
//   2  - File not found
//   3  - Invalid RPT file
//   4  - Read error
//   5  - Write error
//   6  - Invalid selection rule
//   7  - No pages selected
//   8  - Decompression error
//   9  - Memory error
//   10 - Unknown error

#include <algorithm>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <optional>
#include <set>
#include <sstream>
#include <string>
#include <vector>

#include <zlib.h>

namespace fs = std::filesystem;

// ============================================================================
// Constants and Exit Codes
// ============================================================================

static constexpr uint32_t RPTINSTHDR_OFFSET = 0xF0;

// Exit codes (avoid name collision with stdlib macros)
constexpr int EC_SUCCESS = 0;
constexpr int EC_INVALID_ARGS = 1;
constexpr int EC_FILE_NOT_FOUND = 2;
constexpr int EC_INVALID_RPT_FILE = 3;
constexpr int EC_READ_ERROR = 4;
constexpr int EC_WRITE_ERROR = 5;
constexpr int EC_INVALID_SELECTION_RULE = 6;
constexpr int EC_NO_PAGES_SELECTED = 7;
constexpr int EC_DECOMPRESSION_ERROR = 8;
constexpr int EC_MEMORY_ERROR = 9;
constexpr int EC_UNKNOWN_ERROR = 10;

// ============================================================================
// Data Structures
// ============================================================================

struct RptHeader {
    int      domain_id             = 0;
    int      report_species_id     = 0;
    std::string timestamp;
    uint32_t page_count            = 0;
    uint32_t section_count         = 0;
    uint32_t binary_object_count   = 0;
    uint32_t section_data_offset   = 0;
};

struct SectionEntry {
    uint32_t section_id  = 0;
    uint32_t start_page  = 0;
    uint32_t page_count  = 0;
};

struct PageTableEntry {
    int      page_number       = 0;
    uint32_t page_offset       = 0;
    uint16_t line_width        = 0;
    uint16_t lines_per_page    = 0;
    uint32_t uncompressed_size = 0;
    uint32_t compressed_size   = 0;

    uint32_t absolute_offset() const {
        return page_offset + RPTINSTHDR_OFFSET;
    }
};

struct BinaryObjectEntry {
    int      index             = 0;
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
// RPT Parsing Functions
// ============================================================================

static std::optional<RptHeader> parse_rpt_header(const uint8_t* data, size_t data_len) {
    if (data_len < 0x1F0) return std::nullopt;
    if (std::memcmp(data, "RPTFILEHDR", 10) != 0) return std::nullopt;

    RptHeader hdr;
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

    hdr.page_count          = read_u32(data + 0x1D4);
    hdr.section_count       = read_u32(data + 0x1E4);
    uint32_t compressed_end = read_u32(data + 0x1E8);
    hdr.section_data_offset = compressed_end;
    if (data_len >= 0x200) {
        hdr.binary_object_count = read_u32(data + 0x1F4);
    }

    return hdr;
}

static std::vector<SectionEntry> read_sections(const uint8_t* data, size_t data_len,
                                               const RptHeader& hdr) {
    std::vector<SectionEntry> sections;
    const char marker[] = "SECTIONHDR";
    constexpr size_t marker_len = 10;

    const uint8_t* mp = find_marker(data, data_len, marker, marker_len);
    if (!mp) return sections;

    size_t data_start = (mp - data) + 13;
    const uint8_t* enddata = find_marker(data + data_start,
                                        data_len - data_start,
                                        "ENDDATA", 7);
    size_t section_bytes_len;
    if (enddata) {
        section_bytes_len = enddata - (data + data_start);
    } else {
        section_bytes_len = data_len - data_start;
    }

    uint32_t num_triplets = static_cast<uint32_t>(section_bytes_len / 12);
    const uint8_t* base = data + data_start;
    for (uint32_t i = 0; i < num_triplets; ++i) {
        const uint8_t* tp = base + i * 12;
        uint32_t sid = read_u32(tp);
        uint32_t sp  = read_u32(tp + 4);
        uint32_t pc  = read_u32(tp + 8);
        if (sp >= 1 && pc >= 1) {
            sections.push_back({sid, sp, pc});
        } else if (sid == 0 && sp == 0 && pc == 0) {
            break;
        }
    }

    return sections;
}

static std::vector<PageTableEntry> read_page_table(const uint8_t* data, size_t data_len,
                                                   uint32_t page_count) {
    std::vector<PageTableEntry> entries;
    const char marker[] = "PAGETBLHDR";
    constexpr size_t marker_len = 10;

    const uint8_t* mp = find_marker(data, data_len, marker, marker_len);
    if (!mp) return entries;

    size_t entry_start = (mp - data) + 13;
    constexpr size_t entry_size = 24;

    entries.reserve(page_count);
    for (uint32_t i = 0; i < page_count; ++i) {
        size_t offset = entry_start + i * entry_size;
        if (offset + entry_size > data_len) break;

        const uint8_t* p = data + offset;
        PageTableEntry e;
        e.page_number       = static_cast<int>(i + 1);
        e.page_offset       = read_u32(p);
        e.line_width        = read_u16(p + 8);
        e.lines_per_page    = read_u16(p + 10);
        e.uncompressed_size = read_u32(p + 12);
        e.compressed_size   = read_u32(p + 16);
        entries.push_back(e);
    }

    return entries;
}

static std::vector<BinaryObjectEntry> read_binary_table(const uint8_t* data, size_t data_len,
                                                        uint32_t count) {
    std::vector<BinaryObjectEntry> entries;
    if (count == 0) return entries;

    const char marker[] = "BPAGETBLHDR";
    constexpr size_t marker_len = 11;

    const uint8_t* mp = find_marker(data, data_len, marker, marker_len);
    if (!mp) return entries;

    size_t entry_start = (mp - data) + 13;
    constexpr size_t entry_size = 16;

    entries.reserve(count);
    for (uint32_t i = 0; i < count; ++i) {
        size_t offset = entry_start + i * entry_size;
        if (offset + entry_size > data_len) break;

        const uint8_t* p = data + offset;
        BinaryObjectEntry e;
        e.index             = static_cast<int>(i + 1);
        e.page_offset       = read_u32(p);
        e.uncompressed_size = read_u32(p + 8);
        e.compressed_size   = read_u32(p + 12);
        entries.push_back(e);
    }

    return entries;
}

static std::optional<std::vector<uint8_t>>
decompress_data(const std::string& filepath, uint32_t offset, uint32_t compressed_size,
               uint32_t uncompressed_size) {
    std::ifstream f(filepath, std::ios::binary);
    if (!f) return std::nullopt;

    std::vector<uint8_t> compressed(compressed_size);
    f.seekg(offset);
    f.read(reinterpret_cast<char*>(compressed.data()), compressed_size);

    uLongf dest_len = uncompressed_size;
    std::vector<uint8_t> decompressed(dest_len);

    int ret = uncompress(decompressed.data(), &dest_len,
                        compressed.data(), static_cast<uLong>(compressed_size));
    if (ret != Z_OK) return std::nullopt;

    decompressed.resize(dest_len);
    return decompressed;
}

// ============================================================================
// Selection Rule Parsing
// ============================================================================

enum class SelectionMode {
    ALL,
    PAGES,
    SECTIONS
};

struct SelectionRule {
    SelectionMode mode = SelectionMode::ALL;
    std::vector<std::pair<int, int>> page_ranges;
    std::vector<uint32_t> section_ids;  // Changed from set to vector to preserve order
};

static SelectionRule parse_selection_rule(const std::string& rule_str) {
    SelectionRule rule;

    if (rule_str == "all" || rule_str.empty()) {
        rule.mode = SelectionMode::ALL;
        return rule;
    }

    // Check if it's a simple comma-separated list of numbers (shorthand for sections)
    bool is_number_list = true;
    for (char c : rule_str) {
        if (!std::isdigit(c) && c != ',' && c != ' ') {
            is_number_list = false;
            break;
        }
    }

    if (is_number_list && rule_str.find(',') != std::string::npos) {
        // Shorthand: "14259,14260" -> sections
        rule.mode = SelectionMode::SECTIONS;
        std::istringstream ss(rule_str);
        std::string token;
        while (std::getline(ss, token, ',')) {
            // Trim whitespace
            size_t start = token.find_first_not_of(" \t");
            size_t end = token.find_last_not_of(" \t");
            if (start != std::string::npos) {
                token = token.substr(start, end - start + 1);
                rule.section_ids.push_back(std::stoul(token));  // Changed from insert to push_back
            }
        }
        return rule;
    }

    // Standard format: "type:value"
    auto colon = rule_str.find(':');
    if (colon == std::string::npos) {
        throw std::runtime_error("Invalid selection rule format (missing ':'): " + rule_str);
    }

    std::string type = rule_str.substr(0, colon);
    std::string value = rule_str.substr(colon + 1);

    // Convert type to lowercase
    std::transform(type.begin(), type.end(), type.begin(), ::tolower);

    if (type == "pages") {
        rule.mode = SelectionMode::PAGES;
        std::istringstream ss(value);
        std::string range_str;
        while (std::getline(ss, range_str, ',')) {
            // Trim
            size_t start = range_str.find_first_not_of(" \t");
            size_t end = range_str.find_last_not_of(" \t");
            if (start != std::string::npos) {
                range_str = range_str.substr(start, end - start + 1);
            }

            auto dash = range_str.find('-');
            if (dash != std::string::npos) {
                int p_start = std::stoi(range_str.substr(0, dash));
                int p_end = std::stoi(range_str.substr(dash + 1));
                rule.page_ranges.push_back({p_start, p_end});
            } else {
                int p = std::stoi(range_str);
                rule.page_ranges.push_back({p, p});
            }
        }
    } else if (type == "section" || type == "sections") {
        rule.mode = SelectionMode::SECTIONS;
        std::istringstream ss(value);
        std::string sid_str;
        while (std::getline(ss, sid_str, ',')) {
            // Trim
            size_t start = sid_str.find_first_not_of(" \t");
            size_t end = sid_str.find_last_not_of(" \t");
            if (start != std::string::npos) {
                sid_str = sid_str.substr(start, end - start + 1);
                rule.section_ids.push_back(std::stoul(sid_str));  // Changed from insert to push_back
            }
        }
    } else {
        throw std::runtime_error("Unknown selector type: " + type);
    }

    return rule;
}

static std::vector<PageTableEntry>
select_pages_by_range(const std::vector<PageTableEntry>& entries,
                     const std::vector<std::pair<int, int>>& ranges) {
    std::vector<PageTableEntry> selected;
    for (const auto& e : entries) {
        for (const auto& [start, end] : ranges) {
            if (e.page_number >= start && e.page_number <= end) {
                selected.push_back(e);
                break;
            }
        }
    }
    return selected;
}

static std::vector<PageTableEntry>
select_pages_by_sections(const std::vector<PageTableEntry>& entries,
                        const std::vector<SectionEntry>& sections,
                        const std::vector<uint32_t>& section_ids) {  // Changed from set to vector
    std::vector<PageTableEntry> selected;
    std::map<uint32_t, const SectionEntry*> section_map;
    for (const auto& s : sections) {
        section_map[s.section_id] = &s;
    }

    // Iterate in the order requested by the user (preserved in vector)
    for (uint32_t sid : section_ids) {
        auto it = section_map.find(sid);
        if (it == section_map.end()) continue;

        const SectionEntry* sec = it->second;
        int start = static_cast<int>(sec->start_page);
        int end = static_cast<int>(sec->start_page + sec->page_count - 1);

        for (const auto& e : entries) {
            if (e.page_number >= start && e.page_number <= end) {
                selected.push_back(e);
            }
        }
    }

    return selected;
}

// ============================================================================
// PDF Page Extraction Functions
// ============================================================================

static std::string find_qpdf() {
    // Check bundled tools first
    std::string bundled = "./tools/qpdf.exe";
    if (fs::exists(bundled)) return bundled;

    // Check common install locations
    std::vector<std::string> paths = {
        "C:\\Users\\freddievr\\qpdf-12.3.2-mingw64\\bin\\qpdf.exe",
        "C:\\Users\\freddievr\\qpdf\\bin\\qpdf.exe",
        "C:\\Program Files\\qpdf\\bin\\qpdf.exe",
        "qpdf.exe"  // Try PATH
    };

    for (const auto& p : paths) {
        if (fs::exists(p)) return p;
        // Try executing to see if it's in PATH
        std::string test_cmd = "\"" + p + "\" --version >nul 2>&1";
        if (std::system(test_cmd.c_str()) == 0) {
            return p;
        }
    }

    return "";
}

static std::string find_magick() {
    std::string bundled = "./tools/magick.exe";
    if (fs::exists(bundled)) return bundled;

    std::vector<std::string> paths = {
        "C:\\Users\\freddievr\\imagemagick\\magick.exe",
        "C:\\Program Files\\ImageMagick\\magick.exe",
        "magick.exe"
    };

    for (const auto& p : paths) {
        if (fs::exists(p)) return p;
        std::string test_cmd = "\"" + p + "\" --version >nul 2>&1";
        if (std::system(test_cmd.c_str()) == 0) {
            return p;
        }
    }

    return "";
}

static bool extract_pdf_pages(const std::string& qpdf_exe,
                              const std::string& input_pdf,
                              const std::string& output_pdf,
                              const std::vector<int>& pages) {
    if (pages.empty()) {
        // No filtering - just copy the PDF
        try {
            fs::copy(input_pdf, output_pdf, fs::copy_options::overwrite_existing);
            return true;
        } catch (...) {
            return false;
        }
    }

    // Build page specification: "1,3,5-7,10"
    std::ostringstream page_spec;

    // Consolidate consecutive pages into ranges
    std::vector<int> sorted_pages = pages;
    std::sort(sorted_pages.begin(), sorted_pages.end());

    size_t i = 0;
    while (i < sorted_pages.size()) {
        int range_start = sorted_pages[i];
        int range_end = range_start;

        // Find consecutive pages
        while (i + 1 < sorted_pages.size() && sorted_pages[i + 1] == sorted_pages[i] + 1) {
            ++i;
            range_end = sorted_pages[i];
        }

        if (!page_spec.str().empty()) {
            page_spec << ",";
        }

        if (range_start == range_end) {
            page_spec << range_start;
        } else {
            page_spec << range_start << "-" << range_end;
        }

        ++i;
    }

    // QPDF command
    std::ostringstream cmd;
    cmd << "\"" << qpdf_exe << "\" \"" << input_pdf << "\" "
        << "--pages . " << page_spec.str() << " -- \"" << output_pdf << "\"";

    int result = std::system(cmd.str().c_str());
    return (result == 0);
}

static bool create_watermark_pdf(const std::string& magick_exe,
                                 const std::string& image_path,
                                 const std::string& watermark_pdf,
                                 int width = 612, int height = 792) {
    // Convert PNG to PDF with page size (Letter: 612x792, A4: 595x842)
    std::ostringstream cmd;
    cmd << "\"" << magick_exe << "\" convert \"" << image_path << "\" "
        << "-page " << width << "x" << height << " "
        << "-gravity center "
        << "\"" << watermark_pdf << "\"";

    int result = std::system(cmd.str().c_str());
    return (result == 0);
}

static bool apply_watermark(const std::string& qpdf_exe,
                           const std::string& input_pdf,
                           const std::string& watermark_pdf,
                           const std::string& output_pdf) {
    // QPDF overlay command
    std::ostringstream cmd;
    cmd << "\"" << qpdf_exe << "\" \"" << input_pdf << "\" "
        << "--overlay \"" << watermark_pdf << "\" -- \"" << output_pdf << "\"";

    int result = std::system(cmd.str().c_str());
    return (result == 0);
}

static bool process_pdf_with_options(const std::string& input_pdf,
                                     const std::string& output_pdf,
                                     const std::vector<int>& pages,
                                     const std::string& watermark_image) {
    std::string qpdf_exe = find_qpdf();
    if (qpdf_exe.empty()) {
        std::cerr << "WARNING: QPDF not found. Copying full PDF without page extraction.\n";
        try {
            fs::copy(input_pdf, output_pdf, fs::copy_options::overwrite_existing);
            return false;
        } catch (...) {
            return false;
        }
    }

    // Step 1: Extract pages (or copy if no filtering)
    std::string temp_extracted = output_pdf + ".temp.pdf";
    if (!extract_pdf_pages(qpdf_exe, input_pdf, temp_extracted, pages)) {
        std::cerr << "ERROR: Failed to extract PDF pages\n";
        return false;
    }

    // Step 2: Apply watermark if provided
    if (!watermark_image.empty() && fs::exists(watermark_image)) {
        std::string magick_exe = find_magick();
        if (magick_exe.empty()) {
            std::cerr << "WARNING: ImageMagick not found. Skipping watermark.\n";
            try {
                fs::rename(temp_extracted, output_pdf);
            } catch (...) {
                fs::copy(temp_extracted, output_pdf, fs::copy_options::overwrite_existing);
                fs::remove(temp_extracted);
            }
        } else {
            std::string watermark_pdf = output_pdf + ".watermark.pdf";

            // Convert image to PDF
            if (!create_watermark_pdf(magick_exe, watermark_image, watermark_pdf)) {
                std::cerr << "WARNING: Failed to create watermark PDF. Skipping watermark.\n";
                try {
                    fs::rename(temp_extracted, output_pdf);
                } catch (...) {
                    fs::copy(temp_extracted, output_pdf, fs::copy_options::overwrite_existing);
                    fs::remove(temp_extracted);
                }
            } else {
                // Apply watermark
                if (!apply_watermark(qpdf_exe, temp_extracted, watermark_pdf, output_pdf)) {
                    std::cerr << "WARNING: Failed to apply watermark.\n";
                    try {
                        fs::rename(temp_extracted, output_pdf);
                    } catch (...) {
                        fs::copy(temp_extracted, output_pdf, fs::copy_options::overwrite_existing);
                        fs::remove(temp_extracted);
                    }
                } else {
                    // Cleanup temp files
                    fs::remove(temp_extracted);
                    fs::remove(watermark_pdf);
                }
            }
        }
    } else {
        // No watermark requested
        try {
            fs::rename(temp_extracted, output_pdf);
        } catch (...) {
            fs::copy(temp_extracted, output_pdf, fs::copy_options::overwrite_existing);
            fs::remove(temp_extracted);
        }
    }

    return true;
}

// ============================================================================
// Main Extraction
// ============================================================================

int main(int argc, char* argv[]) {
    // Validate arguments
    if (argc != 5) {
        std::cerr << "Usage: " << argv[0]
                  << " <input_rpt> <selection_rule> <output_txt> <output_binary>\n";
        std::cerr << "\nArguments:\n";
        std::cerr << "  input_rpt       - Path to input .rpt file\n";
        std::cerr << "  selection_rule  - \"all\", \"pages:1-5\", \"sections:14259,14260\", or \"14259,14260\"\n";
        std::cerr << "  output_txt      - Path to write concatenated text output\n";
        std::cerr << "  output_binary   - Path to write binary output (PDF/AFP)\n";
        std::cerr << "\nExit Codes:\n";
        std::cerr << "  0  - Success\n";
        std::cerr << "  1  - Invalid arguments\n";
        std::cerr << "  2  - File not found\n";
        std::cerr << "  3  - Invalid RPT file\n";
        std::cerr << "  4  - Read error\n";
        std::cerr << "  5  - Write error\n";
        std::cerr << "  6  - Invalid selection rule\n";
        std::cerr << "  7  - No pages selected\n";
        std::cerr << "  8  - Decompression error\n";
        std::cerr << "  9  - Memory error\n";
        std::cerr << "  10 - Unknown error\n";
        return EC_INVALID_ARGS;
    }

    std::string input_rpt = argv[1];
    std::string selection_rule_str = argv[2];
    std::string output_txt = argv[3];
    std::string output_binary = argv[4];

    try {
        // Validate input file
        if (!fs::exists(input_rpt)) {
            std::cerr << "ERROR: Input file not found: " << input_rpt << "\n";
            return EC_FILE_NOT_FOUND;
        }

        // Read file
        auto file_data = read_file(input_rpt);
        if (file_data.size() < 0x200) {
            std::cerr << "ERROR: File too small or cannot read\n";
            return EC_READ_ERROR;
        }

        // Parse header
        auto hdr_opt = parse_rpt_header(file_data.data(), file_data.size());
        if (!hdr_opt) {
            std::cerr << "ERROR: Not a valid RPT file (no RPTFILEHDR signature)\n";
            return EC_INVALID_RPT_FILE;
        }
        RptHeader hdr = *hdr_opt;

        // Read page table
        auto page_entries = read_page_table(file_data.data(), file_data.size(), hdr.page_count);
        if (page_entries.empty()) {
            std::cerr << "ERROR: No PAGETBLHDR found\n";
            return EC_INVALID_RPT_FILE;
        }

        // Read sections
        auto sections = read_sections(file_data.data(), file_data.size(), hdr);

        // Parse selection rule
        SelectionRule rule = parse_selection_rule(selection_rule_str);

        // Select pages
        std::vector<PageTableEntry> selected;
        if (rule.mode == SelectionMode::ALL) {
            selected = page_entries;
        } else if (rule.mode == SelectionMode::PAGES) {
            selected = select_pages_by_range(page_entries, rule.page_ranges);
        } else if (rule.mode == SelectionMode::SECTIONS) {
            selected = select_pages_by_sections(page_entries, sections, rule.section_ids);
        }

        if (selected.empty()) {
            std::cerr << "ERROR: No pages matched the selection rule\n";
            return EC_NO_PAGES_SELECTED;
        }

        // Extract and write text pages
        std::ofstream txt_out(output_txt, std::ios::binary);
        if (!txt_out) {
            std::cerr << "ERROR: Cannot open output TXT file: " << output_txt << "\n";
            return EC_WRITE_ERROR;
        }

        for (const auto& entry : selected) {
            auto page_data = decompress_data(input_rpt, entry.absolute_offset(),
                                            entry.compressed_size, entry.uncompressed_size);
            if (page_data) {
                txt_out.write(reinterpret_cast<const char*>(page_data->data()),
                            page_data->size());
            }
        }
        txt_out.close();

        // Extract binary objects (if present)
        auto binary_entries = read_binary_table(file_data.data(), file_data.size(),
                                               hdr.binary_object_count);

        if (binary_entries.empty()) {
            std::cout << "NOTE: No binary objects (PDF/AFP) found in RPT file. Only text extracted.\n";
        }

        if (!binary_entries.empty()) {
            // First, extract full PDF/binary to temp file
            std::string temp_full_binary = output_binary + ".full.tmp";
            {
                std::ofstream full_bin_out(temp_full_binary, std::ios::binary);
                if (!full_bin_out) {
                    std::cerr << "ERROR: Cannot open temp binary file: " << temp_full_binary << "\n";
                    return EC_WRITE_ERROR;
                }

                for (const auto& entry : binary_entries) {
                    auto bin_data = decompress_data(input_rpt, entry.absolute_offset(),
                                                   entry.compressed_size, entry.uncompressed_size);
                    if (bin_data) {
                        full_bin_out.write(reinterpret_cast<const char*>(bin_data->data()),
                                          bin_data->size());
                    }
                }
                full_bin_out.close();
            }

            // Check if it's a PDF by reading magic bytes
            bool is_pdf = false;
            {
                std::ifstream check(temp_full_binary, std::ios::binary);
                char magic[5] = {0};
                check.read(magic, 4);
                is_pdf = (std::strncmp(magic, "%PDF", 4) == 0);
            }

            if (is_pdf) {
                // Build PDF page numbers from selected text pages
                // Assumption: PDF pages correspond 1:1 with text pages
                std::vector<int> pdf_pages;
                for (const auto& entry : selected) {
                    pdf_pages.push_back(entry.page_number);
                }

                // Look for watermark image
                std::string watermark;
                std::vector<std::string> watermark_paths = {
                    "./tools/watermarks/confidential.png",
                    "./watermarks/confidential.png",
                    "./confidential.png"
                };
                for (const auto& wm_path : watermark_paths) {
                    if (fs::exists(wm_path)) {
                        watermark = wm_path;
                        break;
                    }
                }

                // Process PDF with page extraction and optional watermark
                if (rule.mode == SelectionMode::ALL) {
                    // No page filtering for "all" mode
                    process_pdf_with_options(temp_full_binary, output_binary, {}, watermark);
                } else {
                    // Extract selected pages only
                    process_pdf_with_options(temp_full_binary, output_binary, pdf_pages, watermark);
                }

                // Cleanup temp file
                fs::remove(temp_full_binary);
            } else {
                // Not a PDF - just rename the full binary file
                try {
                    fs::rename(temp_full_binary, output_binary);
                } catch (...) {
                    fs::copy(temp_full_binary, output_binary, fs::copy_options::overwrite_existing);
                    fs::remove(temp_full_binary);
                }
            }
        }

        std::cout << "SUCCESS: Extracted " << selected.size() << " pages\n";
        std::cout << "  TXT:  " << output_txt << "\n";
        if (!binary_entries.empty()) {
            std::cout << "  BIN:  " << output_binary;

            // Check if it's a PDF
            std::ifstream check(output_binary, std::ios::binary);
            char magic[5] = {0};
            if (check.read(magic, 4) && std::strncmp(magic, "%PDF", 4) == 0) {
                std::cout << " (PDF";
                if (rule.mode != SelectionMode::ALL) {
                    std::cout << " - " << selected.size() << " pages extracted";
                }
                std::cout << ")";
            }
            std::cout << "\n";
        }

        return EC_SUCCESS;

    } catch (const std::runtime_error& e) {
        std::cerr << "ERROR: " << e.what() << "\n";
        return EC_INVALID_SELECTION_RULE;
    } catch (const std::exception& e) {
        std::cerr << "FATAL ERROR: " << e.what() << "\n";
        return EC_UNKNOWN_ERROR;
    }
}
