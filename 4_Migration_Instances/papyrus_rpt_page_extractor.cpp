// papyrus_rpt_page_extractor.cpp - RPT Page Extractor for Papyrus Integration
//
// Enhanced version supporting:
//   - Binary input (from Papyrus %TMPFILE% macro)
//   - File path input (from SelectionRule or direct path parameter)
//   - Multiple page ranges (e.g., "pages:1-5,10-20,50-60")
//   - Multiple sections (e.g., "sections:14259,14260,14261")
//
// Compile (Windows MSVC):
//   cl.exe /O2 papyrus_rpt_page_extractor.cpp /Fe:papyrus_rpt_page_extractor.exe /link zlib.lib
//
// Compile (macOS/Linux):
//   g++ -std=c++17 -O2 -o papyrus_rpt_page_extractor papyrus_rpt_page_extractor.cpp -lz
//
// Usage (Papyrus Parameter Line):
//   %TMPFILE/InputRptFile/rpt% "%SelectionRule%" %TMPFILE/OutputText/txt% %TMPFILE/OutputBinary/pdf%
//
// Arguments:
//   1. input_rpt_path     - Path to .rpt file (from %TMPFILE% or file path)
//   2. selection_rule     - Selection specification (see Selection Rules below)
//   3. output_txt_path    - Path for concatenated text output
//   4. output_binary_path - Path for binary (PDF/AFP) output
//
// Selection Rules:
//   "all"                              Extract all pages
//   "pages:10-20"                      Extract page range (1-based, inclusive)
//   "pages:1-5,10-20,50-60"            Multiple page ranges (comma-separated)
//   "pages:5"                          Extract single page
//   "section:14259"                    Extract pages for section ID 14259
//   "sections:14259,14260,14261"       Multiple section IDs (comma-separated)
//
// Return Codes:
//   0  - Success
//   1  - Invalid arguments
//   2  - Cannot open input RPT file
//   3  - Cannot write output text file
//   4  - Cannot write output binary file
//   5  - Invalid RPT file format
//   6  - Decompression error
//   7  - No text pages found or extracted
//   8  - Section ID(s) not found
//   9  - Invalid selection rule format
//   10 - Unknown error
//

#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <optional>
#include <set>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

#include <zlib.h>

namespace fs = std::filesystem;

// ============================================================================
// Constants
// ============================================================================

static constexpr uint32_t RPTINSTHDR_OFFSET = 0xF0;
static constexpr bool ENABLE_LOGGING = false;

// ============================================================================
// Logging Utility
// ============================================================================

static void log_debug(const std::string& msg) {
    if (ENABLE_LOGGING) {
        std::cerr << "[DEBUG] " << msg << "\n";
    }
}

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
    uint32_t page_table_offset     = 0;
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
// Little-endian Helpers
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

// ============================================================================
// File I/O Utilities
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
// RPT Header Parsing
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

// ============================================================================
// Section Table Reading
// ============================================================================

