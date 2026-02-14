// papyrus_rpt_search.cpp
// Standalone MAP File Index Search Tool (C++ port of papyrus_rpt_search.py)
//
// Searches for indexed field values in binary MAP files without requiring
// a database connection. Implements binary search on sorted MAP entries.
//
// Modes:
//   1. Search by raw IDs:      --map FILE --line-id N --field-id N --value "text"
//   2. Search by field name:    --map FILE --metadata JSON --field NAME --value "text"
//   3. List indexed fields:     --map FILE --list-fields [--metadata JSON]
//   4. List field values:       --map FILE --line-id N --field-id N --list-values
//
// Output formats: table (default), csv, json
//
// No database or ODBC required — reads binary MAP files directly.
// Compile: compile_search.bat (MinGW-w64, no ODBC needed)

#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <map>
#include <set>
#include <sstream>
#include <iomanip>
#include <cstring>
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <filesystem>

namespace fs = std::filesystem;

// ============================================================================
// Data structures
// ============================================================================

struct MapHeader {
    std::string filename;
    std::string date_string;
    int segment_count = 0;
    int total_size = 0;
};

struct MapSegment {
    int index = 0;
    int offset = 0;       // Start of segment in file (at **ME marker)
    int size = 0;          // Total segment size
    int data_offset = 0;   // Start of entry data (after metadata)
    int line_id = 0;
    int field_id = 0;
    int field_width = 0;
    int entry_count = 0;
};

struct IndexEntry {
    std::string value;
    int page_number = 0;
    uint32_t u32_index = 0;
    std::string entry_format;  // "page" or "u32_index"
};

struct SearchResult {
    std::string value;
    int page = 0;
    uint32_t u32_index = 0;
    std::string format;  // "page" or "u32_index"
};

struct MetadataField {
    std::string name;
    int line_id = 0;
    int field_id = 0;
    int start_column = 0;
    int end_column = 0;
};

// ============================================================================
// MAP File Parser
// ============================================================================
//
// MAP files use UTF-16LE encoding. The **ME segment marker is 8 bytes:
//   0x2A 0x00 0x2A 0x00 0x4D 0x00 0x45 0x00
//
// Segment metadata at offset +24 from **ME:
//   +0:  page_start   (2 bytes)
//   +2:  line_id      (2 bytes)
//   +4:  unknown      (2 bytes)
//   +6:  field_id     (2 bytes)
//   +8:  unknown      (2 bytes)
//   +10: field_width  (2 bytes)
//   +12: unknown      (2 bytes)
//   +14: entry_count  (2 bytes)
//
// Data offset varies between MAP files (~0xC0-0xE0 from **ME). Found
// dynamically by searching for first entry whose length == field_width.
// Segment 0 data starts at me_pos + 0xC2.

class MapFileParser {
public:
    std::vector<uint8_t> data;
    std::vector<MapSegment> segments;
    MapHeader header;
    bool loaded = false;

    // UTF-16LE encoded **ME marker (8 bytes)
    static constexpr uint8_t ME_MARKER[8] = {0x2A, 0x00, 0x2A, 0x00, 0x4D, 0x00, 0x45, 0x00};
    static constexpr size_t ME_MARKER_LEN = 8;

    bool load(const std::string& path) {
        std::ifstream file(path, std::ios::binary | std::ios::ate);
        if (!file.is_open()) {
            std::cerr << "ERROR: Cannot open MAP file: " << path << "\n";
            return false;
        }

        auto file_size = file.tellg();
        file.seekg(0, std::ios::beg);

        data.resize(file_size);
        file.read(reinterpret_cast<char*>(data.data()), file_size);
        file.close();

        loaded = true;
        header.total_size = (int)file_size;
        header.filename = fs::path(path).filename().string();

        parseHeader();
        return true;
    }

    void parseHeader() {
        if (data.size() < 90) return;

        // Segment count at offset 18
        if (data.size() >= 20) {
            header.segment_count = readU16(18);
        }

        // Date string at offset 0x20 (UTF-16LE, 10 chars = 20 bytes)
        if (data.size() >= 0x34) {
            std::string date;
            for (size_t i = 0x20; i + 1 < 0x34 && i + 1 < data.size(); i += 2) {
                char c = (char)data[i];
                if (data[i + 1] == 0 && c != 0) {
                    date += c;
                }
            }
            while (!date.empty() && date.back() == '\0') date.pop_back();
            header.date_string = date;
        }
    }

