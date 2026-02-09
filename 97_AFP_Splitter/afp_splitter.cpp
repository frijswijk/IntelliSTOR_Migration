#include "afp_parser.h"
#include <iostream>
#include <string>
#include <cstring>

void printUsage(const char* progName) {
    std::cout << "\n";
    std::cout << "=============================================================================\n";
    std::cout << "AFP Page Splitter v1.1\n";
    std::cout << "=============================================================================\n";
    std::cout << "Extract specific pages from AFP (Advanced Function Presentation) files\n";
    std::cout << "\n";
    std::cout << "Usage:\n";
    std::cout << "  " << progName << " <input.afp> <page_ranges> <output.afp> [--raw]\n";
    std::cout << "\n";
    std::cout << "Arguments:\n";
    std::cout << "  input.afp     Input AFP file path\n";
    std::cout << "  page_ranges   Page range specification (see examples below)\n";
    std::cout << "  output.afp    Output AFP file path\n";
    std::cout << "\n";
    std::cout << "Options:\n";
    std::cout << "  --raw    Raw copy mode: copies everything from file start through\n";
    std::cout << "           the requested pages (includes all prior pages).\n";
    std::cout << "\n";
    std::cout << "By default, extracts only the requested pages into a clean standalone\n";
    std::cout << "AFP document with proper BDT/EDT envelope and inter-page records.\n";
    std::cout << "\n";
    std::cout << "Page Range Format:\n";
    std::cout << "  Single page:        5\n";
    std::cout << "  Range:              1-5\n";
    std::cout << "  Multiple ranges:    1-2,5-8\n";
    std::cout << "  Mixed:              1-2,5,8-10\n";
    std::cout << "  Duplicates:         1-5,4-6     (pages 4-5 appear twice)\n";
    std::cout << "\n";
    std::cout << "Range Normalization:\n";
    std::cout << "  - If start < 1, it's changed to 1\n";
    std::cout << "  - If end > max pages, it's changed to last page\n";
    std::cout << "  - If range is reversed (8-5), it's swapped to (5-8)\n";
    std::cout << "\n";
    std::cout << "Examples:\n";
    std::cout << "  " << progName << " input.afp 1-2 output.afp\n";
    std::cout << "      Extract pages 1 and 2\n";
    std::cout << "\n";
    std::cout << "  " << progName << " input.afp 5 output.afp\n";
    std::cout << "      Extract only page 5\n";
    std::cout << "\n";
    std::cout << "  " << progName << " input.afp 1-3,5-7 output.afp\n";
    std::cout << "      Extract pages 1,2,3,5,6,7\n";
    std::cout << "\n";
    std::cout << "=============================================================================\n";
    std::cout << "\n";
}

void printError(const std::string& message) {
    std::cerr << "\n";
    std::cerr << "=============================================================================\n";
    std::cerr << "ERROR\n";
    std::cerr << "=============================================================================\n";
    std::cerr << message << "\n";
    std::cerr << "=============================================================================\n";
    std::cerr << "\n";
}

void printSuccess(const std::string& outputFile, int totalPages, int extractedPages) {
    std::cout << "\n";
    std::cout << "=============================================================================\n";
    std::cout << "SUCCESS\n";
    std::cout << "=============================================================================\n";
    std::cout << "Output file:      " << outputFile << "\n";
    std::cout << "Source pages:     " << totalPages << "\n";
    std::cout << "Extracted pages:  " << extractedPages << "\n";
    std::cout << "=============================================================================\n";
    std::cout << "\n";
}

int main(int argc, char* argv[]) {
    // Check for help flag
    if (argc == 2 && (strcmp(argv[1], "--help") == 0 || strcmp(argv[1], "-h") == 0 || strcmp(argv[1], "/?") == 0)) {
        printUsage(argv[0]);
        return 0;
    }

    // Check arguments
    if (argc != 4 && argc != 5) {
        std::cerr << "Error: Invalid number of arguments\n";
        printUsage(argv[0]);
        return 1;
    }

    std::string inputFile = argv[1];
    std::string rangeStr = argv[2];
    std::string outputFile = argv[3];
    bool rawMode = false;

    // Check for optional flag
    if (argc == 5) {
        if (strcmp(argv[4], "--raw") == 0) {
            rawMode = true;
        } else if (strcmp(argv[4], "--with-resources") == 0) {
            // Accept old flag for backwards compatibility (it was the default now)
            rawMode = false;
        } else {
            std::cerr << "Error: Unknown option: " << argv[4] << "\n";
            printUsage(argv[0]);
            return 1;
        }
    }

    std::cout << "\n";
    std::cout << "=============================================================================\n";
    std::cout << "AFP Page Splitter\n";
    std::cout << "=============================================================================\n";
    std::cout << "Input file:   " << inputFile << "\n";
    std::cout << "Page ranges:  " << rangeStr << "\n";
    std::cout << "Output file:  " << outputFile << "\n";
    std::cout << "Mode:         " << (rawMode ? "Raw (includes prior pages)" : "Clean extraction") << "\n";
    std::cout << "=============================================================================\n";
    std::cout << "\n";

    // Create splitter
    AFPSplitter splitter;

    // Load AFP file
    std::cout << "Loading AFP file...\n";
    if (!splitter.loadFile(inputFile)) {
        printError("Failed to load AFP file: " + splitter.getLastError());
        return 1;
    }

    int totalPages = splitter.getPageCount();
    std::cout << "Found " << totalPages << " page(s) in input file\n";
    std::cout << "\n";

    // Parse page ranges
    std::cout << "Parsing page ranges...\n";
    std::vector<PageRange> ranges = splitter.parsePageRanges(rangeStr);
    if (ranges.empty()) {
        printError("Failed to parse page ranges: " + splitter.getLastError());
        return 1;
    }

    // Display parsed ranges
    std::cout << "Parsed ranges:\n";
    for (const auto& range : ranges) {
        if (range.start == range.end) {
            std::cout << "  Page " << range.start << "\n";
        } else {
            std::cout << "  Pages " << range.start << " to " << range.end << "\n";
        }
    }
    std::cout << "\n";

    // Calculate total pages to extract
    int extractedPages = 0;
    for (const auto& range : ranges) {
        extractedPages += (range.end - range.start + 1);
    }

    std::cout << "Extracting " << extractedPages << " page(s)...\n";

    // Extract pages: default is clean extraction, --raw for legacy simple mode
    bool success;
    if (rawMode) {
        success = splitter.extractPages(ranges, outputFile);
    } else {
        success = splitter.extractPagesWithResources(ranges, outputFile);
    }

    if (!success) {
        printError("Failed to extract pages: " + splitter.getLastError());
        return 1;
    }

    printSuccess(outputFile, totalPages, extractedPages);
    return 0;
}
