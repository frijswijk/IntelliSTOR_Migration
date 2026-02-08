// papyrus_extract_folder_species.cpp
// Simplified C++ version of Extract_Folder_Species.py for Papyrus integration
// Extracts folder hierarchy and report species from IntelliSTOR MS SQL database

#include <windows.h>
#include <sql.h>
#include <sqlext.h>
#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <map>
#include <set>
#include <sstream>
#include <algorithm>
#include <ctime>
#include <filesystem>
#include <functional>

namespace fs = std::filesystem;

// Exit codes
enum ExitCode {
    EC_SUCCESS = 0,
    EC_INVALID_ARGS = 1,
    EC_DB_CONNECTION_FAILED = 2,
    EC_EXTRACTION_FAILED = 3,
    EC_OUTPUT_ERROR = 4
};

// Configuration
struct Config {
    std::string server;
    std::string database;
    std::string output_dir;
    std::string country_code;  // Either 2-letter code or "0" for auto-detection
    bool windows_auth = false;
    std::string username;
    std::string password;
    bool quiet = false;
};

// Folder structure
struct Folder {
    int item_id;
    std::string name;
    int parent_id;
    int item_type;
    std::string country_code;
};

// Folder-Species mapping
struct FolderSpecies {
    int item_id;
    int domain_id;
    int report_species_id;
};

// Report name
struct ReportName {
    int domain_id;
    int species_id;
    int item_id;
    std::string name;
};

// ODBC connection manager
class ODBCConnection {
private:
    SQLHENV henv = nullptr;
    SQLHDBC hdbc = nullptr;
    SQLHSTMT hstmt = nullptr;
    bool connected = false;

public:
    ~ODBCConnection() {
        disconnect();
    }

    bool connect(const Config& cfg) {
        SQLRETURN ret;

        ret = SQLAllocHandle(SQL_HANDLE_ENV, SQL_NULL_HANDLE, &henv);
        if (!SQL_SUCCEEDED(ret)) return false;

        ret = SQLSetEnvAttr(henv, SQL_ATTR_ODBC_VERSION, (SQLPOINTER)SQL_OV_ODBC3, 0);
        if (!SQL_SUCCEEDED(ret)) return false;

        ret = SQLAllocHandle(SQL_HANDLE_DBC, henv, &hdbc);
        if (!SQL_SUCCEEDED(ret)) return false;

        std::string conn_str;
        if (cfg.windows_auth) {
            conn_str = "DRIVER={SQL Server};SERVER=" + cfg.server +
                      ";DATABASE=" + cfg.database + ";Trusted_Connection=yes;";
        } else {
            conn_str = "DRIVER={SQL Server};SERVER=" + cfg.server +
                      ";DATABASE=" + cfg.database +
                      ";UID=" + cfg.username + ";PWD=" + cfg.password + ";";
        }

        SQLCHAR outstr[1024];
        SQLSMALLINT outstrlen;
        ret = SQLDriverConnect(hdbc, nullptr, (SQLCHAR*)conn_str.c_str(), SQL_NTS,
                              outstr, sizeof(outstr), &outstrlen, SQL_DRIVER_NOPROMPT);

        if (!SQL_SUCCEEDED(ret)) {
            SQLCHAR sqlstate[6], message[SQL_MAX_MESSAGE_LENGTH];
            SQLINTEGER native_error;
            SQLSMALLINT text_length;
            SQLGetDiagRec(SQL_HANDLE_DBC, hdbc, 1, sqlstate, &native_error,
                         message, sizeof(message), &text_length);
            std::cerr << "Connection failed: " << message << "\n";
            return false;
        }

        connected = true;
        if (!cfg.quiet) {
            std::cout << "Connected to " << cfg.server << "/" << cfg.database << "\n";
        }
        return true;
    }

