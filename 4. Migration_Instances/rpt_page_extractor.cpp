// rpt_page_extractor.cpp - Decompress and extract pages from IntelliSTOR .RPT files
//
// Standalone C++17 CLI tool. Faithful port of the Python rpt_page_extractor.py
// and rpt_section_reader.py.
//
// Compile: g++ -std=c++17 -O2 -o rpt_page_extractor rpt_page_extractor.cpp -lz
// Compile (macOS): clang++ -std=c++17 -O2 -o rpt_page_extractor rpt_page_extractor.cpp -lz
//
// Supports:
//   - Full extraction: all pages from one or more RPT files
//   - Page range:      --pages 10-20 (extract pages 10 through 20)
//   - Section-based:   --section-id 14259 (extract only pages belonging to that section)
//   - Multi-section:   --section-id 14259 14260 14261 (multiple sections, in order)
//   - Folder mode:     --folder <dir> (process all RPT files in a directory)
//
// RPT File Layout:
//   [0x000] RPTFILEHDR     - "RPTFILEHDR\t{domain}:{species}\t{timestamp}" terminated by 0x1A
//   [0x0F0] RPTINSTHDR     - Instance metadata (base offset for page_offset)
//   [0x1D0] Table Directory - page_count, section_count, offsets
//   [0x200] COMPRESSED DATA - per-page zlib streams (0x78 0x01 header)
//   [...]   SECTIONHDR     - section triplets (SECTION_ID, START_PAGE, PAGE_COUNT)
//   [...]   PAGETBLHDR     - 24-byte entries per page
//
// PAGETBLHDR Entry Format (24 bytes, little-endian):
//   [page_offset:4]        - Byte offset relative to RPTINSTHDR (add 0xF0 for absolute)
//   [pad:4]                - Reserved (always 0)
//   [line_width:2]         - Max characters per line on this page
//   [lines_per_page:2]     - Number of lines on this page
//   [uncompressed_size:4]  - Decompressed page data size in bytes
//   [compressed_size:4]    - zlib stream size in bytes
//   [pad:4]                - Reserved (always 0)

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

// ============================================================================
// Data Structures
// ============================================================================

struct RptHeader {
    int      domain_id           = 0;
    int      report_species_id   = 0;
    std::string timestamp;
    uint32_t page_count          = 0;
    uint32_t section_count       = 0;
    uint32_t section_data_offset = 0;   // approximate: compressed_data_end
    uint32_t page_table_offset   = 0;
};

struct SectionEntry {
    uint32_t section_id  = 0;
    uint32_t start_page  = 0;
    uint32_t page_count  = 0;
};

struct PageTableEntry {
    int      page_number       = 0;   // 1-based
    uint32_t page_offset       = 0;   // relative to RPTINSTHDR
    uint16_t line_width        = 0;
    uint16_t lines_per_page    = 0;
    uint32_t uncompressed_size = 0;
    uint32_t compressed_size   = 0;

    uint32_t absolute_offset() const {
        return page_offset + RPTINSTHDR_OFFSET;
    }
};

struct ExtractionStats {
    std::string file;
    uint32_t pages_total        = 0;
    uint32_t pages_selected     = 0;
    uint32_t pages_extracted    = 0;
    uint64_t bytes_compressed   = 0;
    uint64_t bytes_decompressed = 0;
    std::string error;
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
// RPT Header Parsing (port of parse_rpt_header)
// ============================================================================

static std::optional<RptHeader> parse_rpt_header(const uint8_t* data, size_t data_len) {
    if (data_len < 0x1F0) return std::nullopt;
    // Check RPTFILEHDR signature
    if (std::memcmp(data, "RPTFILEHDR", 10) != 0) return std::nullopt;

    RptHeader hdr;

    // Find end of header line (terminated by 0x1A)
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

    return hdr;
}

// ============================================================================
// SECTIONHDR Parsing (port of read_sectionhdr)
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
                // The triplets extend beyond our scan region; work from full data
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
    // Look for ENDDATA to bound the section
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
// PAGETBLHDR Parsing (port of read_page_table)
// ============================================================================

static std::vector<PageTableEntry>
read_page_table(const std::vector<uint8_t>& file_data, uint32_t page_count) {
    std::vector<PageTableEntry> entries;

    const char marker[] = "PAGETBLHDR";
    constexpr size_t marker_len = 10;

    const uint8_t* mp = find_marker(file_data.data(), file_data.size(), marker, marker_len);
    if (!mp) return entries;

    // Skip marker (10 bytes) + 3 null padding bytes = 13 bytes
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
        // skip pad at p+4
        e.line_width        = read_u16(p + 8);
        e.lines_per_page    = read_u16(p + 10);
        e.uncompressed_size = read_u32(p + 12);
        e.compressed_size   = read_u32(p + 16);
        // skip pad at p+20
        entries.push_back(e);
    }