    void parseSegments() {
        if (!loaded || data.size() < 10) return;

        segments.clear();

        // Find all **ME markers (UTF-16LE, 8 bytes each)
        std::vector<size_t> me_positions;
        for (size_t i = 0; i + ME_MARKER_LEN <= data.size(); i++) {
            if (std::memcmp(&data[i], ME_MARKER, ME_MARKER_LEN) == 0) {
                me_positions.push_back(i);
                i += ME_MARKER_LEN - 1; // Skip past marker
            }
        }

        header.segment_count = (int)me_positions.size();

        for (size_t seg_idx = 0; seg_idx < me_positions.size(); seg_idx++) {
            size_t me_pos = me_positions[seg_idx];
            size_t next_pos = (seg_idx + 1 < me_positions.size())
                              ? me_positions[seg_idx + 1]
                              : data.size();

            MapSegment seg;
            seg.index = (int)seg_idx;
            seg.offset = (int)me_pos;
            seg.size = (int)(next_pos - me_pos);

            if (seg_idx == 0) {
                // Segment 0: lookup/directory table
                seg.data_offset = (int)(me_pos + 0xC2);
                seg.field_width = 0;
                seg.entry_count = 0;
                seg.line_id = 0;
                seg.field_id = 0;
            } else {
                // Segments 1+: index data for specific fields
                // Metadata at offset +24 from **ME marker
                size_t meta_off = me_pos + 24;

                if (meta_off + 16 <= data.size()) {
                    seg.line_id     = readU16(meta_off + 2);
                    seg.field_id    = readU16(meta_off + 6);
                    seg.field_width = readU16(meta_off + 10);
                    seg.entry_count = readU16(meta_off + 14);
                }

                // Dynamically find data_offset
                seg.data_offset = findDataOffset(me_pos, next_pos, seg.field_width);
            }

            segments.push_back(seg);
        }
    }

    MapSegment* findSegmentForField(int line_id, int field_id) {
        for (auto& seg : segments) {
            if (seg.index > 0 && seg.line_id == line_id && seg.field_id == field_id) {
                return &seg;
            }
        }
        return nullptr;
    }

private:
    uint16_t readU16(size_t offset) {
        if (offset + 2 > data.size()) return 0;
        return (uint16_t)data[offset] | ((uint16_t)data[offset + 1] << 8);
    }

    uint32_t readU32(size_t offset) {
        if (offset + 4 > data.size()) return 0;
        return (uint32_t)data[offset] | ((uint32_t)data[offset + 1] << 8) |
               ((uint32_t)data[offset + 2] << 16) | ((uint32_t)data[offset + 3] << 24);
    }

    int findDataOffset(size_t me_pos, size_t next_pos, int field_width) {
        if (field_width == 0 || field_width > 100) {
            return (int)(me_pos + 0xCD);
        }

        size_t search_start = me_pos + 0xC0;
        size_t search_end   = std::min(me_pos + 0xE0, next_pos - 2);

        for (size_t probe = search_start; probe < search_end; probe++) {
            if (probe + 2 > data.size()) break;
            uint16_t probe_len = readU16(probe);
            if (probe_len == (uint16_t)field_width) {
                if (probe + 2 + field_width <= data.size()) {
                    int printable = 0;
                    for (int j = 0; j < field_width; j++) {
                        uint8_t b = data[probe + 2 + j];
                        if (b >= 32 && b < 127) printable++;
                    }
                    if (printable > field_width / 2) {
                        return (int)probe;
                    }
                }
            }
        }

        return (int)(me_pos + 0xCD);
    }

public:
    uint16_t pubReadU16(size_t offset) { return readU16(offset); }
    uint32_t pubReadU32(size_t offset) { return readU32(offset); }
};

// ============================================================================
// Metadata Resolver (reads JSON exported by papyrus_export_metadata.py)
// ============================================================================

class MetadataResolver {
public:
    std::string species_name;
    std::vector<MetadataField> indexed_fields;