    void disconnect() {
        if (hstmt) SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
        if (hdbc) {
            if (connected) SQLDisconnect(hdbc);
            SQLFreeHandle(SQL_HANDLE_DBC, hdbc);
        }
        if (henv) SQLFreeHandle(SQL_HANDLE_ENV, henv);
        connected = false;
    }

    bool executeQuery(const std::string& query) {
        if (hstmt) {
            SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
            hstmt = nullptr;
        }

        SQLRETURN ret = SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt);
        if (!SQL_SUCCEEDED(ret)) return false;

        ret = SQLExecDirect(hstmt, (SQLCHAR*)query.c_str(), SQL_NTS);
        if (!SQL_SUCCEEDED(ret)) {
            SQLCHAR sqlstate[6], message[SQL_MAX_MESSAGE_LENGTH];
            SQLINTEGER native_error;
            SQLSMALLINT text_length;
            SQLGetDiagRec(SQL_HANDLE_STMT, hstmt, 1, sqlstate, &native_error,
                         message, sizeof(message), &text_length);
            std::cerr << "Query failed: " << message << "\n";
            return false;
        }

        return true;
    }

    std::string fetchString(int col) {
        SQLCHAR buffer[4096];
        SQLLEN indicator;
        SQLRETURN ret = SQLGetData(hstmt, col, SQL_C_CHAR, buffer, sizeof(buffer), &indicator);
        if (SQL_SUCCEEDED(ret) && indicator != SQL_NULL_DATA) {
            std::string result((char*)buffer);
            // Trim whitespace
            result.erase(result.find_last_not_of(" \t\n\r\f\v") + 1);
            result.erase(0, result.find_first_not_of(" \t\n\r\f\v"));
            return result;
        }
        return "";
    }

    int fetchInt(int col) {
        SQLINTEGER value;
        SQLLEN indicator;
        SQLRETURN ret = SQLGetData(hstmt, col, SQL_C_SLONG, &value, 0, &indicator);
        if (SQL_SUCCEEDED(ret) && indicator != SQL_NULL_DATA) {
            return value;
        }
        return 0;
    }

    bool fetch() {
        SQLRETURN ret = SQLFetch(hstmt);
        return SQL_SUCCEEDED(ret);
    }

    bool tableExists(const std::string& table_name) {
        std::string query = "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = '" + table_name + "'";

        SQLHSTMT temp_stmt = nullptr;
        SQLRETURN ret = SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &temp_stmt);
        if (!SQL_SUCCEEDED(ret)) return false;

        ret = SQLExecDirect(temp_stmt, (SQLCHAR*)query.c_str(), SQL_NTS);
        if (!SQL_SUCCEEDED(ret)) {
            SQLFreeHandle(SQL_HANDLE_STMT, temp_stmt);
            return false;
        }

        ret = SQLFetch(temp_stmt);
        if (!SQL_SUCCEEDED(ret)) {
            SQLFreeHandle(SQL_HANDLE_STMT, temp_stmt);
            return false;
        }

        SQLINTEGER count;
        SQLLEN indicator;
        ret = SQLGetData(temp_stmt, 1, SQL_C_SLONG, &count, 0, &indicator);
        SQLFreeHandle(SQL_HANDLE_STMT, temp_stmt);

        return SQL_SUCCEEDED(ret) && count > 0;
    }

    std::vector<std::string> getColumnNames() {
        std::vector<std::string> columns;
        if (!hstmt) return columns;

        SQLSMALLINT num_cols = 0;
        SQLNumResultCols(hstmt, &num_cols);

        for (SQLSMALLINT i = 1; i <= num_cols; i++) {
            SQLCHAR col_name[256];
            SQLSMALLINT name_len;
            SQLRETURN ret = SQLDescribeCol(hstmt, i, col_name, sizeof(col_name),
                                          &name_len, nullptr, nullptr, nullptr, nullptr);
            if (SQL_SUCCEEDED(ret)) {
                columns.push_back(std::string((char*)col_name));
            }
        }

        return columns;
    }
};

// CSV writer helper
class CSVWriter {
private:
    std::ofstream file;

