#ifndef AFP_PARSER_H
#define AFP_PARSER_H

#include <string>
#include <vector>
#include <cstdint>
#include <map>
#include <memory>

// AFP Structured Field Identifier
struct AFPStructuredField {
    uint8_t introducer;      // Always 0x5A
    uint16_t length;         // Length of SF (including introducer)
    uint8_t classCode;       // D3 for MO:DCA
    uint8_t typeCode;        // Type (A8=Begin, A9=End, etc.)
    uint8_t categoryCode;    // Category code
    size_t offset;           // Offset in file
    std::vector<uint8_t> data; // Field data

    AFPStructuredField() : introducer(0x5A), length(0), classCode(0xD3),
                           typeCode(0), categoryCode(0), offset(0) {}

    // Helper to get full identifier
    std::string getIdentifier() const;

    // Check field types
    bool isBeginPage() const;
    bool isEndPage() const;
    bool isBeginDocument() const;
    bool isEndDocument() const;
    bool isBeginPageGroup() const;
    bool isEndPageGroup() const;
    bool isResource() const;
    bool isTLE() const;
};

// Page structure in AFP file
struct AFPPage {
    int pageNumber;          // Logical page number (1-based)
    size_t startOffset;      // Start offset in file (includes any preceding page group)
    size_t endOffset;        // End offset in file (exclusive)
    size_t actualPageStart;  // Actual Begin Page offset (for reference)
    std::vector<size_t> fieldOffsets; // Offsets of structured fields in page
    std::map<std::string, std::string> tleIndexes; // TLE indexes (for future use)

    AFPPage() : pageNumber(0), startOffset(0), endOffset(0), actualPageStart(0) {}

    size_t getSize() const { return endOffset - startOffset; }
};

// Page range specification
struct PageRange {
    int start;
    int end;

    PageRange(int s, int e) : start(s), end(e) {}

    bool isValid() const { return start > 0 && end >= start; }

    void normalize(int maxPages);
};

// AFP Document Parser
class AFPParser {
public:
    AFPParser();
    ~AFPParser();

    // Parse AFP file and identify pages
    bool parse(const std::string& filename);

    // Get total number of pages
    int getPageCount() const { return static_cast<int>(pages_.size()); }

    // Get page information
    const AFPPage* getPage(int pageNum) const;
    const std::vector<AFPPage>& getAllPages() const { return pages_; }

    // Get raw file data
    const std::vector<uint8_t>& getRawData() const { return fileData_; }

    // Get last error
    const std::string& getLastError() const { return lastError_; }

    // Get preamble (document header/resources before first page)
    const std::vector<uint8_t>& getPreamble() const { return documentHeader_; }

    // Get postamble (document footer/closing fields after last page)
    const std::vector<uint8_t>& getPostamble() const { return documentFooter_; }

    // Get all resources from entire file
    const std::vector<std::vector<uint8_t>>& getAllResources() const { return allResources_; }

private:
    std::vector<uint8_t> fileData_;
    std::vector<AFPPage> pages_;
    std::vector<uint8_t> documentHeader_;  // Everything before first page
    std::vector<uint8_t> documentFooter_;  // Everything after last page
    std::vector<std::vector<uint8_t>> allResources_;  // All resource structured fields
    std::string lastError_;

    // Parse structured fields and identify pages
    bool parseStructuredFields();
};

// AFP Splitter - extracts pages and creates new AFP files
class AFPSplitter {
public:
    AFPSplitter();
    ~AFPSplitter();

    // Load AFP file
    bool loadFile(const std::string& filename);

    // Parse page range string (e.g., "1-2,5-8,10")
    std::vector<PageRange> parsePageRanges(const std::string& rangeStr);

    // Extract pages and write to output file
    bool extractPages(const std::vector<PageRange>& ranges, const std::string& outputFile);

    // Extract pages with resource collection (only requested pages, no previous pages)
    bool extractPagesWithResources(const std::vector<PageRange>& ranges, const std::string& outputFile);

    // Get page count
    int getPageCount() const { return parser_ ? parser_->getPageCount() : 0; }

    // Get last error message
    const std::string& getLastError() const { return lastError_; }

private:
    std::unique_ptr<AFPParser> parser_;
    std::string lastError_;
    std::string inputFilename_;

    // Expand page ranges to list of page numbers
    std::vector<int> expandPageRanges(const std::vector<PageRange>& ranges);

    // Write AFP file with selected pages
    bool writeAFPFile(const std::vector<int>& pageNumbers, const std::string& outputFile);
};

// Utility functions
namespace AFPUtil {
    // Read big-endian uint16
    uint16_t readUInt16BE(const uint8_t* data);

    // Write big-endian uint16
    void writeUInt16BE(uint8_t* data, uint16_t value);

    // Validate AFP file signature
    bool isValidAFP(const uint8_t* data, size_t length);

    // Trim whitespace from string
    std::string trim(const std::string& str);

    // Convert ASCII character to EBCDIC (Code Page 037/500)
    uint8_t asciiToEbcdic(char c);
}

#endif // AFP_PARSER_H
