#include "afp_parser.h"
#include <fstream>
#include <iostream>
#include <sstream>
#include <algorithm>
#include <cstring>

// ============================================================================
// AFPStructuredField Implementation
// ============================================================================

std::string AFPStructuredField::getIdentifier() const {
    char buf[16];
    snprintf(buf, sizeof(buf), "%02X%02X%02X", classCode, typeCode, categoryCode);
    return std::string(buf);
}

bool AFPStructuredField::isBeginPage() const {
    return classCode == 0xD3 && typeCode == 0xA8 && categoryCode == 0xAF;
}

bool AFPStructuredField::isEndPage() const {
    return classCode == 0xD3 && typeCode == 0xA9 && categoryCode == 0xAF;
}

bool AFPStructuredField::isBeginDocument() const {
    return classCode == 0xD3 && typeCode == 0xA8 && categoryCode == 0xA8;
}

bool AFPStructuredField::isEndDocument() const {
    return classCode == 0xD3 && typeCode == 0xA9 && categoryCode == 0xAD;
}

bool AFPStructuredField::isBeginPageGroup() const {
    return classCode == 0xD3 && typeCode == 0xA8 && categoryCode == 0xAD;
}

bool AFPStructuredField::isEndPageGroup() const {
    return classCode == 0xD3 && typeCode == 0xA9 && categoryCode == 0xAF;
}

bool AFPStructuredField::isResource() const {
    return classCode == 0xD3 && typeCode == 0xA6;
}

bool AFPStructuredField::isTLE() const {
    return classCode == 0xD3 && typeCode == 0xB2 && categoryCode == 0xEB;
}

// ============================================================================
// PageRange Implementation
// ============================================================================

void PageRange::normalize(int maxPages) {
    // Clamp to valid range
    if (start < 1) start = 1;
    if (end > maxPages) end = maxPages;
    if (start > end) std::swap(start, end);
}

// ============================================================================
// AFPParser Implementation
// ============================================================================

AFPParser::AFPParser() {
}

AFPParser::~AFPParser() {
}

bool AFPParser::parse(const std::string& filename) {
    // Read entire file into memory
    std::ifstream file(filename, std::ios::binary | std::ios::ate);
    if (!file.is_open()) {
        lastError_ = "Failed to open file: " + filename;
        return false;
    }

    std::streamsize size = file.tellg();
    file.seekg(0, std::ios::beg);

    fileData_.resize(size);
    if (!file.read(reinterpret_cast<char*>(fileData_.data()), size)) {
        lastError_ = "Failed to read file: " + filename;
        return false;
    }

    // Validate AFP signature
    if (!AFPUtil::isValidAFP(fileData_.data(), fileData_.size())) {
        lastError_ = "Invalid AFP file format";
        return false;
    }

    // Parse structured fields and identify pages
    return parseStructuredFields();
}