    return entries;
}

// ============================================================================
// Page Decompression (port of decompress_pages)
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
            std::cerr << "  WARNING: Page " << entry.page_number
                      << " offset 0x" << std::hex << std::uppercase << abs_off
                      << std::dec << " exceeds file size "
                      << format_number(file_size) << "\n";
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
            std::cerr << "  WARNING: Page " << entry.page_number
                      << " decompression failed (zlib error " << ret << ")\n";
            continue;
        }
        decompressed.resize(dest_len);
        results.emplace_back(entry.page_number, std::move(decompressed));
    }

    return results;
}

// ============================================================================
// Page Selection (port of select_pages_by_*)
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

struct SectionSelection {
    std::vector<PageTableEntry> entries;
    std::vector<uint32_t>       found_ids;
    std::vector<uint32_t>       skipped_ids;
};

static SectionSelection
select_pages_by_sections(const std::vector<PageTableEntry>& entries,
                         const std::vector<SectionEntry>&   sections,
                         const std::vector<uint32_t>&       section_ids) {
    SectionSelection result;

    // Build lookup map
    std::map<uint32_t, const SectionEntry*> section_map;
    for (const auto& s : sections) {
        section_map[s.section_id] = &s;
    }

    for (uint32_t sid : section_ids) {
        auto it = section_map.find(sid);
        if (it == section_map.end()) {
            result.skipped_ids.push_back(sid);
            continue;
        }
        result.found_ids.push_back(sid);
        const SectionEntry* sec = it->second;
        int start = static_cast<int>(sec->start_page);
        int end   = static_cast<int>(sec->start_page + sec->page_count - 1);
        auto range = select_pages_by_range(entries, start, end);
        result.entries.insert(result.entries.end(), range.begin(), range.end());
    }

    return result;
}

// ============================================================================
// Output (port of save_pages)
// ============================================================================

static int save_pages(const std::vector<std::pair<int, std::vector<uint8_t>>>& pages,
                      const std::string& output_dir) {
    std::error_code ec;
    fs::create_directories(output_dir, ec);
    if (ec) {
        std::cerr << "  ERROR: Cannot create directory " << output_dir
                  << ": " << ec.message() << "\n";
        return 0;
    }

    int saved = 0;
    for (const auto& [page_num, content] : pages) {
        std::ostringstream fname;
        fname << "page_" << std::setw(5) << std::setfill('0') << page_num << ".txt";
        fs::path outpath = fs::path(output_dir) / fname.str();

        std::ofstream out(outpath, std::ios::binary);
        if (!out) {
            std::cerr << "  WARNING: Cannot write " << outpath << "\n";
            continue;
        }
        out.write(reinterpret_cast<const char*>(content.data()),
                  static_cast<std::streamsize>(content.size()));
        ++saved;
    }
    return saved;
}

// ============================================================================
// Remove .rpt/.RPT extension (case-insensitive)
// ============================================================================

static std::string strip_rpt_extension(const std::string& filename) {
    if (filename.size() >= 4) {
        std::string ext = filename.substr(filename.size() - 4);
        // Case-insensitive check for ".rpt"
        if (ext[0] == '.' &&
            (ext[1] == 'r' || ext[1] == 'R') &&
            (ext[2] == 'p' || ext[2] == 'P') &&
            (ext[3] == 't' || ext[3] == 'T')) {
            return filename.substr(0, filename.size() - 4);
        }
    }
    return filename;
}

