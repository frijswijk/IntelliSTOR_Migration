// rpt_file_builder.cpp - Create IntelliSTOR .RPT files from text pages and optional PDF/AFP
//
// Standalone C++17 CLI tool. Faithful port of the Python rpt_file_builder.py.
//
// Compile: g++ -std=c++17 -O2 -o rpt_file_builder rpt_file_builder.cpp -lz
// Compile (macOS): clang++ -std=c++17 -O2 -o rpt_file_builder rpt_file_builder.cpp -lz
//
// This is the inverse of rpt_page_extractor.cpp: it takes extracted text pages
// (and optionally a binary document like a PDF) and assembles them into a valid
// .RPT binary file that conforms to the IntelliSTOR RPT specification.
//
// RPT File Layout (builder output):
//   [0x000] RPTFILEHDR     - 240 bytes: header line + sub-header + zero-padding
//   [0x0F0] RPTINSTHDR     - 224 bytes: instance metadata + zero-padding
//   [0x1D0] Table Directory - 48 bytes: 3 rows x 16 bytes (offsets to trailer structures)
//   [0x200] COMPRESSED DATA - Per-page zlib streams + interleaved binary object streams
//   [...]   SECTIONHDR     - Marker + section triplets + ENDDATA
//   [...]   PAGETBLHDR     - Marker + 24-byte page entries + ENDDATA
//   [...]   BPAGETBLHDR    - Marker + 16-byte binary entries + ENDDATA (optional)
//
// All offsets in the Table Directory, PAGETBLHDR, and BPAGETBLHDR are relative
// to RPTINSTHDR at absolute position 0xF0.

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <optional>
#include <regex>
#include <sstream>
#include <string>
#include <vector>

#include <zlib.h>

namespace fs = std::filesystem;

// ============================================================================
// Constants
// ============================================================================

static constexpr uint32_t RPTFILEHDR_SIZE   = 0x0F0;  // 240 bytes
static constexpr uint32_t RPTINSTHDR_SIZE   = 0x0E0;  // 224 bytes
static constexpr uint32_t TABLE_DIR_SIZE    = 0x030;  // 48 bytes (3 rows x 16 bytes)
static constexpr uint32_t COMPRESSED_START  = 0x200;  // Compressed data always starts here
static constexpr uint32_t RPTINSTHDR_OFFSET = 0x0F0;  // Base for all relative offsets

static const uint8_t ENDDATA_MARKER[]     = {'E','N','D','D','A','T','A',0,0};              // 9 bytes
static const uint8_t SECTIONHDR_MARKER[]  = {'S','E','C','T','I','O','N','H','D','R',0,0,0};  // 13 bytes
static const uint8_t PAGETBLHDR_MARKER[]  = {'P','A','G','E','T','B','L','H','D','R',0,0,0};  // 13 bytes
static const uint8_t BPAGETBLHDR_MARKER[] = {'B','P','A','G','E','T','B','L','H','D','R',0,0}; // 13 bytes

// ============================================================================
// Data Structures
// ============================================================================

struct SectionDef {
    uint32_t section_id;
    uint32_t start_page;   // 1-based
    uint32_t page_count;
};

struct PageInfo {
    int index;             // 0-based index in text_pages list
    int page_number;       // 1-based page number in the output RPT
    int line_width;
    int lines_per_page;
    uint32_t uncompressed_size;
    std::vector<uint8_t> compressed_data;
    uint32_t compressed_size;
};

struct BinaryChunkInfo {
    int index;             // 0-based index
    uint32_t uncompressed_size;
    std::vector<uint8_t> compressed_data;
    uint32_t compressed_size;
};

struct BuildSpec {
    int species_id = 0;
    int domain_id  = 1;
    std::string timestamp;
    std::vector<std::vector<uint8_t>> text_pages;    // Raw text content per page
    std::vector<SectionDef> sections;
    std::string binary_file;                          // Path to PDF/AFP to embed
    std::optional<std::vector<uint8_t>> object_header_page;
    std::optional<std::vector<uint8_t>> template_rptinsthdr;  // 224-byte RPTINSTHDR from template
    std::optional<std::vector<uint8_t>> template_table_dir;   // 48-byte Table Directory from template
    std::optional<int> line_width_override;
    std::optional<int> lines_per_page_override;
};

// For verification:
struct RptHeader {
    int      domain_id             = 0;
    int      report_species_id     = 0;
    std::string timestamp;
    uint32_t page_count            = 0;
    uint32_t section_count         = 0;
    uint32_t binary_object_count   = 0;
    uint32_t section_data_offset   = 0;
    uint32_t page_table_offset     = 0;
};

struct SectionEntry {
    uint32_t section_id  = 0;
    uint32_t start_page  = 0;
    uint32_t page_count  = 0;
};

// ============================================================================
// Little-endian helpers (safe, no alignment issues)
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

static void write_u16_le(uint8_t* p, uint16_t v) {
    std::memcpy(p, &v, sizeof(v));
}

static void write_u32_le(uint8_t* p, uint32_t v) {
    std::memcpy(p, &v, sizeof(v));
}

// ============================================================================
// Utility: read entire file into a vector
// ============================================================================

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

// ============================================================================
// Utility: find a byte pattern in a buffer
// ============================================================================

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
// Utility: format numbers with commas
// ============================================================================

static std::string format_number(uint64_t n) {
    std::string s = std::to_string(n);
    int insert_pos = static_cast<int>(s.length()) - 3;
    while (insert_pos > 0) {
        s.insert(insert_pos, ",");
        insert_pos -= 3;
    }
    return s;
}

// ============================================================================
// Utility: zlib compress wrapper
// ============================================================================

static std::vector<uint8_t> zlib_compress(const uint8_t* src, size_t src_len) {
    uLongf dest_len = compressBound(static_cast<uLong>(src_len));
    std::vector<uint8_t> dest(dest_len);

    int ret = compress(dest.data(), &dest_len, src, static_cast<uLong>(src_len));
    if (ret != Z_OK) {
        std::cerr << "  ERROR: zlib compress failed (error " << ret << ")\n";
        return {};
    }
    dest.resize(dest_len);
    return dest;
}

// ============================================================================
// Utility: zlib decompress wrapper
// ============================================================================

static std::vector<uint8_t> zlib_decompress(const uint8_t* src, size_t src_len,
                                            size_t expected_len) {
    uLongf dest_len = static_cast<uLongf>(expected_len);
    std::vector<uint8_t> dest(dest_len);

    int ret = uncompress(dest.data(), &dest_len, src, static_cast<uLong>(src_len));
    if (ret != Z_OK) {
        std::cerr << "  ERROR: zlib decompress failed (error " << ret << ")\n";
        return {};
    }
    dest.resize(dest_len);
    return dest;
}

// ============================================================================
// Utility: generate timestamp string "YYYY/MM/DD HH:MM:SS.mmm"
// ============================================================================

static std::string generate_timestamp() {
    auto now = std::chrono::system_clock::now();
    auto time_t_now = std::chrono::system_clock::to_time_t(now);
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
                  now.time_since_epoch()) % 1000;

    std::tm tm_buf{};
#if defined(_WIN32)
    localtime_s(&tm_buf, &time_t_now);
#else
    localtime_r(&time_t_now, &tm_buf);
#endif

    char buf[64];
    std::snprintf(buf, sizeof(buf), "%04d/%02d/%02d %02d:%02d:%02d.%03d",
                  tm_buf.tm_year + 1900, tm_buf.tm_mon + 1, tm_buf.tm_mday,
                  tm_buf.tm_hour, tm_buf.tm_min, tm_buf.tm_sec,
                  static_cast<int>(ms.count()));
    return std::string(buf);
}

// ============================================================================
// Verification: parse_rpt_header (port from rpt_page_extractor.cpp)
// ============================================================================