    std::string escape(const std::string& s) {
        if (s.find(',') == std::string::npos &&
            s.find('"') == std::string::npos &&
            s.find('\n') == std::string::npos) {
            return s;
        }
        std::string result = "\"";
        for (char c : s) {
            if (c == '"') result += "\"\"";
            else result += c;
        }
        result += "\"";
        return result;
    }

public:
    CSVWriter(const std::string& filename) {
        // Open in binary mode to control line endings explicitly
        file.open(filename, std::ios::out | std::ios::binary);
        if (!file.is_open()) {
            throw std::runtime_error("Cannot open file: " + filename);
        }
    }

    void writeRow(const std::vector<std::string>& values) {
        for (size_t i = 0; i < values.size(); ++i) {
            if (i > 0) file << ",";
            file << escape(values[i]);
        }

        // Platform-native line ending (matches Python's newline='')
        #ifdef _WIN32
            file << "\r\n";  // CRLF on Windows
        #else
            file << "\n";    // LF on Unix/Linux
        #endif
    }
};

// Country code detection
bool isCountryCode(const std::string& name) {
    static const char* codes[] = {
        "SG", "AU", "BN", "CN", "HK", "ID", "JP", "MY", "PH", "KR", "TH", "TW", "UK", "US", "VN"
    };

    // Trim whitespace from both ends (matching Python's strip())
    std::string trimmed = name;
    trimmed.erase(0, trimmed.find_first_not_of(" \t\n\r\f\v"));
    trimmed.erase(trimmed.find_last_not_of(" \t\n\r\f\v") + 1);

    // Check length AFTER trimming (matching Python behavior)
    if (trimmed.length() != 2) {
        return false;
    }

    // Convert to uppercase
    std::string upper = trimmed;
    std::transform(upper.begin(), upper.end(), upper.begin(), ::toupper);

    for (const auto& code : codes) {
        if (upper == code) return true;
    }
    return false;
}

// Main extractor class
class FolderSpeciesExtractor {
private:
    Config cfg;
    ODBCConnection db;

    std::map<int, Folder> folders;
    std::vector<FolderSpecies> folder_species;
    std::map<std::tuple<int, int, int>, std::string> report_names;
    std::set<int> valid_folder_ids;
    std::map<int, std::string> folder_country_codes;
    std::map<int, std::string> report_country_codes;
    std::vector<std::string> country_conflicts;

public:
    FolderSpeciesExtractor(const Config& config) : cfg(config) {}

    bool connect() {
        return db.connect(cfg);
    }

    bool loadFolders() {
        if (!cfg.quiet) std::cout << "Loading folders...\n";

        if (!db.tableExists("FOLDER")) {
            std::cerr << "FOLDER table does not exist\n";
            return false;
        }

        std::string query = "SELECT ITEM_ID, NAME, PARENT_ID, PRIVATE_ROOT_ID, ITEM_TYPE FROM FOLDER ORDER BY ITEM_ID";

        if (!db.executeQuery(query)) {
            std::cerr << "Failed to load folders\n";
            return false;
        }

        int count = 0;
        while (db.fetch()) {
            Folder f;
            f.item_id = db.fetchInt(1);
            f.name = db.fetchString(2);
            f.parent_id = db.fetchInt(3);
            // PRIVATE_ROOT_ID = fetchInt(4) - not needed
            f.item_type = db.fetchInt(5);
            folders[f.item_id] = f;
            count++;
        }

        if (!cfg.quiet) std::cout << "  Loaded " << count << " folders\n";
        return true;
    }