// ============================================================================
// Main extraction (port of extract_rpt)
// ============================================================================

static ExtractionStats extract_rpt(
        const std::string& filepath,
        const std::string& output_base,
        std::optional<std::pair<int,int>> page_range,
        const std::vector<uint32_t>& section_ids,
        bool info_only)
{
    ExtractionStats stats;
    stats.file = filepath;

    // Read entire file
    auto file_data = read_file(filepath);
    if (file_data.size() < 0x200) {
        stats.error = "File too small or cannot read";
        return stats;
    }

    // Parse header
    auto hdr_opt = parse_rpt_header(file_data.data(), file_data.size());
    if (!hdr_opt) {
        stats.error = "Not a valid RPT file (no RPTFILEHDR signature)";
        return stats;
    }
    RptHeader& hdr = *hdr_opt;
    stats.pages_total = hdr.page_count;

    std::string rpt_name = strip_rpt_extension(
        fs::path(filepath).filename().string());

    // Read page table
    auto page_entries = read_page_table(file_data, hdr.page_count);
    if (page_entries.empty()) {
        stats.error = "No PAGETBLHDR found";
        return stats;
    }

    // Read sections (we already have the file data, but read_sectionhdr
    // re-reads the file -- acceptable for correctness; matches Python behaviour)
    auto [shdr_opt, sections] = read_sectionhdr(filepath);
    // Update section_count from actual parsing
    if (shdr_opt) {
        hdr.section_count = shdr_opt->section_count;
    }

    // --- Display info ---
    std::string sep(70, '=');
    std::cout << "\n" << sep << "\n";
    std::cout << "File: " << filepath << "\n";
    std::cout << "  Species: " << hdr.report_species_id
              << ", Domain: " << hdr.domain_id << "\n";
    std::cout << "  Timestamp: " << hdr.timestamp << "\n";
    std::cout << "  Pages: " << hdr.page_count
              << ", Sections: " << hdr.section_count << "\n";

    uint64_t total_comp   = 0;
    uint64_t total_uncomp = 0;
    for (const auto& e : page_entries) {
        total_comp   += e.compressed_size;
        total_uncomp += e.uncompressed_size;
    }
    if (total_comp > 0) {
        double ratio = static_cast<double>(total_uncomp) / static_cast<double>(total_comp);
        std::cout << "  Compressed: " << format_number(total_comp)
                  << " bytes -> Uncompressed: " << format_number(total_uncomp)
                  << " bytes (" << std::fixed << std::setprecision(1) << ratio << "x)\n";
    }

    // Collect requested section IDs for marker display
    std::set<uint32_t> requested_sids(section_ids.begin(), section_ids.end());

    if (!sections.empty()) {
        std::cout << "\n  Sections (" << sections.size() << "):\n";
        std::cout << "  " << std::setw(12) << std::right << "SECTION_ID"
                  << "  " << std::setw(10) << "START_PAGE"
                  << "  " << std::setw(10) << "PAGE_COUNT" << "\n";
        std::cout << "  " << std::string(12, '-')
                  << "  " << std::string(10, '-')
                  << "  " << std::string(10, '-') << "\n";
        for (const auto& s : sections) {
            std::string marker = requested_sids.count(s.section_id) ? " <--" : "";
            std::cout << "  " << std::setw(12) << s.section_id
                      << "  " << std::setw(10) << s.start_page
                      << "  " << std::setw(10) << s.page_count
                      << marker << "\n";
        }
    }

    if (info_only) {
        // Show page table sample (first 5 / last 5)
        std::cout << "\n  Page Table (first 5 / last 5):\n";
        std::cout << "  " << std::setw(6) << std::right << "PAGE"
                  << "  " << std::setw(10) << "OFFSET"
                  << "  " << std::setw(6) << "WIDTH"
                  << "  " << std::setw(6) << "LINES"
                  << "  " << std::setw(8) << "UNCOMP"
                  << "  " << std::setw(8) << "COMP" << "\n";

        std::vector<const PageTableEntry*> show;
        if (page_entries.size() <= 10) {
            for (const auto& e : page_entries) show.push_back(&e);
        } else {
            for (size_t i = 0; i < 5; ++i) show.push_back(&page_entries[i]);
            show.push_back(nullptr); // separator
            for (size_t i = page_entries.size() - 5; i < page_entries.size(); ++i)
                show.push_back(&page_entries[i]);
        }
        for (const auto* ep : show) {
            if (!ep) {
                std::cout << "  " << std::setw(6) << std::right << "..." << "\n";
                continue;
            }
            std::cout << "  " << std::setw(6) << ep->page_number
                      << "  0x" << std::hex << std::uppercase
                      << std::setw(8) << std::setfill('0') << ep->absolute_offset()
                      << std::dec << std::setfill(' ')
                      << "  " << std::setw(6) << ep->line_width
                      << "  " << std::setw(6) << ep->lines_per_page
                      << "  " << std::setw(8) << format_number(ep->uncompressed_size)
                      << "  " << std::setw(8) << format_number(ep->compressed_size)
                      << "\n";
        }
        return stats;
    }

    // --- Select pages to extract ---
    std::vector<PageTableEntry> selected = page_entries; // default: all
    std::vector<uint32_t> found_ids;

    if (!section_ids.empty()) {
        auto sel = select_pages_by_sections(page_entries, sections, section_ids);
        selected   = std::move(sel.entries);
        found_ids  = std::move(sel.found_ids);
        auto& skipped = sel.skipped_ids;

        if (!skipped.empty()) {
            std::cout << "\n  Skipped (not found): ";
            for (size_t i = 0; i < skipped.size(); ++i) {
                if (i > 0) std::cout << ", ";
                std::cout << skipped[i];
            }
            std::cout << "\n";
        }
        if (found_ids.empty()) {
            stats.error = "None of the requested section IDs found in SECTIONHDR";
            std::cout << "\n  ERROR: " << stats.error << "\n";
            if (!sections.empty()) {
                std::cout << "  Available section IDs: ";
                size_t limit = std::min(sections.size(), (size_t)20);
                for (size_t i = 0; i < limit; ++i) {
                    if (i > 0) std::cout << ", ";
                    std::cout << sections[i].section_id;
                }
                std::cout << "\n";
            }
            return stats;
        }

        // Build section map for display
        std::map<uint32_t, const SectionEntry*> section_map;
        for (const auto& s : sections) section_map[s.section_id] = &s;

        for (uint32_t sid : found_ids) {
            const SectionEntry* si = section_map[sid];
            std::cout << "\n  Extracting section " << sid << ": pages "
                      << si->start_page << "-"
                      << (si->start_page + si->page_count - 1)
                      << " (" << si->page_count << " pages)\n";
        }
        uint32_t total_section_pages = 0;
        for (uint32_t sid : found_ids) {
            total_section_pages += section_map[sid]->page_count;
        }
        std::cout << "\n  Total: " << found_ids.size() << " section(s), "
                  << total_section_pages << " pages\n";

    } else if (page_range.has_value()) {
        int start_p = std::max(1, page_range->first);
        int end_p   = std::min(static_cast<int>(hdr.page_count), page_range->second);
        selected = select_pages_by_range(page_entries, start_p, end_p);
        std::cout << "\n  Extracting page range: " << start_p << "-" << end_p
                  << " (" << selected.size() << " pages)\n";
    } else {
        std::cout << "\n  Extracting all " << hdr.page_count << " pages\n";
    }

    stats.pages_selected = static_cast<uint32_t>(selected.size());

    if (selected.empty()) {
        stats.error = "No pages to extract";
        return stats;
    }

    // Determine output directory
    std::string output_dir;
    if (!section_ids.empty() && !found_ids.empty()) {
        if (found_ids.size() == 1) {
            output_dir = (fs::path(output_base) / rpt_name /
                          ("section_" + std::to_string(found_ids[0]))).string();
        } else {
            std::ostringstream label;
            for (size_t i = 0; i < found_ids.size(); ++i) {
                if (i > 0) label << "_";
                label << found_ids[i];
            }
            output_dir = (fs::path(output_base) / rpt_name /
                          ("sections_" + label.str())).string();
        }
    } else if (page_range.has_value()) {
        output_dir = (fs::path(output_base) / rpt_name /
                      ("pages_" + std::to_string(page_range->first) + "-" +
                       std::to_string(page_range->second))).string();
    } else {
        output_dir = (fs::path(output_base) / rpt_name).string();
    }

    // Decompress and save
    auto pages = decompress_pages(filepath, selected);
    stats.pages_extracted = static_cast<uint32_t>(pages.size());
    for (const auto& e : selected) {
        stats.bytes_compressed += e.compressed_size;
    }
    for (const auto& [pn, content] : pages) {
        stats.bytes_decompressed += content.size();
    }

    int saved = save_pages(pages, output_dir);
    std::cout << "  Saved " << saved << " pages to " << output_dir << "/\n";
    std::cout << "  Total decompressed: " << format_number(stats.bytes_decompressed)
              << " bytes\n";

    uint32_t failed = stats.pages_selected - stats.pages_extracted;
    if (failed > 0) {
        std::cout << "  WARNING: " << failed << " pages failed to decompress\n";
    }

    return stats;
}