static std::optional<RptHeader> parse_rpt_header(const uint8_t* data, size_t data_len) {
    if (data_len < 0x1F0) return std::nullopt;
    // Check RPTFILEHDR signature
    if (std::memcmp(data, "RPTFILEHDR", 10) != 0) return std::nullopt;

    RptHeader hdr;

    // Find end of header line (terminated by 0x1A or 0x00)
    size_t header_end = 0;
    for (size_t i = 0; i < std::min(data_len, (size_t)192); ++i) {
        if (data[i] == 0x1A || data[i] == 0x00) {
            header_end = i;
            break;
        }
    }
    if (header_end == 0) header_end = 192;

    std::string header_line(reinterpret_cast<const char*>(data), header_end);

    // Split by tabs
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
        // Trim trailing whitespace
        while (!hdr.timestamp.empty() &&
               (hdr.timestamp.back() == ' ' || hdr.timestamp.back() == '\r' ||
                hdr.timestamp.back() == '\n')) {
            hdr.timestamp.pop_back();
        }
    }

    // Table Directory at 0x1D0
    hdr.page_count          = read_u32(data + 0x1D4);
    hdr.section_count       = read_u32(data + 0x1E4);
    uint32_t compressed_end = read_u32(data + 0x1E8);
    hdr.section_data_offset = compressed_end;
    if (data_len >= 0x200) {
        hdr.binary_object_count = read_u32(data + 0x1F4);
    }

    return hdr;
}

// ============================================================================
// Verification: read_sectionhdr (port from rpt_page_extractor.cpp)
// ============================================================================

static std::pair<std::optional<RptHeader>, std::vector<SectionEntry>>
read_sectionhdr(const std::string& filepath) {
    auto file_data = read_file(filepath);
    if (file_data.size() < 0x200) {
        return {std::nullopt, {}};
    }

    auto hdr_opt = parse_rpt_header(file_data.data(), file_data.size());
    if (!hdr_opt) return {std::nullopt, {}};

    RptHeader& hdr = *hdr_opt;
    std::vector<SectionEntry> sections;

    const char marker[] = "SECTIONHDR";
    constexpr size_t marker_len = 10;

    // Strategy 1: Targeted scan near compressed_data_end offset
    if (hdr.section_data_offset > 0) {
        size_t scan_start = (hdr.section_data_offset > 16)
                            ? hdr.section_data_offset - 16 : 0;
        size_t scan_len   = std::min((size_t)4096, file_data.size() - scan_start);
        const uint8_t* region = file_data.data() + scan_start;

        const uint8_t* mp = find_marker(region, scan_len, marker, marker_len);
        if (mp) {
            size_t data_start = (mp - region) + 13; // skip marker(10) + 3 null bytes
            uint32_t count = (hdr.section_count > 0) ? hdr.section_count : 1000;
            size_t needed = count * 12;

            const uint8_t* triplet_base;
            size_t triplet_avail;

            if (data_start + needed <= scan_len) {
                triplet_base  = region + data_start;
                triplet_avail = scan_len - data_start;
            } else {
                size_t abs_data = scan_start + data_start;
                triplet_base  = file_data.data() + abs_data;
                triplet_avail = file_data.size() - abs_data;
            }

            uint32_t actual = std::min((uint32_t)(triplet_avail / 12), count);
            for (uint32_t i = 0; i < actual; ++i) {
                const uint8_t* tp = triplet_base + i * 12;
                uint32_t sid = read_u32(tp);
                uint32_t sp  = read_u32(tp + 4);
                uint32_t pc  = read_u32(tp + 8);
                if (sp >= 1 && pc >= 1) {
                    sections.push_back({sid, sp, pc});
                } else if (sid == 0 && sp == 0 && pc == 0) {
                    break;
                }
            }
            if (!sections.empty()) {
                hdr.section_count = static_cast<uint32_t>(sections.size());
                return {hdr, sections};
            }
        }
    }

    // Strategy 2: Full file scan fallback
    const uint8_t* mp = find_marker(file_data.data(), file_data.size(), marker, marker_len);
    if (!mp) return {hdr, {}};

    size_t data_start = (mp - file_data.data()) + 13;
    const uint8_t* enddata = find_marker(file_data.data() + data_start,
                                         file_data.size() - data_start,
                                         "ENDDATA", 7);
    size_t section_bytes_len;
    if (enddata) {
        section_bytes_len = enddata - (file_data.data() + data_start);
    } else {
        section_bytes_len = file_data.size() - data_start;
    }

    uint32_t num_triplets = static_cast<uint32_t>(section_bytes_len / 12);
    const uint8_t* base = file_data.data() + data_start;
    for (uint32_t i = 0; i < num_triplets; ++i) {
        const uint8_t* tp = base + i * 12;
        uint32_t sid = read_u32(tp);
        uint32_t sp  = read_u32(tp + 4);
        uint32_t pc  = read_u32(tp + 8);
        if (sp >= 1 && pc >= 1) {
            sections.push_back({sid, sp, pc});
        }
    }
    hdr.section_count = static_cast<uint32_t>(sections.size());

    return {hdr, sections};
}

// ============================================================================
// Object Header Generation
// ============================================================================

static std::vector<uint8_t> generate_object_header(const std::string& binary_path) {
    std::string filename = fs::path(binary_path).filename().string();

    // Get file modification time
    std::error_code ec;
    auto ftime = fs::last_write_time(binary_path, ec);
    std::string mtime_str;
    if (!ec) {
        // Convert file_time_type to system_clock time_point
        auto sctp = std::chrono::time_point_cast<std::chrono::system_clock::duration>(
            ftime - fs::file_time_type::clock::now() + std::chrono::system_clock::now());
        auto time_t_val = std::chrono::system_clock::to_time_t(sctp);
        std::tm tm_buf{};
#if defined(_WIN32)
        localtime_s(&tm_buf, &time_t_val);
#else
        localtime_r(&time_t_val, &tm_buf);
#endif
        char buf[32];
        std::snprintf(buf, sizeof(buf), "%04d%02d%02d%02d%02d%02d",
                      tm_buf.tm_year + 1900, tm_buf.tm_mon + 1, tm_buf.tm_mday,
                      tm_buf.tm_hour, tm_buf.tm_min, tm_buf.tm_sec);
        mtime_str = buf;
    } else {
        mtime_str = "00000000000000";
    }

    std::ostringstream oss;
    oss << "StorQM PLUS Object Header Page:\n";
    oss << "Object File Name: " << filename << "\n";
    oss << "Object File Timestamp: " << mtime_str << "\n";

    // Try to extract PDF metadata if it is a PDF
    {
        std::string fn_upper = filename;
        std::transform(fn_upper.begin(), fn_upper.end(), fn_upper.begin(),
                       [](unsigned char c){ return static_cast<char>(std::toupper(c)); });
        if (fn_upper.size() >= 4 && fn_upper.substr(fn_upper.size() - 4) == ".PDF") {
            std::ifstream pdf_f(binary_path, std::ios::binary);
            if (pdf_f) {
                std::vector<char> pdf_header(4096);
                pdf_f.read(pdf_header.data(), 4096);
                auto bytes_read = pdf_f.gcount();
                std::string pdf_text(pdf_header.data(), static_cast<size_t>(bytes_read));

                const char* pdf_fields[] = {
                    "Title", "Subject", "Author", "Creator",
                    "Producer", "CreationDate", "LastModifiedDate", "Keywords"
                };

                bool meta_ok = true;
                for (const char* field_name : pdf_fields) {
                    std::string value;
                    // Try regex: /FieldName\s*\(([^)]*)\)
                    std::string pattern = std::string("/") + field_name + "\\s*\\(([^)]*)\\)";
                    try {
                        std::regex re(pattern);
                        std::smatch match;
                        if (std::regex_search(pdf_text, match, re)) {
                            value = match[1].str();
                        } else {
                            // Try fallback: find /FieldName then next parenthesized value
                            std::string search_key = std::string("/") + field_name;
                            auto idx = pdf_text.find(search_key);
                            if (idx != std::string::npos) {
                                size_t snippet_end = std::min(idx + 200, pdf_text.size());
                                std::string snippet = pdf_text.substr(idx, snippet_end - idx);
                                std::regex re2("\\(([^)]*)\\)");
                                std::smatch match2;
                                if (std::regex_search(snippet, match2, re2)) {
                                    value = match2[1].str();
                                }
                            }
                        }
                    } catch (...) {
                        // regex error, leave value empty
                    }
                    oss << "PDF " << field_name << ": " << value << "\n";
                }

                if (!meta_ok) {
                    // Fallback: empty fields (should not reach here)
                    for (const char* field_name : pdf_fields) {
                        oss << "PDF " << field_name << ": \n";
                    }
                }
            } else {
                // Cannot read PDF, write empty fields
                const char* pdf_fields[] = {
                    "Title", "Subject", "Author", "Creator",
                    "Producer", "CreationDate", "LastModifiedDate", "Keywords"
                };
                for (const char* field_name : pdf_fields) {
                    oss << "PDF " << field_name << ": \n";
                }
            }
        }
    }

    std::string text = oss.str();

    // Encode as ASCII, replacing non-ASCII with '?'
    std::vector<uint8_t> result(text.size());
    for (size_t i = 0; i < text.size(); ++i) {
        uint8_t c = static_cast<uint8_t>(text[i]);
        result[i] = (c > 127) ? 0x3F : c;
    }
    return result;
}