    bool loadFolderSpecies() {
        if (!cfg.quiet) std::cout << "Loading folder-species mappings...\n";

        if (!db.tableExists("FOLDER_SPECIES")) {
            std::cerr << "FOLDER_SPECIES table does not exist\n";
            return false;
        }

        std::string query = "SELECT ITEM_ID, DOMAIN_ID, REPORT_SPECIES_ID FROM FOLDER_SPECIES ORDER BY ITEM_ID, REPORT_SPECIES_ID";

        if (!db.executeQuery(query)) {
            std::cerr << "Failed to load folder-species mappings\n";
            return false;
        }

        int count = 0;
        while (db.fetch()) {
            FolderSpecies fs;
            fs.item_id = db.fetchInt(1);
            fs.domain_id = db.fetchInt(2);
            fs.report_species_id = db.fetchInt(3);
            folder_species.push_back(fs);
            count++;
        }

        if (!cfg.quiet) std::cout << "  Loaded " << count << " mappings\n";
        return true;
    }

    bool loadReportNames() {
        if (!cfg.quiet) std::cout << "Loading report names...\n";

        if (!db.tableExists("REPORT_SPECIES_NAME")) {
            std::cerr << "REPORT_SPECIES_NAME table does not exist\n";
            return false;
        }

        std::string query = "SELECT DOMAIN_ID, REPORT_SPECIES_ID, ITEM_ID, NAME FROM REPORT_SPECIES_NAME ORDER BY REPORT_SPECIES_ID, ITEM_ID";

        if (!db.executeQuery(query)) {
            std::cerr << "Failed to load report names\n";
            return false;
        }

        int count = 0;
        while (db.fetch()) {
            int domain_id = db.fetchInt(1);
            int species_id = db.fetchInt(2);
            int item_id = db.fetchInt(3);
            std::string name = db.fetchString(4);
            report_names[std::make_tuple(domain_id, species_id, item_id)] = name;
            count++;
        }

        if (!cfg.quiet) std::cout << "  Loaded " << count << " report names\n";
        return true;
    }

    void validateHierarchy() {
        if (!cfg.quiet) std::cout << "Validating folder hierarchy...\n";

        std::set<int> all_ids;
        for (const auto& pair : folders) {
            all_ids.insert(pair.first);
        }

        std::function<bool(int, std::set<int>&)> isValid = [&](int item_id, std::set<int>& visited) -> bool {
            if (visited.count(item_id)) return false;  // Circular reference
            if (valid_folder_ids.count(item_id)) return true;  // Already validated

            auto it = folders.find(item_id);
            if (it == folders.end()) return false;

            const Folder& f = it->second;
            if (f.item_type == 3) return false;  // Exclude ITEM_TYPE=3

            if (f.parent_id == 0) {
                valid_folder_ids.insert(item_id);
                return true;
            }

            if (all_ids.count(f.parent_id) == 0) return false;  // Orphan

            visited.insert(item_id);
            if (isValid(f.parent_id, visited)) {
                valid_folder_ids.insert(item_id);
                return true;
            }

            return false;
        };

        for (const auto& pair : folders) {
            std::set<int> visited;
            isValid(pair.first, visited);
        }

        int excluded = folders.size() - valid_folder_ids.size();
        if (!cfg.quiet) {
            std::cout << "  Valid folders: " << valid_folder_ids.size() << "\n";
            std::cout << "  Excluded folders: " << excluded << "\n";
        }
    }

    void assignCountryCodes() {
        if (!cfg.quiet) std::cout << "Assigning country codes...\n";

        if (cfg.country_code != "0") {
            // Fixed country mode
            for (int item_id : valid_folder_ids) {
                folder_country_codes[item_id] = cfg.country_code;
            }
            if (!cfg.quiet) {
                std::cout << "  Assigned " << cfg.country_code << " to all folders\n";
            }
        } else {
            // Auto-detection mode
            std::map<int, std::vector<int>> children;
            for (int item_id : valid_folder_ids) {
                int parent_id = folders[item_id].parent_id;
                if (parent_id != 0) {
                    children[parent_id].push_back(item_id);
                }
            }

            std::function<void(int, const std::string&)> assign = [&](int item_id, const std::string& parent_code) {
                const Folder& f = folders[item_id];
                std::string code = parent_code;

                // isCountryCode now handles length check and trimming internally
                if (isCountryCode(f.name)) {
                    // Trim whitespace before uppercasing
                    code = f.name;
                    code.erase(0, code.find_first_not_of(" \t\n\r\f\v"));
                    code.erase(code.find_last_not_of(" \t\n\r\f\v") + 1);
                    std::transform(code.begin(), code.end(), code.begin(), ::toupper);
                }

                folder_country_codes[item_id] = code;

                for (int child_id : children[item_id]) {
                    assign(child_id, code);
                }
            };

            for (int item_id : valid_folder_ids) {
                if (folders[item_id].parent_id == 0) {
                    assign(item_id, "SG");
                }
            }

            if (!cfg.quiet) {
                std::cout << "  Assigned country codes to " << folder_country_codes.size() << " folders\n";
            }
        }
    }

