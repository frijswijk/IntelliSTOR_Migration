# AFP Page Splitter

Extract specific pages from AFP (Advanced Function Presentation) files.

## Overview

This tool allows you to split AFP documents by extracting specific page ranges. It maintains the integrity of the AFP format and produces valid output files.

## Features

- **Flexible Page Ranges**: Extract single pages, ranges, or multiple ranges
- **Duplicate Pages**: Can extract the same page multiple times
- **Auto-Normalization**: Automatically handles invalid ranges (reversed, out-of-bounds)
- **Fast Processing**: Efficient binary parsing and extraction
- **Standalone**: Compiled as static executable, no DLL dependencies

## Building

### Prerequisites

- MinGW-w64 (GCC for Windows)
- Located at: `C:\Users\freddievr\mingw64`

### Compile

```bash
compile.bat
```

This will create `afp_splitter.exe`

## Usage

### Basic Syntax

```
afp_splitter.exe <input.afp> <page_ranges> <output.afp>
```

### Page Range Format

| Format | Description | Example |
|--------|-------------|---------|
| `5` | Single page | Extract page 5 |
| `1-5` | Page range | Extract pages 1 through 5 |
| `1-2,5-8` | Multiple ranges | Extract pages 1,2,5,6,7,8 |
| `1-5,4-6` | Overlapping ranges | Pages 4-5 appear twice |

### Range Normalization

The tool automatically handles edge cases:

- **Start < 1**: Changed to 1
- **End > Max Pages**: Changed to last page
- **Reversed Range (8-5)**: Swapped to (5-8)

### Examples

#### Extract pages 1 and 2
```bash
afp_splitter.exe input.afp 1-2 output.afp
```

#### Extract only page 5
```bash
afp_splitter.exe input.afp 5 output.afp
```

#### Extract multiple ranges
```bash
afp_splitter.exe input.afp 1-3,5-7 output.afp
```
Output: Pages 1,2,3,5,6,7

#### Extract with duplicates
```bash
afp_splitter.exe input.afp 1-5,4-6 output.afp
```
Output: Pages 1,2,3,4,5,4,5,6 (pages 4-5 appear twice)

#### Auto-reverse range
```bash
afp_splitter.exe input.afp 8-5 output.afp
```
Output: Pages 5,6,7,8 (automatically reversed)

## File Structure

```
97_AFP_Splitter/
├── afp_parser.h        # Header file with class definitions
├── afp_parser.cpp      # AFP parsing implementation
├── afp_splitter.cpp    # Main program
├── compile.bat         # Build script
└── README.md           # This file
```

## How It Works

1. **Parse AFP File**: Reads the input AFP and identifies all page boundaries
2. **Parse Ranges**: Converts range string (e.g., "1-2,5-8") into page list
3. **Normalize Ranges**: Applies normalization rules (clamp, reverse)
4. **Extract Pages**: Copies requested pages to output file
5. **Write Output**: Creates valid AFP file with extracted pages

## AFP Format Details

### Structured Fields

AFP uses structured fields identified by:
- **Introducer**: `0x5A` (always)
- **Length**: 2 bytes (big-endian)
- **Class Code**: `0xD3` (MO:DCA)
- **Type Code**: Function type
- **Category Code**: Component type

### Page Boundaries

Pages are delimited by:
- **Begin Page**: `0xD3 0xA8 0xAF`
- **End Page**: `0xD3 0xA9 0xAF`

## Future Enhancements

### TLE (Tagged Logical Element) Support

Future version will support extraction by TLE indexes:

```bash
afp_splitter.exe input.afp --tle ACCOUNT_NO=12345 output.afp
```

This will extract all pages matching the specified TLE field value.

### Planned Features

- [ ] TLE index parsing
- [ ] Extract by metadata fields
- [ ] Batch processing
- [ ] Page reordering
- [ ] Merge multiple AFP files
- [ ] AFP validation tool
- [ ] Page count without extraction

## Integration

This tool is designed to integrate with the Papyrus reporting system:

```
IntelliSTOR_Migration/
├── 97_AFP_Splitter/           # This project
└── papyrus_rpt_page_Extractor_v2.cpp  # Future integration target
```

## Testing

Test with sample files:

```bash
# Test basic extraction
afp_splitter.exe F:\RPT\26027272.AFP 1-2 output_test.afp

# Test with your 5-page document
afp_splitter.exe F:\RPT\26027272.AFP 1-5 full_copy.afp
afp_splitter.exe F:\RPT\26027272.AFP 2-3 pages_2_3.afp
afp_splitter.exe F:\RPT\26027272.AFP 1,3,5 odd_pages.afp
```

## Troubleshooting

### "Failed to load AFP file"
- Check file path is correct
- Verify file is valid AFP format
- Check file permissions

### "Failed to parse page ranges"
- Check range syntax: "1-5" or "1-2,5-8"
- Use commas between ranges
- Use hyphens for ranges
- No spaces in range string

### "No pages found"
- File may not be valid AFP format
- File may be corrupted
- Check file size (must be > 8 bytes)

## License

Internal tool for IntelliSTOR Migration project.

## Author

Created for Papyrus AFP processing pipeline.