    bool load(const std::string& path) {
        std::ifstream file(path);
        if (!file.is_open()) return false;

        std::string content((std::istreambuf_iterator<char>(file)),
                            std::istreambuf_iterator<char>());
        file.close();

        // Simple JSON parser for our specific format
        // Extract species name
        species_name = extractJsonString(content, "\"name\"");

        // Extract indexed_fields array
        size_t arr_start = content.find("\"indexed_fields\"");
        if (arr_start == std::string::npos) return true;  // No indexed fields

        size_t bracket_start = content.find('[', arr_start);
        size_t bracket_end = findMatchingBracket(content, bracket_start);

        if (bracket_start == std::string::npos || bracket_end == std::string::npos)
            return true;

        std::string arr_content = content.substr(bracket_start + 1, bracket_end - bracket_start - 1);

        // Parse each field object
        size_t pos = 0;
        while (pos < arr_content.size()) {
            size_t obj_start = arr_content.find('{', pos);
            if (obj_start == std::string::npos) break;
            size_t obj_end = arr_content.find('}', obj_start);
            if (obj_end == std::string::npos) break;

            std::string obj = arr_content.substr(obj_start, obj_end - obj_start + 1);

            MetadataField f;
            f.name = extractJsonString(obj, "\"name\"");
            f.line_id = extractJsonInt(obj, "\"line_id\"");
            f.field_id = extractJsonInt(obj, "\"field_id\"");
            f.start_column = extractJsonInt(obj, "\"start_column\"");
            f.end_column = extractJsonInt(obj, "\"end_column\"");

            if (!f.name.empty()) {
                indexed_fields.push_back(f);
            }

            pos = obj_end + 1;
        }

        return true;
    }

    MetadataField* resolveField(const std::string& name) {
        std::string upper_name = toUpper(name);
        for (auto& f : indexed_fields) {
            if (toUpper(trim(f.name)) == upper_name) {
                return &f;
            }
        }
        return nullptr;
    }

private:
    static std::string toUpper(const std::string& s) {
        std::string result = s;
        std::transform(result.begin(), result.end(), result.begin(), ::toupper);
        return result;
    }

    static std::string trim(const std::string& s) {
        size_t start = s.find_first_not_of(" \t\n\r");
        if (start == std::string::npos) return "";
        size_t end = s.find_last_not_of(" \t\n\r");
        return s.substr(start, end - start + 1);
    }

    static std::string extractJsonString(const std::string& json, const std::string& key) {
        size_t pos = json.find(key);
        if (pos == std::string::npos) return "";
        pos = json.find(':', pos + key.size());
        if (pos == std::string::npos) return "";
        pos = json.find('"', pos + 1);
        if (pos == std::string::npos) return "";
        size_t end = json.find('"', pos + 1);
        if (end == std::string::npos) return "";
        return json.substr(pos + 1, end - pos - 1);
    }

    static int extractJsonInt(const std::string& json, const std::string& key) {
        size_t pos = json.find(key);
        if (pos == std::string::npos) return 0;
        pos = json.find(':', pos + key.size());
        if (pos == std::string::npos) return 0;
        pos++;
        while (pos < json.size() && (json[pos] == ' ' || json[pos] == '\t')) pos++;
        std::string num;
        while (pos < json.size() && (isdigit(json[pos]) || json[pos] == '-')) {
            num += json[pos++];
        }
        try { return std::stoi(num); } catch (...) { return 0; }
    }

    static size_t findMatchingBracket(const std::string& s, size_t open_pos) {
        if (open_pos == std::string::npos || open_pos >= s.size()) return std::string::npos;
        int depth = 1;
        for (size_t i = open_pos + 1; i < s.size(); i++) {
            if (s[i] == '[') depth++;
            else if (s[i] == ']') { depth--; if (depth == 0) return i; }
        }
        return std::string::npos;
    }
};

// ============================================================================
// Entry Format Detection
// ============================================================================

bool detectU32Format(MapFileParser& parser, const MapSegment& seg, int sample_count) {
    int entry_size = 7 + seg.field_width;
    if (entry_size <= 0 || seg.field_width == 0) return false;

    size_t end_boundary = std::min((size_t)(seg.offset + seg.size), parser.data.size());
    int odd_count = 0, valid_count = 0;

    for (int i = 0; i < sample_count; i++) {
        size_t offset = seg.data_offset + (size_t)i * entry_size;
        if (offset + entry_size > end_boundary) break;

        uint16_t length = parser.pubReadU16(offset);
        if (length != seg.field_width) break;

        size_t trailing_start = offset + 2 + seg.field_width;
        if (trailing_start + 2 > end_boundary) break;

        uint16_t u16 = parser.pubReadU16(trailing_start);
        valid_count++;
        if (u16 % 2 == 1) odd_count++;
    }

    return odd_count == valid_count && valid_count >= 3;
}

// ============================================================================
// Binary Search
// ============================================================================