    std::pair<std::string, std::string> getReportNames(int domain_id, int species_id) {
        auto display_key = std::make_tuple(domain_id, species_id, 0);
        std::string display_name = "UNKNOWN_" + std::to_string(species_id);
        if (report_names.count(display_key)) {
            display_name = report_names[display_key];
        }

        auto name_key = std::make_tuple(domain_id, species_id, 1);
        std::string name = display_name;
        if (report_names.count(name_key)) {
            name = report_names[name_key];
        }

        return {name, display_name};
    }

    std::string trackReportCountryCode(int species_id, const std::string& folder_code) {
        if (report_country_codes.count(species_id)) {
            std::string existing = report_country_codes[species_id];
            if (existing != "SG" && folder_code != existing) {
                // Conflict detected
                std::stringstream conflict_msg;
                conflict_msg << "Report Species " << species_id << ": "
                            << "Already assigned to " << existing << ", "
                            << "cannot override with " << folder_code;
                country_conflicts.push_back(conflict_msg.str());
                return existing;
            } else if (existing == "SG" && folder_code != "SG") {
                report_country_codes[species_id] = folder_code;
                return folder_code;
            } else {
                return existing;
            }
        } else {
            report_country_codes[species_id] = folder_code;
            return folder_code;
        }
    }

    void writeConflictLog() {
        if (country_conflicts.empty()) {
            if (!cfg.quiet) {
                std::cout << "No country code conflicts detected\n";
            }
            return;
        }

        std::string log_file = cfg.output_dir + "/log.txt";
        std::ofstream file(log_file);
        if (!file.is_open()) {
            std::cerr << "Warning: Could not create log.txt\n";
            return;
        }

        file << "Country Code Assignment Conflicts\n";
        file << "======================================================================\n\n";
        file << "Total conflicts: " << country_conflicts.size() << "\n\n";

        for (const auto& conflict : country_conflicts) {
            file << conflict << "\n";
        }

        file.close();

        if (!cfg.quiet) {
            std::cout << country_conflicts.size() << " country code conflicts detected\n";
            std::cout << "Conflicts written to " << log_file << "\n";
        }
    }

    bool generateFolderHierarchyCSV() {
        if (!cfg.quiet) std::cout << "Generating Folder_Hierarchy.csv...\n";

        std::string output_file = cfg.output_dir + "/Folder_Hierarchy.csv";
        CSVWriter csv(output_file);

        csv.writeRow({"ITEM_ID", "NAME", "PARENT_ID", "ITEM_TYPE", "COUNTRY_CODE"});

        std::vector<int> sorted_ids(valid_folder_ids.begin(), valid_folder_ids.end());
        std::sort(sorted_ids.begin(), sorted_ids.end());

        for (int item_id : sorted_ids) {
            const Folder& f = folders[item_id];
            std::string country = folder_country_codes.count(item_id) ? folder_country_codes[item_id] : "SG";
            csv.writeRow({
                std::to_string(f.item_id),
                f.name,
                std::to_string(f.parent_id),
                std::to_string(f.item_type),
                country
            });
        }

        if (!cfg.quiet) std::cout << "  Written " << sorted_ids.size() << " folders\n";
        return true;
    }

