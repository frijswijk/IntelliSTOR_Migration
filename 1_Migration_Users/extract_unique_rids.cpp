#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <set>
#include <vector>
#include <algorithm>
#include <filesystem>
#include <cstring>

namespace fs = std::filesystem;

/**
 * Extract Unique RIDs from Permissions CSV Files
 *
 * This program reads three permission CSV files from a specified folder:
 *   1. STYPE_FOLDER_ACCESS.csv
 *   2. STYPE_REPORT_SPECIES_ACCESS.csv
 *   3. STYPE_SECTION_ACCESS.csv
 *
 * Extracts all unique RIDs (Relative IDs) from the RID column and outputs
 * them to a new CSV file with deduplication and sorting.
 *
 * Usage:
 *   extract_unique_rids <folder_path>
 *   extract_unique_rids <folder_path> <output_file>
 *
 * Example:
 *   extract_unique_rids /path/to/Users_SG
 *   extract_unique_rids /path/to/Users_SG my_rids.csv
 */

// Forward declarations
bool extract_rids_from_files(const std::string& folder_path, std::set<std::string>& all_rids);
bool process_csv_file(const fs::path& filepath, std::set<std::string>& rids);
std::vector<std::string> parse_csv_line(const std::string& line);
int parse_rid_numeric(const std::string& rid);
bool write_unique_rids(const std::set<std::string>& rids, const fs::path& output_path);
void print_usage(const char* program_name);

/**
 * Parse a CSV line and return fields.
 * Simple CSV parser that handles quoted fields.
 */
std::vector<std::string> parse_csv_line(const std::string& line) {
    std::vector<std::string> fields;
    std::string field;
    bool in_quotes = false;

    for (size_t i = 0; i < line.length(); ++i) {
        char c = line[i];

        if (c == '"') {
            in_quotes = !in_quotes;
        } else if (c == ',' && !in_quotes) {
            fields.push_back(field);
            field.clear();
        } else {
            field += c;
        }
    }
    fields.push_back(field); // Add last field

    return fields;
}

/**
 * Parse numeric value from RID string for sorting.
 * Returns the numeric value if valid, otherwise returns INT_MAX.
 */
int parse_rid_numeric(const std::string& rid) {
    try {
        return std::stoi(rid);
    } catch (...) {
        return INT_MAX;
    }
}

/**
 * Process a single CSV file and extract RIDs.
 */
bool process_csv_file(const fs::path& filepath, std::set<std::string>& rids) {
    std::ifstream file(filepath);
    if (!file.is_open()) {
        std::cerr << "Error: Cannot open file: " << filepath << std::endl;
        return false;
    }

    std::string line;
    int row_count = 0;
    int rid_column_index = -1;

    // Read header
    if (std::getline(file, line)) {
        auto headers = parse_csv_line(line);
        for (size_t i = 0; i < headers.size(); ++i) {
            if (headers[i] == "RID") {
                rid_column_index = i;
                break;
            }
        }
    }

    if (rid_column_index == -1) {
        std::cerr << "Error: RID column not found in " << filepath.filename() << std::endl;
        return false;
    }

    std::cout << "Processing " << filepath.filename() << "..." << std::endl;

    // Read data rows
    while (std::getline(file, line)) {
        row_count++;
        auto fields = parse_csv_line(line);

        if (static_cast<int>(fields.size()) > rid_column_index) {
            std::string rid_str = fields[rid_column_index];

            // Trim whitespace
            size_t start = rid_str.find_first_not_of(" \t\r\n");
            size_t end = rid_str.find_last_not_of(" \t\r\n");
            if (start != std::string::npos) {
                rid_str = rid_str.substr(start, end - start + 1);
            } else {
                rid_str.clear();
            }

            // Split by pipe delimiter
            if (!rid_str.empty()) {
                std::stringstream ss(rid_str);
                std::string rid;
                while (std::getline(ss, rid, '|')) {
                    // Trim individual RID
                    size_t rid_start = rid.find_first_not_of(" \t\r\n");
                    size_t rid_end = rid.find_last_not_of(" \t\r\n");
                    if (rid_start != std::string::npos) {
                        rid = rid.substr(rid_start, rid_end - rid_start + 1);
                        if (!rid.empty()) {
                            rids.insert(rid);
                        }
                    }
                }
            }
        }
    }

    std::cout << "  Rows processed: " << row_count << std::endl;
    std::cout << "  Unique RIDs so far: " << rids.size() << std::endl;

    file.close();
    return true;
}

