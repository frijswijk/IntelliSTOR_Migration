// papyrus_rpt_search_page_extract.cpp
//
// Combined MAP File Search + RPT Page Extractor
//
// Merges papyrus_rpt_search.cpp (MAP index search) with rpt_page_extractor.cpp
// (RPT page decompression and extraction).
//
// Modes:
//   1. Normal RPT extraction (backward-compatible with rpt_page_extractor):
//      All existing flags: --pages, --section-id, --info, --binary-only, etc.
//
//   2. MAP search + extract:
//      --map FILE --line-id N --field-id N --value TEXT [RPT files]
//      Searches MAP file for value -> extracts matching pages from RPT
//
//   3. MAP search + section intersection:
//      --map FILE --line-id N --field-id N --value TEXT --section-id ID [RPT files]
//      Searches MAP -> intersects with section pages -> extracts only overlapping
//
// No database or ODBC required. Reads binary MAP + RPT files directly.
// Requires zlib for RPT decompression.
//
// Compile (Windows/MinGW):
//   g++ -std=c++17 -O2 -static -o papyrus_rpt_search_page_extract.exe papyrus_rpt_search_page_extract.cpp -lz
//
// Compile (macOS):
//   clang++ -std=c++17 -O2 -o papyrus_rpt_search_page_extract papyrus_rpt_search_page_extract.cpp -lz

#include <algorithm>
#include <chrono>
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
// MAP Data Structures (from papyrus_rpt_search.cpp)
// ============================================================================

struct MapHeader {
    std::string filename;
    std::string date_string;
    int segment_count = 0;
    int total_size = 0;
};

struct MapSegment {
    int index = 0;
    int offset = 0;
    int size = 0;
    int data_offset = 0;
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
    std::string format;
};

struct MetadataField {
    std::string name;
    int line_id = 0;
    int field_id = 0;
    int start_column = 0;
    int end_column = 0;
};

// ============================================================================
// RPT Data Structures (from rpt_page_extractor.cpp)
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

struct BinaryDocument {
    std::vector<uint8_t> data;
    std::string filename;
    std::string format_description;
};

struct ExtractionStats {
    std::string file;
    uint32_t pages_total        = 0;
    uint32_t pages_selected     = 0;
    uint32_t pages_extracted    = 0;
    uint64_t bytes_compressed   = 0;
    uint64_t bytes_decompressed = 0;
    uint32_t binary_objects     = 0;
    std::string binary_filename;
    uint64_t binary_size        = 0;
    std::string error;
};

// ============================================================================
// Little-endian helpers (RPT)
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
// Utility: sanitize string for use in file/directory names
// ============================================================================

static std::string sanitize_for_path(const std::string& s, size_t max_len = 80) {
    std::string result;
    result.reserve(s.size());
    for (char c : s) {
        if (c == '/' || c == '\\' || c == ':' || c == '*' || c == '?' ||
            c == '"' || c == '<'  || c == '>' || c == '|' || c == ' ') {
            result += '_';
        } else {
            result += c;
        }
    }
    if (result.size() > max_len) {
        result = result.substr(0, max_len);
    }
    return result;
}

// ============================================================================
// MAP File Parser
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
// ============================================================================

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

        // Check MAPHDR signature (UTF-16LE: "MAPHDR" = 12 bytes)
        // Decode first 12 bytes as UTF-16LE
        std::string sig;
        for (size_t i = 0; i + 1 < 12 && i + 1 < data.size(); i += 2) {
            if (data[i + 1] == 0 && data[i] >= 32 && data[i] < 127) {
                sig += (char)data[i];
            }
        }
        // sig should be "MAPHDR"

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
            // Trim trailing nulls
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
                    // +2: line_id, +6: field_id, +10: field_width, +14: entry_count
                    seg.line_id     = readU16(meta_off + 2);
                    seg.field_id    = readU16(meta_off + 6);
                    seg.field_width = readU16(meta_off + 10);
                    seg.entry_count = readU16(meta_off + 14);
                }

                // Dynamically find data_offset: search [me_pos+0xC0, me_pos+0xE0]
                // for first entry whose 2-byte length == field_width
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
            return (int)(me_pos + 0xCD); // Fallback
        }

        size_t search_start = me_pos + 0xC0;
        size_t search_end   = std::min(me_pos + 0xE0, next_pos - 2);

        for (size_t probe = search_start; probe < search_end; probe++) {
            if (probe + 2 > data.size()) break;
            uint16_t probe_len = readU16(probe);
            if (probe_len == (uint16_t)field_width) {
                // Verify: following bytes should look like ASCII data
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

        // Fallback to hardcoded offset
        return (int)(me_pos + 0xCD);
    }

public:
    uint16_t pubReadU16(size_t offset) { return readU16(offset); }
    uint32_t pubReadU32(size_t offset) { return readU32(offset); }
};