    bool generateFolderReportCSV() {
        if (!cfg.quiet) std::cout << "Generating Folder_Report.csv...\n";

        std::string output_file = cfg.output_dir + "/Folder_Report.csv";
        CSVWriter csv(output_file);

        csv.writeRow({"ITEM_ID", "ITEM_NAME", "REPORT_SPECIES_ID", "REPORT_SPECIES_NAME", "REPORT_SPECIES_DISPLAYNAME", "COUNTRY_CODE"});

        // Collect records into a vector for sorting (matching Python behavior)
        struct FolderReportRecord {
            int item_id;
            std::string item_name;
            int report_species_id;
            std::string report_species_name;
            std::string report_species_displayname;
            std::string country_code;
        };

        std::vector<FolderReportRecord> records;
        int skipped_invalid = 0;
        int skipped_zero = 0;

        for (const auto& fs : folder_species) {
            if (valid_folder_ids.count(fs.item_id) == 0) {
                skipped_invalid++;
                continue;
            }

            if (fs.report_species_id == 0) {
                skipped_zero++;
                continue;
            }

            auto names = getReportNames(fs.domain_id, fs.report_species_id);
            std::string folder_name = folders[fs.item_id].name;
            std::string folder_code = folder_country_codes.count(fs.item_id) ? folder_country_codes[fs.item_id] : "SG";
            std::string report_code = trackReportCountryCode(fs.report_species_id, folder_code);

            records.push_back({
                fs.item_id,
                folder_name,
                fs.report_species_id,
                names.first,
                names.second,
                report_code
            });
        }

        // Explicit sort by ITEM_ID, then REPORT_SPECIES_ID (matching Python)
        std::sort(records.begin(), records.end(),
            [](const FolderReportRecord& a, const FolderReportRecord& b) {
                if (a.item_id != b.item_id) return a.item_id < b.item_id;
                return a.report_species_id < b.report_species_id;
            }
        );

        // Write sorted records
        for (const auto& rec : records) {
            csv.writeRow({
                std::to_string(rec.item_id),
                rec.item_name,
                std::to_string(rec.report_species_id),
                rec.report_species_name,
                rec.report_species_displayname,
                rec.country_code
            });
        }

        if (!cfg.quiet) {
            std::cout << "  Written " << records.size() << " mappings\n";
            std::cout << "  Skipped " << skipped_invalid << " invalid folders\n";
            std::cout << "  Skipped " << skipped_zero << " species ID=0\n";
        }
        return true;
    }

    bool generateReportSpeciesCSV() {
        if (!cfg.quiet) std::cout << "Generating Report_Species.csv...\n";

        std::string output_file = cfg.output_dir + "/Report_Species.csv";
        CSVWriter csv(output_file);

        csv.writeRow({"REPORT_SPECIES_ID", "REPORT_SPECIES_NAME", "REPORT_SPECIES_DISPLAYNAME", "COUNTRY_CODE", "IN_USE"});

        std::map<int, int> unique_species;  // species_id -> domain_id

        for (const auto& fs : folder_species) {
            if (valid_folder_ids.count(fs.item_id) && fs.report_species_id > 0) {
                if (unique_species.count(fs.report_species_id) == 0) {
                    unique_species[fs.report_species_id] = fs.domain_id;
                }
            }
        }

        for (const auto& pair : unique_species) {
            int species_id = pair.first;
            int domain_id = pair.second;
            auto names = getReportNames(domain_id, species_id);
            std::string country = report_country_codes.count(species_id) ? report_country_codes[species_id] : "SG";

            csv.writeRow({
                std::to_string(species_id),
                names.first,
                names.second,
                country,
                "1"
            });
        }

        if (!cfg.quiet) std::cout << "  Written " << unique_species.size() << " species\n";
        return true;
    }