// ============================================================================
// BCD Timestamp Encoding
// ============================================================================

static std::array<uint8_t, 8> encode_bcd_timestamp(const std::string& timestamp_str) {
    std::array<uint8_t, 8> buf{};

    // Parse "YYYY/MM/DD HH:MM:SS.mmm" or "YYYY/MM/DD HH:MM:SS"
    std::regex re(R"((\d{4})/(\d{2})/(\d{2})\s+(\d{2}):(\d{2}):(\d{2}))");
    std::smatch m;
    if (!std::regex_search(timestamp_str, m, re)) {
        return buf;  // all zeros
    }

    uint16_t year  = static_cast<uint16_t>(std::stoi(m[1].str()));
    uint8_t  month = static_cast<uint8_t>(std::stoi(m[2].str()));
    uint8_t  day   = static_cast<uint8_t>(std::stoi(m[3].str()));
    uint8_t  hour  = static_cast<uint8_t>(std::stoi(m[4].str()));
    uint8_t  minute = static_cast<uint8_t>(std::stoi(m[5].str()));
    uint8_t  second = static_cast<uint8_t>(std::stoi(m[6].str()));

    // Year as uint16 LE at [0:2]
    std::memcpy(&buf[0], &year, sizeof(year));
    buf[2] = month;
    buf[3] = day;
    buf[4] = hour;
    buf[5] = minute;
    buf[6] = second;
    buf[7] = 0x00;

    return buf;
}

// ============================================================================
// Page Analysis
// ============================================================================

static PageInfo analyze_page(const std::vector<uint8_t>& page_data, int index, int page_number,
                             const std::optional<int>& width_override,
                             const std::optional<int>& lines_override) {
    // Replace any byte > 127 with '?' (0x3F)
    std::vector<uint8_t> clean_data = page_data;
    for (auto& b : clean_data) {
        if (b > 127) b = 0x3F;
    }

    // Convert to string for line analysis
    std::string text(clean_data.begin(), clean_data.end());

    // Split by '\n' to count lines and find max line width
    int line_width = 0;
    int lines_count = 0;
    {
        std::istringstream stream(text);
        std::string line;
        while (std::getline(stream, line)) {
            // Remove trailing '\r' if present
            if (!line.empty() && line.back() == '\r') {
                line.pop_back();
            }
            int len = static_cast<int>(line.size());
            if (len > line_width) line_width = len;
            ++lines_count;
        }
    }

    if (width_override.has_value()) {
        line_width = *width_override;
    }
    if (lines_override.has_value()) {
        lines_count = *lines_override;
    }

    // Compress
    auto compressed = zlib_compress(page_data.data(), page_data.size());

    PageInfo pi;
    pi.index             = index;
    pi.page_number       = page_number;
    pi.line_width        = line_width;
    pi.lines_per_page    = lines_count;
    pi.uncompressed_size = static_cast<uint32_t>(page_data.size());
    pi.compressed_data   = std::move(compressed);
    pi.compressed_size   = static_cast<uint32_t>(pi.compressed_data.size());
    return pi;
}

// ============================================================================
// Binary File Chunking
// ============================================================================

static std::vector<std::vector<uint8_t>> chunk_binary_file(const std::string& path,
                                                           int num_chunks) {
    auto binary_data = read_file(path);
    std::vector<std::vector<uint8_t>> chunks;

    if (num_chunks <= 0 || binary_data.empty()) {
        return chunks;
    }
    if (num_chunks == 1) {
        chunks.push_back(std::move(binary_data));
        return chunks;
    }

    size_t chunk_size = binary_data.size() / static_cast<size_t>(num_chunks);
    size_t offset = 0;
    for (int i = 0; i < num_chunks; ++i) {
        if (i == num_chunks - 1) {
            // Last chunk gets remaining bytes
            chunks.emplace_back(binary_data.begin() + offset, binary_data.end());
        } else {
            chunks.emplace_back(binary_data.begin() + offset,
                                binary_data.begin() + offset + chunk_size);
            offset += chunk_size;
        }
    }
    return chunks;
}

// ============================================================================
// Compress Binary Chunks
// ============================================================================

static std::vector<BinaryChunkInfo> compress_chunks(
    const std::vector<std::vector<uint8_t>>& chunks) {
    std::vector<BinaryChunkInfo> result;
    result.reserve(chunks.size());

    for (int i = 0; i < static_cast<int>(chunks.size()); ++i) {
        auto compressed = zlib_compress(chunks[i].data(), chunks[i].size());
        BinaryChunkInfo ci;
        ci.index             = i;
        ci.uncompressed_size = static_cast<uint32_t>(chunks[i].size());
        ci.compressed_data   = std::move(compressed);
        ci.compressed_size   = static_cast<uint32_t>(ci.compressed_data.size());
        result.push_back(std::move(ci));
    }
    return result;
}

// ============================================================================
// Build RPTFILEHDR (0x000-0x0EF, 240 bytes)
// ============================================================================

static std::vector<uint8_t> build_rptfilehdr(int domain_id, int species_id,
                                              const std::string& timestamp,
                                              uint32_t compressed_data_end_rel) {
    std::vector<uint8_t> buf(RPTFILEHDR_SIZE, 0);  // 240 bytes, zero-filled

    // Build header line: "RPTFILEHDR\t{domain:04d}:{species}\t{timestamp}\x1a"
    char header_line[256];
    std::snprintf(header_line, sizeof(header_line),
                  "RPTFILEHDR\t%04d:%d\t%s\x1a",
                  domain_id, species_id, timestamp.c_str());

    size_t hlen = std::strlen(header_line);
    std::memcpy(buf.data(), header_line, std::min(hlen, (size_t)RPTFILEHDR_SIZE));

    // Fixed sub-header at 0xC0-0xEF
    // 0xC0: E0 00 05 01  (0x010500E0 LE)
    write_u32_le(buf.data() + 0xC0, 0x010500E0);
    // 0xC4: 01 00 00 00  (constant 1)
    write_u32_le(buf.data() + 0xC4, 1);
    // 0xC8: E0 00 00 00  (pointer to 0xE0)
    write_u32_le(buf.data() + 0xC8, 0xE0);
    // 0xD4: "ENDHDR\x00\x00" (8 bytes)
    std::memcpy(buf.data() + 0xD4, "ENDHDR\x00\x00", 8);
    // 0xE0: F0 00 00 00  (pointer to RPTINSTHDR)
    write_u32_le(buf.data() + 0xE0, 0xF0);
    // 0xE8: compressed_data_end (relative to RPTINSTHDR)
    write_u32_le(buf.data() + 0xE8, compressed_data_end_rel);

    return buf;
}

// ============================================================================
// Build RPTINSTHDR (0x0F0-0x1CF, 224 bytes)
// ============================================================================