std::vector<IndexEntry> binarySearchEntries(
    MapFileParser& parser,
    const MapSegment& seg,
    const std::string& search_value,
    bool prefix_match = false
) {
    std::vector<IndexEntry> matches;

    if (seg.field_width == 0 || seg.field_width > 100) return matches;

    int entry_size = 7 + seg.field_width;
    size_t end_boundary = std::min((size_t)(seg.offset + seg.size), parser.data.size());
    size_t data_start = seg.data_offset;
    int available_bytes = (int)(end_boundary - data_start);
    int total_entries = available_bytes / entry_size;

    if (total_entries <= 0) return matches;

    bool is_u32 = detectU32Format(parser, seg, std::min(100, total_entries));

    // Pad search value to field_width
    std::string padded_search = search_value;
    while ((int)padded_search.size() < seg.field_width) padded_search += ' ';
    padded_search = padded_search.substr(0, seg.field_width);

    // Binary search for first match
    int lo = 0, hi = total_entries - 1;
    int first_match = -1;

    while (lo <= hi) {
        int mid = (lo + hi) / 2;
        size_t offset = data_start + (size_t)mid * entry_size;

        if (offset + entry_size > end_boundary) { hi = mid - 1; continue; }

        uint16_t length = parser.pubReadU16(offset);
        if (length != seg.field_width) { hi = mid - 1; continue; }

        std::string entry_value((char*)&parser.data[offset + 2], seg.field_width);

        if (prefix_match) {
            std::string entry_prefix = entry_value.substr(0, search_value.size());
            std::string search_prefix = search_value;
            if (entry_prefix < search_prefix) lo = mid + 1;
            else if (entry_prefix > search_prefix) hi = mid - 1;
            else { first_match = mid; hi = mid - 1; }
        } else {
            if (entry_value < padded_search) lo = mid + 1;
            else if (entry_value > padded_search) hi = mid - 1;
            else { first_match = mid; hi = mid - 1; }
        }
    }

    if (first_match < 0) return matches;

    // Collect all matching entries
    for (int i = first_match; i < total_entries; i++) {
        size_t offset = data_start + (size_t)i * entry_size;
        if (offset + entry_size > end_boundary) break;

        uint16_t length = parser.pubReadU16(offset);
        if (length != seg.field_width) break;

        std::string entry_value((char*)&parser.data[offset + 2], seg.field_width);
        std::string stripped = entry_value;
        stripped.erase(stripped.find_last_not_of(' ') + 1);

        std::string search_stripped = search_value;
        search_stripped.erase(search_stripped.find_last_not_of(' ') + 1);

        if (prefix_match) {
            if (stripped.substr(0, search_stripped.size()) != search_stripped) break;
        } else {
            if (stripped != search_stripped) break;
        }

        IndexEntry entry;
        entry.value = stripped;

        size_t trailing_start = offset + 2 + seg.field_width;
        if (is_u32) {
            entry.u32_index = parser.pubReadU32(trailing_start);
            entry.page_number = 0;
            entry.entry_format = "u32_index";
        } else {
            entry.page_number = parser.pubReadU16(trailing_start);
            entry.u32_index = 0;
            entry.entry_format = "page";
        }

        matches.push_back(entry);
    }

    return matches;
}

// ============================================================================
// Page Resolution (Segment 0 lookup for u32_index format)
// ============================================================================

std::map<uint32_t, int> buildSegment0PageLookup(MapFileParser& parser) {
    std::map<uint32_t, int> lookup;

    if (parser.segments.empty()) return lookup;

    const auto& seg0 = parser.segments[0];
    int record_size = 15;
    size_t offset = seg0.data_offset;
    size_t end = std::min((size_t)(seg0.offset + seg0.size), parser.data.size());

    while (offset + record_size <= end) {
        if (offset + record_size > parser.data.size()) break;

        uint32_t page_raw = parser.pubReadU32(offset);
        uint8_t rec_type = parser.data[offset + 5];
        uint32_t u32_join_key = parser.pubReadU32(offset + 7);

        if (rec_type == 0x08) {
            int page_number = (int)(page_raw & 0x7FFFFFFF);
            lookup[u32_join_key] = page_number;
        }

        offset += record_size;
    }

    return lookup;
}

