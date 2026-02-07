# IntelliSTOR Migration - Session Summary

## Date: February 2025

## Objective
Understand and document the IntelliSTOR binary MAP file structure for migration to a new system.

---

## Key Discoveries

### 1. MAP File Binary Structure

The MAP file is a binary index that enables fast search/lookup of field values in spool files.

**File Structure:**
```
[MAPHDR header - 90 bytes]
[**ME Segment 0 - Lookup/Directory table]
[**ME Segment 1 - Index data for field 1]
[**ME Segment 2 - Index data for field 2]
...
[**ME Segment N - Index data for field N]
```

### 2. Segment 0: Lookup/Directory Table

Segment 0 contains a mapping table that tells you which segment contains index data for a specific (LINE_ID, FIELD_ID) combination.

**Entry Format:** 4 bytes each
```
[SEG_NUM:1][LINE_ID:1][FIELD_ID:1][FLAGS:1]
```

**Location:** Approximately offset 0xC2 from Segment 0's **ME marker (0x11C from file start for typical files)

### 3. Segments 1-N: Index Data

Each segment stores index entries for ONE indexed field.

**Segment Metadata (offset +24 from **ME):**
| Offset | Size | Field |
|--------|------|-------|
| +0 | 2B | page_start |
| +2 | 2B | LINE_ID |
| +6 | 2B | FIELD_ID |
| +10 | 2B | field_width |
| +14 | 2B | entry_count |

**Data Offset:** 0xCD (205 bytes) from **ME marker

### 4. Index Entry Format

```
[length:2][value:N][page:2][flags:3]

Where:
- length = field_width (2 bytes, little-endian)
- value = ASCII text, space-padded to field_width
- page = page number in spool file (2 bytes, little-endian)
- flags = usually 0x00 0x00 0x00 (3 bytes)

Total entry size = 7 + field_width bytes
```

**Example (Reference_ID field, width=18):**
```
Entry: 'EP24123109039499' → PAGE 2

Hex: 00 12 45 50 32 34 31 32 33 31 30 39 30 33 39 34 39 39 20 20 02 00 00 00 00
     ^^^^^ ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ ^^^^^ ^^^^^^^^^
     length            text value (18 bytes)                  page   flags
```

### 5. Search Algorithm

```
1. Get LINE_ID, FIELD_ID from FIELD table (WHERE IS_INDEXED=1)
2. Find segment with matching LINE_ID + FIELD_ID
3. Read entries from segment: [length:2][value:N][page:2][flags:3]
4. Match value → get PAGE number
5. Use PAGE to extract from spool file
```

---

## Files Created/Modified

### Documentation
| File | Description |
|------|-------------|
| `SECTION_SEGMENT_WORKFLOW.md` | Complete algorithm specification |
| `INTELLISTOR_VIEWER_GUIDE.md` | User guide for the viewer tool |
| `SESSION_SUMMARY.md` | This summary |
| `DATABASE_REFERENCE.md` | MS SQL database guide |

### Code
| File | Description |
|------|-------------|
| `intellistor_viewer.py` | Python tool for MAP/spool file analysis |

---

## Test Results

### MAP File Analysis (25001002.MAP)
```
Segment Count: 9
Date: 1/01/2025

Segments:
  0: Lookup/Directory
  1: LINE 4, FIELD 2, width=55 (product)
  2: LINE 5, FIELD 3, width=18 (Reference_ID)
  3: LINE 5, FIELD 6, width=4 (value_date)
  4-8: LINE 6, various fields
```

### Search Tests
```
Search: 'EP24123109039499' (LINE 5, FIELD 3) → PAGE 2 ✓
Search: 'EP2412310' (partial match) → PAGE 2, 12 ✓
Search: '99' (LINE 6, FIELD 3) → 23 pages ✓
```

### Spool File Analysis
```
CDU100P.txt: ASA format, 4 pages, offsets [0, 7182, 14364, 20194] ✓
FRX16.txt: Form Feed format, 10 pages ✓
```

---

## Key Insights

1. **Binary segments ≠ Database segments**
   - Binary **ME segments organize index data by LINE_ID/FIELD_ID
   - Database REPORT_INSTANCE_SEGMENT tracks ingestion arrival chunks (concatenation segments)

2. **The MAP file does NOT store the actual field values directly searchable**
   - Instead, it provides a lookup: given (LINE_ID, FIELD_ID, value) → page number
   - The actual text values ARE stored in the index entries

3. **Segment 0 is critical for navigation**
   - Without parsing Segment 0, you'd have to scan all segments to find a field
   - Segment 0 provides O(1) lookup to find the right segment

4. **Data offset is consistent**
   - Index entries start at offset 0xCD (205 bytes) from **ME marker
   - This includes: **ME(8) + header(16) + metadata + padding

---

## Next Steps

1. **Validate with more MAP files** - Test the parser with different report types
2. **Handle date/numeric fields** - Current implementation focuses on text fields
3. **Integration with spool extraction** - Combine MAP search with spool file page extraction
4. **Performance testing** - Test with large MAP files (300K+ entries)
5. **Database integration** - Connect field definitions to MAP file segments

---

## Commands for Next Session

```bash
# Analyze a MAP file
python intellistor_viewer.py --map 25001002.MAP --show-entries

# Search for a value
python intellistor_viewer.py --map 25001002.MAP --search EP24123109039499 --line 5 --field 3

# Analyze spool file
python intellistor_viewer.py --spool Report_TXT_Viewer/CDU100P.txt

# Show report info (requires database)
python intellistor_viewer.py --report CDU100P
```
