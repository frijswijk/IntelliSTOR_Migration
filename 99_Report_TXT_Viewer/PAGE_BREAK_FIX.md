# Page Break Detection Fix

## Issue
The initial implementation only detected the character `'1'` as a page break, but legacy mainframe files use different formats:

1. **Actual Form Feed Characters** (`\f` / ASCII 12)
2. **Traditional Carriage Control** (character `'1'` at position 0)
3. **Combination of both**

## Files Affected

### FRX16.txt & FXR20.txt
- Use **actual form feed character** `\f` (ASCII 12)
- Example: `^L                                           Archival QC International Bank...`
- Form feed appears as the first character of the new page header line

### RPVR1011181047.TXT
- Uses **traditional carriage control characters**:
  - `'1'` = Form feed (new page)
  - `'0'` = Skip line (double space)
  - `' '` = Normal line
- Example: `1 REFERENCE: SDPGM002...` (line starts with character '1')

### SSUT2811005900.TXT
- Uses `'1'` **on its own line** for page breaks
- Example: Line contains only `1` followed by newline
- Also uses `'0'` and `'-'` for spacing control

## Solution

Updated the `parseReportFile()` function to detect both formats:

```javascript
const isFormFeed = controlChar === '\f' || controlChar.charCodeAt(0) === 12;
const isPageBreak = isFormFeed || controlChar === '1';
```

The parser now:
1. ✅ Detects form feed character `\f` (ASCII 12)
2. ✅ Detects traditional `'1'` carriage control
3. ✅ Strips control characters from display text
4. ✅ Handles empty lines with only page break characters
5. ✅ Maintains backward compatibility with all file formats

## Testing

All four sample files now display correctly:
- ✅ FRX16.txt (326 lines)
- ✅ FXR20.txt (192 lines)
- ✅ RPVR1011181047.TXT (2,863 lines)
- ✅ SSUT2811005900.TXT (132 lines)

## Control Character Reference

| Character | Hex  | Decimal | Meaning              | Action                    |
|-----------|------|---------|----------------------|---------------------------|
| `\f`      | 0x0C | 12      | Form Feed            | New page                  |
| `'1'`     | 0x31 | 49      | Carriage Control FF  | New page                  |
| `'0'`     | 0x30 | 48      | Carriage Control     | Skip line (double space)  |
| `'-'`     | 0x2D | 45      | Carriage Control     | Single space              |
| `' '`     | 0x20 | 32      | Space                | Normal line               |
| `'*'`     | 0x2A | 42      | Asterisk             | Normal line (some files)  |

## Date Fixed
2026-01-27