// ============================================================================
// Metadata Resolver (from papyrus_rpt_search.cpp)
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

        species_name = extractJsonString(content, "\"name\"");

        size_t arr_start = content.find("\"indexed_fields\"");
        if (arr_start == std::string::npos) return true;

        size_t bracket_start = content.find('[', arr_start);
        size_t bracket_end = findMatchingBracket(content, bracket_start);

        if (bracket_start == std::string::npos || bracket_end == std::string::npos)
            return true;

        std::string arr_content = content.substr(bracket_start + 1, bracket_end - bracket_start - 1);

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
// MAP Entry Format Detection (from papyrus_rpt_search.cpp)
// ============================================================================

static bool detectU32Format(MapFileParser& parser, const MapSegment& seg, int sample_count) {
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
// MAP Binary Search (from papyrus_rpt_search.cpp)
// ============================================================================

static std::vector<IndexEntry> binarySearchEntries(
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
// MAP Page Resolution (Segment 0 lookup for u32_index format)
// ============================================================================

static std::map<uint32_t, int> buildSegment0PageLookup(MapFileParser& parser) {
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

static std::vector<SearchResult> resolvePages(
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
// SECTIONHDR Parsing
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
            size_t data_start = (mp - region) + 13;
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
// PAGETBLHDR Parsing
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
// BPAGETBLHDR Parsing
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
// Object Header Detection
// ============================================================================

static const char* OBJECT_HEADER_PREFIX = "StorQM PLUS Object Header Page:";

static std::optional<std::map<std::string, std::string>>
parse_object_header(const std::vector<uint8_t>& page_content) {
    std::string text(page_content.begin(), page_content.end());

    if (text.find(OBJECT_HEADER_PREFIX) == std::string::npos) {
        return std::nullopt;
    }

    std::map<std::string, std::string> metadata;
    std::istringstream stream(text);
    std::string line;
    while (std::getline(stream, line)) {
        size_t start = line.find_first_not_of(" \t\r\n");
        if (start == std::string::npos) continue;
        size_t end = line.find_last_not_of(" \t\r\n");
        line = line.substr(start, end - start + 1);

        auto colon_pos = line.find(':');
        if (colon_pos == std::string::npos) continue;

        if (line.find(OBJECT_HEADER_PREFIX) == 0) continue;

        std::string key = line.substr(0, colon_pos);
        std::string value = line.substr(colon_pos + 1);

        size_t ks = key.find_first_not_of(" \t");
        size_t ke = key.find_last_not_of(" \t");
        if (ks != std::string::npos) key = key.substr(ks, ke - ks + 1);
        else continue;

        size_t vs = value.find_first_not_of(" \t");
        size_t ve = value.find_last_not_of(" \t");
        if (vs != std::string::npos) value = value.substr(vs, ve - vs + 1);
        else continue;

        if (!key.empty() && !value.empty()) {
            metadata[key] = value;
        }
    }

    return metadata;
}

static std::string detect_binary_type(const std::vector<uint8_t>& data,
                                       const std::optional<std::map<std::string, std::string>>& object_header) {
    if (data.size() >= 4 &&
        data[0] == '%' && data[1] == 'P' && data[2] == 'D' && data[3] == 'F') {
        return ".pdf";
    }

    if (!data.empty() && data[0] == 0x5A) {
        return ".afp";
    }

    if (object_header) {
        auto it = object_header->find("Object File Name");
        if (it != object_header->end()) {
            const std::string& obj_filename = it->second;
            auto dot_pos = obj_filename.rfind('.');
            if (dot_pos != std::string::npos) {
                std::string ext = obj_filename.substr(dot_pos + 1);
                std::string ext_lower;
                for (char c : ext) ext_lower += static_cast<char>(std::tolower(static_cast<unsigned char>(c)));
                if (ext_lower == "pdf" || ext_lower == "afp") {
                    return "." + ext_lower;
                }
            }
        }
    }

    return ".bin";
}

// ============================================================================
// Binary Object Decompression and Assembly
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
            std::cerr << "  WARNING: Binary object " << entry.index
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
            std::cerr << "  WARNING: Binary object " << entry.index
                      << " decompression failed (zlib error " << ret << ")\n";
            continue;
        }
        decompressed.resize(dest_len);
        results.emplace_back(entry.index, std::move(decompressed));
    }

    return results;
}

static BinaryDocument
assemble_binary_document(const std::vector<std::pair<int, std::vector<uint8_t>>>& objects,
                         const std::optional<std::map<std::string, std::string>>& object_header,
                         const std::string& rpt_name) {
    BinaryDocument doc;

    size_t total_size = 0;
    for (const auto& [idx, data] : objects) {
        total_size += data.size();
    }
    doc.data.reserve(total_size);
    for (const auto& [idx, data] : objects) {
        doc.data.insert(doc.data.end(), data.begin(), data.end());
    }

    std::string ext = detect_binary_type(doc.data, object_header);

    if (object_header) {
        auto it = object_header->find("Object File Name");
        if (it != object_header->end() && !it->second.empty()) {
            doc.filename = it->second;
            size_t s = doc.filename.find_first_not_of(" \t");
            size_t e = doc.filename.find_last_not_of(" \t");
            if (s != std::string::npos) doc.filename = doc.filename.substr(s, e - s + 1);
        }
    }
    if (doc.filename.empty()) {
        doc.filename = rpt_name + "_binary" + ext;
    }

    if (ext == ".pdf") doc.format_description = "PDF";
    else if (ext == ".afp") doc.format_description = "AFP";
    else doc.format_description = "Binary";

    return doc;
}

// ============================================================================
// Decompress a single page (for Object Header detection)
// ============================================================================

static std::optional<std::vector<uint8_t>>
decompress_single_page(const std::string& filepath, const PageTableEntry& entry) {
    std::ifstream f(filepath, std::ios::binary | std::ios::ate);
    if (!f) return std::nullopt;
    auto file_size = static_cast<size_t>(f.tellg());

    uint32_t abs_off = entry.absolute_offset();
    if (static_cast<size_t>(abs_off) + entry.compressed_size > file_size) {
        return std::nullopt;
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
        compressed.resize(entry.compressed_size + 64);
        f.seekg(abs_off);
        f.read(reinterpret_cast<char*>(compressed.data()), entry.compressed_size + 64);
        dest_len = entry.uncompressed_size;
        ret = uncompress(decompressed.data(), &dest_len,
                         compressed.data(),
                         static_cast<uLong>(entry.compressed_size + 64));
        if (ret != Z_OK) return std::nullopt;
    }
    decompressed.resize(dest_len);
    return decompressed;
}

// ============================================================================
// Page Selection
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
// Output: save_pages
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
// Main extraction (modified to support search_pages intersection)
// ============================================================================

static ExtractionStats extract_rpt(
        const std::string& filepath,
        const std::string& output_base,
        std::optional<std::pair<int,int>> page_range,
        const std::vector<uint32_t>& section_ids,
        const std::set<int>& search_pages,
        const std::string& search_description,
        bool info_only,
        bool binary_only,
        bool no_binary,
        bool page_concat,
        const std::string& export_sections_csv = "")
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

    // Read sections
    auto [shdr_opt, sections] = read_sectionhdr(filepath);
    if (shdr_opt) {
        hdr.section_count = shdr_opt->section_count;
    }

    // Read binary object table
    std::vector<BinaryObjectEntry> binary_entries;
    if (hdr.binary_object_count > 0) {
        binary_entries = read_binary_page_table(file_data, hdr.binary_object_count);
    }

    // Parse Object Header from text page 1
    std::optional<std::map<std::string, std::string>> object_header;
    if (!binary_entries.empty() && !page_entries.empty()) {
        auto first_page = decompress_single_page(filepath, page_entries[0]);
        if (first_page) {
            object_header = parse_object_header(*first_page);
        }
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
    if (hdr.binary_object_count > 0) {
        std::cout << "  Binary Objects: " << hdr.binary_object_count << "\n";
    }

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

    // Export sections as CSV if requested
    if (!export_sections_csv.empty() && !sections.empty()) {
        fs::path csv_path(export_sections_csv);
        if (csv_path.has_parent_path()) {
            std::error_code ec;
            fs::create_directories(csv_path.parent_path(), ec);
        }
        std::ofstream csv_out(export_sections_csv);
        if (!csv_out) {
            std::cerr << "  WARNING: Cannot write CSV: " << export_sections_csv << "\n";
        } else {
            csv_out << "Report_Species_Id,Section_Id,Start_Page,Pages\n";
            for (const auto& s : sections) {
                csv_out << hdr.report_species_id << ","
                        << s.section_id << ","
                        << s.start_page << ","
                        << s.page_count << "\n";
            }
            std::cout << "\n  Sections exported to: " << export_sections_csv << "\n";
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
            show.push_back(nullptr);
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

        // Show binary object table if present
        if (!binary_entries.empty()) {
            std::cout << "\n  Binary Objects (" << binary_entries.size()
                      << "):  [BPAGETBLHDR]\n";
            std::cout << "  " << std::setw(7) << std::right << "INDEX"
                      << "  " << std::setw(10) << "OFFSET"
                      << "  " << std::setw(11) << "UNCOMP_SIZE"
                      << "  " << std::setw(10) << "COMP_SIZE" << "\n";
            std::cout << "  " << std::string(7, '-')
                      << "  " << std::string(10, '-')
                      << "  " << std::string(11, '-')
                      << "  " << std::string(10, '-') << "\n";
            for (const auto& be : binary_entries) {
                std::cout << "  " << std::setw(7) << be.index
                          << "  0x" << std::hex << std::uppercase
                          << std::setw(8) << std::setfill('0') << be.absolute_offset()
                          << std::dec << std::setfill(' ')
                          << "  " << std::setw(11) << format_number(be.uncompressed_size)
                          << "  " << std::setw(10) << format_number(be.compressed_size)
                          << "\n";
            }

            if (object_header) {
                std::cout << "\n  Object Header:\n";
                for (const auto& [key, value] : *object_header) {
                    std::cout << "    " << key << ": " << value << "\n";
                }
            }

            auto bin_objs = decompress_binary_objects(filepath, binary_entries);
            if (!bin_objs.empty()) {
                auto doc = assemble_binary_document(bin_objs, object_header, rpt_name);
                std::cout << "\n  Assembled document: " << doc.format_description
                          << " (" << format_number(doc.data.size()) << " bytes)\n";
                std::cout << "  Output filename: " << doc.filename << "\n";
            }
        }

        return stats;
    }

    // =====================================================================
    // Select pages to extract (4-way logic: search+section, search, section, range, all)
    // =====================================================================
    std::vector<PageTableEntry> selected = page_entries; // default: all
    std::vector<uint32_t> found_ids;

    if (!search_pages.empty() && !section_ids.empty()) {
        // INTERSECTION MODE: search_pages ∩ section_allowed_pages
        auto sec_sel = select_pages_by_sections(page_entries, sections, section_ids);
        found_ids = std::move(sec_sel.found_ids);

        if (!sec_sel.skipped_ids.empty()) {
            std::cout << "\n  Skipped sections (not found): ";
            for (size_t i = 0; i < sec_sel.skipped_ids.size(); ++i) {
                if (i > 0) std::cout << ", ";
                std::cout << sec_sel.skipped_ids[i];
            }
            std::cout << "\n";
        }

        if (found_ids.empty()) {
            stats.error = "None of the requested section IDs found in SECTIONHDR";
            std::cout << "\n  ERROR: " << stats.error << "\n";
            return stats;
        }

        // Build set of section-allowed page numbers
        std::set<int> section_page_set;
        for (const auto& e : sec_sel.entries) {
            section_page_set.insert(e.page_number);
        }

        // Intersect: search_pages ∩ section_page_set
        std::set<int> intersection;
        for (int sp : search_pages) {
            if (section_page_set.count(sp)) {
                intersection.insert(sp);
            }
        }

        std::cout << "\n  MAP search returned " << search_pages.size() << " page(s), "
                  << "section(s) allow " << section_page_set.size() << " page(s), "
                  << "intersection: " << intersection.size() << " page(s)\n";

        if (intersection.empty()) {
            stats.error = "Search results do not overlap with the requested section(s)";
            std::cout << "  WARNING: " << stats.error << "\n";
            return stats;
        }

        // Select page_entries that are in the intersection
        selected.clear();
        for (const auto& e : page_entries) {
            if (intersection.count(e.page_number)) {
                selected.push_back(e);
            }
        }

    } else if (!search_pages.empty()) {
        // SEARCH-ONLY MODE: extract pages from MAP search
        selected.clear();
        for (const auto& e : page_entries) {
            if (search_pages.count(e.page_number)) {
                selected.push_back(e);
            }
        }
        std::cout << "\n  MAP search matched " << search_pages.size()
                  << " page(s), extracting " << selected.size() << " page(s)\n";

    } else if (!section_ids.empty()) {
        // SECTION-ONLY MODE (existing behavior, unchanged)
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

    // =====================================================================
    // Determine output directory
    // =====================================================================
    std::string output_dir;
    if (!search_pages.empty() && !section_ids.empty() && !found_ids.empty()) {
        // Search + section intersection
        std::string search_label = sanitize_for_path(search_description);
        if (found_ids.size() == 1) {
            output_dir = (fs::path(output_base) / rpt_name /
                          ("search_" + search_label + "_in_section_" +
                           std::to_string(found_ids[0]))).string();
        } else {
            std::ostringstream sid_label;
            for (size_t i = 0; i < found_ids.size(); ++i) {
                if (i > 0) sid_label << "_";
                sid_label << found_ids[i];
            }
            output_dir = (fs::path(output_base) / rpt_name /
                          ("search_" + search_label + "_in_sections_" +
                           sid_label.str())).string();
        }
    } else if (!search_pages.empty()) {
        // Search only
        std::string search_label = sanitize_for_path(search_description);
        output_dir = (fs::path(output_base) / rpt_name /
                      ("search_" + search_label)).string();
    } else if (!section_ids.empty() && !found_ids.empty()) {
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

    stats.pages_selected = static_cast<uint32_t>(selected.size());

    // -------------------------------------------------------------------
    // Extract text pages (unless --binary-only)
    // -------------------------------------------------------------------
    if (!binary_only) {
        if (page_concat) {
            if (!selected.empty()) {
                auto pages = decompress_pages(filepath, selected);
                stats.pages_extracted = static_cast<uint32_t>(pages.size());
                for (const auto& e : selected) {
                    stats.bytes_compressed += e.compressed_size;
                }
                for (const auto& [pn, content] : pages) {
                    stats.bytes_decompressed += content.size();
                }

                std::error_code ec;
                fs::create_directories(output_dir, ec);
                std::string concat_filename = rpt_name + ".txt";
                fs::path concat_path = fs::path(output_dir) / concat_filename;
                std::ofstream out(concat_path, std::ios::binary);
                if (out) {
                    for (size_t i = 0; i < pages.size(); ++i) {
                        if (i > 0) {
                            out.write("\x0c\n", 2);
                        }
                        out.write(reinterpret_cast<const char*>(pages[i].second.data()),
                                  static_cast<std::streamsize>(pages[i].second.size()));
                    }
                }

                std::cout << "  Saved concatenated text: " << concat_filename
                          << " (" << stats.pages_extracted << " pages) to "
                          << output_dir << "/\n";
                std::cout << "  Total decompressed: " << format_number(stats.bytes_decompressed)
                          << " bytes\n";

                uint32_t failed = static_cast<uint32_t>(selected.size()) - stats.pages_extracted;
                if (failed > 0) {
                    std::cout << "  WARNING: " << failed << " pages failed to decompress\n";
                }
            }
        } else {
            // Normal mode: individual page files
            std::vector<PageTableEntry> text_selected = selected;
            if (!binary_entries.empty() && object_header && !selected.empty()) {
                std::vector<PageTableEntry> filtered;
                for (const auto& e : selected) {
                    if (e.page_number != 1) filtered.push_back(e);
                }
                if (filtered.size() != selected.size()) {
                    std::cout << "  Object Header page (page 1) separated from text output\n";
                }
                text_selected = std::move(filtered);
            }

            if (!text_selected.empty()) {
                auto pages = decompress_pages(filepath, text_selected);
                stats.pages_extracted = static_cast<uint32_t>(pages.size());
                for (const auto& e : text_selected) {
                    stats.bytes_compressed += e.compressed_size;
                }
                for (const auto& [pn, content] : pages) {
                    stats.bytes_decompressed += content.size();
                }

                int saved = save_pages(pages, output_dir);
                std::cout << "  Saved " << saved << " text pages to " << output_dir << "/\n";
                std::cout << "  Total decompressed: " << format_number(stats.bytes_decompressed)
                          << " bytes\n";

                uint32_t failed = static_cast<uint32_t>(text_selected.size()) - stats.pages_extracted;
                if (failed > 0) {
                    std::cout << "  WARNING: " << failed << " pages failed to decompress\n";
                }
            }

            // Save Object Header as separate file
            if (!binary_entries.empty() && object_header) {
                auto first_page = decompress_single_page(filepath, page_entries[0]);
                if (first_page) {
                    std::error_code ec;
                    fs::create_directories(output_dir, ec);
                    fs::path oh_path = fs::path(output_dir) / "object_header.txt";
                    std::ofstream oh_out(oh_path, std::ios::binary);
                    if (oh_out) {
                        oh_out.write(reinterpret_cast<const char*>(first_page->data()),
                                     static_cast<std::streamsize>(first_page->size()));
                        std::cout << "  Saved object_header.txt to " << output_dir << "/\n";
                    }
                }
            }
        }
    } else {
        if (binary_entries.empty()) {
            stats.error = "No binary objects found in this RPT file (--binary-only requires BPAGETBLHDR)";
            std::cout << "\n  ERROR: " << stats.error << "\n";
            return stats;
        }
    }

    // -------------------------------------------------------------------
    // Extract binary objects (unless --no-binary)
    // -------------------------------------------------------------------
    if (!no_binary && !binary_entries.empty()) {
        auto bin_objs = decompress_binary_objects(filepath, binary_entries);
        if (!bin_objs.empty()) {
            auto doc = assemble_binary_document(bin_objs, object_header, rpt_name);

            std::error_code ec;
            fs::create_directories(output_dir, ec);
            fs::path bin_path = fs::path(output_dir) / doc.filename;
            std::ofstream bin_out(bin_path, std::ios::binary);
            if (bin_out) {
                bin_out.write(reinterpret_cast<const char*>(doc.data.data()),
                              static_cast<std::streamsize>(doc.data.size()));
            }

            stats.binary_objects  = static_cast<uint32_t>(bin_objs.size());
            stats.binary_filename = doc.filename;
            stats.binary_size     = doc.data.size();

            std::cout << "  Saved " << doc.format_description
                      << " document: " << doc.filename
                      << " (" << format_number(doc.data.size()) << " bytes) to "
                      << output_dir << "/\n";
        } else {
            std::cout << "  WARNING: Binary objects found but all decompression failed\n";
        }
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
"Combined MAP File Search + RPT Page Extractor.\n"
"Searches MAP file indexes and extracts matching pages from RPT files.\n"
"Fully backward-compatible with rpt_page_extractor.\n"
"\n"
"RPT Extraction Options:\n"
"  --info                Show RPT file info without extracting\n"
"  --pages <range>       Page range \"10-20\" or \"5\" (1-based, inclusive)\n"
"  --section-id <id...>  One or more SECTION_IDs (in order, skips missing)\n"
"  --folder <dir>        Process all .RPT files in directory\n"
"  --output <dir>        Output base directory (default: \".\")\n"
"  --binary-only         Extract only the binary document (PDF/AFP), skip text pages\n"
"  --no-binary           Extract only text pages, skip binary objects (PDF/AFP)\n"
"  --page-concat         Concatenate all text pages into a single file (form-feed separated)\n"
"  --export-sections <file>  Export section table as CSV\n"
"\n"
"MAP Search Options:\n"
"  --map <file>          Path to MAP file for index search\n"
"  --metadata <json>     Path to species metadata JSON (for --field NAME mode)\n"
"  --field <name>        Field name (requires --metadata), e.g., ACCOUNT_NO\n"
"  --line-id <n>         LINE_ID (raw numeric, no metadata needed)\n"
"  --field-id <n>        FIELD_ID (raw numeric)\n"
"  --value <text>        Value to search for (required when --map is used)\n"
"  --prefix              Enable prefix matching (default: exact match)\n"
"\n"
"General:\n"
"  --help                Show this help\n"
"\n"
"Search Modes:\n"
"  When --map is provided, the tool first searches the MAP file for the\n"
"  specified value, then extracts matching pages from the RPT file(s).\n"
"\n"
"  Combined with --section-id, it intersects the search results with the\n"
"  section's page range, so the user only sees search hits within their\n"
"  allowed sections.\n"
"\n"
"Examples:\n"
"  # Normal RPT extraction (backward-compatible)\n"
"  " << prog << " --info 260271NL.RPT\n"
"  " << prog << " --section-id 14259 251110OD.RPT\n"
"  " << prog << " --pages 10-20 251110OD.RPT\n"
"\n"
"  # MAP search + extract pages\n"
"  " << prog << " --map 2511109P.MAP --line-id 8 --field-id 1 \\\n"
"      --value \"200-044295-001\" 251110OD.RPT\n"
"\n"
"  # MAP search + extract (using field name from metadata)\n"
"  " << prog << " --map 2511109P.MAP --metadata DDU017P_metadata.json \\\n"
"      --field ACCOUNT_NO --value \"200-044295-001\" 251110OD.RPT\n"
"\n"
"  # MAP search with prefix matching\n"
"  " << prog << " --map 2511109P.MAP --line-id 8 --field-id 1 \\\n"
"      --value \"200-044\" --prefix 251110OD.RPT\n"
"\n"
"  # MAP search + section intersection (only pages in section AND matching search)\n"
"  " << prog << " --map 2511109P.MAP --line-id 8 --field-id 1 \\\n"
"      --value \"200-044295-001\" --section-id 14259 251110OD.RPT\n"
"\n"
"  # MAP search + concatenate matching pages\n"
"  " << prog << " --map 2511109P.MAP --line-id 8 --field-id 1 \\\n"
"      --value \"200-044295-001\" --page-concat 251110OD.RPT\n"
"\n"
"  # Process all RPT files in a folder with MAP search\n"
"  " << prog << " --map 2511109P.MAP --line-id 8 --field-id 1 \\\n"
"      --value \"200-044295-001\" --folder /path/to/rpt/files\n";
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

    // --- Parse arguments ---
    // RPT extraction flags
    bool info_only = false;
    bool binary_only = false;
    bool no_binary = false;
    bool page_concat = false;
    std::string pages_str;
    std::vector<uint32_t> section_ids;
    std::string folder;
    std::string output_base = ".";
    std::string export_sections_csv;
    std::vector<std::string> rpt_files;

    // MAP search flags
    std::string map_path;
    std::string metadata_path;
    std::string field_name;
    int map_line_id = -1;
    int map_field_id = -1;
    std::string search_value;
    bool prefix_match = false;

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];

        if (arg == "--help" || arg == "-h") {
            print_help(argv[0]);
            return 0;
        }
        else if (arg == "--info") {
            info_only = true;
        }
        else if (arg == "--binary-only") {
            binary_only = true;
        }
        else if (arg == "--no-binary") {
            no_binary = true;
        }
        else if (arg == "--page-concat") {
            page_concat = true;
        }
        else if (arg == "--export-sections") {
            if (i + 1 >= argc) {
                std::cerr << "Error: --export-sections requires a file path\n";
                return 1;
            }
            export_sections_csv = argv[++i];
        }
        else if (arg == "--pages") {
            if (i + 1 >= argc) {
                std::cerr << "Error: --pages requires an argument\n";
                return 1;
            }
            pages_str = argv[++i];
        }
        else if (arg == "--section-id") {
            while (i + 1 < argc) {
                std::string next = argv[i + 1];
                if (next.empty() || next[0] == '-') break;
                try {
                    uint32_t sid = static_cast<uint32_t>(std::stoul(next));
                    section_ids.push_back(sid);
                    ++i;
                } catch (...) {
                    break;
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
        // MAP search arguments
        else if (arg == "--map") {
            if (i + 1 >= argc) {
                std::cerr << "Error: --map requires a file path\n";
                return 1;
            }
            map_path = argv[++i];
        }
        else if (arg == "--metadata") {
            if (i + 1 >= argc) {
                std::cerr << "Error: --metadata requires a file path\n";
                return 1;
            }
            metadata_path = argv[++i];
        }
        else if (arg == "--field") {
            if (i + 1 >= argc) {
                std::cerr << "Error: --field requires a name\n";
                return 1;
            }
            field_name = argv[++i];
        }
        else if (arg == "--line-id") {
            if (i + 1 >= argc) {
                std::cerr << "Error: --line-id requires a number\n";
                return 1;
            }
            map_line_id = std::stoi(argv[++i]);
        }
        else if (arg == "--field-id") {
            if (i + 1 >= argc) {
                std::cerr << "Error: --field-id requires a number\n";
                return 1;
            }
            map_field_id = std::stoi(argv[++i]);
        }
        else if (arg == "--value") {
            if (i + 1 >= argc) {
                std::cerr << "Error: --value requires text\n";
                return 1;
            }
            search_value = argv[++i];
        }
        else if (arg == "--prefix") {
            prefix_match = true;
        }
        else if (arg[0] == '-') {
            std::cerr << "Error: Unknown option: " << arg << "\n";
            return 1;
        }
        else {
            rpt_files.push_back(arg);
        }
    }

    // --- Validate arguments ---
    if (rpt_files.empty() && folder.empty()) {
        std::cerr << "Error: Provide either RPT file path(s) or --folder <directory>\n";
        return 1;
    }

    if (!pages_str.empty() && !section_ids.empty()) {
        std::cerr << "Error: Cannot use both --pages and --section-id\n";
        return 1;
    }

    if (!pages_str.empty() && !map_path.empty()) {
        std::cerr << "Error: Cannot use both --pages and --map (MAP search determines pages)\n";
        return 1;
    }

    if (binary_only && no_binary) {
        std::cerr << "Error: Cannot use both --binary-only and --no-binary\n";
        return 1;
    }

    if (page_concat && binary_only) {
        std::cerr << "Error: Cannot use both --page-concat and --binary-only\n";
        return 1;
    }

    // Validate MAP search arguments
    if (!map_path.empty()) {
        if (search_value.empty()) {
            std::cerr << "Error: --map requires --value\n";
            return 1;
        }
        if (!field_name.empty()) {
            if (metadata_path.empty()) {
                std::cerr << "Error: --field requires --metadata to resolve field names.\n"
                          << "Use --line-id and --field-id for raw ID mode.\n";
                return 1;
            }
        } else {
            if (map_line_id < 0 || map_field_id < 0) {
                std::cerr << "Error: --map + --value requires either (--line-id + --field-id) "
                          << "or (--field + --metadata)\n";
                return 1;
            }
        }
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
        for (const auto& f : rpt_files) {
            if (!fs::exists(f)) {
                std::cerr << "Error: RPT file not found: " << f << "\n";
                return 1;
            }
        }
    }

    // =====================================================================
    // MAP Search Phase (if --map provided)
    // =====================================================================
    std::set<int> search_pages;
    std::string search_description;

    if (!map_path.empty()) {
        if (!fs::exists(map_path)) {
            std::cerr << "ERROR: MAP file not found: " << map_path << "\n";
            return 1;
        }

        MapFileParser parser;
        if (!parser.load(map_path)) {
            return 1;
        }
        parser.parseSegments();

        // Load metadata if provided
        MetadataResolver metadata_obj;
        MetadataResolver* metadata = nullptr;
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

        // Resolve field name to IDs if --field used
        if (!field_name.empty()) {
            if (!metadata) {
                std::cerr << "ERROR: --field requires --metadata\n";
                return 1;
            }
            auto* resolved = metadata->resolveField(field_name);
            if (!resolved) {
                std::cerr << "ERROR: Field '" << field_name << "' not found in metadata.\n"
                          << "\nAvailable indexed fields:\n";
                for (const auto& f : metadata->indexed_fields) {
                    std::cerr << "  " << f.name << " (LINE_ID=" << f.line_id
                              << ", FIELD_ID=" << f.field_id << ")\n";
                }
                return 1;
            }
            map_line_id = resolved->line_id;
            map_field_id = resolved->field_id;
            std::cout << "Resolved '" << field_name << "' -> LINE_ID="
                      << map_line_id << ", FIELD_ID=" << map_field_id << "\n";
        }

        // Find segment for the field
        auto* seg = parser.findSegmentForField(map_line_id, map_field_id);
        if (!seg) {
            std::cerr << "ERROR: No segment found for LINE_ID=" << map_line_id
                      << ", FIELD_ID=" << map_field_id << "\n"
                      << "\nAvailable segments:\n";
            for (const auto& s : parser.segments) {
                if (s.index > 0) {
                    std::cerr << "  Segment " << s.index << ": LINE_ID=" << s.line_id
                              << ", FIELD_ID=" << s.field_id << "\n";
                }
            }
            return 1;
        }

        auto t0 = std::chrono::steady_clock::now();

        // Binary search
        auto matches = binarySearchEntries(parser, *seg, search_value, prefix_match);
        auto results = resolvePages(matches, parser);

        auto t1 = std::chrono::steady_clock::now();
        double elapsed_ms = std::chrono::duration<double, std::milli>(t1 - t0).count();

        // Build display name for search
        std::string display_name;
        if (!field_name.empty()) {
            display_name = field_name;
        } else if (metadata) {
            for (const auto& f : metadata->indexed_fields) {
                if (f.line_id == map_line_id && f.field_id == map_field_id) {
                    display_name = f.name;
                    break;
                }
            }
        }
        if (display_name.empty()) {
            display_name = "L" + std::to_string(map_line_id) + "_F" + std::to_string(map_field_id);
        }

        // Build search_description for folder naming
        search_description = display_name + "=" + search_value;

        // Collect unique page numbers
        int unresolved_count = 0;
        for (const auto& r : results) {
            if (r.page > 0) {
                search_pages.insert(r.page);
            } else {
                unresolved_count++;
            }
        }

        // Print search summary
        std::string sep(70, '=');
        std::cout << sep << "\n";
        std::cout << "MAP Search: " << map_path << "\n";
        std::cout << "  Field: " << display_name << " (LINE_ID="
                  << map_line_id << ", FIELD_ID=" << map_field_id << ")\n";
        std::cout << "  Search: \"" << search_value << "\""
                  << (prefix_match ? " (prefix)" : " (exact)") << "\n";
        std::cout << "  Matches: " << results.size()
                  << ", Unique pages: " << search_pages.size();
        if (unresolved_count > 0) {
            std::cout << " (" << unresolved_count << " unresolved)";
        }
        std::cout << "\n";
        std::cout << "  Search time: " << std::fixed << std::setprecision(1)
                  << elapsed_ms << "ms\n";

        // Show matched pages
        if (!search_pages.empty() && search_pages.size() <= 20) {
            std::cout << "  Pages: ";
            bool first = true;
            for (int p : search_pages) {
                if (!first) std::cout << ", ";
                std::cout << p;
                first = false;
            }
            std::cout << "\n";
        }

        if (search_pages.empty()) {
            std::cout << "\n  No matching pages found. Nothing to extract.\n";
            return 0;
        }
    }

    // =====================================================================
    // RPT Extraction Phase
    // =====================================================================
    std::vector<ExtractionStats> all_stats;
    for (const auto& filepath : rpt_files) {
        auto stats = extract_rpt(filepath, output_base, page_range,
                                 section_ids, search_pages, search_description,
                                 info_only, binary_only, no_binary, page_concat,
                                 export_sections_csv);
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