    bool extractAll() {
        if (!loadFolders()) return false;
        if (!loadFolderSpecies()) return false;
        if (!loadReportNames()) return false;
        validateHierarchy();
        assignCountryCodes();
        if (!generateFolderHierarchyCSV()) return false;
        if (!generateFolderReportCSV()) return false;
        if (!generateReportSpeciesCSV()) return false;
        writeConflictLog();  // Write conflict log if any
        return true;
    }
};

void printUsage(const char* prog) {
    std::cout << "Usage: " << prog << " [OPTIONS]\n\n";
    std::cout << "Required:\n";
    std::cout << "  --server SERVER       MS SQL Server hostname\n";
    std::cout << "  --database DATABASE   Database name\n";
    std::cout << "  --Country CODE        Country code: 2-letter (SG, HK) or \"0\" for auto-detect\n\n";
    std::cout << "Authentication:\n";
    std::cout << "  --windows-auth        Use Windows Authentication\n";
    std::cout << "  --user USERNAME       SQL Server username\n";
    std::cout << "  --password PASSWORD   SQL Server password\n\n";
    std::cout << "Options:\n";
    std::cout << "  --output-dir DIR      Output directory (default: current)\n";
    std::cout << "  --quiet               Suppress progress messages\n";
    std::cout << "  --help                Show this help\n\n";
    std::cout << "Example:\n";
    std::cout << "  " << prog << " --server SQLSRV01 --database IntelliSTOR_SG --windows-auth --Country SG\n";
}

int main(int argc, char* argv[]) {
    Config cfg;
    cfg.output_dir = ".";
    cfg.windows_auth = true;

    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];

        if (arg == "--help") {
            printUsage(argv[0]);
            return EC_SUCCESS;
        } else if (arg == "--server" && i + 1 < argc) {
            cfg.server = argv[++i];
        } else if (arg == "--database" && i + 1 < argc) {
            cfg.database = argv[++i];
        } else if (arg == "--Country" && i + 1 < argc) {
            cfg.country_code = argv[++i];
        } else if (arg == "--output-dir" && i + 1 < argc) {
            cfg.output_dir = argv[++i];
        } else if (arg == "--windows-auth") {
            cfg.windows_auth = true;
        } else if (arg == "--user" && i + 1 < argc) {
            cfg.username = argv[++i];
            cfg.windows_auth = false;
        } else if (arg == "--password" && i + 1 < argc) {
            cfg.password = argv[++i];
            cfg.windows_auth = false;
        } else if (arg == "--quiet") {
            cfg.quiet = true;
        } else {
            std::cerr << "Unknown argument: " << arg << "\n";
            printUsage(argv[0]);
            return EC_INVALID_ARGS;
        }
    }

    if (cfg.server.empty() || cfg.database.empty() || cfg.country_code.empty()) {
        std::cerr << "Error: Missing required arguments\n\n";
        printUsage(argv[0]);
        return EC_INVALID_ARGS;
    }

    try {
        fs::create_directories(cfg.output_dir);
    } catch (const std::exception& e) {
        std::cerr << "Error creating output directory: " << e.what() << "\n";
        return EC_OUTPUT_ERROR;
    }

    if (!cfg.quiet) {
        std::cout << "==================================================\n";
        std::cout << "Papyrus Folder & Species Extractor\n";
        std::cout << "==================================================\n\n";
    }

    FolderSpeciesExtractor extractor(cfg);

    if (!extractor.connect()) {
        std::cerr << "Failed to connect to database\n";
        return EC_DB_CONNECTION_FAILED;
    }

    if (!extractor.extractAll()) {
        std::cerr << "Extraction failed\n";
        return EC_EXTRACTION_FAILED;
    }

    if (!cfg.quiet) {
        std::cout << "\n==================================================\n";
        std::cout << "Extraction completed successfully\n";
        std::cout << "Output: " << cfg.output_dir << "\n";
        std::cout << "==================================================\n";
    }

    return EC_SUCCESS;
}