static std::vector<uint8_t> build_rptinsthdr(const BuildSpec& spec) {
    if (spec.template_rptinsthdr.has_value() &&
        spec.template_rptinsthdr->size() == RPTINSTHDR_SIZE) {
        // Use template as base, patch key fields
        std::vector<uint8_t> buf = *spec.template_rptinsthdr;

        // Patch species_id at offset 0x14
        write_u32_le(buf.data() + 0x14, static_cast<uint32_t>(spec.species_id));

        // Patch report timestamp at 0x18 (8 bytes)
        auto ts_bytes = encode_bcd_timestamp(spec.timestamp);
        std::memcpy(buf.data() + 0x18, ts_bytes.data(), 8);

        return buf;
    }

    // Build from scratch
    std::vector<uint8_t> buf(RPTINSTHDR_SIZE, 0);  // 224 bytes, zero-filled

    // 0x00: "RPTINSTHDR\x00\x00" (12 bytes)
    std::memcpy(buf.data(), "RPTINSTHDR\x00\x00", 12);
    // 0x0C: pointer to RPTFILEHDR sub-header (0xE0)
    write_u32_le(buf.data() + 0x0C, 0xE0);
    // 0x10: instance number (always 1)
    write_u32_le(buf.data() + 0x10, 1);
    // 0x14: species_id
    write_u32_le(buf.data() + 0x14, static_cast<uint32_t>(spec.species_id));
    // 0x18: report timestamp (8 bytes BCD)
    auto ts_bytes = encode_bcd_timestamp(spec.timestamp);
    std::memcpy(buf.data() + 0x18, ts_bytes.data(), 8);
    // 0x22: creation timestamp (same format)
    std::memcpy(buf.data() + 0x22, ts_bytes.data(), 8);
    // 0x33: modification timestamp
    std::memcpy(buf.data() + 0x33, ts_bytes.data(), 8);
    // 0x40: fixed constants 01 01
    buf[0x40] = 0x01;
    buf[0x41] = 0x01;
    // 0xA0: report format info (0x0409 = 1033)
    write_u32_le(buf.data() + 0xA0, 0x0409);
    // 0xD0: "ENDHDR\x00\x00" (8 bytes)
    std::memcpy(buf.data() + 0xD0, "ENDHDR\x00\x00", 8);

    return buf;
}

// ============================================================================
// Compressed Data Assembly
// ============================================================================

struct AssembledData {
    std::vector<uint8_t> data;
    std::vector<uint32_t> page_offsets;
    std::vector<uint32_t> binary_offsets;  // empty if no binary
};

static AssembledData assemble_compressed_data(
    const std::vector<PageInfo>& page_infos,
    const std::vector<BinaryChunkInfo>* binary_chunks) {

    AssembledData result;
    uint32_t abs_pos = COMPRESSED_START;  // 0x200

    if (binary_chunks && !binary_chunks->empty()) {
        // Interleaved: text1, bin1, text2, bin2, ...
        for (size_t i = 0; i < page_infos.size(); ++i) {
            result.page_offsets.push_back(abs_pos);
            result.data.insert(result.data.end(),
                               page_infos[i].compressed_data.begin(),
                               page_infos[i].compressed_data.end());
            abs_pos += page_infos[i].compressed_size;

            if (i < binary_chunks->size()) {
                result.binary_offsets.push_back(abs_pos);
                result.data.insert(result.data.end(),
                                   (*binary_chunks)[i].compressed_data.begin(),
                                   (*binary_chunks)[i].compressed_data.end());
                abs_pos += (*binary_chunks)[i].compressed_size;
            }
        }
    } else {
        // Text-only: sequential
        for (const auto& pi : page_infos) {
            result.page_offsets.push_back(abs_pos);
            result.data.insert(result.data.end(),
                               pi.compressed_data.begin(),
                               pi.compressed_data.end());
            abs_pos += pi.compressed_size;
        }
    }

    return result;
}

// ============================================================================
// Trailer Construction: SECTIONHDR
// ============================================================================

static std::vector<uint8_t> build_sectionhdr(const std::vector<SectionDef>& sections) {
    std::vector<uint8_t> buf;
    buf.insert(buf.end(), SECTIONHDR_MARKER, SECTIONHDR_MARKER + 13);

    for (const auto& sec : sections) {
        uint8_t entry[12];
        write_u32_le(entry + 0, sec.section_id);
        write_u32_le(entry + 4, sec.start_page);
        write_u32_le(entry + 8, sec.page_count);
        buf.insert(buf.end(), entry, entry + 12);
    }

    buf.insert(buf.end(), ENDDATA_MARKER, ENDDATA_MARKER + 9);
    return buf;
}

// ============================================================================
// Trailer Construction: PAGETBLHDR
// ============================================================================

static std::vector<uint8_t> build_pagetblhdr(const std::vector<PageInfo>& page_infos,
                                              const std::vector<uint32_t>& page_offsets) {
    std::vector<uint8_t> buf;
    buf.insert(buf.end(), PAGETBLHDR_MARKER, PAGETBLHDR_MARKER + 13);

    for (size_t i = 0; i < page_infos.size(); ++i) {
        uint32_t abs_offset = page_offsets[i];
        uint32_t rel_offset = abs_offset - RPTINSTHDR_OFFSET;  // subtract 0xF0

        // 24-byte entry: <IIHHIII>
        uint8_t entry[24];
        std::memset(entry, 0, 24);
        write_u32_le(entry + 0,  rel_offset);                                      // page_offset (relative)
        write_u32_le(entry + 4,  0);                                                // reserved
        write_u16_le(entry + 8,  static_cast<uint16_t>(page_infos[i].line_width));  // line_width
        write_u16_le(entry + 10, static_cast<uint16_t>(page_infos[i].lines_per_page)); // lines_per_page
        write_u32_le(entry + 12, page_infos[i].uncompressed_size);                 // uncompressed_size
        write_u32_le(entry + 16, page_infos[i].compressed_size);                   // compressed_size
        write_u32_le(entry + 20, 0);                                                // reserved

        buf.insert(buf.end(), entry, entry + 24);
    }

    buf.insert(buf.end(), ENDDATA_MARKER, ENDDATA_MARKER + 9);
    return buf;
}

// ============================================================================
// Trailer Construction: BPAGETBLHDR
// ============================================================================

static std::vector<uint8_t> build_bpagetblhdr(const std::vector<BinaryChunkInfo>& binary_chunks,
                                               const std::vector<uint32_t>& binary_offsets) {
    std::vector<uint8_t> buf;
    buf.insert(buf.end(), BPAGETBLHDR_MARKER, BPAGETBLHDR_MARKER + 13);

    for (size_t i = 0; i < binary_chunks.size(); ++i) {
        uint32_t abs_offset = binary_offsets[i];
        uint32_t rel_offset = abs_offset - RPTINSTHDR_OFFSET;

        // 16-byte entry: <IIII>
        uint8_t entry[16];
        std::memset(entry, 0, 16);
        write_u32_le(entry + 0,  rel_offset);                      // page_offset (relative)
        write_u32_le(entry + 4,  0);                                // reserved
        write_u32_le(entry + 8,  binary_chunks[i].uncompressed_size); // uncompressed_size
        write_u32_le(entry + 12, binary_chunks[i].compressed_size);   // compressed_size

        buf.insert(buf.end(), entry, entry + 16);
    }

    buf.insert(buf.end(), ENDDATA_MARKER, ENDDATA_MARKER + 9);
    return buf;
}

// ============================================================================
// Table Directory Construction (0x1D0-0x1FF, 48 bytes)
// ============================================================================

