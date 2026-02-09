# Watermark Usage Guide for papyrus_rpt_page_extractor_v2

## Overview

The v2 extractor adds parameter-driven watermark functionality for PDF outputs. Watermarks are **optional** - if no watermark parameters are provided, the tool works exactly like the original version.

## Compilation

```bash
# GCC/MinGW
g++ -std=c++17 -O2 -static -o papyrus_rpt_page_extractor_v2.exe papyrus_rpt_page_extractor_v2.cpp -lz -s

# MSVC
cl /EHsc /O2 /MT papyrus_rpt_page_extractor_v2.cpp /Fe:papyrus_rpt_page_extractor_v2.exe
```

## Basic Usage (No Watermark)

```bash
papyrus_rpt_page_extractor_v2.exe input.rpt all output.txt output.pdf
```

This works identically to the original version - no watermark is applied.

## Watermark Parameters

All watermark parameters are optional. You only need `--WatermarkImage` to enable watermarking.

### Required for Watermarking
- `--WatermarkImage <path>` - Path to watermark image file (PNG, JPG, etc.)

### Optional Parameters (with defaults)
- `--WatermarkPosition <position>` - Where to place the watermark (default: Center)
- `--WatermarkRotation <degrees>` - Rotation angle -180 to 180 (default: 0)
- `--WatermarkOpacity <percent>` - Opacity 0 to 100% (default: 30)
- `--WatermarkScale <scale>` - Size multiplier 0.5 to 2.0 (default: 1.0)

## Position Options

The watermark can be positioned at:

| Position       | Description                    |
|----------------|--------------------------------|
| `Center`       | Center of the page (default)   |
| `TopLeft`      | Top-left corner                |
| `TopCenter`    | Top center                     |
| `TopRight`     | Top-right corner               |
| `MiddleLeft`   | Middle left side               |
| `MiddleRight`  | Middle right side              |
| `BottomLeft`   | Bottom-left corner             |
| `BottomCenter` | Bottom center                  |
| `BottomRight`  | Bottom-right corner            |
| `Repeat`       | Tiled from top-left to bottom-right |

## Usage Examples

### Example 1: Simple Centered Watermark (30% opacity)
```bash
papyrus_rpt_page_extractor_v2.exe input.rpt all output.txt output.pdf ^
  --WatermarkImage confidential.png
```

### Example 2: Top-Right Corner at 50% Opacity
```bash
papyrus_rpt_page_extractor_v2.exe input.rpt pages:1-10 output.txt output.pdf ^
  --WatermarkImage logo.png ^
  --WatermarkPosition TopRight ^
  --WatermarkOpacity 50
```

### Example 3: Rotated Watermark at 45 Degrees
```bash
papyrus_rpt_page_extractor_v2.exe input.rpt sections:14259,14260 output.txt output.pdf ^
  --WatermarkImage draft.png ^
  --WatermarkPosition Center ^
  --WatermarkRotation 45 ^
  --WatermarkOpacity 40 ^
  --WatermarkScale 1.5
```

### Example 4: Tiled/Repeated Watermark
```bash
papyrus_rpt_page_extractor_v2.exe input.rpt all output.txt output.pdf ^
  --WatermarkImage confidential.png ^
  --WatermarkPosition Repeat ^
  --WatermarkOpacity 20 ^
  --WatermarkScale 0.5
```

### Example 5: Small Bottom-Right Watermark (Like a Stamp)
```bash
papyrus_rpt_page_extractor_v2.exe input.rpt all output.txt output.pdf ^
  --WatermarkImage approved.png ^
  --WatermarkPosition BottomRight ^
  --WatermarkOpacity 80 ^
  --WatermarkScale 0.3
```

### Example 6: Diagonal "CONFIDENTIAL" Banner
```bash
papyrus_rpt_page_extractor_v2.exe input.rpt all output.txt output.pdf ^
  --WatermarkImage confidential_text.png ^
  --WatermarkPosition Center ^
  --WatermarkRotation -45 ^
  --WatermarkOpacity 25 ^
  --WatermarkScale 1.8
```

## How It Works

### Page Size Awareness
The watermark system automatically detects the PDF page dimensions (width × height) and calculates appropriate positioning:
- **Letter size**: 612 × 792 points
- **A4 size**: 595 × 842 points
- **Custom sizes**: Detected automatically