bool AFPParser::parseStructuredFields() {
    pages_.clear();
    allResources_.clear();
    size_t offset = 0;
    int currentPage = 0;
    size_t pageStartOffset = 0;
    bool inPage = false;
    size_t firstPageOffset = 0;
    bool foundFirstPage = false;

    while (offset + 8 <= fileData_.size()) {
        // Check for structured field introducer
        if (fileData_[offset] != 0x5A) {
            // Not a structured field, skip byte
            offset++;
            continue;
        }

        AFPStructuredField field;
        field.introducer = fileData_[offset];
        field.length = AFPUtil::readUInt16BE(&fileData_[offset + 1]);
        field.offset = offset;

        // Validate length
        if (field.length < 8 || offset + field.length > fileData_.size()) {
            offset++;
            continue;
        }

        field.classCode = fileData_[offset + 3];
        field.typeCode = fileData_[offset + 4];
        field.categoryCode = fileData_[offset + 5];

        // Copy field data
        field.data.resize(field.length - 8);
        if (field.length > 8) {
            memcpy(field.data.data(), &fileData_[offset + 8], field.length - 8);
        }

        // For resource collection mode: collect ALL structured fields from the entire file
        // except page/document boundaries. Pages will still contain embedded resources,
        // but we also put them in the Resource Group for reference.
        // This handles both inline and external resource modes.
        if (field.classCode == 0xD3 &&
            !field.isBeginPage() && !field.isEndPage() &&
            !field.isBeginDocument() && !field.isEndDocument() &&
            !field.isBeginPageGroup() && !field.isEndPageGroup()) {

            std::vector<uint8_t> resourceData(field.length);
            memcpy(resourceData.data(), &fileData_[offset], field.length);
            allResources_.push_back(resourceData);
        }

        // Track first page for preamble extraction
        if (field.isBeginPage() && !foundFirstPage) {
            firstPageOffset = offset;
            foundFirstPage = true;
        }

        // Check for page boundaries
        if (field.isBeginPage()) {
            if (!inPage) {
                currentPage++;
                inPage = true;

                // For page tracking, save where this Begin Page actually is
                size_t actualBeginPageOffset = offset;

                // Determine start offset (may include inter-page data)
                if (currentPage == 1 || pages_.empty()) {
                    pageStartOffset = offset;
                } else {
                    // Start from end of previous page (includes inter-page structures)
                    pageStartOffset = pages_.back().endOffset;
                }

                // Store actual Begin Page location separately
                // (we'll use this in End Page handler)
                if (currentPage == 1) {
                    // For first page, track where Begin Page is
                    offset = actualBeginPageOffset; // Restore for consistency
                }
            }
        } else if (field.isEndPage()) {
            if (inPage) {
                AFPPage page;
                page.pageNumber = currentPage;
                page.startOffset = pageStartOffset;
                page.endOffset = offset + field.length;

                // Find where the Begin Page actually is by scanning back
                size_t scanOffset = pageStartOffset;
                while (scanOffset < offset) {
                    if (fileData_[scanOffset] == 0x5A && scanOffset + 8 <= fileData_.size()) {
                        uint16_t len = AFPUtil::readUInt16BE(&fileData_[scanOffset + 1]);
                        if (len >= 8 && scanOffset + len <= fileData_.size()) {
                            if (fileData_[scanOffset + 3] == 0xD3 &&
                                fileData_[scanOffset + 4] == 0xA8 &&
                                fileData_[scanOffset + 5] == 0xAF) {
                                page.actualPageStart = scanOffset;
                                break;
                            }
                        }
                    }
                    scanOffset++;
                }

                if (page.actualPageStart == 0) {
                    page.actualPageStart = pageStartOffset; // Fallback
                }

                pages_.push_back(page);
                inPage = false;
            }
        }

        offset += field.length;
    }

    // If we have an unclosed page, add it
    if (inPage) {
        AFPPage page;
        page.pageNumber = currentPage;
        page.startOffset = pageStartOffset;
        page.endOffset = fileData_.size();
        pages_.push_back(page);
    }

    if (pages_.empty()) {
        lastError_ = "No pages found in AFP file";
        return false;
    }

    // Store preamble (everything before first page) as document header
    if (foundFirstPage && firstPageOffset > 0) {
        documentHeader_.resize(firstPageOffset);
        memcpy(documentHeader_.data(), fileData_.data(), firstPageOffset);
    }

    // Store postamble (everything after last page) as document footer
    if (!pages_.empty()) {
        size_t lastPageEnd = pages_.back().endOffset;
        if (lastPageEnd < fileData_.size()) {
            size_t postambleSize = fileData_.size() - lastPageEnd;
            documentFooter_.resize(postambleSize);
            memcpy(documentFooter_.data(), &fileData_[lastPageEnd], postambleSize);
        }
    }

    return true;
}

const AFPPage* AFPParser::getPage(int pageNum) const {
    if (pageNum < 1 || pageNum > static_cast<int>(pages_.size())) {
        return nullptr;
    }
    return &pages_[pageNum - 1];
}

// ============================================================================
// AFPSplitter Implementation
// ============================================================================

AFPSplitter::AFPSplitter() : parser_(nullptr) {
}

AFPSplitter::~AFPSplitter() {
}

bool AFPSplitter::loadFile(const std::string& filename) {
    parser_ = std::make_unique<AFPParser>();
    if (!parser_->parse(filename)) {
        lastError_ = parser_->getLastError();
        return false;
    }
    return true;
}

std::vector<PageRange> AFPSplitter::parsePageRanges(const std::string& rangeStr) {
    std::vector<PageRange> ranges;
    std::string trimmed = AFPUtil::trim(rangeStr);

    if (trimmed.empty()) {
        return ranges;
    }

    // Split by comma
    std::istringstream ss(trimmed);
    std::string token;

    while (std::getline(ss, token, ',')) {
        token = AFPUtil::trim(token);
        if (token.empty()) continue;

        // Check if it's a range (contains '-')
        size_t dashPos = token.find('-');
        if (dashPos != std::string::npos) {
            // Range format: "start-end"
            std::string startStr = token.substr(0, dashPos);
            std::string endStr = token.substr(dashPos + 1);

            try {
                int start = std::stoi(AFPUtil::trim(startStr));
                int end = std::stoi(AFPUtil::trim(endStr));
                ranges.push_back(PageRange(start, end));
            } catch (...) {
                lastError_ = "Invalid page range: " + token;
            }
        } else {
            // Single page
            try {
                int page = std::stoi(token);
                ranges.push_back(PageRange(page, page));
            } catch (...) {
                lastError_ = "Invalid page number: " + token;
            }
        }
    }

    // Normalize ranges
    int maxPages = getPageCount();
    for (auto& range : ranges) {
        range.normalize(maxPages);
    }

    return ranges;
}

std::vector<int> AFPSplitter::expandPageRanges(const std::vector<PageRange>& ranges) {
    std::vector<int> pages;

    for (const auto& range : ranges) {
        for (int i = range.start; i <= range.end; i++) {
            pages.push_back(i);
        }
    }

    return pages;
}