static std::vector<uint8_t> build_table_directory(
    uint32_t page_count, uint32_t section_count, uint32_t binary_count,
    uint32_t sectionhdr_abs, uint32_t pagetblhdr_abs, uint32_t bpagetblhdr_abs,
    const std::optional<std::vector<uint8_t>>& template_table_dir) {

    std::vector<uint8_t> buf(TABLE_DIR_SIZE, 0);  // 48 bytes, zero-filled

    // Extract type prefix bytes from template if available
    uint16_t type_extra_0 = 0;  // bytes 2-3 of type field for Row 0
    uint16_t type_extra_1 = 0;  // bytes 2-3 of type field for Row 1
    if (template_table_dir.has_value() &&
        template_table_dir->size() >= TABLE_DIR_SIZE) {
        type_extra_0 = read_u16(template_table_dir->data() + 2);
        type_extra_1 = read_u16(template_table_dir->data() + 0x10 + 2);
    }

    // Row 0: PAGETBLHDR
    uint32_t pagetbl_rel = pagetblhdr_abs - RPTINSTHDR_OFFSET;
    buf[0] = 0x02;
    buf[1] = 0x01;
    write_u16_le(buf.data() + 2, type_extra_0);
    write_u32_le(buf.data() + 4, page_count);
    write_u32_le(buf.data() + 8, pagetbl_rel);
    // bytes 12-15: zero padding (already zero)

    // Row 1: SECTIONHDR
    uint32_t sectionhdr_rel = sectionhdr_abs - RPTINSTHDR_OFFSET;
    buf[0x10] = 0x01;
    buf[0x11] = 0x01;
    write_u16_le(buf.data() + 0x12, type_extra_1);
    write_u32_le(buf.data() + 0x14, section_count);
    write_u32_le(buf.data() + 0x18, sectionhdr_rel);
    // bytes 0x1C-0x1F: zero padding (already zero)

    // Row 2: BPAGETBLHDR (or all zeros for text-only)
    if (binary_count > 0) {
        uint32_t bpagetbl_rel = bpagetblhdr_abs - RPTINSTHDR_OFFSET;
        buf[0x20] = 0x03;
        buf[0x21] = 0x01;
        // bytes 0x22-0x23: zero (no template extra needed for BPAGETBLHDR)
        write_u32_le(buf.data() + 0x24, binary_count);
        write_u32_le(buf.data() + 0x28, bpagetbl_rel);
    }

    return buf;
}

// ============================================================================
// Final Assembly: build_rpt
// ============================================================================

static size_t build_rpt(BuildSpec& spec, const std::string& output_path, bool verbose) {
    // ---- Prepare all text pages ----
    std::vector<std::vector<uint8_t>> all_pages;
    if (!spec.binary_file.empty() && spec.object_header_page.has_value()) {
        // Object Header is page 1
        all_pages.push_back(*spec.object_header_page);
    }
    for (auto& page : spec.text_pages) {
        all_pages.push_back(page);
    }

    int total_text_pages = static_cast<int>(all_pages.size());
    if (verbose) {
        std::cout << "  Text pages: " << total_text_pages << "\n";
        if (!spec.binary_file.empty()) {
            std::cout << "  Binary file: " << spec.binary_file << "\n";
        }
    }

    // ---- Analyze and compress text pages ----
    std::vector<PageInfo> page_infos;
    page_infos.reserve(total_text_pages);
    for (int i = 0; i < total_text_pages; ++i) {
        auto pi = analyze_page(all_pages[i], i, i + 1,
                               spec.line_width_override, spec.lines_per_page_override);
        page_infos.push_back(std::move(pi));
    }

    // ---- Chunk and compress binary file ----
    std::vector<BinaryChunkInfo> binary_chunks;
    bool has_binary = false;
    if (!spec.binary_file.empty()) {
        // Number of chunks = number of text pages
        int num_chunks = total_text_pages;
        auto raw_chunks = chunk_binary_file(spec.binary_file, num_chunks);
        binary_chunks = compress_chunks(raw_chunks);
        has_binary = !binary_chunks.empty();
        if (verbose && has_binary) {
            uint64_t total_bin_uncomp = 0, total_bin_comp = 0;
            for (const auto& c : binary_chunks) {
                total_bin_uncomp += c.uncompressed_size;
                total_bin_comp   += c.compressed_size;
            }
            std::cout << "  Binary chunks: " << binary_chunks.size()
                      << ", uncomp=" << format_number(total_bin_uncomp)
                      << ", comp=" << format_number(total_bin_comp) << "\n";
        }
    }

    // ---- Assemble compressed data area ----
    auto assembled = assemble_compressed_data(
        page_infos, has_binary ? &binary_chunks : nullptr);

    uint32_t compressed_data_end_abs = COMPRESSED_START +
                                       static_cast<uint32_t>(assembled.data.size());
    uint32_t compressed_data_end_rel = compressed_data_end_abs - RPTINSTHDR_OFFSET;

    if (verbose) {
        std::cout << "  Compressed data: " << format_number(assembled.data.size())
                  << " bytes (0x" << std::hex << std::uppercase << COMPRESSED_START
                  << " - 0x" << compressed_data_end_abs
                  << std::dec << ")\n";
    }

    // ---- Update section definitions if using default single section ----
    if (spec.sections.size() == 1 && spec.sections[0].section_id == 0) {
        spec.sections[0].page_count = static_cast<uint32_t>(total_text_pages);
    }

    // ---- Build trailer structures ----
    auto sectionhdr_block  = build_sectionhdr(spec.sections);
    auto pagetblhdr_block  = build_pagetblhdr(page_infos, assembled.page_offsets);

    std::vector<uint8_t> bpagetblhdr_block;
    uint32_t binary_count = 0;
    if (has_binary && !assembled.binary_offsets.empty()) {
        binary_count = static_cast<uint32_t>(binary_chunks.size());
        bpagetblhdr_block = build_bpagetblhdr(binary_chunks, assembled.binary_offsets);
    }

    // ---- Calculate absolute offsets for trailer structures ----
    uint32_t sectionhdr_abs  = compressed_data_end_abs;
    uint32_t pagetblhdr_abs  = sectionhdr_abs + static_cast<uint32_t>(sectionhdr_block.size());
    uint32_t bpagetblhdr_abs = pagetblhdr_abs + static_cast<uint32_t>(pagetblhdr_block.size());

    if (verbose) {
        std::cout << "  SECTIONHDR at: 0x" << std::hex << std::uppercase
                  << sectionhdr_abs << std::dec << "\n";
        std::cout << "  PAGETBLHDR at: 0x" << std::hex << std::uppercase
                  << pagetblhdr_abs << std::dec << "\n";
        if (binary_count > 0) {
            std::cout << "  BPAGETBLHDR at: 0x" << std::hex << std::uppercase
                      << bpagetblhdr_abs << std::dec << "\n";
        }
    }

    // ---- Build Table Directory ----
    auto table_dir = build_table_directory(
        static_cast<uint32_t>(total_text_pages),
        static_cast<uint32_t>(spec.sections.size()),
        binary_count,
        sectionhdr_abs,
        pagetblhdr_abs,
        bpagetblhdr_abs,
        spec.template_table_dir
    );

    // ---- Build RPTFILEHDR ----
    auto rptfilehdr = build_rptfilehdr(
        spec.domain_id, spec.species_id, spec.timestamp,
        compressed_data_end_rel
    );

    // ---- Build RPTINSTHDR ----
    auto rptinsthdr = build_rptinsthdr(spec);

    // ---- Final Assembly ----
    std::vector<uint8_t> output;
    size_t total_size = rptfilehdr.size() + rptinsthdr.size() + table_dir.size() +
                        assembled.data.size() + sectionhdr_block.size() +
                        pagetblhdr_block.size() + bpagetblhdr_block.size();
    output.reserve(total_size);

    output.insert(output.end(), rptfilehdr.begin(), rptfilehdr.end());        // 0x000 - 0x0EF (240)
    output.insert(output.end(), rptinsthdr.begin(), rptinsthdr.end());        // 0x0F0 - 0x1CF (224)
    output.insert(output.end(), table_dir.begin(), table_dir.end());          // 0x1D0 - 0x1FF (48)
    output.insert(output.end(), assembled.data.begin(), assembled.data.end()); // 0x200 - ...
    output.insert(output.end(), sectionhdr_block.begin(), sectionhdr_block.end());
    output.insert(output.end(), pagetblhdr_block.begin(), pagetblhdr_block.end());
    if (!bpagetblhdr_block.empty()) {
        output.insert(output.end(), bpagetblhdr_block.begin(), bpagetblhdr_block.end());
    }

    // ---- Write output ----
    {
        fs::path out_path(output_path);
        if (out_path.has_parent_path()) {
            std::error_code ec;
            fs::create_directories(out_path.parent_path(), ec);
        }
    }
    {
        std::ofstream f(output_path, std::ios::binary);
        if (!f) {
            std::cerr << "  ERROR: Cannot write output file: " << output_path << "\n";
            return 0;
        }
        f.write(reinterpret_cast<const char*>(output.data()),
                static_cast<std::streamsize>(output.size()));
    }

    std::cout << "  Built RPT file: " << output_path
              << " (" << format_number(output.size()) << " bytes)\n";
    std::cout << "  Pages: " << total_text_pages
              << ", Sections: " << spec.sections.size()
              << ", Binary objects: " << binary_count << "\n";

    return output.size();
}

