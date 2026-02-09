# AFP Page Splitter

Extract specific pages from AFP (Advanced Function Presentation) files, producing valid AFP output that can be viewed and printed.

## Building

Requires MinGW-w64 (GCC for Windows). Run:

```
compile.bat
```

This produces `afp_splitter.exe` (statically linked, no DLL dependencies).

## Usage

```
afp_splitter.exe <input.afp> <page_ranges> <output.afp> [--with-resources]
```

### Extraction Modes

| Mode | Flag | Behaviour |
|------|------|-----------|
| **Resource Collection** | `--with-resources` | Extracts only the requested pages wrapped in a new BDT/EDT document envelope. Includes inter-page records (MPS, etc.). Produces a clean, standalone AFP file. **Recommended.** |
| Simple | _(none)_ | Copies everything from the start of the file up to and including the requested pages. Prior pages are included to preserve document structure. |

### Page Range Format

| Format | Description | Result |
|--------|-------------|--------|
| `5` | Single page | Page 5 |
| `1-5` | Range | Pages 1, 2, 3, 4, 5 |
| `1-2,5-8` | Multiple ranges | Pages 1, 2, 5, 6, 7, 8 |
| `1-5,4-6` | Overlapping | Pages 1, 2, 3, 4, 5, 4, 5, 6 (duplicates preserved) |
| `8-5` | Reversed | Pages 5, 6, 7, 8 (auto-corrected) |

Ranges are normalised automatically:
- Start values below 1 are clamped to 1.
- End values beyond the last page are clamped to the last page.
- Reversed ranges (e.g. `8-5`) are swapped.

### Examples

```bash
# Extract pages 2-3 from an AFP file (recommended mode)
afp_splitter.exe input.afp 2-3 output.afp --with-resources

# Extract a single page
afp_splitter.exe input.afp 5 page5.afp --with-resources

# Extract multiple non-contiguous ranges
afp_splitter.exe input.afp 1-3,7-9 selection.afp --with-resources
```

### Output

```
=============================================================================
AFP Page Splitter
=============================================================================
Input file:   input.afp
Page ranges:  2-3
Output file:  output.afp
Mode:         Resource Collection
=============================================================================

Loading AFP file...
Found 5 page(s) in input file

Parsing page ranges...
Parsed ranges:
  Pages 2 to 3

Extracting 2 page(s)...

=============================================================================
SUCCESS
=============================================================================
Output file:      output.afp
Source pages:     5
Extracted pages:  2
=============================================================================
```

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `Failed to load AFP file` | File not found or not valid AFP | Check file path and that it starts with `0x5A 0xD3` |
| `Failed to parse page ranges` | Bad range syntax | Use `1-5` or `1-2,5-8` (no spaces) |
| `No pages found` | File has no BPG/EPG page boundaries | Verify the file is a paged AFP document |

## File Structure

```
97_AFP_Splitter/
  afp_parser.h          Class definitions and API
  afp_parser.cpp        AFP parsing and extraction logic
  afp_splitter.cpp      CLI entry point
  compile.bat           Build script (MinGW-w64)
  README.md             This file
  TECHNICAL.md          Architecture and AFP format reference
```

## License

Internal tool for IntelliSTOR Migration project.