std::vector<SearchResult> resolvePages(
    const std::vector<IndexEntry>& entries,
    MapFileParser& parser
) {
    std::vector<SearchResult> results;

    if (entries.empty()) return results;

    if (entries[0].entry_format == "page") {
        for (const auto& e : entries) {
            results.push_back({e.value, e.page_number, 0, "page"});
        }
    } else {
        auto lookup = buildSegment0PageLookup(parser);
        for (const auto& e : entries) {
            int page = 0;
            auto it = lookup.find(e.u32_index);
            if (it != lookup.end()) page = it->second;
            results.push_back({e.value, page, e.u32_index, "u32_index"});
        }
        if (lookup.empty()) {
            std::cerr << "WARNING: Could not build Segment 0 page lookup for u32_index resolution\n";
        }
    }

    return results;
}

// ============================================================================
// Output Functions
// ============================================================================

void outputTable(const std::vector<SearchResult>& results,
                 const std::string& field_name, int line_id, int field_id,
                 int field_width, int entry_count, int seg_index) {

    std::cout << "\nSegment " << seg_index << ": LINE_ID=" << line_id
              << ", FIELD_ID=" << field_id;
    if (!field_name.empty()) std::cout << " (" << field_name << ")";
    std::cout << "\nField width: " << field_width << ", Entry count: " << entry_count << "\n";

    if (results.empty()) {
        std::cout << "\nNo matches found.\n";
        return;
    }

    std::cout << "\n" << results.size() << " match(es) found:\n\n";

    int val_width = 5;
    for (const auto& r : results) {
        val_width = std::max(val_width, (int)r.value.size());
    }

    if (results[0].format == "u32_index") {
        std::cout << "  " << std::left << std::setw(val_width) << "VALUE"
                  << "  " << std::right << std::setw(8) << "PAGE"
                  << "  " << std::setw(12) << "U32_INDEX" << "\n";
        std::cout << "  " << std::string(val_width, '-')
                  << "  " << std::string(8, '-')
                  << "  " << std::string(12, '-') << "\n";
        for (const auto& r : results) {
            std::string page_str = r.page > 0 ? std::to_string(r.page) : "(unresolved)";
            std::cout << "  " << std::left << std::setw(val_width) << r.value
                      << "  " << std::right << std::setw(8) << page_str
                      << "  " << std::setw(12) << r.u32_index << "\n";
        }
    } else {
        std::cout << "  " << std::left << std::setw(val_width) << "VALUE"
                  << "  " << std::right << std::setw(8) << "PAGE" << "\n";
        std::cout << "  " << std::string(val_width, '-')
                  << "  " << std::string(8, '-') << "\n";
        for (const auto& r : results) {
            std::cout << "  " << std::left << std::setw(val_width) << r.value
                      << "  " << std::right << std::setw(8) << r.page << "\n";
        }
    }
}

void outputCsv(const std::vector<SearchResult>& results) {
    if (results.empty()) return;

    if (results[0].format == "u32_index") {
        std::cout << "value,page,u32_index\n";
        for (const auto& r : results) {
            std::cout << r.value << "," << r.page << "," << r.u32_index << "\n";
        }
    } else {
        std::cout << "value,page\n";
        for (const auto& r : results) {
            std::cout << r.value << "," << r.page << "\n";
        }
    }
}

void outputJson(const std::vector<SearchResult>& results,
                const std::string& field_name, int line_id, int field_id,
                int entry_count, int seg_index) {
    std::cout << "{\n"
              << "  \"matches\": [\n";
    for (size_t i = 0; i < results.size(); i++) {
        std::cout << "    {\"value\": \"" << results[i].value
                  << "\", \"page\": " << results[i].page;
        if (results[i].format == "u32_index") {
            std::cout << ", \"u32_index\": " << results[i].u32_index;
        }
        std::cout << "}" << (i + 1 < results.size() ? "," : "") << "\n";
    }
    std::cout << "  ],\n"
              << "  \"match_count\": " << results.size() << ",\n"
              << "  \"field\": \"" << (field_name.empty() ? "L" + std::to_string(line_id) + "/F" + std::to_string(field_id) : field_name) << "\",\n"
              << "  \"line_id\": " << line_id << ",\n"
              << "  \"field_id\": " << field_id << ",\n"
              << "  \"segment\": " << seg_index << ",\n"
              << "  \"entry_count\": " << entry_count << ",\n"
              << "  \"format\": \"" << (results.empty() ? "unknown" : results[0].format) << "\"\n"
              << "}\n";
}

// ============================================================================
// List Fields
// ============================================================================

