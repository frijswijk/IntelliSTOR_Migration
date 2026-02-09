// QPDF Library Integration for Watermark Overlay
// This replaces the qpdf.exe external call with QPDF C++ library
//
// Compilation requires:
// -I"C:/Users/freddievr/qpdf-12.3.2-mingw64/include"
// -L"C:/Users/freddievr/qpdf-12.3.2-mingw64/lib"
// -lqpdf -ljpeg -lz

#ifndef WATERMARK_QPDF_LIB_H
#define WATERMARK_QPDF_LIB_H

#include <string>
#include <iostream>

// Uncomment when building with QPDF library
// #define USE_QPDF_LIBRARY

#ifdef USE_QPDF_LIBRARY

#include <qpdf/QPDF.hh>
#include <qpdf/QPDFPageDocumentHelper.hh>
#include <qpdf/QPDFPageObjectHelper.hh>
#include <qpdf/QPDFWriter.hh>
#include <qpdf/QUtil.hh>

namespace WatermarkQPDF {

// Overlay watermark PDF onto input PDF using QPDF C++ library
inline bool overlay_pdf_with_library(const std::string& input_pdf,
                                     const std::string& watermark_pdf,
                                     const std::string& output_pdf) {
    try {
        // Open input PDF
        QPDF qpdf_input;
        qpdf_input.processFile(input_pdf.c_str());

        // Open watermark PDF
        QPDF qpdf_watermark;
        qpdf_watermark.processFile(watermark_pdf.c_str());

        // Get first page of watermark (the watermark itself)
        QPDFPageDocumentHelper watermark_dh(qpdf_watermark);
        std::vector<QPDFPageObjectHelper> watermark_pages = watermark_dh.getAllPages();

        if (watermark_pages.empty()) {
            std::cerr << "ERROR: Watermark PDF has no pages\n";
            return false;
        }

        QPDFPageObjectHelper watermark_page = watermark_pages[0];

        // Get input pages
        QPDFPageDocumentHelper input_dh(qpdf_input);
        std::vector<QPDFPageObjectHelper> input_pages = input_dh.getAllPages();

        // Overlay watermark on each page
        for (auto& page : input_pages) {
            // Get the watermark page's content as a form XObject
            QPDFObjectHandle watermark_dict = watermark_page.getObjectHandle();

            // Copy watermark resources and content to input page
            // This is a simplified approach - full implementation would:
            // 1. Create form XObject from watermark page
            // 2. Add to page resources
            // 3. Append drawing command to page content stream

            // Get page content
            QPDFObjectHandle page_dict = page.getObjectHandle();
            QPDFObjectHandle contents = page_dict.getKey("/Contents");

            // Get watermark content
            QPDFObjectHandle wm_contents = watermark_dict.getKey("/Contents");

            if (contents.isStream() && wm_contents.isStream()) {
                // Append watermark content to page content
                std::string page_content = contents.getStreamData();
                std::string wm_content = wm_contents.getStreamData();

                // Wrap watermark in graphics state save/restore
                std::string combined = page_content + "\nq\n" + wm_content + "\nQ\n";

                // Update content stream
                contents.replaceStreamData(combined, QPDFObjectHandle::newNull(), QPDFObjectHandle::newNull());
            }
        }

        // Write output
        QPDFWriter writer(qpdf_input, output_pdf.c_str());
        writer.setStreamDataMode(qpdf_stream_data_mode_e::qpdf_s_preserve);
        writer.write();

        return true;

    } catch (std::exception& e) {
        std::cerr << "QPDF Library Error: " << e.what() << "\n";
        return false;
    }
}

} // namespace WatermarkQPDF

#else

// Stub when library is not available
namespace WatermarkQPDF {
    inline bool overlay_pdf_with_library(const std::string&, const std::string&, const std::string&) {
        std::cerr << "ERROR: QPDF library not available. Compile with USE_QPDF_LIBRARY defined.\n";
        return false;
    }
}

#endif // USE_QPDF_LIBRARY

#endif // WATERMARK_QPDF_LIB_H