/**
 * Extract RIDs from all three permission CSV files.
 */
bool extract_rids_from_files(const std::string& folder_path, std::set<std::string>& all_rids) {
    fs::path base_path(folder_path);

    std::vector<std::string> csv_files = {
        "STYPE_FOLDER_ACCESS.csv",
        "STYPE_REPORT_SPECIES_ACCESS.csv",
        "STYPE_SECTION_ACCESS.csv"
    };

    for (const auto& filename : csv_files) {
        fs::path filepath = base_path / filename;

        if (!fs::exists(filepath)) {
            std::cerr << "Error: CSV file not found: " << filepath << std::endl;
            return false;
        }

        if (!process_csv_file(filepath, all_rids)) {
            return false;
        }
    }

    return true;
}

/**
 * Write unique RIDs to output CSV file (sorted numerically).
 */
bool write_unique_rids(const std::set<std::string>& rids, const fs::path& output_path) {
    // Sort RIDs numerically
    std::vector<std::pair<int, std::string>> sorted_rids;
    for (const auto& rid : rids) {
        sorted_rids.push_back({parse_rid_numeric(rid), rid});
    }
    std::sort(sorted_rids.begin(), sorted_rids.end());

    // Write to CSV
    std::ofstream output_file(output_path);
    if (!output_file.is_open()) {
        std::cerr << "Error: Cannot create output file: " << output_path << std::endl;
        return false;
    }

    output_file << "RID\n";
    for (const auto& [numeric_val, rid] : sorted_rids) {
        output_file << rid << "\n";
    }

    output_file.close();

    std::cout << "\nOutput written to: " << output_path << std::endl;
    std::cout << "Total unique RIDs: " << rids.size() << std::endl;

    return true;
}

/**
 * Print usage information.
 */
void print_usage(const char* program_name) {
    std::cout << "Usage: " << program_name << " <folder_path> [output_file]\n\n"
              << "Extract unique RIDs from permissions CSV files.\n\n"
              << "Arguments:\n"
              << "  folder_path    Path to folder containing the CSV files\n"
              << "  output_file    Output CSV filename (default: Unique_RIDs.csv)\n\n"
              << "Input Files (expected in the folder):\n"
              << "  - STYPE_FOLDER_ACCESS.csv\n"
              << "  - STYPE_REPORT_SPECIES_ACCESS.csv\n"
              << "  - STYPE_SECTION_ACCESS.csv\n\n"
              << "Examples:\n"
              << "  " << program_name << " /path/to/Users_SG\n"
              << "  " << program_name << " /path/to/Users_SG my_rids.csv\n";
}

/**
 * Main entry point.
 */
int main(int argc, char* argv[]) {
    if (argc < 2 || argc > 3) {
        print_usage(argv[0]);
        return 1;
    }

    std::string folder_path = argv[1];
    std::string output_filename = (argc == 3) ? argv[2] : "Unique_RIDs.csv";

    // Validate folder path
    fs::path folder(folder_path);
    if (!fs::exists(folder)) {
        std::cerr << "Error: Folder not found: " << folder_path << std::endl;
        return 1;
    }

    if (!fs::is_directory(folder)) {
        std::cerr << "Error: Path is not a directory: " << folder_path << std::endl;
        return 1;
    }

    try {
        // Extract RIDs
        std::cout << "Reading CSV files from: " << folder_path << "\n" << std::endl;

        std::set<std::string> all_rids;
        if (!extract_rids_from_files(folder_path, all_rids)) {
            return 1;
        }

        // Write output
        fs::path output_path = folder / output_filename;
        if (!write_unique_rids(all_rids, output_path)) {
            return 1;
        }

        std::cout << "\nSuccess!" << std::endl;
        return 0;

    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }
}