// ============================================================================
// Verification
// ============================================================================

static bool verify_rpt(const std::string& output_path, bool verbose) {
    // Read header area
    std::ifstream f(output_path, std::ios::binary);
    if (!f) {
        std::cerr << "  VERIFY FAIL: Cannot open file\n";
        return false;
    }

    std::vector<uint8_t> header_data(0x200);
    f.read(reinterpret_cast<char*>(header_data.data()), 0x200);
    auto bytes_read = f.gcount();
    if (bytes_read < 0x200) {
        std::cerr << "  VERIFY FAIL: File too small\n";
        return false;
    }

    auto hdr_opt = parse_rpt_header(header_data.data(), header_data.size());
    if (!hdr_opt) {
        std::cerr << "  VERIFY FAIL: Not a valid RPT file\n";
        return false;
    }

    if (verbose) {
        std::cout << "\n  Verification:\n";
        std::cout << "    Domain: " << hdr_opt->domain_id
                  << ", Species: " << hdr_opt->report_species_id << "\n";
        std::cout << "    Timestamp: " << hdr_opt->timestamp << "\n";
        std::cout << "    Pages: " << hdr_opt->page_count
                  << ", Sections: " << hdr_opt->section_count << "\n";
        std::cout << "    Binary objects: " << hdr_opt->binary_object_count << "\n";
    }

    // Verify sections
    auto [shdr_opt, sections] = read_sectionhdr(output_path);
    if (verbose) {
        std::cout << "    Sections read back: " << sections.size() << "\n";
        for (const auto& s : sections) {
            std::cout << "      Section " << s.section_id
                      << ": pages " << s.start_page
                      << "-" << (s.start_page + s.page_count - 1) << "\n";
        }
    }

    // Try to decompress first page to verify zlib streams work
    if (hdr_opt->page_count > 0) {
        // Read full file for page table parsing
        auto file_data = read_file(output_path);
        if (file_data.size() >= 0x200) {
            // Find PAGETBLHDR marker
            const char marker[] = "PAGETBLHDR";
            const uint8_t* mp = find_marker(file_data.data(), file_data.size(), marker, 10);
            if (mp) {
                size_t entry_start = (mp - file_data.data()) + 13;
                if (entry_start + 24 <= file_data.size()) {
                    const uint8_t* p = file_data.data() + entry_start;
                    uint32_t page_offset       = read_u32(p);
                    uint32_t uncompressed_size = read_u32(p + 12);
                    uint32_t compressed_size   = read_u32(p + 16);

                    uint32_t abs_off = page_offset + RPTINSTHDR_OFFSET;
                    if (static_cast<size_t>(abs_off) + compressed_size <= file_data.size() &&
                        uncompressed_size > 0 && compressed_size > 0) {
                        auto decompressed = zlib_decompress(
                            file_data.data() + abs_off, compressed_size, uncompressed_size);
                        if (decompressed.empty()) {
                            std::cerr << "  VERIFY FAIL: Could not decompress first page\n";
                            return false;
                        }
                        if (verbose) {
                            // Show preview of first page
                            size_t preview_len = std::min(decompressed.size(), (size_t)80);
                            std::string preview(decompressed.begin(),
                                                decompressed.begin() + preview_len);
                            // Replace non-printable chars
                            for (auto& c : preview) {
                                if (c < 0x20 && c != '\n' && c != '\r' && c != '\t') c = '.';
                            }
                            std::cout << "    First page preview: " << preview << "...\n";
                        }
                    }
                }
            }
        }
    }

    if (verbose) {
        std::cout << "    Verification: PASSED\n";
    }
    return true;
}

// ============================================================================
// Section CSV Parsing
// ============================================================================

static std::vector<SectionDef> parse_section_csv(const std::string& csv_path,
                                                  int& species_id) {
    std::vector<SectionDef> sections;

    std::ifstream f(csv_path);
    if (!f) {
        std::cerr << "ERROR: Cannot read section CSV: " << csv_path << "\n";
        return sections;
    }

    // Read header line
    std::string header_line;
    if (!std::getline(f, header_line)) {
        std::cerr << "ERROR: Empty CSV file: " << csv_path << "\n";
        return sections;
    }

    // Parse header to find column indices
    std::vector<std::string> headers;
    {
        std::istringstream ss(header_line);
        std::string col;
        while (std::getline(ss, col, ',')) {
            // Trim whitespace
            size_t start = col.find_first_not_of(" \t\r\n");
            size_t end   = col.find_last_not_of(" \t\r\n");
            if (start != std::string::npos) {
                col = col.substr(start, end - start + 1);
            }
            headers.push_back(col);
        }
    }

    // Find required column indices
    int col_section_id = -1, col_start_page = -1, col_pages = -1, col_species = -1;
    for (int i = 0; i < static_cast<int>(headers.size()); ++i) {
        if (headers[i] == "Section_Id") col_section_id = i;
        else if (headers[i] == "Start_Page") col_start_page = i;
        else if (headers[i] == "Pages") col_pages = i;
        else if (headers[i] == "Report_Species_Id") col_species = i;
    }

    if (col_section_id < 0 || col_start_page < 0 || col_pages < 0) {
        std::cerr << "ERROR: CSV missing required columns (Section_Id, Start_Page, Pages)\n";
        std::cerr << "  Expected: Report_Species_Id,Section_Id,Start_Page,Pages\n";
        return sections;
    }

    // Parse data rows
    std::string line;
    int row_num = 1;
    bool first_data_row = true;
    while (std::getline(f, line)) {
        ++row_num;
        // Trim
        size_t start = line.find_first_not_of(" \t\r\n");
        if (start == std::string::npos) continue;

        std::vector<std::string> cols;
        {
            std::istringstream ss(line);
            std::string val;
            while (std::getline(ss, val, ',')) {
                size_t vs = val.find_first_not_of(" \t\r\n");
                size_t ve = val.find_last_not_of(" \t\r\n");
                if (vs != std::string::npos) {
                    val = val.substr(vs, ve - vs + 1);
                } else {
                    val.clear();
                }
                cols.push_back(val);
            }
        }

        int max_col = std::max({col_section_id, col_start_page, col_pages});
        if (static_cast<int>(cols.size()) <= max_col) {
            std::cerr << "ERROR: Invalid CSV row " << row_num << ": not enough columns\n";
            continue;
        }

        try {
            uint32_t sid = static_cast<uint32_t>(std::stoul(cols[col_section_id]));
            uint32_t sp  = static_cast<uint32_t>(std::stoul(cols[col_start_page]));
            uint32_t pc  = static_cast<uint32_t>(std::stoul(cols[col_pages]));
            sections.push_back({sid, sp, pc});

            // Auto-override species from first row if species is at default (0)
            if (first_data_row && species_id == 0 && col_species >= 0 &&
                col_species < static_cast<int>(cols.size())) {
                try {
                    int csv_species = std::stoi(cols[col_species]);
                    if (csv_species != 0) {
                        species_id = csv_species;
                        std::cout << "  Using species " << csv_species << " from CSV\n";
                    }
                } catch (...) {}
            }
            first_data_row = false;
        } catch (const std::exception& e) {
            std::cerr << "ERROR: Invalid CSV row " << row_num << ": " << e.what() << "\n";
        }
    }

    return sections;
}