// ============================================================================
// CLI: page range parsing
// ============================================================================

static std::optional<std::pair<int,int>> parse_page_range(const std::string& s) {
    auto dash = s.find('-');
    if (dash != std::string::npos) {
        try {
            int a = std::stoi(s.substr(0, dash));
            int b = std::stoi(s.substr(dash + 1));
            return std::make_pair(a, b);
        } catch (...) {
            return std::nullopt;
        }
    } else {
        try {
            int n = std::stoi(s);
            return std::make_pair(n, n);
        } catch (...) {
            return std::nullopt;
        }
    }
}

// ============================================================================
// CLI: help text
// ============================================================================

static void print_help(const char* prog) {
    std::cout <<
"Usage: " << prog << " [options] <rptfile...>\n"
"\n"
"Extract and decompress pages from IntelliSTOR .RPT files.\n"
"\n"
"Options:\n"
"  --info                Show RPT file info without extracting\n"
"  --pages <range>       Page range \"10-20\" or \"5\" (1-based, inclusive)\n"
"  --section-id <id...>  One or more SECTION_IDs (in order, skips missing)\n"
"  --folder <dir>        Process all .RPT files in directory\n"
"  --output <dir>        Output base directory (default: \".\")\n"
"  --help                Show help\n"
"\n"
"Examples:\n"
"  # Show RPT file info (no extraction)\n"
"  " << prog << " --info 260271NL.RPT\n"
"\n"
"  # Extract all pages from an RPT file\n"
"  " << prog << " 260271NL.RPT\n"
"\n"
"  # Extract specific page range\n"
"  " << prog << " --pages 10-20 251110OD.RPT\n"
"\n"
"  # Extract pages for a specific section (by SECTION_ID)\n"
"  " << prog << " --section-id 14259 251110OD.RPT\n"
"\n"
"  # Extract pages for multiple sections (in order, skips missing)\n"
"  " << prog << " --section-id 14259 14260 14261 251110OD.RPT\n"
"\n"
"  # Process all RPT files in a folder\n"
"  " << prog << " --folder /path/to/rpt/files\n"
"\n"
"  # Custom output directory\n"
"  " << prog << " --output /tmp/extracted 251110OD.RPT\n";
}

