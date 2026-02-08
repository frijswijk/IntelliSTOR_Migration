// pdf_page_extraction_example.cpp
// Example implementations for PDF page extraction and watermarking
// Two approaches: 1) Native C++ with PoDoFo, 2) External QPDF tool

#include <iostream>
#include <fstream>
#include <vector>
#include <string>
#include <filesystem>
#include <cstdlib>

namespace fs = std::filesystem;

// ============================================================================
// APPROACH 1: Using QPDF External Tool (RECOMMENDED - Simpler)
// ============================================================================

class QPDFExtractor {
public:
    QPDFExtractor(const std::string& qpdf_exe_path = "qpdf.exe")
        : qpdf_path(qpdf_exe_path) {}

    // Extract specific pages from PDF
    bool extractPages(const std::string& input_pdf,
                     const std::string& output_pdf,
                     const std::vector<int>& pages) {
        if (pages.empty()) return false;

        // Build page range string: "1,3,5-7,10"
        std::string page_spec;
        for (size_t i = 0; i < pages.size(); ++i) {
            if (i > 0) page_spec += ",";
            page_spec += std::to_string(pages[i]);
        }

        // QPDF command: qpdf input.pdf --pages . 1,3,5-7 -- output.pdf
        std::string cmd = "\"" + qpdf_path + "\" \"" + input_pdf + "\" "
                         + "--pages . " + page_spec + " -- \"" + output_pdf + "\"";

        int result = system(cmd.c_str());
        return (result == 0);
    }

    // Extract page range from PDF
    bool extractPageRange(const std::string& input_pdf,
                         const std::string& output_pdf,
                         int start_page, int end_page) {
        std::string page_spec = std::to_string(start_page) + "-" + std::to_string(end_page);

        std::string cmd = "\"" + qpdf_path + "\" \"" + input_pdf + "\" "
                         + "--pages . " + page_spec + " -- \"" + output_pdf + "\"";

        int result = system(cmd.c_str());
        return (result == 0);
    }

    // Apply watermark to PDF (overlay method)
    bool applyWatermark(const std::string& input_pdf,
                       const std::string& watermark_pdf,
                       const std::string& output_pdf) {
        // QPDF overlay command
        std::string cmd = "\"" + qpdf_path + "\" \"" + input_pdf + "\" "
                         + "--overlay \"" + watermark_pdf + "\" -- \"" + output_pdf + "\"";

        int result = system(cmd.c_str());
        return (result == 0);
    }

    // Convert image watermark to PDF first (using ImageMagick or similar)
    bool createWatermarkPDF(const std::string& image_path,
                           const std::string& output_pdf,
                           int page_width = 612,  // Letter size
                           int page_height = 792) {
        // This requires ImageMagick's convert tool
        // convert confidential.png -page 612x792 watermark.pdf
        std::string cmd = "magick convert \"" + image_path + "\" "
                         + "-page " + std::to_string(page_width) + "x" + std::to_string(page_height) + " "
                         + "\"" + output_pdf + "\"";

        int result = system(cmd.c_str());
        return (result == 0);
    }

private:
    std::string qpdf_path;
};

// ============================================================================
// APPROACH 2: Using PoDoFo Library (More Complex, Better Integration)
// ============================================================================

#ifdef USE_PODOFO

#include <podofo/podofo.h>

using namespace PoDoFo;

class PoDoFoExtractor {
public:
    // Extract specific pages from PDF
    bool extractPages(const std::string& input_pdf,
                     const std::string& output_pdf,
                     const std::vector<int>& pages) {
        try {
            // Load input PDF
            PdfMemDocument input_doc;
            input_doc.Load(input_pdf.c_str());

            // Create output PDF
            PdfMemDocument output_doc;

            int total_pages = input_doc.GetPageCount();

            // Copy selected pages
            for (int page_num : pages) {
                if (page_num < 1 || page_num > total_pages) {
                    std::cerr << "Invalid page number: " << page_num << std::endl;
                    continue;
                }

                // Get page from input (0-indexed)
                PdfPage* src_page = input_doc.GetPage(page_num - 1);
                if (!src_page) continue;

                // Copy page to output
                output_doc.GetPages().AppendDocumentPages(input_doc, page_num - 1, 1);
            }

            // Save output PDF
            output_doc.Write(output_pdf.c_str());
            return true;

        } catch (const PdfError& e) {
            std::cerr << "PoDoFo error: " << e.what() << std::endl;
            return false;
        }
    }

    // Apply image watermark to PDF
    bool applyImageWatermark(const std::string& input_pdf,
                            const std::string& watermark_image,
                            const std::string& output_pdf,
                            double opacity = 0.3) {
        try {
            // Load input PDF
            PdfMemDocument doc;
            doc.Load(input_pdf.c_str());

            // Load watermark image
            PdfImage watermark(&doc);
            watermark.LoadFromFile(watermark_image.c_str());

            // Apply watermark to each page
            int page_count = doc.GetPageCount();
            for (int i = 0; i < page_count; ++i) {
                PdfPage* page = doc.GetPage(i);
                if (!page) continue;

                PdfRect page_rect = page->GetMediaBox();
                double page_width = page_rect.GetWidth();
                double page_height = page_rect.GetHeight();

                // Calculate watermark position (centered)
                double watermark_width = page_width * 0.6;  // 60% of page width
                double watermark_height = watermark_width * watermark.GetHeight() / watermark.GetWidth();
                double x = (page_width - watermark_width) / 2;
                double y = (page_height - watermark_height) / 2;

                // Get page content stream
                PdfPainter painter;
                painter.SetPage(page);

                // Set opacity
                PdfExtGState ext_state(&doc);
                ext_state.SetFillOpacity(opacity);
                painter.SetExtGState(&ext_state);

                // Draw watermark
                painter.DrawImage(watermark, x, y, watermark_width, watermark_height);
                painter.FinishPage();
            }

            // Save output
            doc.Write(output_pdf.c_str());
            return true;

        } catch (const PdfError& e) {
            std::cerr << "PoDoFo error: " << e.what() << std::endl;
            return false;
        }
    }