void listFields(MapFileParser& parser, MetadataResolver* metadata) {
    if (parser.segments.empty()) {
        std::cout << "No segments found in MAP file.\n";
        return;
    }

    std::cout << "\nMAP File: " << parser.header.filename << "\n";
    if (!parser.header.date_string.empty())
        std::cout << "Date: " << parser.header.date_string << "\n";
    std::cout << "Segment count: " << parser.header.segment_count << "\n";

    if (metadata && !metadata->species_name.empty()) {
        std::cout << "Species: " << metadata->species_name << "\n";
    }

    int field_seg_count = 0;
    for (const auto& seg : parser.segments) {
        if (seg.index > 0) field_seg_count++;
    }

    std::cout << "\nIndexed Fields (" << field_seg_count << " segments):\n\n";

    if (metadata && !metadata->indexed_fields.empty()) {
        std::cout << "  " << std::right << std::setw(3) << "SEG"
                  << "  " << std::setw(7) << "LINE_ID"
                  << "  " << std::setw(8) << "FIELD_ID"
                  << "  " << std::left << std::setw(20) << "NAME"
                  << "  " << std::right << std::setw(5) << "WIDTH"
                  << "  " << std::setw(8) << "ENTRIES"
                  << "  " << "COLUMNS" << "\n";
        std::cout << "  " << std::string(3, '-')
                  << "  " << std::string(7, '-')
                  << "  " << std::string(8, '-')
                  << "  " << std::string(20, '-')
                  << "  " << std::string(5, '-')
                  << "  " << std::string(8, '-')
                  << "  " << std::string(7, '-') << "\n";
    } else {
        std::cout << "  " << std::right << std::setw(3) << "SEG"
                  << "  " << std::setw(7) << "LINE_ID"
                  << "  " << std::setw(8) << "FIELD_ID"
                  << "  " << std::setw(5) << "WIDTH"
                  << "  " << std::setw(8) << "ENTRIES" << "\n";
        std::cout << "  " << std::string(3, '-')
                  << "  " << std::string(7, '-')
                  << "  " << std::string(8, '-')
                  << "  " << std::string(5, '-')
                  << "  " << std::string(8, '-') << "\n";
    }

    for (const auto& seg : parser.segments) {
        if (seg.index == 0) continue;

        std::string name = "";
        std::string columns = "";

        if (metadata) {
            for (const auto& f : metadata->indexed_fields) {
                if (f.line_id == seg.line_id && f.field_id == seg.field_id) {
                    name = f.name;
                    if (f.start_column > 0 || f.end_column > 0) {
                        columns = std::to_string(f.start_column) + "-" + std::to_string(f.end_column);
                    }
                    break;
                }
            }
        }

        if (metadata && !metadata->indexed_fields.empty()) {
            std::cout << "  " << std::right << std::setw(3) << seg.index
                      << "  " << std::setw(7) << seg.line_id
                      << "  " << std::setw(8) << seg.field_id
                      << "  " << std::left << std::setw(20) << name
                      << "  " << std::right << std::setw(5) << seg.field_width
                      << "  " << std::setw(8) << seg.entry_count
                      << "  " << columns << "\n";
        } else {
            std::cout << "  " << std::right << std::setw(3) << seg.index
                      << "  " << std::setw(7) << seg.line_id
                      << "  " << std::setw(8) << seg.field_id
                      << "  " << std::setw(5) << seg.field_width
                      << "  " << std::setw(8) << seg.entry_count << "\n";
        }
    }
}

// ============================================================================
// List Values
// ============================================================================

void listValues(MapFileParser& parser, int line_id, int field_id,
                MetadataResolver* metadata, int max_values) {

    auto* seg = parser.findSegmentForField(line_id, field_id);
    if (!seg) {
        std::cerr << "No segment found for LINE_ID=" << line_id << ", FIELD_ID=" << field_id << "\n";
        return;
    }

    std::string field_name = "LINE " + std::to_string(line_id) + " / FIELD " + std::to_string(field_id);
    if (metadata) {
        for (const auto& f : metadata->indexed_fields) {
            if (f.line_id == line_id && f.field_id == field_id) {
                field_name = f.name;
                break;
            }
        }
    }

    // Read all entries
    int entry_size = 7 + seg->field_width;
    size_t end_boundary = std::min((size_t)(seg->offset + seg->size), parser.data.size());

    std::map<std::string, int> value_counts;
    int total_entries = 0;

    for (size_t offset = seg->data_offset; offset + entry_size <= end_boundary; offset += entry_size) {
        uint16_t length = parser.pubReadU16(offset);
        if (length != seg->field_width) break;

        std::string value((char*)&parser.data[offset + 2], seg->field_width);
        value.erase(value.find_last_not_of(' ') + 1);  // trim trailing spaces

        value_counts[value]++;
        total_entries++;

        if (max_values > 0 && total_entries >= max_values) break;
    }

    std::cout << "\nField: " << field_name << " (LINE_ID=" << line_id << ", FIELD_ID=" << field_id << ")\n";
    std::cout << "Total entries: " << total_entries << ", Unique values: " << value_counts.size() << "\n\n";
    std::cout << "  " << std::left << std::setw(seg->field_width + 2) << "VALUE"
              << "  " << std::right << std::setw(6) << "COUNT" << "\n";
    std::cout << "  " << std::string(seg->field_width + 2, '-')
              << "  " << std::string(6, '-') << "\n";

    for (const auto& [value, count] : value_counts) {
        std::cout << "  " << std::left << std::setw(seg->field_width + 2) << value
                  << "  " << std::right << std::setw(6) << count << "\n";
    }
}