// ============================================================================
// CLI: collect .RPT files from a directory (recursive)
// ============================================================================

static std::vector<std::string> collect_rpt_files(const std::string& dir) {
    std::vector<std::string> files;
    std::error_code ec;
    for (const auto& entry : fs::recursive_directory_iterator(dir, ec)) {
        if (!entry.is_regular_file()) continue;
        std::string ext = entry.path().extension().string();
        // Case-insensitive .rpt check
        if (ext.size() == 4 && ext[0] == '.' &&
            (ext[1] == 'r' || ext[1] == 'R') &&
            (ext[2] == 'p' || ext[2] == 'P') &&
            (ext[3] == 't' || ext[3] == 'T')) {
            files.push_back(entry.path().string());
        }
    }
    std::sort(files.begin(), files.end());
    return files;
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
    bool info_only = false;
    std::string pages_str;
    std::vector<uint32_t> section_ids;
    std::string folder;
    std::string output_base = ".";
    std::vector<std::string> rpt_files;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];

        if (arg == "--help" || arg == "-h") {
            print_help(argv[0]);
            return 0;
        }
        else if (arg == "--info") {
            info_only = true;
        }
        else if (arg == "--pages") {
            if (i + 1 >= argc) {
                std::cerr << "Error: --pages requires an argument\n";
                return 1;
            }
            pages_str = argv[++i];
        }
        else if (arg == "--section-id") {
            // Consume all following numeric arguments
            while (i + 1 < argc) {
                std::string next = argv[i + 1];
                // Stop if it looks like another option or a filename
                if (next.empty() || next[0] == '-') break;
                // Try to parse as integer
                try {
                    uint32_t sid = static_cast<uint32_t>(std::stoul(next));
                    section_ids.push_back(sid);
                    ++i;
                } catch (...) {
                    break; // not a number, treat as filename
                }
            }
            if (section_ids.empty()) {
                std::cerr << "Error: --section-id requires at least one ID\n";
                return 1;
            }
        }
        else if (arg == "--folder") {
            if (i + 1 >= argc) {
                std::cerr << "Error: --folder requires an argument\n";
                return 1;
            }
            folder = argv[++i];
        }
        else if (arg == "--output" || arg == "-o") {
            if (i + 1 >= argc) {
                std::cerr << "Error: --output requires an argument\n";
                return 1;
            }
            output_base = argv[++i];
        }
        else if (arg[0] == '-') {
            std::cerr << "Error: Unknown option: " << arg << "\n";
            return 1;
        }
        else {
            rpt_files.push_back(arg);
        }
    }

    // Validate
    if (rpt_files.empty() && folder.empty()) {
        std::cerr << "Error: Provide either RPT file path(s) or --folder <directory>\n";
        return 1;
    }

    if (!pages_str.empty() && !section_ids.empty()) {
        std::cerr << "Error: Cannot use both --pages and --section-id\n";
        return 1;
    }

    // Parse page range
    std::optional<std::pair<int,int>> page_range;
    if (!pages_str.empty()) {
        page_range = parse_page_range(pages_str);
        if (!page_range) {
            std::cerr << "Error: Invalid page range: " << pages_str
                      << ". Use format \"10-20\" or \"5\".\n";
            return 1;
        }
    }

    // Collect RPT files
    if (!folder.empty()) {
        if (!fs::is_directory(folder)) {
            std::cerr << "Error: Folder does not exist: " << folder << "\n";
            return 1;
        }
        rpt_files = collect_rpt_files(folder);
        if (rpt_files.empty()) {
            std::cout << "No .RPT files found in " << folder << "\n";
            return 0;
        }
        std::cout << "Found " << rpt_files.size() << " RPT files in " << folder << "\n";
    } else {
        // Verify files exist
        for (const auto& f : rpt_files) {
            if (!fs::exists(f)) {
                std::cerr << "Error: RPT file not found: " << f << "\n";
                return 1;
            }
        }
    }

    // Process each RPT file
    std::vector<ExtractionStats> all_stats;
    for (const auto& filepath : rpt_files) {
        auto stats = extract_rpt(filepath, output_base, page_range,
                                 section_ids, info_only);
        if (!stats.error.empty()) {
            std::cout << "  ERROR: " << stats.error << "\n";
        }
        all_stats.push_back(std::move(stats));
    }

    // Summary for batch mode
    if (rpt_files.size() > 1) {
        uint64_t total_pages = 0;
        uint64_t total_bytes = 0;
        int errors = 0;
        for (const auto& s : all_stats) {
            total_pages += s.pages_extracted;
            total_bytes += s.bytes_decompressed;
            if (!s.error.empty()) ++errors;
        }
        std::string sep(70, '=');
        std::cout << "\n" << sep << "\n";
        std::cout << "SUMMARY: " << rpt_files.size() << " files, "
                  << total_pages << " pages extracted, "
                  << format_number(total_bytes) << " bytes decompressed, "
                  << errors << " errors\n";
    }

    return 0;
}