static std::vector<SectionEntry>
read_sectionhdr(const std::vector<uint8_t>& file_data, uint32_t section_data_offset) {
    std::vector<SectionEntry> sections;

    const char marker[] = "SECTIONHDR";
    constexpr size_t marker_len = 10;

    if (section_data_offset > 0) {
        size_t scan_start = (section_data_offset > 16) ? section_data_offset - 16 : 0;
        size_t scan_len   = std::min((size_t)4096, file_data.size() - scan_start);
        const uint8_t* region = file_data.data() + scan_start;

        const uint8_t* mp = find_marker(region, scan_len, marker, marker_len);
        if (mp) {
            size_t data_start = (mp - region) + 13;
            const uint8_t* triplet_base = region + data_start;
            size_t triplet_avail = scan_len - data_start;

            uint32_t count = std::min((uint32_t)(triplet_avail / 12), (uint32_t)1000);
            for (uint32_t i = 0; i < count; ++i) {
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
            if (!sections.empty()) return sections;
        }
    }

    const uint8_t* mp = find_marker(file_data.data(), file_data.size(), marker, marker_len);
    if (!mp) return sections;

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

    return sections;
}

// ============================================================================
// Page Table Reading
// ============================================================================

static std::vector<PageTableEntry>
read_page_table(const std::vector<uint8_t>& file_data, uint32_t page_count) {
    std::vector<PageTableEntry> entries;

    const char marker[] = "PAGETBLHDR";
    constexpr size_t marker_len = 10;

    const uint8_t* mp = find_marker(file_data.data(), file_data.size(), marker, marker_len);
    if (!mp) return entries;

    size_t entry_start = (mp - file_data.data()) + 13;
    constexpr size_t entry_size = 24;

    entries.reserve(page_count);
    for (uint32_t i = 0; i < page_count; ++i) {
        size_t offset = entry_start + i * entry_size;
        if (offset + entry_size > file_data.size()) break;

        const uint8_t* p = file_data.data() + offset;
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

// ============================================================================
// Page Decompression
// ============================================================================

static std::vector<std::pair<int, std::vector<uint8_t>>>
decompress_pages(const std::string& filepath,
                 const std::vector<PageTableEntry>& entries) {
    std::vector<std::pair<int, std::vector<uint8_t>>> results;

    std::ifstream f(filepath, std::ios::binary | std::ios::ate);
    if (!f) return results;
    auto file_size = static_cast<size_t>(f.tellg());

    results.reserve(entries.size());
    for (const auto& entry : entries) {
        uint32_t abs_off = entry.absolute_offset();
        if (static_cast<size_t>(abs_off) + entry.compressed_size > file_size) {
            log_debug("Page " + std::to_string(entry.page_number) + " exceeds file size");
            continue;
        }

        std::vector<uint8_t> compressed(entry.compressed_size);
        f.seekg(abs_off);
        f.read(reinterpret_cast<char*>(compressed.data()), entry.compressed_size);

        uLongf dest_len = entry.uncompressed_size;
        std::vector<uint8_t> decompressed(dest_len);

        int ret = uncompress(decompressed.data(), &dest_len,
                             compressed.data(),
                             static_cast<uLong>(entry.compressed_size));
        if (ret != Z_OK) {
            log_debug("Page " + std::to_string(entry.page_number) + " decompression failed");
            continue;
        }
        decompressed.resize(dest_len);
        results.emplace_back(entry.page_number, std::move(decompressed));
    }

    return results;
}

// ============================================================================
// Binary Object Table Reading
// ============================================================================

static std::vector<BinaryObjectEntry>
read_binary_page_table(const std::vector<uint8_t>& file_data, uint32_t count) {
    std::vector<BinaryObjectEntry> entries;
    if (count == 0) return entries;

    const char marker[] = "BPAGETBLHDR";
    constexpr size_t marker_len = 11;

    const uint8_t* mp = find_marker(file_data.data(), file_data.size(), marker, marker_len);
    if (!mp) return entries;

    size_t entry_start = (mp - file_data.data()) + 13;
    constexpr size_t entry_size = 16;

    entries.reserve(count);
    for (uint32_t i = 0; i < count; ++i) {
        size_t offset = entry_start + i * entry_size;
        if (offset + entry_size > file_data.size()) break;

        const uint8_t* p = file_data.data() + offset;
        BinaryObjectEntry e;
        e.index             = static_cast<int>(i + 1);
        e.page_offset       = read_u32(p);
        e.uncompressed_size = read_u32(p + 8);
        e.compressed_size   = read_u32(p + 12);
        entries.push_back(e);
    }

    return entries;
}

// ============================================================================
// Binary Object Decompression
// ============================================================================

static std::vector<std::pair<int, std::vector<uint8_t>>>
decompress_binary_objects(const std::string& filepath,
                          const std::vector<BinaryObjectEntry>& entries) {
    std::vector<std::pair<int, std::vector<uint8_t>>> results;

    std::ifstream f(filepath, std::ios::binary | std::ios::ate);
    if (!f) return results;
    auto file_size = static_cast<size_t>(f.tellg());

    results.reserve(entries.size());
    for (const auto& entry : entries) {
        uint32_t abs_off = entry.absolute_offset();
        if (static_cast<size_t>(abs_off) + entry.compressed_size > file_size) {
            log_debug("Binary object " + std::to_string(entry.index) + " exceeds file size");
            continue;
        }

        std::vector<uint8_t> compressed(entry.compressed_size);
        f.seekg(abs_off);
        f.read(reinterpret_cast<char*>(compressed.data()), entry.compressed_size);

        uLongf dest_len = entry.uncompressed_size;
        std::vector<uint8_t> decompressed(dest_len);

        int ret = uncompress(decompressed.data(), &dest_len,
                             compressed.data(),
                             static_cast<uLong>(entry.compressed_size));
        if (ret != Z_OK) {
            log_debug("Binary object " + std::to_string(entry.index) + " decompression failed");
            continue;
        }
        decompressed.resize(dest_len);
        results.emplace_back(entry.index, std::move(decompressed));
    }

    return results;
}

// ============================================================================
// Page Selection Functions
// ============================================================================

static std::vector<PageTableEntry>
select_pages_by_range(const std::vector<PageTableEntry>& entries,
                      int start_page, int end_page) {
    std::vector<PageTableEntry> selected;
    for (const auto& e : entries) {
        if (e.page_number >= start_page && e.page_number <= end_page) {
            selected.push_back(e);
        }
    }
    return selected;
}

static std::pair<std::vector<PageTableEntry>, std::vector<uint32_t>>
select_pages_by_sections(const std::vector<PageTableEntry>& entries,
                         const std::vector<SectionEntry>&   sections,
                         const std::vector<uint32_t>&       section_ids) {
    std::vector<PageTableEntry> selected;
    std::vector<uint32_t> found_ids;

    std::map<uint32_t, const SectionEntry*> section_map;
    for (const auto& s : sections) {
        section_map[s.section_id] = &s;
    }

    for (uint32_t sid : section_ids) {
        auto it = section_map.find(sid);
        if (it == section_map.end()) continue;
        
        found_ids.push_back(sid);
        const SectionEntry* sec = it->second;
        int start = static_cast<int>(sec->start_page);
        int end   = static_cast<int>(sec->start_page + sec->page_count - 1);
        auto range = select_pages_by_range(entries, start, end);
        selected.insert(selected.end(), range.begin(), range.end());
    }

    return {selected, found_ids};
}

// ============================================================================
// Parse Selection Rule (Enhanced with multiple ranges/sections)
// ============================================================================

enum class SelectionMode {
    ALL,
    PAGES,
    SECTIONS
};

struct SelectionRule {
    SelectionMode mode;
    std::vector<std::pair<int,int>> page_ranges;  // For PAGES mode (multiple ranges)
    std::vector<uint32_t> section_ids;            // For SECTIONS mode
};

static std::optional<SelectionRule> parse_selection_rule(const std::string& rule_str) {
    SelectionRule rule;

    if (rule_str == "all") {
        rule.mode = SelectionMode::ALL;
        return rule;
    }

    if (rule_str.substr(0, 6) == "pages:") {
        // Format: "pages:1-5,10-20,50-60" or "pages:10-20" or "pages:5"
        std::string ranges_str = rule_str.substr(6);
        
        // Split by comma for multiple ranges
        std::stringstream ss(ranges_str);
        std::string range_token;
        
        while (std::getline(ss, range_token, ',')) {
            // Trim whitespace
            size_t start = range_token.find_first_not_of(" \t");
            size_t end = range_token.find_last_not_of(" \t");
            if (start == std::string::npos) continue;
            range_token = range_token.substr(start, end - start + 1);
            
            try {
                auto dash = range_token.find('-');
                if (dash != std::string::npos) {
                    int range_start = std::stoi(range_token.substr(0, dash));
                    int range_end = std::stoi(range_token.substr(dash + 1));
                    rule.page_ranges.push_back({range_start, range_end});
                } else {
                    int page = std::stoi(range_token);
                    rule.page_ranges.push_back({page, page});
                }
            } catch (...) {
                return std::nullopt;
            }
        }
        
        if (!rule.page_ranges.empty()) {
            rule.mode = SelectionMode::PAGES;
            return rule;
        }
        return std::nullopt;
    }

    if (rule_str.substr(0, 8) == "section:") {
        // Format: "section:14259"
        try {
            uint32_t sid = std::stoul(rule_str.substr(8));
            rule.mode = SelectionMode::SECTIONS;
            rule.section_ids.push_back(sid);
            return rule;
        } catch (...) {
            return std::nullopt;
        }
    }

    if (rule_str.substr(0, 9) == "sections:") {
        // Format: "sections:14259,14260,14261"
        std::string ids_str = rule_str.substr(9);
        std::stringstream ss(ids_str);
        std::string token;
        while (std::getline(ss, token, ',')) {
            // Trim whitespace
            size_t start = token.find_first_not_of(" \t");
            size_t end = token.find_last_not_of(" \t");
            if (start == std::string::npos) continue;
            token = token.substr(start, end - start + 1);
            
            try {
                uint32_t sid = std::stoul(token);
                rule.section_ids.push_back(sid);
            } catch (...) {
                return std::nullopt;
            }
        }
        if (!rule.section_ids.empty()) {
            rule.mode = SelectionMode::SECTIONS;
            return rule;
        }
        return std::nullopt;
    }

    return std::nullopt;
}

// ============================================================================
// Main Extraction Logic for Papyrus
// ============================================================================

int papyrus_extract_rpt(
    const std::string& input_rpt_path,
    const std::string& selection_rule_str,
    const std::string& output_txt_path,
    const std::string& output_binary_path)
{
    log_debug("Starting extraction: " + input_rpt_path);
    log_debug("Rule: " + selection_rule_str);

    // ========== Parse Selection Rule ==========
    auto rule_opt = parse_selection_rule(selection_rule_str);
    if (!rule_opt) {
        std::cerr << "ERROR: Invalid selection rule format: " << selection_rule_str << std::endl;
        std::cerr << "  Valid formats:" << std::endl;
        std::cerr << "    all" << std::endl;
        std::cerr << "    pages:10-20  or  pages:1-5,10-20,50-60  or  pages:5" << std::endl;
        std::cerr << "    section:14259" << std::endl;
        std::cerr << "    sections:14259,14260,14261" << std::endl;
        return 9;
    }
    SelectionRule rule = *rule_opt;

    // ========== Step 1: Read Input File ==========
    auto file_data = read_file(input_rpt_path);
    if (file_data.size() < 0x200) {
        std::cerr << "ERROR: Cannot open input RPT file or file too small: " << input_rpt_path << std::endl;
        return 2;
    }

    // ========== Step 2: Parse Header ==========
    auto hdr_opt = parse_rpt_header(file_data.data(), file_data.size());
    if (!hdr_opt) {
        std::cerr << "ERROR: Invalid RPT file format (no RPTFILEHDR signature)" << std::endl;
        return 5;
    }
    RptHeader hdr = *hdr_opt;

    log_debug("Pages: " + std::to_string(hdr.page_count) +
              ", Sections: " + std::to_string(hdr.section_count) +
              ", Binary objects: " + std::to_string(hdr.binary_object_count));

    // ========== Step 3: Read Page Table ==========
    auto page_entries = read_page_table(file_data, hdr.page_count);
    if (page_entries.empty()) {
        std::cerr << "ERROR: No PAGETBLHDR found in RPT file" << std::endl;
        return 5;
    }

    // ========== Step 4: Read Section Table (if needed) ==========
    std::vector<SectionEntry> sections;
    if (rule.mode == SelectionMode::SECTIONS) {
        sections = read_sectionhdr(file_data, hdr.section_data_offset);
        if (sections.empty()) {
            std::cerr << "ERROR: No sections found in RPT file" << std::endl;
            return 8;
        }
    }

    // ========== Step 5: Read Binary Object Table ==========
    std::vector<BinaryObjectEntry> binary_entries;
    if (hdr.binary_object_count > 0) {
        binary_entries = read_binary_page_table(file_data, hdr.binary_object_count);
    }

    // ========== Step 6: Select Pages Based on Rule ==========
    std::vector<PageTableEntry> selected_pages;

    switch (rule.mode) {
        case SelectionMode::ALL:
            selected_pages = page_entries;
            log_debug("Selecting all " + std::to_string(page_entries.size()) + " pages");
            break;

        case SelectionMode::PAGES: {
            // Multiple page ranges
            for (const auto& [start, end] : rule.page_ranges) {
                int start_p = std::max(1, start);
                int end_p = std::min(static_cast<int>(hdr.page_count), end);
                auto range_pages = select_pages_by_range(page_entries, start_p, end_p);
                selected_pages.insert(selected_pages.end(), range_pages.begin(), range_pages.end());
            }
            log_debug("Selecting " + std::to_string(selected_pages.size()) + " pages from " + 
                     std::to_string(rule.page_ranges.size()) + " range(s)");
            break;
        }

        case SelectionMode::SECTIONS: {
            // Multiple sections
            auto [pages, found] = select_pages_by_sections(page_entries, sections, rule.section_ids);
            selected_pages = pages;
            
            if (found.empty()) {
                std::cerr << "ERROR: None of the requested section IDs found in RPT file" << std::endl;
                std::cerr << "  Available sections: ";
                for (size_t i = 0; i < std::min(sections.size(), (size_t)10); ++i) {
                    if (i > 0) std::cerr << ", ";
                    std::cerr << sections[i].section_id;
                }
                if (sections.size() > 10) std::cerr << ", ...";
                std::cerr << std::endl;
                return 8;
            }
            log_debug("Selecting " + std::to_string(selected_pages.size()) + " pages from " +
                     std::to_string(found.size()) + " section(s)");
            break;
        }
    }

    if (selected_pages.empty()) {
        std::cerr << "ERROR: No pages selected for extraction" << std::endl;
        return 7;
    }

    // ========== Step 7: Decompress Selected Pages ==========
    auto pages = decompress_pages(input_rpt_path, selected_pages);
    
    if (pages.empty()) {
        std::cerr << "ERROR: No pages decompressed from RPT file" << std::endl;
        return 6;
    }

    // ========== Step 8: Write Text Output (Concatenated) ==========
    std::ofstream txt_out(output_txt_path, std::ios::binary);
    if (!txt_out.is_open()) {
        std::cerr << "ERROR: Cannot write output TXT file: " << output_txt_path << std::endl;
        return 3;
    }

    for (size_t i = 0; i < pages.size(); ++i) {
        if (i > 0) {
            // Form-feed separator between pages
            txt_out.write("\x0c\n", 2);
        }
        const auto& page_data = pages[i].second;
        txt_out.write(reinterpret_cast<const char*>(page_data.data()),
                      static_cast<std::streamsize>(page_data.size()));
    }
    txt_out.close();

    log_debug("Text output written: " + std::to_string(pages.size()) + " pages");

    // ========== Step 9: Write Binary Output (if present) ==========
    std::ofstream bin_out(output_binary_path, std::ios::binary);
    if (!bin_out.is_open()) {
        std::cerr << "ERROR: Cannot write output binary file: " << output_binary_path << std::endl;
        return 4;
    }

    if (!binary_entries.empty()) {
        auto bin_objs = decompress_binary_objects(input_rpt_path, binary_entries);
        
        if (!bin_objs.empty()) {
            // Concatenate all binary objects in order
            for (const auto& [idx, data] : bin_objs) {
                bin_out.write(reinterpret_cast<const char*>(data.data()),
                              static_cast<std::streamsize>(data.size()));
            }
            log_debug("Binary output written: " + std::to_string(bin_objs.size()) + " objects");
        }
    }
    bin_out.close();

    std::cout << "SUCCESS: Extraction completed" << std::endl;
    std::cout << "  Pages extracted: " << pages.size() << std::endl;
    std::cout << "  Text output: " << output_txt_path << std::endl;
    std::cout << "  Binary output: " << output_binary_path << std::endl;

    return 0; // Success
}

// ============================================================================
// Main Entry Point
// ============================================================================

int main(int argc, char* argv[]) {
    // Validate arguments
    if (argc != 5) {
        std::cerr << "papyrus_rpt_page_extractor - RPT extraction for Papyrus\n\n";
        std::cerr << "Usage: papyrus_rpt_page_extractor <input_rpt> <selection_rule> <output_txt> <output_binary>\n\n";
        std::cerr << "Arguments:\n";
        std::cerr << "  input_rpt       - Path to .rpt file (from Papyrus %TMPFILE% or direct path)\n";
        std::cerr << "  selection_rule  - Selection specification:\n";
        std::cerr << "                    'all'                            - Extract all pages\n";
        std::cerr << "                    'pages:10-20'                    - Extract page range (1-based)\n";
        std::cerr << "                    'pages:1-5,10-20,50-60'          - Multiple page ranges\n";
        std::cerr << "                    'pages:5'                        - Extract single page\n";
        std::cerr << "                    'section:14259'                  - Extract one section\n";
        std::cerr << "                    'sections:14259,14260,14261'     - Multiple section IDs\n";
        std::cerr << "  output_txt      - Path for concatenated text output\n";
        std::cerr << "  output_binary   - Path for binary output (PDF/AFP)\n\n";
        std::cerr << "Return Codes:\n";
        std::cerr << "  0 - Success\n";
        std::cerr << "  1 - Invalid arguments\n";
        std::cerr << "  2 - Cannot open input RPT file\n";
        std::cerr << "  3 - Cannot write output TXT file\n";
        std::cerr << "  4 - Cannot write output binary file\n";
        std::cerr << "  5 - Invalid RPT file format\n";
        std::cerr << "  6 - Decompression error\n";
        std::cerr << "  7 - No text pages found\n";
        std::cerr << "  8 - Section ID(s) not found\n";
        std::cerr << "  9 - Invalid selection rule format\n";
        std::cerr << "  10 - Unknown error\n";
        return 1;
    }

    try {
        std::string input_rpt = argv[1];
        std::string selection_rule = argv[2];
        std::string output_txt = argv[3];
        std::string output_binary = argv[4];

        int result = papyrus_extract_rpt(input_rpt, selection_rule, output_txt, output_binary);
        return result;

    } catch (const std::exception& e) {
        std::cerr << "FATAL ERROR: " << e.what() << std::endl;
        return 10;
    }
}