// ============================================================================
// Usage
// ============================================================================

void printUsage(const char* progname) {
    std::cout << "Usage: " << progname << " [options]\n\n"
              << "Standalone MAP file index search tool.\n"
              << "Searches for indexed field values in binary MAP files.\n\n"
              << "MAP file:\n"
              << "  --map FILE             Path to MAP file (required)\n\n"
              << "Metadata (optional):\n"
              << "  --metadata JSON        Path to species metadata JSON file\n\n"
              << "Field specification:\n"
              << "  --field NAME           Field name (requires --metadata)\n"
              << "  --line-id N            LINE_ID (raw numeric)\n"
              << "  --field-id N           FIELD_ID (raw numeric)\n\n"
              << "Search:\n"
              << "  --value TEXT           Value to search for\n"
              << "  --prefix               Enable prefix matching (default: exact)\n\n"
              << "Listing modes:\n"
              << "  --list-fields          List all indexed fields in the MAP file\n"
              << "  --list-values          List all values for the specified field\n"
              << "  --max-values N         Max values to list (0 = all, default: 0)\n\n"
              << "Output:\n"
              << "  --format FMT           Output format: table, csv, json (default: table)\n"
              << "  --help                 Show this help\n\n"
              << "Examples:\n"
              << "  # Search by raw IDs:\n"
              << "  " << progname << " --map 25001002.MAP --line-id 5 --field-id 3 --value \"200-044295-001\"\n\n"
              << "  # Search by field name (requires metadata JSON):\n"
              << "  " << progname << " --map 25001002.MAP --metadata DDU017P_metadata.json --field ACCOUNT_NO --value \"200-044295-001\"\n\n"
              << "  # Prefix search:\n"
              << "  " << progname << " --map 25001002.MAP --line-id 5 --field-id 3 --value \"200-044\" --prefix\n\n"
              << "  # List all indexed fields:\n"
              << "  " << progname << " --map 25001002.MAP --list-fields\n\n"
              << "  # List all values for a field:\n"
              << "  " << progname << " --map 25001002.MAP --line-id 5 --field-id 3 --list-values\n\n"
              << "  # Output as JSON:\n"
              << "  " << progname << " --map 25001002.MAP --line-id 5 --field-id 3 --value \"200-044295-001\" --format json\n";
}

// ============================================================================
// Main
// ============================================================================