// ============================================================================
// Input Collection
// ============================================================================

static BuildSpec collect_inputs(
    const std::vector<std::string>& input_files,
    int species_id, int domain_id,
    const std::string& timestamp_arg,
    const std::string& binary_arg,
    const std::string& object_header_arg,
    const std::vector<std::string>& section_specs,
    const std::string& section_csv,
    const std::optional<int>& line_width,
    const std::optional<int>& lines_per_page,
    const std::string& template_path) {

    BuildSpec spec;
    spec.species_id = species_id;
    spec.domain_id  = domain_id;
    spec.timestamp  = timestamp_arg.empty() ? generate_timestamp() : timestamp_arg;

    if (line_width.has_value()) spec.line_width_override = *line_width;
    if (lines_per_page.has_value()) spec.lines_per_page_override = *lines_per_page;

    // Load template RPTINSTHDR if provided
    if (!template_path.empty()) {
        if (!fs::exists(template_path)) {
            std::cerr << "ERROR: Template file not found: " << template_path << "\n";
            std::exit(1);
        }
        std::ifstream tf(template_path, std::ios::binary);
        std::vector<uint8_t> tpl_data(COMPRESSED_START);
        tf.read(reinterpret_cast<char*>(tpl_data.data()), COMPRESSED_START);
        auto bytes_read = static_cast<size_t>(tf.gcount());
        if (bytes_read >= COMPRESSED_START) {
            spec.template_rptinsthdr = std::vector<uint8_t>(
                tpl_data.begin() + RPTINSTHDR_OFFSET,
                tpl_data.begin() + RPTINSTHDR_OFFSET + RPTINSTHDR_SIZE);
            spec.template_table_dir = std::vector<uint8_t>(
                tpl_data.begin() + RPTINSTHDR_OFFSET + RPTINSTHDR_SIZE,
                tpl_data.begin() + COMPRESSED_START);
        }
    }

    // Collect text pages
    std::vector<std::vector<uint8_t>> text_pages;
    std::string binary_file = binary_arg;
    std::string object_header_file = object_header_arg;

    if (input_files.size() == 1 && fs::is_directory(input_files[0])) {
        // Directory mode: scan for page_NNNNN.txt, object_header.txt, *.pdf, *.afp
        std::string directory = input_files[0];

        // Collect page_*.txt files, sorted
        std::vector<std::string> page_files;
        for (const auto& entry : fs::directory_iterator(directory)) {
            if (!entry.is_regular_file()) continue;
            std::string fname = entry.path().filename().string();
            if (fname.size() >= 9 && fname.substr(0, 5) == "page_" &&
                fname.substr(fname.size() - 4) == ".txt") {
                page_files.push_back(entry.path().string());
            }
        }
        std::sort(page_files.begin(), page_files.end());

        std::string obj_header_path = (fs::path(directory) / "object_header.txt").string();

        // Auto-detect binary file if not specified
        if (binary_file.empty()) {
            for (const auto& entry : fs::directory_iterator(directory)) {
                if (!entry.is_regular_file()) continue;
                std::string ext = entry.path().extension().string();
                // Case-insensitive check for .pdf or .afp
                std::string ext_lower;
                for (char c : ext) ext_lower += static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
                if (ext_lower == ".pdf" || ext_lower == ".afp") {
                    binary_file = entry.path().string();
                    break;
                }
            }
        }

        // Load object header if present and binary file exists
        if (fs::exists(obj_header_path) && !binary_file.empty()) {
            if (object_header_file.empty()) {
                object_header_file = obj_header_path;
            }
        }

        if (page_files.empty()) {
            std::cerr << "ERROR: No page_*.txt files found in " << directory << "\n";
            std::exit(1);
        }

        for (const auto& pf : page_files) {
            auto data = read_file(pf);
            text_pages.push_back(std::move(data));
        }
    } else {
        // Individual file mode: collect .txt files in order
        for (const auto& fpath : input_files) {
            if (!fs::exists(fpath)) {
                std::cerr << "ERROR: Input file not found: " << fpath << "\n";
                std::exit(1);
            }
            std::string ext = fs::path(fpath).extension().string();
            std::string ext_lower;
            for (char c : ext) ext_lower += static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
            if (ext_lower == ".txt") {
                auto data = read_file(fpath);
                text_pages.push_back(std::move(data));
            }
            // Skip non-txt files (binary files should use --binary flag)
        }
    }

    if (text_pages.empty()) {
        std::cerr << "ERROR: At least 1 text page required\n";
        std::exit(1);
    }

    // Load object header
    if (!object_header_file.empty()) {
        if (!fs::exists(object_header_file)) {
            std::cerr << "ERROR: Object header file not found: " << object_header_file << "\n";
            std::exit(1);
        }
        spec.object_header_page = read_file(object_header_file);
    }

    // Binary file
    if (!binary_file.empty()) {
        if (!fs::exists(binary_file)) {
            std::cerr << "ERROR: Binary file not found: " << binary_file << "\n";
            std::exit(1);
        }
        spec.binary_file = binary_file;
        // Generate object header if not provided
        if (!spec.object_header_page.has_value()) {
            spec.object_header_page = generate_object_header(binary_file);
        }
    }

    spec.text_pages = std::move(text_pages);

    // Parse section specifications
    if (!section_specs.empty()) {
        for (const auto& sec_spec : section_specs) {
            // Format: "SECTION_ID:START_PAGE:PAGE_COUNT"
            std::vector<std::string> parts;
            {
                std::istringstream ss(sec_spec);
                std::string part;
                while (std::getline(ss, part, ':')) {
                    parts.push_back(part);
                }
            }
            if (parts.size() != 3) {
                std::cerr << "ERROR: Invalid section spec: " << sec_spec
                          << " (expected SECTION_ID:START_PAGE:PAGE_COUNT)\n";
                std::exit(1);
            }
            try {
                uint32_t sid = static_cast<uint32_t>(std::stoul(parts[0]));
                uint32_t sp  = static_cast<uint32_t>(std::stoul(parts[1]));
                uint32_t pc  = static_cast<uint32_t>(std::stoul(parts[2]));
                spec.sections.push_back({sid, sp, pc});
            } catch (...) {
                std::cerr << "ERROR: Invalid section spec values: " << sec_spec << "\n";
                std::exit(1);
            }
        }
    } else if (!section_csv.empty()) {
        spec.sections = parse_section_csv(section_csv, spec.species_id);
        if (spec.sections.empty()) {
            std::cerr << "ERROR: No sections found in CSV: " << section_csv << "\n";
            std::exit(1);
        }
        std::cout << "  Loaded " << spec.sections.size()
                  << " sections from " << section_csv << "\n";
    } else {
        // Default: single section covering all pages
        uint32_t total_pages = static_cast<uint32_t>(spec.text_pages.size());
        if (!spec.binary_file.empty() && spec.object_header_page.has_value()) {
            total_pages += 1;  // Object Header is page 1
        }
        spec.sections.push_back({0, 1, total_pages});
    }

    return spec;
}

// ============================================================================
// CLI: help text
// ============================================================================

