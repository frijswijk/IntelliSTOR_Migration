// papyrus_rpt_page_extractor.cpp - RPT extractor with QPDF library integration
//
// Standalone C++17 CLI tool for Papyrus shell method calls with enhanced watermark support.
// Links QPDF as a C++ library - zero external process calls, fully self-contained.
//
// Compile: See compile.bat (requires QPDF development files)
//
// Usage: papyrus_rpt_page_extractor.exe <input_rpt> <selection_rule> <output_txt> <output_binary> [watermark_options]
//
// Selection rule formats:
//   - "all": All pages
//   - "pages:1-5": Pages 1-5
//   - "pages:1-5,10-20": Multiple page ranges
//   - "sections:14259": Single section
//   - "sections:14259,14260,14261": Multiple sections
//   - "14259,14260": Shorthand for sections (comma-separated numbers without prefix)
//
// Watermark options (all optional, no watermark if not provided):
//   --WatermarkImage <path>       - Path to watermark image (PNG, JPG, etc.)
//   --WatermarkPosition <pos>     - Position: Center, TopLeft, TopCenter, TopRight,
//                                   MiddleLeft, MiddleRight, BottomLeft, BottomCenter,
//                                   BottomRight, Repeat, Tiling (default: Center)
//   --WatermarkRotation <degrees> - Rotation angle: -180 to 180 degrees (default: 0)
//   --WatermarkOpacity <percent>  - Opacity: 0 to 100% (default: 30)
//   --WatermarkScale <scale>      - Scale factor: 0.5 to 2.0 (default: 1.0)
//
// Examples:
//   Basic extraction (no watermark):
//     papyrus_rpt_page_extractor.exe input.rpt all output.txt output.pdf
//
//   With centered watermark at 30% opacity:
//     papyrus_rpt_page_extractor.exe input.rpt pages:1-10 output.txt output.pdf --WatermarkImage logo.png
//
//   With custom watermark settings:
//     papyrus_rpt_page_extractor.exe input.rpt all output.txt output.pdf --WatermarkImage confidential.png --WatermarkPosition TopRight --WatermarkOpacity 50 --WatermarkRotation 45 --WatermarkScale 0.8
//
// Dependencies:
//   - QPDF library (linked at compile time - no external exe needed)
//   - zlib (for RPT decompression)
//   - stb_image headers (bundled)
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
#include <chrono>
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

#include <process.h>  // _getpid() for parallel-safe temp file naming
#include <zlib.h>

// QPDF library headers
#include <qpdf/QPDF.hh>
#include <qpdf/QPDFJob.hh>
#include <qpdf/QPDFWriter.hh>
#include <qpdf/QPDFPageDocumentHelper.hh>
#include <qpdf/QPDFPageObjectHelper.hh>

#include "afp_parser.h"

namespace fs = std::filesystem;

// ============================================================================
// Constants and Exit Codes
// ============================================================================

static constexpr uint32_t RPTINSTHDR_OFFSET = 0xF0;

// Exit codes
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
// Watermark Configuration
// ============================================================================

enum class WatermarkPosition {
    CENTER,
    TOP_LEFT,
    TOP_CENTER,
    TOP_RIGHT,
    MIDDLE_LEFT,
    MIDDLE_RIGHT,
    BOTTOM_LEFT,
    BOTTOM_CENTER,
    BOTTOM_RIGHT,
    REPEAT,
    TILING
};

struct WatermarkConfig {
    std::string image_path;
    WatermarkPosition position = WatermarkPosition::CENTER;
    int rotation = 0;           // -180 to 180 degrees
    int opacity = 30;           // 0 to 100%
    double scale = 1.0;         // 0.5 to 2.0

    bool is_valid() const {
        return !image_path.empty() && fs::exists(image_path);
    }