int main(int argc, char* argv[]) {
    // Parse arguments
    std::string map_path;
    std::string metadata_path;
    std::string field_name;
    int line_id = -1;
    int field_id = -1;
    std::string search_value;
    bool prefix_match = false;
    bool do_list_fields = false;
    bool do_list_values = false;
    int max_values = 0;
    std::string format = "table";

    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];

        if (arg == "--help") {
            printUsage(argv[0]);
            return 0;
        } else if (arg == "--map" && i + 1 < argc) {
            map_path = argv[++i];
        } else if (arg == "--metadata" && i + 1 < argc) {
            metadata_path = argv[++i];
        } else if (arg == "--field" && i + 1 < argc) {
            field_name = argv[++i];
        } else if (arg == "--line-id" && i + 1 < argc) {
            line_id = std::stoi(argv[++i]);
        } else if (arg == "--field-id" && i + 1 < argc) {
            field_id = std::stoi(argv[++i]);
        } else if (arg == "--value" && i + 1 < argc) {
            search_value = argv[++i];
        } else if (arg == "--prefix") {
            prefix_match = true;
        } else if (arg == "--list-fields") {
            do_list_fields = true;
        } else if (arg == "--list-values") {
            do_list_values = true;
        } else if (arg == "--max-values" && i + 1 < argc) {
            max_values = std::stoi(argv[++i]);
        } else if (arg == "--format" && i + 1 < argc) {
            format = argv[++i];
        } else {
            std::cerr << "Unknown argument: " << arg << "\n";
            printUsage(argv[0]);
            return 1;
        }
    }

    // Validate --map
    if (map_path.empty()) {
        std::cerr << "Error: --map is required.\n\n";
        printUsage(argv[0]);
        return 1;
    }

    if (!fs::exists(map_path)) {
        std::cerr << "ERROR: MAP file not found: " << map_path << "\n";
        return 1;
    }

    // Load MAP file
    MapFileParser parser;
    if (!parser.load(map_path)) {
        return 1;
    }
    parser.parseSegments();

    // Load metadata if provided
    MetadataResolver* metadata = nullptr;
    MetadataResolver metadata_obj;
    if (!metadata_path.empty()) {
        if (!fs::exists(metadata_path)) {
            std::cerr << "ERROR: Metadata file not found: " << metadata_path << "\n";
            return 1;
        }
        if (!metadata_obj.load(metadata_path)) {
            std::cerr << "ERROR: Failed to parse metadata file: " << metadata_path << "\n";
            return 1;
        }
        metadata = &metadata_obj;
    }

    // === Mode: List fields ===
    if (do_list_fields) {
        listFields(parser, metadata);
        return 0;
    }

    // === Resolve field ===
    if (!field_name.empty()) {
        if (!metadata) {
            std::cerr << "ERROR: --field requires --metadata to resolve field names.\n"
                      << "Use --line-id and --field-id for raw ID mode (no metadata needed).\n";
            return 1;
        }
        auto* resolved = metadata->resolveField(field_name);
        if (!resolved) {
            std::cerr << "ERROR: Field '" << field_name << "' not found in metadata.\n"
                      << "\nAvailable indexed fields:\n";
            for (const auto& f : metadata->indexed_fields) {
                std::cerr << "  " << f.name << " (LINE_ID=" << f.line_id << ", FIELD_ID=" << f.field_id << ")\n";
            }
            return 1;
        }
        line_id = resolved->line_id;
        field_id = resolved->field_id;
        std::cerr << "Resolved '" << field_name << "' -> LINE_ID=" << line_id << ", FIELD_ID=" << field_id << "\n";
    }

    // Check field IDs
    if (line_id < 0 || field_id < 0) {
        std::cerr << "ERROR: Must specify either --field NAME (with --metadata) "
                  << "or --line-id N --field-id N\n";
        return 1;
    }

    // === Mode: List values ===
    if (do_list_values) {
        listValues(parser, line_id, field_id, metadata, max_values);
        return 0;
    }

    // === Mode: Search ===
    if (search_value.empty()) {
        std::cerr << "ERROR: --value is required for search mode.\n"
                  << "Use --list-fields to see available fields, or --list-values to see all values.\n";
        return 1;
    }

    // Find segment
    auto* seg = parser.findSegmentForField(line_id, field_id);
    if (!seg) {
        std::cerr << "ERROR: No segment found for LINE_ID=" << line_id << ", FIELD_ID=" << field_id << "\n"
                  << "\nAvailable segments:\n";
        for (const auto& s : parser.segments) {
            if (s.index > 0) {
                std::cerr << "  Segment " << s.index << ": LINE_ID=" << s.line_id << ", FIELD_ID=" << s.field_id << "\n";
            }
        }
        return 1;
    }

    auto t0 = std::chrono::steady_clock::now();

    // Search
    auto matches = binarySearchEntries(parser, *seg, search_value, prefix_match);
    auto results = resolvePages(matches, parser);

    auto t1 = std::chrono::steady_clock::now();
    double elapsed_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();

    // Get field name for display
    std::string display_name = "";
    if (metadata) {
        for (const auto& f : metadata->indexed_fields) {
            if (f.line_id == line_id && f.field_id == field_id) {
                display_name = f.name;
                break;
            }
        }
    }

    // Output
    if (format == "table") {
        outputTable(results, display_name, line_id, field_id,
                   seg->field_width, seg->entry_count, seg->index);
        std::cout << "\nSearch completed in " << std::fixed << std::setprecision(1) << elapsed_ms << "ms\n";
    } else if (format == "csv") {
        outputCsv(results);
    } else if (format == "json") {
        outputJson(results, display_name, line_id, field_id, seg->entry_count, seg->index);
    }

    return 0;
}