static void print_help(const char* prog) {
    std::cout <<
"Usage: " << prog << " [options] -o <output.RPT> <input_files...>\n"
"\n"
"Create IntelliSTOR .RPT files from text pages and optional PDF/AFP.\n"
"\n"
"Options:\n"
"  -o, --output <file>       Output .RPT file path (required)\n"
"  --species <id>            Report species ID (default: 0)\n"
"  --domain <id>             Domain ID (default: 1)\n"
"  --timestamp <ts>          Report timestamp (default: current time)\n"
"                            Format: \"YYYY/MM/DD HH:MM:SS.mmm\"\n"
"  --binary <file>           Path to PDF or AFP file to embed as binary object\n"
"  --object-header <file>    Path to text file for Object Header page (page 1)\n"
"  --section <spec>          Section spec: \"SECTION_ID:START_PAGE:PAGE_COUNT\"\n"
"                            (can repeat)\n"
"  --section-csv <file>      CSV file with sections (Report_Species_Id,Section_Id,\n"
"                            Start_Page,Pages). Alternative to repeating --section.\n"
"  --line-width <n>          Override line width for all pages\n"
"  --lines-per-page <n>      Override lines per page for all pages\n"
"  --template <file>         Reference .RPT file to copy RPTINSTHDR metadata from\n"
"  --info                    Dry run: show what would be built without writing\n"
"  --verbose, -v             Show detailed build progress\n"
"  --help, -h                Show this help\n"
"\n"
"Input:\n"
"  Provide either a directory containing page_NNNNN.txt files, or individual\n"
"  text file paths. In directory mode, binary files (*.pdf, *.afp) and\n"
"  object_header.txt are auto-detected.\n"
"\n"
"Examples:\n"
"  # Build text-only RPT from page files\n"
"  " << prog << " --species 49626 --domain 1 \\\n"
"    -o output.RPT page_00001.txt page_00002.txt\n"
"\n"
"  # Build from a directory of extracted pages\n"
"  " << prog << " --species 49626 -o output.RPT ./extracted/260271NL/\n"
"\n"
"  # Build RPT with embedded PDF\n"
"  " << prog << " --species 52759 --domain 1 \\\n"
"    --binary HKCIF001_016_20280309.PDF \\\n"
"    -o output.RPT object_header.txt page_00002.txt\n"
"\n"
"  # Build with template (roundtrip)\n"
"  " << prog << " --template original.RPT \\\n"
"    --species 49626 -o rebuilt.RPT ./extracted/original/\n"
"\n"
"  # Build RPT with multiple sections\n"
"  " << prog << " --species 12345 \\\n"
"    --section 14259:1:10 --section 14260:11:5 \\\n"
"    -o output.RPT page_*.txt\n"
"\n"
"  # Build RPT with sections from CSV (exported by rpt_page_extractor --export-sections)\n"
"  " << prog << " --section-csv sections.csv \\\n"
"    -o output.RPT ./extracted/260271NL/\n";
}

// ============================================================================
// main
// ============================================================================

int main(int argc, char* argv[]) {
    if (argc < 2) {
        print_help(argv[0]);
        return 1;
    }

    // Parse arguments
    int species_id = 0;
    int domain_id  = 1;
    std::string timestamp_arg;
    std::string binary_arg;
    std::string object_header_arg;
    std::vector<std::string> section_specs;
    std::string section_csv;
    std::optional<int> line_width;
    std::optional<int> lines_per_page;
    std::string template_path;
    std::string output_path;
    bool info_only = false;
    bool verbose   = false;
    std::vector<std::string> input_files;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];

        if (arg == "--help" || arg == "-h") {
            print_help(argv[0]);
            return 0;
        }
        else if (arg == "--species") {
            if (i + 1 >= argc) {
                std::cerr << "Error: --species requires an argument\n";
                return 1;
            }
            try {
                species_id = std::stoi(argv[++i]);
            } catch (...) {
                std::cerr << "Error: Invalid species ID: " << argv[i] << "\n";
                return 1;
            }
        }
        else if (arg == "--domain") {
            if (i + 1 >= argc) {
                std::cerr << "Error: --domain requires an argument\n";
                return 1;
            }
            try {
                domain_id = std::stoi(argv[++i]);
            } catch (...) {
                std::cerr << "Error: Invalid domain ID: " << argv[i] << "\n";
                return 1;
            }
        }
        else if (arg == "--timestamp") {
            if (i + 1 >= argc) {
                std::cerr << "Error: --timestamp requires an argument\n";
                return 1;
            }
            timestamp_arg = argv[++i];
        }
        else if (arg == "--binary") {
            if (i + 1 >= argc) {
                std::cerr << "Error: --binary requires an argument\n";
                return 1;
            }
            binary_arg = argv[++i];
        }
        else if (arg == "--object-header") {
            if (i + 1 >= argc) {
                std::cerr << "Error: --object-header requires an argument\n";
                return 1;
            }
            object_header_arg = argv[++i];
        }
        else if (arg == "--section") {
            if (i + 1 >= argc) {
                std::cerr << "Error: --section requires an argument\n";
                return 1;
            }
            section_specs.push_back(argv[++i]);
        }
        else if (arg == "--section-csv") {
            if (i + 1 >= argc) {
                std::cerr << "Error: --section-csv requires an argument\n";
                return 1;
            }
            section_csv = argv[++i];
        }
        else if (arg == "--line-width") {
            if (i + 1 >= argc) {
                std::cerr << "Error: --line-width requires an argument\n";
                return 1;
            }
            try {
                line_width = std::stoi(argv[++i]);
            } catch (...) {
                std::cerr << "Error: Invalid line width: " << argv[i] << "\n";
                return 1;
            }
        }
        else if (arg == "--lines-per-page") {
            if (i + 1 >= argc) {
                std::cerr << "Error: --lines-per-page requires an argument\n";
                return 1;
            }
            try {
                lines_per_page = std::stoi(argv[++i]);
            } catch (...) {
                std::cerr << "Error: Invalid lines per page: " << argv[i] << "\n";
                return 1;
            }
        }
        else if (arg == "--template") {
            if (i + 1 >= argc) {
                std::cerr << "Error: --template requires an argument\n";
                return 1;
            }
            template_path = argv[++i];
        }
        else if (arg == "-o" || arg == "--output") {
            if (i + 1 >= argc) {
                std::cerr << "Error: " << arg << " requires an argument\n";
                return 1;
            }
            output_path = argv[++i];
        }
        else if (arg == "--info") {
            info_only = true;
        }
        else if (arg == "--verbose" || arg == "-v") {
            verbose = true;
        }
        else if (arg[0] == '-') {
            std::cerr << "Error: Unknown option: " << arg << "\n";
            return 1;
        }
        else {
            input_files.push_back(arg);
        }
    }

    // Validate
    if (output_path.empty() && !info_only) {
        std::cerr << "Error: Output path required (-o / --output)\n";
        return 1;
    }
    if (!section_specs.empty() && !section_csv.empty()) {
        std::cerr << "Error: Cannot use both --section and --section-csv\n";
        return 1;
    }
    if (!section_csv.empty() && !fs::exists(section_csv)) {
        std::cerr << "Error: Section CSV file not found: " << section_csv << "\n";
        return 1;
    }
    if (input_files.empty()) {
        std::cerr << "Error: At least one input file or directory required\n";
        return 1;
    }

    // Collect inputs
    auto spec = collect_inputs(input_files, species_id, domain_id,
                               timestamp_arg, binary_arg, object_header_arg,
                               section_specs, section_csv,
                               line_width, lines_per_page, template_path);

    if (info_only) {
        std::cout << "\nBuild plan:\n";
        std::cout << "  Species: " << spec.species_id
                  << ", Domain: " << spec.domain_id << "\n";
        std::cout << "  Timestamp: " << spec.timestamp << "\n";
        std::cout << "  Text pages: " << spec.text_pages.size() << "\n";
        if (!spec.binary_file.empty()) {
            std::error_code ec;
            auto bin_size = fs::file_size(spec.binary_file, ec);
            std::cout << "  Binary file: " << spec.binary_file
                      << " (" << format_number(bin_size) << " bytes)\n";
            if (spec.object_header_page.has_value()) {
                std::cout << "  Object Header: "
                          << spec.object_header_page->size() << " bytes\n";
            }
        }
        std::cout << "  Sections: " << spec.sections.size() << "\n";
        for (const auto& s : spec.sections) {
            std::cout << "    " << s.section_id << ": pages " << s.start_page
                      << "-" << (s.start_page + s.page_count - 1) << "\n";
        }
        std::cout << "  Template: "
                  << (spec.template_rptinsthdr.has_value() ? "yes" : "no") << "\n";
        std::cout << "  Output: " << output_path << "\n";
        return 0;
    }

    // Build
    std::cout << "\nBuilding RPT file: " << output_path << "\n";
    size_t file_size = build_rpt(spec, output_path, verbose);
    if (file_size == 0) {
        return 1;
    }

    // Verify
    verify_rpt(output_path, verbose);

    return 0;
}