    // Check and preserve page orientation
    std::string getPageOrientation(const std::string& pdf_path, int page_num) {
        try {
            PdfMemDocument doc;
            doc.Load(pdf_path.c_str());

            PdfPage* page = doc.GetPage(page_num - 1);
            if (!page) return "unknown";

            PdfRect rect = page->GetMediaBox();
            double width = rect.GetWidth();
            double height = rect.GetHeight();

            if (width > height) {
                return "landscape";
            } else {
                return "portrait";
            }

        } catch (const PdfError& e) {
            std::cerr << "PoDoFo error: " << e.what() << std::endl;
            return "unknown";
        }
    }
};

#endif // USE_PODOFO

// ============================================================================
// Integration Example: Modified RPT Extractor with PDF Page Extraction
// ============================================================================

class PDFPageExtractor {
public:
    PDFPageExtractor(const std::string& qpdf_path = "qpdf.exe",
                    const std::string& temp_dir = "./temp")
        : qpdf(qpdf_path), temp_directory(temp_dir) {
        fs::create_directories(temp_directory);
    }

    // Extract PDF pages based on selection rule
    bool extractPDFPages(const std::string& full_pdf,
                        const std::vector<int>& page_numbers,
                        const std::string& output_pdf,
                        const std::string& watermark_image = "") {
        std::string temp_extracted = temp_directory + "/temp_extracted.pdf";

        // Step 1: Extract selected pages
        if (!qpdf.extractPages(full_pdf, temp_extracted, page_numbers)) {
            std::cerr << "Failed to extract pages from PDF" << std::endl;
            return false;
        }

        // Step 2: Apply watermark if provided
        if (!watermark_image.empty() && fs::exists(watermark_image)) {
            std::string watermark_pdf = temp_directory + "/watermark.pdf";

            // Convert image to PDF (requires ImageMagick)
            if (!qpdf.createWatermarkPDF(watermark_image, watermark_pdf)) {
                std::cerr << "Failed to create watermark PDF, skipping watermark" << std::endl;
                // Continue without watermark
                fs::copy(temp_extracted, output_pdf, fs::copy_options::overwrite_existing);
            } else {
                // Apply watermark
                if (!qpdf.applyWatermark(temp_extracted, watermark_pdf, output_pdf)) {
                    std::cerr << "Failed to apply watermark" << std::endl;
                    fs::copy(temp_extracted, output_pdf, fs::copy_options::overwrite_existing);
                }
            }
        } else {
            // No watermark, just copy extracted PDF
            fs::copy(temp_extracted, output_pdf, fs::copy_options::overwrite_existing);
        }

        // Cleanup temp files
        fs::remove(temp_extracted);
        fs::remove(temp_directory + "/watermark.pdf");

        return true;
    }

    // Extract PDF sections (continuous page ranges)
    bool extractPDFSections(const std::string& full_pdf,
                           const std::vector<std::pair<int, int>>& section_ranges,
                           const std::string& output_pdf,
                           const std::string& watermark_image = "") {
        // Convert section ranges to individual page numbers
        std::vector<int> pages;
        for (const auto& range : section_ranges) {
            for (int p = range.first; p <= range.second; ++p) {
                pages.push_back(p);
            }
        }

        return extractPDFPages(full_pdf, pages, output_pdf, watermark_image);
    }

private:
    QPDFExtractor qpdf;
    std::string temp_directory;
};

// ============================================================================
// Usage Examples
// ============================================================================

void example_usage() {
    PDFPageExtractor extractor("qpdf.exe", "./temp");

    // Example 1: Extract pages 1, 3, 5-10 from PDF
    std::vector<int> pages = {1, 3, 5, 6, 7, 8, 9, 10};
    extractor.extractPDFPages("input.pdf", pages, "output_pages.pdf");

    // Example 2: Extract pages with watermark
    extractor.extractPDFPages("input.pdf", pages, "output_watermarked.pdf",
                             "confidential.png");

    // Example 3: Extract sections (page ranges)
    std::vector<std::pair<int, int>> sections = {
        {1, 5},   // Pages 1-5
        {10, 15}  // Pages 10-15
    };
    extractor.extractPDFSections("input.pdf", sections, "output_sections.pdf",
                                "confidential.png");
}

// ============================================================================
// Main Function (Testing)
// ============================================================================

int main(int argc, char* argv[]) {
    if (argc < 4) {
        std::cout << "Usage: " << argv[0] << " <input.pdf> <output.pdf> <pages> [watermark.png]\n";
        std::cout << "  pages: comma-separated list (e.g., 1,3,5-10)\n";
        return 1;
    }

    std::string input_pdf = argv[1];
    std::string output_pdf = argv[2];
    std::string page_spec = argv[3];
    std::string watermark = (argc > 4) ? argv[4] : "";

    // Parse page specification
    std::vector<int> pages;
    // TODO: Parse page_spec string to extract page numbers
    // For now, simple example:
    pages = {1, 2, 3, 4, 5};

    PDFPageExtractor extractor;
    if (extractor.extractPDFPages(input_pdf, pages, output_pdf, watermark)) {
        std::cout << "Success! Created: " << output_pdf << std::endl;
        return 0;
    } else {
        std::cerr << "Failed to extract PDF pages" << std::endl;
        return 1;
    }
}
