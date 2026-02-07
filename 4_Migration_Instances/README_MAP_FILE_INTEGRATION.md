# MAP File Reference — Field-Value Search Index

## Purpose

MAP files are **binary field-value search indices** (UTF-16LE encoding) created during IntelliSTOR report ingestion. They enable searching for specific field values (e.g., ACCOUNT_NO) and locating which page(s) in the spool file contain that value.

Each MAP file corresponds to one report instance and is linked via the `MAPFILE` database table.

---

## What MAP Files Are NOT

MAP files do **NOT** define sections or segments for page segregation.

- **Section segregation** (which pages belong to which branch/section) comes exclusively from the **RPT file SECTIONHDR** binary structure — 12-byte triplets of (SECTION_ID, START_PAGE, PAGE_COUNT).
- **REPORT_INSTANCE_SEGMENT** tracks **ingestion arrival chunks** (concatenation segments from spool arrivals), NOT section page ranges.
- See `SECTION_SEGMENT_WORKFLOW.md` Sections 7-8 for the authoritative specification on section segregation.

---

## MAP File Binary Structure

| Component | Description |
|-----------|-------------|
| **MAPHDR** (bytes 0-23) | Header with `MAPHDR` signature (UTF-16LE), flags, and segment count at bytes 18-19 |
| **Segment 0** | Lookup/directory table — maps (LINE_ID, FIELD_ID) combinations to segment numbers |
| **Segments 1-N** | Sorted field-value index entries, one segment per indexed field |
| **\*\*ME markers** | UTF-16LE markers (`2a002a004d004500`) that delimit each segment boundary |

**Segment 0 (Directory):** 4-byte entries mapping (LINE_ID, FIELD_ID) to a segment number. This provides O(1) lookup to find which segment contains the index for a given field.

**Segments 1-N (Field Indices):** Each segment stores sorted index entries for ONE indexed field:
- Entry format: `[length:2][value:N][page:2][flags:3]`
- The value is the actual field content (e.g., an account number string)
- The page number tells you which spool page contains that value

For the full binary specification, see `SECTION_SEGMENT_WORKFLOW.md` Section 6.

---

## ACCOUNT_NO Indexing

The primary use case for MAP files is locating report pages by field value:

1. Application receives search request: `ACCOUNT_NO = "200-044295-001"`
2. Look up ACCOUNT_NO's (LINE_ID, FIELD_ID) in the `FIELD` table (`IS_INDEXED=1`)
3. Read Segment 0 to find which MAP segment covers that field
4. Binary search the sorted entries in that segment for the target value
5. Extract the page number from the matching entry
6. Retrieve that page from the spool/RPT file

**Row positions** within index entries use odd numbers (11, 13, 15, ..., 59, stride of 2) indicating up to 25 data rows per page where the field value appears.

---

## Database Relationships

| Table | Role |
|-------|------|
| `MAPFILE` | MAP file registry (MAP_FILE_ID, FILENAME, LOCATION_ID) |
| `SST_STORAGE` | Links MAP files to report instances (MAP_FILE_ID, DOMAIN_ID, REPORT_SPECIES_ID, AS_OF_TIMESTAMP) |
| `FIELD` | Field definitions with `IS_INDEXED=1` for fields that appear in MAP indices |
| `SIGNATURE` | Links fields to report species via STYPE_ID |

---

## Analysis Tools

Scripts in this directory for MAP file analysis (useful for migration):

| Script | Purpose |
|--------|---------|
| `parse_binary_map.py` | Basic binary MAP structure analysis |
| `parse_binary_map_complete.py` | Complete binary parser with database correlation |
| `extract_map_segments.py` | Extract segment metadata from binary MAP files |
| `analyze_map_structure.py` | Detailed hex analysis of MAP structure |
| `batch_verify_maps.py` | Count segments across all MAP files in a directory |
| `batch_verify_binary_maps.py` | Verify binary MAP file integrity |
| `diagnose_map_files.py` | Show raw content for debugging |
| `correlate_map_segments.py` | Correlate MAP binary segments with database |
| `db_export_map_data.py` | Export MAP-related data from database |
| `intellistor_viewer.py` | Interactive MAP/spool file analysis tool (see `INTELLISTOR_VIEWER_GUIDE.md`) |

---

## Related Documentation

| Document | Content |
|----------|---------|
| `SECTION_SEGMENT_WORKFLOW.md` | **Authoritative reference** — MAP file structure (Section 6), RPT SECTIONHDR for sections (Section 7), Index Search Workflow (Section 8) |
| `INTELLISTOR_VIEWER_GUIDE.md` | Interactive tool for MAP file analysis and spool file operations |
| `SESSION_SUMMARY.md` | MAP file structure discoveries and key insights |
| `EXTRACT_INSTANCES_DOCUMENTATION.md` | Current extraction script (uses RPT SECTIONHDR, not MAP files) |

---

## Historical Note

Version 2.0 of `extract_instances_sections.py` (now superseded by `Extract_Instances.py` v3.0) used MAP files for segment name lookups via a `MapFileCache` class and `--map-dir` argument. This approach was based on an incorrect assumption that MAP files contain section/segment definitions. The `verify_map_file.py` script was designed for that obsolete workflow and uses regex-based text parsing that does not correctly handle the binary MAP file format.

The current `Extract_Instances.py` v3.0 uses RPT file SECTIONHDR exclusively for section data via `rpt_section_reader.py`.

---

**Document Version**: 2.0 (corrected)
**Last Updated**: 2026-02-07