    // Convert position enum to gravity string
    static std::string position_to_gravity(WatermarkPosition pos) {
        switch (pos) {
            case WatermarkPosition::CENTER:        return "center";
            case WatermarkPosition::TOP_LEFT:      return "northwest";
            case WatermarkPosition::TOP_CENTER:    return "north";
            case WatermarkPosition::TOP_RIGHT:     return "northeast";
            case WatermarkPosition::MIDDLE_LEFT:   return "west";
            case WatermarkPosition::MIDDLE_RIGHT:  return "east";
            case WatermarkPosition::BOTTOM_LEFT:   return "southwest";
            case WatermarkPosition::BOTTOM_CENTER: return "south";
            case WatermarkPosition::BOTTOM_RIGHT:  return "southeast";
            case WatermarkPosition::REPEAT:        return "center"; // Repeat uses tiling, not gravity
            case WatermarkPosition::TILING:        return "tiling"; // Grid pattern
            default:                               return "center";
        }
    }

    static WatermarkPosition parse_position(const std::string& pos_str) {
        std::string pos_lower = pos_str;
        std::transform(pos_lower.begin(), pos_lower.end(), pos_lower.begin(), ::tolower);

        if (pos_lower == "center") return WatermarkPosition::CENTER;
        if (pos_lower == "topleft") return WatermarkPosition::TOP_LEFT;
        if (pos_lower == "topcenter") return WatermarkPosition::TOP_CENTER;
        if (pos_lower == "topright") return WatermarkPosition::TOP_RIGHT;
        if (pos_lower == "middleleft") return WatermarkPosition::MIDDLE_LEFT;
        if (pos_lower == "middleright") return WatermarkPosition::MIDDLE_RIGHT;
        if (pos_lower == "bottomleft" || pos_lower == "leftbottom") return WatermarkPosition::BOTTOM_LEFT;
        if (pos_lower == "bottomcenter") return WatermarkPosition::BOTTOM_CENTER;
        if (pos_lower == "bottomright" || pos_lower == "rightbottom") return WatermarkPosition::BOTTOM_RIGHT;
        if (pos_lower == "repeat") return WatermarkPosition::REPEAT;
        if (pos_lower == "tiling") return WatermarkPosition::TILING;

        return WatermarkPosition::CENTER; // default
    }
};

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
                rule.section_ids.push_back(std::stoul(token));
            }
        }
        return rule;
    }

    if (is_number_list) {
        // Bare number: "2" -> pages:2
        rule.mode = SelectionMode::PAGES;
        int p = std::stoi(rule_str);
        rule.page_ranges.push_back({p, p});
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
                rule.section_ids.push_back(std::stoul(sid_str));
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
                        const std::vector<uint32_t>& section_ids) {
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
// Lean Watermarking using stb_image (minimal external dependencies)
// ============================================================================

#include "watermark_lean.h"

// ============================================================================
// PDF Page Size Detection using QPDF Library
// ============================================================================

struct PageSize {
    int width = 612;   // Letter default
    int height = 792;
};

static PageSize get_pdf_page_size(const std::string& pdf_path) {
    PageSize size;
    try {
        QPDF qpdf;
        qpdf.processFile(pdf_path.c_str());
        QPDFPageDocumentHelper dh(qpdf);
        auto pages = dh.getAllPages();
        if (pages.empty()) return size;

        // Get first page's MediaBox
        auto page_obj = pages[0].getObjectHandle();
        auto mediabox = page_obj.getKey("/MediaBox");
        if (mediabox.isArray() && mediabox.getArrayNItems() >= 4) {
            int x0 = static_cast<int>(mediabox.getArrayItem(0).getNumericValue());
            int y0 = static_cast<int>(mediabox.getArrayItem(1).getNumericValue());
            int x1 = static_cast<int>(mediabox.getArrayItem(2).getNumericValue());
            int y1 = static_cast<int>(mediabox.getArrayItem(3).getNumericValue());
            int w = x1 - x0;
            int h = y1 - y0;

            // Check for /Rotate — swap width/height for 90/270
            int rotate = 0;
            auto rotate_obj = page_obj.getKey("/Rotate");
            if (rotate_obj.isInteger()) {
                rotate = static_cast<int>(rotate_obj.getIntValue());
            }
            if (rotate == 90 || rotate == 270 || rotate == -90 || rotate == -270) {
                std::swap(w, h);
            }

            if (w > 0 && h > 0) {
                size.width = w;
                size.height = h;
            }
        }
    } catch (const std::exception& e) {
        std::cerr << "WARNING: Could not read PDF page size: " << e.what() << "\n";
    }
    return size;
}

// ============================================================================
// PDF Page Extraction using QPDF Library
// ============================================================================

static bool extract_pdf_pages(const std::string& input_pdf,
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

    try {
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

        // Use QPDFJob to extract pages (equivalent to: qpdf input --pages . range -- output)
        QPDFJob j;
        auto c = j.config();
        c->inputFile(input_pdf);
        c->outputFile(output_pdf);
        c->pages()->pageSpec(".", page_spec.str())->endPages();
        c->checkConfiguration();
        j.run();

        return true;
    } catch (const std::exception& e) {
        std::cerr << "ERROR: QPDF page extraction failed: " << e.what() << "\n";
        return false;
    }
}

// ============================================================================
// AFP Page Extraction using AFPSplitter Library
// ============================================================================

static bool extract_afp_pages(const std::string& input_afp,
                              const std::string& output_afp,
                              const std::vector<int>& pages) {
    if (pages.empty()) {
        // No filtering - just copy the AFP as-is (ALL mode)
        try {
            fs::copy(input_afp, output_afp, fs::copy_options::overwrite_existing);
            return true;
        } catch (...) {
            return false;
        }
    }

    try {
        AFPSplitter splitter;
        if (!splitter.loadFile(input_afp)) {
            std::cerr << "ERROR: AFP load failed: " << splitter.getLastError() << "\n";
            return false;
        }

        // Build PageRange vector from page numbers
        std::vector<PageRange> ranges;
        size_t i = 0;
        while (i < pages.size()) {
            int range_start = pages[i];
            int range_end = range_start;
            while (i + 1 < pages.size() && pages[i + 1] == pages[i] + 1) {
                ++i;
                range_end = pages[i];
            }
            ranges.push_back(PageRange(range_start, range_end));
            ++i;
        }

        if (!splitter.extractPagesWithResources(ranges, output_afp)) {
            std::cerr << "ERROR: AFP page extraction failed: " << splitter.getLastError() << "\n";
            return false;
        }

        return true;
    } catch (const std::exception& e) {
        std::cerr << "ERROR: AFP extraction exception: " << e.what() << "\n";
        return false;
    }
}

// ============================================================================
// Watermark Overlay using QPDF Library
// ============================================================================

static bool apply_watermark_simple(const std::string& input_pdf,
                                   const std::string& output_pdf,
                                   const WatermarkConfig& config) {
    if (!config.is_valid()) {
        std::cerr << "WARNING: Invalid watermark configuration. Skipping watermark.\n";
        try {
            fs::copy(input_pdf, output_pdf, fs::copy_options::overwrite_existing);
            return true;
        } catch (...) {
            return false;
        }
    }

    std::cout << "INFO: Applying watermark (100% C++ - stb_image + QPDF library)...\n";

    // Create temp watermark PDF using pure C++ (no ImageMagick!)
    fs::path output_dir = fs::path(output_pdf).parent_path();
    if (output_dir.empty()) output_dir = fs::current_path();

    auto now = std::chrono::steady_clock::now();
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(now.time_since_epoch()).count();
    auto pid = static_cast<long>(_getpid());
    std::string temp_wm_pdf = (output_dir / ("_wm_" + std::to_string(pid) + "_" + std::to_string(ms) + ".pdf")).string();

    // Read actual page dimensions from input PDF
    PageSize pg = get_pdf_page_size(input_pdf);
    std::cout << "  Target PDF page size: " << pg.width << " x " << pg.height << " points\n";

    // Process watermark and generate PDF (pure C++)
    std::cout << "  Generating watermark PDF (stb_image processing + pure C++ PDF)...\n";

    std::string gravity = WatermarkConfig::position_to_gravity(config.position);

    bool wm_ok = WatermarkLean::create_watermark_pdf(
        config.image_path,
        config.rotation,
        config.opacity,
        config.scale,
        gravity,
        temp_wm_pdf,
        pg.width,
        pg.height
    );

    if (!wm_ok) {
        std::cerr << "ERROR: Failed to create watermark PDF\n";
        try {
            fs::copy(input_pdf, output_pdf, fs::copy_options::overwrite_existing);
        } catch (...) {}
        return false;
    }

    // Use QPDF library to overlay (no external process!)
    std::cout << "  Overlaying with QPDF library...\n";

    bool overlay_ok = false;
    try {
        // Scope the QPDFJob so it releases all file handles before cleanup
        {
            QPDFJob j;
            auto c = j.config();
            c->inputFile(input_pdf);
            c->outputFile(output_pdf);
            c->overlay()->file(temp_wm_pdf)->to("1-z")->repeat("1-z")->endUnderlayOverlay();
            c->checkConfiguration();
            j.run();
        }
        overlay_ok = true;
    } catch (const std::filesystem::filesystem_error& e) {
        // QPDFJob may throw filesystem_error during internal cleanup even when
        // the overlay itself succeeded. Check if output was actually written.
        if (fs::exists(output_pdf) && fs::file_size(output_pdf) > 0) {
            overlay_ok = true;
            std::cerr << "WARNING: QPDF temp cleanup issue (overlay succeeded): " << e.what() << "\n";
        } else {
            std::cerr << "ERROR: QPDF overlay failed: " << e.what() << "\n";
        }
    } catch (const std::exception& e) {
        std::cerr << "ERROR: QPDF overlay failed: " << e.what() << "\n";
    }

    // Clean up temp watermark PDF (retry with error_code to avoid exceptions)
    std::error_code ec;
    fs::remove(temp_wm_pdf, ec);

    if (overlay_ok) {
        std::cout << "INFO: Watermark applied successfully!\n";
        return true;
    } else {
        try {
            fs::copy(input_pdf, output_pdf, fs::copy_options::overwrite_existing);
        } catch (...) {}
        return false;
    }
}

// ============================================================================
// PDF Document Properties
// ============================================================================

static bool set_pdf_metadata(const std::string& pdf_path) {
    std::string temp = pdf_path + ".meta.tmp";
    try {
        QPDF qpdf;
        qpdf.processFile(pdf_path.c_str());

        // Get or create /Info dictionary
        auto trailer = qpdf.getTrailer();
        QPDFObjectHandle info;
        if (trailer.hasKey("/Info") && trailer.getKey("/Info").isDictionary()) {
            info = trailer.getKey("/Info");
        } else {
            info = qpdf.makeIndirectObject(QPDFObjectHandle::newDictionary());
            trailer.replaceKey("/Info", info);
        }

        info.replaceKey("/Producer", QPDFObjectHandle::newString("ISIS Papyrus"));
        info.replaceKey("/Creator", QPDFObjectHandle::newString("Papyrus Content Governance"));

        QPDFWriter writer(qpdf, temp.c_str());
        writer.write();

        // Replace original with metadata-stamped version
        std::error_code ec;
        fs::remove(pdf_path, ec);
        fs::rename(temp, pdf_path, ec);
        if (ec) {
            fs::copy(temp, pdf_path, fs::copy_options::overwrite_existing);
            fs::remove(temp, ec);
        }
        return true;
    } catch (const std::exception& e) {
        std::cerr << "WARNING: Could not set PDF metadata: " << e.what() << "\n";
        std::error_code ec;
        fs::remove(temp, ec);
        return false;
    }
}

// ============================================================================
// Main PDF Processing with Watermark Options
// ============================================================================

static bool process_pdf_with_watermark(const std::string& input_pdf,
                                       const std::string& output_pdf,
                                       const std::vector<int>& pages,
                                       const WatermarkConfig& watermark_config) {
    // Step 1: Extract pages if needed
    std::string temp_extracted = output_pdf + ".temp.pdf";
    if (!extract_pdf_pages(input_pdf, temp_extracted, pages)) {
        std::cerr << "ERROR: Failed to extract PDF pages\n";
        return false;
    }

    // Step 2: Apply watermark if configured
    if (watermark_config.is_valid()) {
        if (!apply_watermark_simple(temp_extracted, output_pdf, watermark_config)) {
            std::cerr << "WARNING: Failed to apply watermark. Using non-watermarked PDF.\n";
        }
        // Cleanup temp file
        fs::remove(temp_extracted);
    } else {
        // No watermark requested
        try {
            fs::rename(temp_extracted, output_pdf);
        } catch (...) {
            fs::copy(temp_extracted, output_pdf, fs::copy_options::overwrite_existing);
            fs::remove(temp_extracted);
        }
    }

    // Step 3: Set document properties (Application + Producer)
    set_pdf_metadata(output_pdf);

    return true;
}

// ============================================================================
// Command-Line Argument Parsing
// ============================================================================

static WatermarkConfig parse_watermark_args(int argc, char* argv[], int start_index) {
    WatermarkConfig config;

    for (int i = start_index; i < argc; ++i) {
        // Normalize: strip leading dashes and lowercase for matching
        std::string arg_normalized = argv[i];
        while (!arg_normalized.empty() && arg_normalized[0] == '-') arg_normalized.erase(0, 1);
        std::transform(arg_normalized.begin(), arg_normalized.end(), arg_normalized.begin(), ::tolower);

        if (arg_normalized == "watermarkimage" && i + 1 < argc) {
            config.image_path = argv[++i];
        }
        else if (arg_normalized == "watermarkposition" && i + 1 < argc) {
            config.position = WatermarkConfig::parse_position(argv[++i]);
        }
        else if (arg_normalized == "watermarkrotation" && i + 1 < argc) {
            int rotation = std::stoi(argv[++i]);
            config.rotation = std::max(-180, std::min(180, rotation));
        }
        else if (arg_normalized == "watermarkopacity" && i + 1 < argc) {
            int opacity = std::stoi(argv[++i]);
            config.opacity = std::max(0, std::min(100, opacity));
        }
        else if (arg_normalized == "watermarkscale" && i + 1 < argc) {
            double scale = std::stod(argv[++i]);
            config.scale = std::max(0.5, std::min(2.0, scale));
        }
    }

    return config;
}

// ============================================================================
// Core extraction logic (shared by normal and export modes)
// ============================================================================

static int extract_rpt(const std::string& input_rpt,
                       const std::string& selection_rule_str,
                       const std::string& output_txt,
                       const std::string& output_binary,
                       const WatermarkConfig& watermark_config,
                       bool export_mode = false,
                       const std::string& export_csv = "") {
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

        // Write CSV if in export mode
        if (export_mode && !export_csv.empty()) {
            std::ofstream csv_out(export_csv);
            if (csv_out) {
                csv_out << "SPECIES_ID,SECTION_ID,START_PAGE,PAGES\n";
                for (const auto& sec : sections) {
                    csv_out << hdr.report_species_id << ","
                            << sec.section_id << ","
                            << sec.start_page << ","
                            << sec.page_count << "\n";
                }
                csv_out.close();
            }
        }

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

            // Detect binary format by reading magic bytes
            bool is_pdf = false;
            bool is_afp = false;
            {
                std::ifstream check(temp_full_binary, std::ios::binary);
                uint8_t magic[256] = {0};
                auto bytes_read = check.read(reinterpret_cast<char*>(magic), sizeof(magic)).gcount();
                is_pdf = (bytes_read >= 4 && std::strncmp(reinterpret_cast<char*>(magic), "%PDF", 4) == 0);
                if (!is_pdf && bytes_read >= 8) {
                    is_afp = AFPUtil::isValidAFP(magic, static_cast<size_t>(bytes_read));
                }
            }

            // In export mode, auto-detect and fix the output extension
            if (export_mode) {
                std::string correct_ext = is_pdf ? ".pdf" : (is_afp ? ".afp" : ".bin");
                fs::path out_path(output_binary);
                if (out_path.extension().string() != correct_ext) {
                    std::string corrected = (out_path.parent_path() / (out_path.stem().string() + correct_ext)).string();
                    // Use the corrected path - but we must update output_binary
                    // Since output_binary is const ref, work with corrected path directly
                    std::string final_binary = corrected;

                    if (is_pdf) {
                        if (rule.mode == SelectionMode::ALL) {
                            process_pdf_with_watermark(temp_full_binary, final_binary, {}, watermark_config);
                        } else {
                            std::vector<int> pdf_pages;
                            for (const auto& entry : selected) pdf_pages.push_back(entry.page_number);
                            process_pdf_with_watermark(temp_full_binary, final_binary, pdf_pages, watermark_config);
                        }
                        fs::remove(temp_full_binary);
                    } else if (is_afp) {
                        std::vector<int> afp_pages;
                        if (rule.mode != SelectionMode::ALL) {
                            for (const auto& entry : selected) afp_pages.push_back(entry.page_number);
                        }
                        if (!extract_afp_pages(temp_full_binary, final_binary, afp_pages)) {
                            try { fs::rename(temp_full_binary, final_binary); }
                            catch (...) { fs::copy(temp_full_binary, final_binary, fs::copy_options::overwrite_existing); fs::remove(temp_full_binary); }
                        } else {
                            fs::remove(temp_full_binary);
                        }
                    } else {
                        try { fs::rename(temp_full_binary, final_binary); }
                        catch (...) { fs::copy(temp_full_binary, final_binary, fs::copy_options::overwrite_existing); fs::remove(temp_full_binary); }
                    }

                    std::cout << "SUCCESS: Extracted " << selected.size() << " pages\n";
                    std::cout << "  TXT:  " << output_txt << "\n";
                    std::cout << "  BIN:  " << final_binary;
                    if (is_pdf) std::cout << " (PDF)";
                    else if (is_afp) std::cout << " (AFP)";
                    std::cout << "\n";
                    if (!export_csv.empty()) std::cout << "  CSV:  " << export_csv << "\n";
                    return EC_SUCCESS;
                }
            }

            if (is_pdf) {
                std::vector<int> pdf_pages;
                for (const auto& entry : selected) {
                    pdf_pages.push_back(entry.page_number);
                }

                if (rule.mode == SelectionMode::ALL) {
                    process_pdf_with_watermark(temp_full_binary, output_binary, {}, watermark_config);
                } else {
                    process_pdf_with_watermark(temp_full_binary, output_binary, pdf_pages, watermark_config);
                }

                fs::remove(temp_full_binary);
            } else if (is_afp) {
                std::vector<int> afp_pages;
                if (rule.mode != SelectionMode::ALL) {
                    for (const auto& entry : selected) {
                        afp_pages.push_back(entry.page_number);
                    }
                }

                if (!extract_afp_pages(temp_full_binary, output_binary, afp_pages)) {
                    try {
                        fs::rename(temp_full_binary, output_binary);
                    } catch (...) {
                        fs::copy(temp_full_binary, output_binary, fs::copy_options::overwrite_existing);
                        fs::remove(temp_full_binary);
                    }
                } else {
                    fs::remove(temp_full_binary);
                }
            } else {
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

            // Detect format of output binary
            std::ifstream check(output_binary, std::ios::binary);
            uint8_t magic[256] = {0};
            auto bytes_read = check.read(reinterpret_cast<char*>(magic), sizeof(magic)).gcount();
            if (bytes_read >= 4) {
                if (std::strncmp(reinterpret_cast<char*>(magic), "%PDF", 4) == 0) {
                    std::cout << " (PDF";
                    if (rule.mode != SelectionMode::ALL) {
                        std::cout << " - " << selected.size() << " pages extracted";
                    }
                    if (watermark_config.is_valid()) {
                        std::cout << " with watermark";
                    }
                    std::cout << ")";
                } else if (bytes_read >= 8 && AFPUtil::isValidAFP(magic, static_cast<size_t>(bytes_read))) {
                    std::cout << " (AFP";
                    if (rule.mode != SelectionMode::ALL) {
                        std::cout << " - " << selected.size() << " pages extracted";
                    }
                    std::cout << ")";
                }
            }
            std::cout << "\n";
        }
        if (export_mode && !export_csv.empty()) {
            std::cout << "  CSV:  " << export_csv << "\n";
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

// ============================================================================
// Export Mode: Single File
// ============================================================================

static int export_single_file(const std::string& input_rpt,
                              const WatermarkConfig& watermark_config) {
    fs::path rpt_path(input_rpt);
    fs::path parent_dir = rpt_path.parent_path();
    if (parent_dir.empty()) parent_dir = fs::current_path();

    fs::path export_dir = parent_dir / "export";
    fs::create_directories(export_dir);

    std::string basename = rpt_path.stem().string();
    std::string output_txt = (export_dir / (basename + ".txt")).string();
    std::string output_binary = (export_dir / (basename + ".bin")).string();  // will be auto-corrected
    std::string export_csv = (export_dir / (basename + ".csv")).string();

    std::cout << "EXPORT: " << rpt_path.filename().string() << "\n";

    return extract_rpt(input_rpt, "all", output_txt, output_binary,
                       watermark_config, true, export_csv);
}

// ============================================================================
// Export Mode: Batch Directory
// ============================================================================

static int export_batch(const std::string& dir_path,
                        const WatermarkConfig& watermark_config) {
    if (!fs::is_directory(dir_path)) {
        std::cerr << "ERROR: Not a directory: " << dir_path << "\n";
        return EC_FILE_NOT_FOUND;
    }

    // Collect all .RPT files
    std::vector<std::string> rpt_files;
    for (const auto& entry : fs::directory_iterator(dir_path)) {
        if (!entry.is_regular_file()) continue;
        std::string ext = entry.path().extension().string();
        std::transform(ext.begin(), ext.end(), ext.begin(), ::tolower);
        if (ext == ".rpt") {
            rpt_files.push_back(entry.path().string());
        }
    }

    if (rpt_files.empty()) {
        std::cerr << "ERROR: No .RPT files found in: " << dir_path << "\n";
        return EC_FILE_NOT_FOUND;
    }

    // Sort for deterministic order
    std::sort(rpt_files.begin(), rpt_files.end());

    // Create export directory
    fs::path export_dir = fs::path(dir_path) / "export";
    fs::create_directories(export_dir);

    // Read progress file (list of already-completed filenames)
    std::string progress_file = (export_dir / "export_progress.txt").string();
    std::set<std::string> completed;
    {
        std::ifstream pf(progress_file);
        std::string line;
        while (std::getline(pf, line)) {
            // Trim whitespace
            size_t start = line.find_first_not_of(" \t\r\n");
            size_t end = line.find_last_not_of(" \t\r\n");
            if (start != std::string::npos) {
                completed.insert(line.substr(start, end - start + 1));
            }
        }
    }

    int total = static_cast<int>(rpt_files.size());
    int processed = 0;
    int skipped = 0;
    int failed = 0;

    std::cout << "BATCH EXPORT: " << total << " RPT files in " << dir_path << "\n";
    if (!completed.empty()) {
        std::cout << "  Resuming: " << completed.size() << " already completed\n";
    }
    std::cout << "\n";

    for (const auto& rpt : rpt_files) {
        std::string filename = fs::path(rpt).filename().string();

        if (completed.count(filename)) {
            skipped++;
            continue;
        }

        std::cout << "--- [" << (processed + skipped + failed + 1) << "/" << total << "] ";

        int rc = export_single_file(rpt, watermark_config);

        if (rc == EC_SUCCESS) {
            processed++;
            // Append to progress file
            std::ofstream pf(progress_file, std::ios::app);
            pf << filename << "\n";
        } else {
            failed++;
            std::cerr << "  FAILED: " << filename << " (exit code " << rc << ")\n";
        }

        std::cout << "\n";
    }

    std::cout << "============================================================================\n";
    std::cout << "BATCH EXPORT SUMMARY\n";
    std::cout << "  Total:     " << total << " files\n";
    std::cout << "  Processed: " << processed << " files\n";
    std::cout << "  Skipped:   " << skipped << " files (already completed)\n";
    if (failed > 0) {
        std::cout << "  Failed:    " << failed << " files\n";
    }
    std::cout << "  Output:    " << export_dir.string() << "\n";
    std::cout << "============================================================================\n";

    return (failed > 0) ? EC_UNKNOWN_ERROR : EC_SUCCESS;
}

// ============================================================================
// Main Entry Point
// ============================================================================

static void print_usage(const char* prog) {
    std::cerr << "Usage:\n";
    std::cerr << "  " << prog << " <input.rpt> <selection_rule> <output_txt> <output_binary> [watermark_options]\n";
    std::cerr << "  " << prog << " <input.rpt> Export [watermark_options]\n";
    std::cerr << "  " << prog << " <directory>  Export [watermark_options]\n";
    std::cerr << "\nRequired Arguments (standard mode):\n";
    std::cerr << "  input_rpt       - Path to input .rpt file\n";
    std::cerr << "  selection_rule  - \"all\", \"pages:1-5\", \"sections:14259,14260\", or \"14259,14260\"\n";
    std::cerr << "  output_txt      - Path to write concatenated text output\n";
    std::cerr << "  output_binary   - Path to write binary output (PDF/AFP)\n";
    std::cerr << "\nExport Mode:\n";
    std::cerr << "  Single file:  Creates export/ subfolder with .txt, .pdf/.afp, .csv\n";
    std::cerr << "  Directory:    Batch processes all .RPT files with restart capability\n";
    std::cerr << "\nWatermark Options (all optional, accepted with or without -- prefix):\n";
    std::cerr << "  WatermarkImage <path>      - Path to watermark image\n";
    std::cerr << "  WatermarkPosition <pos>    - Center, TopLeft, TopCenter, TopRight,\n";
    std::cerr << "                               MiddleLeft, MiddleRight, BottomLeft,\n";
    std::cerr << "                               BottomCenter, BottomRight, Repeat, Tiling\n";
    std::cerr << "  WatermarkRotation <deg>    - Rotation: -180 to 180 degrees (default: 0)\n";
    std::cerr << "  WatermarkOpacity <pct>     - Opacity: 0 to 100% (default: 30)\n";
    std::cerr << "  WatermarkScale <scale>     - Scale: 0.5 to 2.0 (default: 1.0)\n";
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
}

int main(int argc, char* argv[]) {
    if (argc < 3) {
        print_usage(argv[0]);
        return EC_INVALID_ARGS;
    }

    std::string arg1 = argv[1];
    std::string arg2 = argv[2];

    // Check for Export mode
    std::string arg2_lower = arg2;
    std::transform(arg2_lower.begin(), arg2_lower.end(), arg2_lower.begin(), ::tolower);

    if (arg2_lower == "export") {
        // Parse watermark options from argv[3+]
        WatermarkConfig watermark_config = parse_watermark_args(argc, argv, 3);

        if (fs::is_directory(arg1)) {
            // Batch directory export
            return export_batch(arg1, watermark_config);
        } else {
            // Single file export
            return export_single_file(arg1, watermark_config);
        }
    }

    // Standard mode: requires 4 positional args
    if (argc < 5) {
        print_usage(argv[0]);
        return EC_INVALID_ARGS;
    }

    std::string input_rpt = argv[1];
    std::string selection_rule_str = argv[2];
    std::string output_txt = argv[3];
    std::string output_binary = argv[4];

    // Parse watermark options (if provided)
    WatermarkConfig watermark_config = parse_watermark_args(argc, argv, 5);

    return extract_rpt(input_rpt, selection_rule_str, output_txt, output_binary, watermark_config);
}
