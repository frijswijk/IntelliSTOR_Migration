// Quick diagnostic tool to analyze AFP page structure
#include <iostream>
#include <fstream>
#include <vector>
#include <iomanip>
#include <cstdint>

int main(int argc, char* argv[]) {
    if (argc != 2) {
        std::cerr << "Usage: " << argv[0] << " <afp_file>\n";
        return 1;
    }

    std::ifstream file(argv[1], std::ios::binary);
    if (!file) {
        std::cerr << "Failed to open: " << argv[1] << "\n";
        return 1;
    }

    // Read file
    std::vector<uint8_t> data((std::istreambuf_iterator<char>(file)),
                              std::istreambuf_iterator<char>());

    size_t offset = 0;
    int pageCount = 0;
    size_t lastEndPageOffset = 0;

    while (offset + 8 <= data.size()) {
        if (data[offset] != 0x5A) {
            offset++;
            continue;
        }

        uint16_t length = (data[offset + 1] << 8) | data[offset + 2];
        if (length < 8 || offset + length > data.size()) {
            offset++;
            continue;
        }

        uint8_t classCode = data[offset + 3];
        uint8_t typeCode = data[offset + 4];
        uint8_t categoryCode = data[offset + 5];

        // Begin Page: D3 A8 AF
        if (classCode == 0xD3 && typeCode == 0xA8 && categoryCode == 0xAF) {
            pageCount++;
            if (lastEndPageOffset > 0) {
                size_t gap = offset - lastEndPageOffset;
                std::cout << "Page " << pageCount << " starts at offset 0x"
                          << std::hex << offset << std::dec
                          << " (gap from last End Page: " << gap << " bytes)\n";

                if (gap > 0 && gap < 200) {
                    std::cout << "  Gap contains: ";
                    for (size_t i = lastEndPageOffset; i < offset && i < lastEndPageOffset + 60; i++) {
                        std::cout << std::hex << std::setw(2) << std::setfill('0')
                                  << (int)data[i] << " ";
                    }
                    std::cout << std::dec << "\n";
                }
            } else {
                std::cout << "Page 1 starts at offset 0x" << std::hex << offset << std::dec << "\n";
            }
        }

        // End Page: D3 A9 AF
        if (classCode == 0xD3 && typeCode == 0xA9 && categoryCode == 0xAF) {
            lastEndPageOffset = offset + length;
            std::cout << "Page " << pageCount << " ends at offset 0x"
                      << std::hex << lastEndPageOffset << std::dec << "\n\n";
        }

        offset += length;
    }

    std::cout << "\nTotal pages found: " << pageCount << "\n";
    std::cout << "Postamble size: " << (data.size() - lastEndPageOffset) << " bytes\n";

    return 0;
}