### Position Calculation
For each position setting:
- **Center**: Centered both horizontally and vertically
- **TopLeft**: 0,0 from page origin
- **TopRight**: Right edge alignment, top position
- **BottomCenter**: Centered horizontally at bottom
- **Repeat**: Tiles the watermark from top-left to bottom-right

### Scaling
The base watermark size is calculated as 30% of the smaller page dimension (width or height), then multiplied by the `--WatermarkScale` factor:
- `0.5` = Half size (15% of page)
- `1.0` = Default (30% of page)
- `2.0` = Double size (60% of page)

### Opacity/Transparency
The opacity setting controls transparency:
- `0` = Fully transparent (invisible)
- `30` = Default (semi-transparent, subtle)
- `100` = Fully opaque (solid)

### Rotation
Watermarks are rotated around their center point:
- `0` = No rotation
- `45` = 45° clockwise
- `-45` = 45° counter-clockwise
- `90` = Vertical orientation

## Dependencies

The watermark feature requires **ImageMagick** to be installed. The tool will search for `magick.exe` in:
1. `./tools/magick.exe` (bundled)
2. `C:\Users\freddievr\imagemagick\magick.exe`
3. `C:\Program Files\ImageMagick\magick.exe`
4. System PATH

**QPDF** is also required for PDF processing and should be available in the same search locations.

## Watermark Image Preparation Tips

### Recommended Image Formats
- PNG with transparency (best for logos/text)
- JPG (for photo-based watermarks)
- SVG converted to PNG

### Image Size Recommendations
- **Width**: 800-2000 pixels
- **Height**: Proportional to maintain aspect ratio
- The tool will automatically resize based on the scale parameter

### Creating Text Watermarks
You can use ImageMagick to create text-based watermarks:

```bash
# Create "CONFIDENTIAL" text watermark
magick -size 2000x400 xc:none ^
  -font Arial -pointsize 120 -gravity center ^
  -fill "rgba(255,0,0,0.8)" -annotate +0+0 "CONFIDENTIAL" ^
  confidential_text.png

# Create "DRAFT" watermark
magick -size 1500x300 xc:none ^
  -font Arial-Bold -pointsize 100 -gravity center ^
  -fill "rgba(128,128,128,0.7)" -annotate +0+0 "DRAFT" ^
  draft_text.png
```

## Performance Considerations

Watermarking adds processing time because it:
1. Extracts PDF pages to images
2. Applies watermark to each page image
3. Converts watermarked images back to PDF

Expected processing time:
- **Without watermark**: 1-2 seconds per 100 pages
- **With watermark**: 5-15 seconds per page (depending on page complexity and resolution)

For large documents, consider:
- Using lower opacity (faster processing)
- Using simpler watermark images (smaller file size)
- Testing with a subset of pages first

## Troubleshooting

### "WARNING: ImageMagick not found. Skipping watermark."
- Install ImageMagick from https://imagemagick.org/
- Or place `magick.exe` in `./tools/` directory

### "WARNING: Failed to prepare watermark image."
- Check that the watermark image file exists and is valid
- Verify the image format is supported (PNG, JPG, GIF)
- Try converting the image to PNG format first

### Watermark appears too large/small
- Adjust the `--WatermarkScale` parameter
- Try values between 0.3 (very small) and 1.5 (large)

### Watermark is too visible/not visible enough
- Adjust the `--WatermarkOpacity` parameter
- Recommended range: 15-50% for subtle watermarks, 60-90% for prominent ones

### Repeat mode creates overlapping watermarks
- Reduce the `--WatermarkScale` (try 0.3-0.5)
- Increase the `--WatermarkOpacity` slightly to improve visibility

## Default Behavior Summary

| Parameter              | Default Value | Range/Options                                      |
|------------------------|---------------|----------------------------------------------------|
| WatermarkImage         | *(none)*      | Any valid image file path                          |
| WatermarkPosition      | Center        | See position options table above                   |
| WatermarkRotation      | 0             | -180 to 180 degrees                                |
| WatermarkOpacity       | 30            | 0 to 100%                                          |
| WatermarkScale         | 1.0           | 0.5 to 2.0                                         |

## Integration with Batch Files

See `watermark_examples.bat` for ready-to-use batch file examples.

## Differences from Original Version

The v2 extractor is **fully backward compatible**:
- All original functionality preserved
- Same command-line for basic usage
- Watermark features are purely additive (optional)
- Same exit codes and error handling
- No watermark if `--WatermarkImage` is not provided

You can safely use v2 as a drop-in replacement for the original extractor.
