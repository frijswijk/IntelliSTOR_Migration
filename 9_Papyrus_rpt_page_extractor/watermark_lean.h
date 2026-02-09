// Lean watermark implementation using stb_image (no external dependencies)
// Single-header libraries for image processing

#ifndef WATERMARK_LEAN_H
#define WATERMARK_LEAN_H

#include <string>
#include <vector>
#include <cmath>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <cstring>
#include <zlib.h>

// stb_image - image loading
#define STB_IMAGE_IMPLEMENTATION
#include "stb_image.h"

// stb_image_write - image writing
#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"

// stb_image_resize - image resizing
#define STB_IMAGE_RESIZE_IMPLEMENTATION
#include "stb_image_resize2.h"

namespace WatermarkLean {

// Simple image structure
struct Image {
    int width = 0;
    int height = 0;
    int channels = 0;
    std::vector<unsigned char> data;

    bool is_valid() const { return width > 0 && height > 0 && !data.empty(); }
};

// Load image from file
inline Image load_image(const std::string& path) {
    Image img;
    unsigned char* pixels = stbi_load(path.c_str(), &img.width, &img.height, &img.channels, 4); // Force RGBA
    if (!pixels) {
        return img;
    }

    img.channels = 4; // RGBA
    size_t size = img.width * img.height * 4;
    img.data.resize(size);
    std::memcpy(img.data.data(), pixels, size);
    stbi_image_free(pixels);

    return img;
}

// Resize image to target width (maintains aspect ratio)
inline Image resize_image(const Image& src, int target_width) {
    if (!src.is_valid() || target_width <= 0) return src;

    float scale = static_cast<float>(target_width) / src.width;
    int target_height = static_cast<int>(src.height * scale);

    Image dst;
    dst.width = target_width;
    dst.height = target_height;
    dst.channels = 4;
    dst.data.resize(target_width * target_height * 4);

    stbir_resize_uint8_linear(
        src.data.data(), src.width, src.height, 0,
        dst.data.data(), target_width, target_height, 0,
        STBIR_RGBA
    );

    return dst;
}

// Rotate image by angle (in degrees) - supports 0, 90, 180, 270 for efficiency
inline Image rotate_image(const Image& src, int angle) {
    if (!src.is_valid()) return src;

    // Normalize angle to 0-360
    angle = ((angle % 360) + 360) % 360;

    // For simple rotations (90, 180, 270), use efficient pixel swapping
    if (angle == 0) {
        return src;
    } else if (angle == 180) {
        Image dst = src;
        for (int y = 0; y < src.height; y++) {
            for (int x = 0; x < src.width; x++) {
                int src_idx = (y * src.width + x) * 4;
                int dst_idx = ((src.height - 1 - y) * src.width + (src.width - 1 - x)) * 4;
                for (int c = 0; c < 4; c++) {
                    dst.data[dst_idx + c] = src.data[src_idx + c];
                }
            }
        }
        return dst;
    } else if (angle == 90) {
        Image dst;
        dst.width = src.height;
        dst.height = src.width;
        dst.channels = 4;
        dst.data.resize(dst.width * dst.height * 4);

        for (int y = 0; y < src.height; y++) {
            for (int x = 0; x < src.width; x++) {
                int src_idx = (y * src.width + x) * 4;
                int dst_idx = (x * dst.width + (src.height - 1 - y)) * 4;
                for (int c = 0; c < 4; c++) {
                    dst.data[dst_idx + c] = src.data[src_idx + c];
                }
            }
        }
        return dst;
    } else if (angle == 270) {
        Image dst;
        dst.width = src.height;
        dst.height = src.width;
        dst.channels = 4;
        dst.data.resize(dst.width * dst.height * 4);

        for (int y = 0; y < src.height; y++) {
            for (int x = 0; x < src.width; x++) {
                int src_idx = (y * src.width + x) * 4;
                int dst_idx = ((src.width - 1 - x) * dst.width + y) * 4;
                for (int c = 0; c < 4; c++) {
                    dst.data[dst_idx + c] = src.data[src_idx + c];
                }
            }
        }
        return dst;
    }

    // For arbitrary angles, just return original (could implement general rotation later if needed)
    return src;
}

// Apply opacity to image (0-100%)
inline void apply_opacity(Image& img, int opacity_percent) {
    if (!img.is_valid() || opacity_percent < 0 || opacity_percent > 100) return;

    float opacity = opacity_percent / 100.0f;

    for (size_t i = 3; i < img.data.size(); i += 4) {
        img.data[i] = static_cast<unsigned char>(img.data[i] * opacity);
    }
}

// Save image as PNG
inline bool save_png(const Image& img, const std::string& path) {
    if (!img.is_valid()) return false;
    return stbi_write_png(path.c_str(), img.width, img.height, 4, img.data.data(), img.width * 4) != 0;
}

// Compress data using zlib (for PDF streams)
inline std::vector<unsigned char> compress_zlib(const std::vector<unsigned char>& data) {
    std::vector<unsigned char> compressed;
    compressed.resize(data.size() + 256);

    uLongf compressed_size = compressed.size();
    int result = compress(compressed.data(), &compressed_size, data.data(), data.size());

    if (result != Z_OK) {
        return data;
    }

    compressed.resize(compressed_size);
    return compressed;
}

// Generate a watermark PDF from PNG with positioning
inline bool generate_watermark_pdf(const std::string& png_path,
                                   const std::string& pdf_path,
                                   const std::string& position,
                                   int page_width = 612,
                                   int page_height = 792) {
    // Load PNG
    int width, height, channels;
    unsigned char* img_data = stbi_load(png_path.c_str(), &width, &height, &channels, 4);
    if (!img_data) return false;

    // Calculate position
    int x = 0, y = 0;
    if (position == "center") {
        x = (page_width - width) / 2;
        y = (page_height - height) / 2;
    } else if (position == "northwest") {
        x = 0; y = page_height - height;
    } else if (position == "north") {
        x = (page_width - width) / 2; y = page_height - height;
    } else if (position == "northeast") {
        x = page_width - width; y = page_height - height;
    } else if (position == "west") {
        x = 0; y = (page_height - height) / 2;
    } else if (position == "east") {
        x = page_width - width; y = (page_height - height) / 2;
    } else if (position == "southwest") {
        x = 0; y = 0;
    } else if (position == "south") {
        x = (page_width - width) / 2; y = 0;
    } else if (position == "southeast") {
        x = page_width - width; y = 0;
    }

    // Separate RGB and Alpha
    std::vector<unsigned char> rgb_data, alpha_data;
    rgb_data.reserve(width * height * 3);
    alpha_data.reserve(width * height);

    for (int i = 0; i < width * height * 4; i += 4) {
        rgb_data.push_back(img_data[i]);
        rgb_data.push_back(img_data[i + 1]);
        rgb_data.push_back(img_data[i + 2]);
        alpha_data.push_back(img_data[i + 3]);
    }
    stbi_image_free(img_data);

    // Compress
    auto rgb_compressed = compress_zlib(rgb_data);
    auto alpha_compressed = compress_zlib(alpha_data);

    // Build PDF
    std::ofstream pdf(pdf_path, std::ios::binary);
    if (!pdf) return false;

    pdf << "%PDF-1.4\n%\xE2\xE3\xCF\xD3\n";

    std::vector<long> obj_offsets;

    obj_offsets.push_back(pdf.tellp());
    pdf << "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n";

    obj_offsets.push_back(pdf.tellp());
    pdf << "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n";

    obj_offsets.push_back(pdf.tellp());
    pdf << "3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 " << page_width << " " << page_height << "]\n";
    pdf << "   /Contents 4 0 R /Resources << /XObject << /Im1 5 0 R >> >> >>\nendobj\n";

    std::stringstream content;
    content << "q\n" << width << " 0 0 " << height << " " << x << " " << y << " cm\n/Im1 Do\nQ\n";
    std::string content_str = content.str();

    obj_offsets.push_back(pdf.tellp());
    pdf << "4 0 obj\n<< /Length " << content_str.length() << " >>\nstream\n";
    pdf << content_str << "endstream\nendobj\n";

    obj_offsets.push_back(pdf.tellp());
    pdf << "5 0 obj\n<< /Type /XObject /Subtype /Image /Width " << width;
    pdf << " /Height " << height << " /ColorSpace /DeviceRGB\n";
    pdf << "   /BitsPerComponent 8 /Filter /FlateDecode /SMask 6 0 R /Length " << rgb_compressed.size() << " >>\nstream\n";
    pdf.write(reinterpret_cast<const char*>(rgb_compressed.data()), rgb_compressed.size());
    pdf << "\nendstream\nendobj\n";

    obj_offsets.push_back(pdf.tellp());
    pdf << "6 0 obj\n<< /Type /XObject /Subtype /Image /Width " << width;
    pdf << " /Height " << height << " /ColorSpace /DeviceGray\n";
    pdf << "   /BitsPerComponent 8 /Filter /FlateDecode /Length " << alpha_compressed.size() << " >>\nstream\n";
    pdf.write(reinterpret_cast<const char*>(alpha_compressed.data()), alpha_compressed.size());
    pdf << "\nendstream\nendobj\n";

    long xref_offset = pdf.tellp();
    pdf << "xref\n0 " << (obj_offsets.size() + 1) << "\n0000000000 65535 f \n";
    for (long offset : obj_offsets) {
        pdf << std::setfill('0') << std::setw(10) << offset << " 00000 n \n";
    }

    pdf << "trailer\n<< /Size " << (obj_offsets.size() + 1) << " /Root 1 0 R >>\n";
    pdf << "startxref\n" << xref_offset << "\n%%EOF\n";

    pdf.close();
    return true;
}

// Create watermark: process image and generate PDF
inline bool create_watermark_pdf(const std::string& watermark_path,
                                int rotation,
                                int opacity,
                                double scale,
                                const std::string& position,
                                const std::string& output_pdf) {
    // Process image
    Image img = load_image(watermark_path);
    if (!img.is_valid()) return false;

    int base_width = 300;
    int target_width = static_cast<int>(base_width * scale);
    if (target_width < 50) target_width = 50;
    img = resize_image(img, target_width);

    if (rotation != 0) {
        img = rotate_image(img, rotation);
    }

    apply_opacity(img, opacity);

    // Save temp PNG
    std::string temp_png = output_pdf + ".temp.png";
    if (!save_png(img, temp_png)) {
        return false;
    }

    // Generate PDF
    bool result = generate_watermark_pdf(temp_png, output_pdf, position);

    // Cleanup
    std::remove(temp_png.c_str());

    return result;
}

} // namespace WatermarkLean

#endif // WATERMARK_LEAN_H