bool AFPSplitter::extractPages(const std::vector<PageRange>& ranges, const std::string& outputFile) {
    if (!parser_) {
        lastError_ = "No AFP file loaded";
        return false;
    }

    // Expand ranges to page list
    std::vector<int> pageNumbers = expandPageRanges(ranges);

    if (pageNumbers.empty()) {
        lastError_ = "No pages to extract";
        return false;
    }

    // Write output file
    return writeAFPFile(pageNumbers, outputFile);
}

bool AFPSplitter::writeAFPFile(const std::vector<int>& pageNumbers, const std::string& outputFile) {
    std::ofstream out(outputFile, std::ios::binary);
    if (!out.is_open()) {
        lastError_ = "Failed to open output file: " + outputFile;
        return false;
    }

    if (pageNumbers.empty()) {
        lastError_ = "No pages to write";
        return false;
    }

    const auto& rawData = parser_->getRawData();
    const auto& postamble = parser_->getPostamble();

    // Find the first requested page
    int firstPageNum = pageNumbers[0];
    const AFPPage* firstPage = parser_->getPage(firstPageNum);
    if (!firstPage) {
        lastError_ = "Invalid first page number: " + std::to_string(firstPageNum);
        return false;
    }

    // SIMPLE APPROACH: Write everything before first requested page
    // This includes all prior pages and their resources
    // NOTE: This means if you request pages 2-4, you'll get pages 1-4
    //       (page 1 is included to preserve document structure)
    if (firstPage->startOffset > 0) {
        out.write(reinterpret_cast<const char*>(rawData.data()), firstPage->startOffset);
    }

    // Write each requested page
    for (int pageNum : pageNumbers) {
        const AFPPage* page = parser_->getPage(pageNum);
        if (!page) {
            lastError_ = "Invalid page number: " + std::to_string(pageNum);
            return false;
        }

        // Write page data
        size_t pageSize = page->getSize();
        out.write(reinterpret_cast<const char*>(&rawData[page->startOffset]), pageSize);
    }

    // Write document postamble (closing structured fields)
    if (!postamble.empty()) {
        out.write(reinterpret_cast<const char*>(postamble.data()), postamble.size());
    }

    out.close();
    return true;
}

bool AFPSplitter::extractPagesWithResources(const std::vector<PageRange>& ranges, const std::string& outputFile) {
    if (!parser_) {
        lastError_ = "No AFP file loaded";
        return false;
    }

    // Expand ranges to page list
    std::vector<int> pageNumbers = expandPageRanges(ranges);

    if (pageNumbers.empty()) {
        lastError_ = "No pages to extract";
        return false;
    }

    std::ofstream out(outputFile, std::ios::binary);
    if (!out.is_open()) {
        lastError_ = "Failed to open output file: " + outputFile;
        return false;
    }

    const auto& rawData = parser_->getRawData();
    const auto& preamble = parser_->getPreamble();
    const auto& postamble = parser_->getPostamble();

    // Write preamble (everything before first page - contains document header and resources)
    if (!preamble.empty()) {
        out.write(reinterpret_cast<const char*>(preamble.data()), preamble.size());
    }

    // Write ONLY the requested pages (not previous pages)
    // Include inter-page structures (Begin Page Group, etc.)
    for (int pageNum : pageNumbers) {
        const AFPPage* page = parser_->getPage(pageNum);
        if (!page) {
            lastError_ = "Invalid page number: " + std::to_string(pageNum);
            return false;
        }

        // Write from startOffset (includes inter-page gap) to endOffset (after End Page)
        // This includes Begin Page Group and other structures needed between pages
        size_t pageContentSize = page->endOffset - page->startOffset;
        out.write(reinterpret_cast<const char*>(&rawData[page->startOffset]), pageContentSize);
    }

    // Write postamble (document closing structures)
    if (!postamble.empty()) {
        out.write(reinterpret_cast<const char*>(postamble.data()), postamble.size());
    }

    out.close();
    return true;
}

// ============================================================================
// Utility Functions
// ============================================================================

namespace AFPUtil {

uint16_t readUInt16BE(const uint8_t* data) {
    return (static_cast<uint16_t>(data[0]) << 8) | static_cast<uint16_t>(data[1]);
}

void writeUInt16BE(uint8_t* data, uint16_t value) {
    data[0] = static_cast<uint8_t>((value >> 8) & 0xFF);
    data[1] = static_cast<uint8_t>(value & 0xFF);
}

bool isValidAFP(const uint8_t* data, size_t length) {
    // Check minimum size for one structured field
    if (length < 8) {
        return false;
    }

    // Check for structured field introducer at start
    if (data[0] != 0x5A) {
        return false;
    }

    // Read length
    uint16_t sfLength = readUInt16BE(&data[1]);
    if (sfLength < 8 || sfLength > length) {
        return false;
    }

    // Check for MO:DCA class code
    if (data[3] != 0xD3) {
        return false;
    }

    return true;
}

std::string trim(const std::string& str) {
    size_t first = str.find_first_not_of(" \t\n\r");
    if (first == std::string::npos) return "";
    size_t last = str.find_last_not_of(" \t\n\r");
    return str.substr(first, (last - first + 1));
}

} // namespace AFPUtil
