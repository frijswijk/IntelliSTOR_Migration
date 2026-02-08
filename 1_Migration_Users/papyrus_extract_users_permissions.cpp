// papyrus_extract_users_permissions.cpp
// Simplified C++ version of Extract_Users_Permissions.py for Papyrus integration
// Extracts users, groups, sections, and permissions from IntelliSTOR MS SQL database

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
#include <iomanip>
#include <ctime>
#include <filesystem>
#include <random>
#include <algorithm>
#include <cstdint>
#include <tuple>

namespace fs = std::filesystem;

// Exit codes
enum ExitCode {
    EC_SUCCESS = 0,
    EC_INVALID_ARGS = 1,
    EC_DB_CONNECTION_FAILED = 2,
    EC_EXTRACTION_FAILED = 3,
    EC_OUTPUT_ERROR = 4
};

// Configuration structure
struct Config {
    std::string server;
    std::string database;
    std::string output_dir;
    bool windows_auth = false;
    std::string username;
    std::string password;
    bool quiet = false;

    // Test data generation options
    bool testdata_mode = false;
    bool testdata_dryrun = false;
    int testdata_users = 5000;
    int testdata_min_groups = 1;
    int testdata_max_groups = 3;
    std::string testdata_special_group = "DocMgmtUsers";
};

// User structure
struct User {
    std::string user_id;
    std::string username;
    std::string full_name;
    std::string email;
    std::string status;
};

// Group structure
struct Group {
    std::string group_id;
    std::string group_name;
    std::string description;
};

// Section structure
struct Section {
    std::string section_id;
    std::string section_name;
    std::string owner;
};

// Permission structure
struct Permission {
    std::string resource_type;
    std::string resource_id;
    std::string principal_type; // USER or GROUP
    std::string principal_id;
    std::string access_level;  // READ, WRITE, DELETE, etc.
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

        // Allocate environment handle
        ret = SQLAllocHandle(SQL_HANDLE_ENV, SQL_NULL_HANDLE, &henv);
        if (!SQL_SUCCEEDED(ret)) {
            std::cerr << "Failed to allocate environment handle\n";
            return false;
        }

        // Set ODBC version
        ret = SQLSetEnvAttr(henv, SQL_ATTR_ODBC_VERSION, (SQLPOINTER)SQL_OV_ODBC3, 0);
        if (!SQL_SUCCEEDED(ret)) {
            std::cerr << "Failed to set ODBC version\n";
            return false;
        }

        // Allocate connection handle
        ret = SQLAllocHandle(SQL_HANDLE_DBC, henv, &hdbc);
        if (!SQL_SUCCEEDED(ret)) {
            std::cerr << "Failed to allocate connection handle\n";
            return false;
        }

        // Build connection string
        std::string conn_str;
        if (cfg.windows_auth) {
            conn_str = "DRIVER={SQL Server};SERVER=" + cfg.server +
                      ";DATABASE=" + cfg.database + ";Trusted_Connection=yes;";
        } else {
            conn_str = "DRIVER={SQL Server};SERVER=" + cfg.server +
                      ";DATABASE=" + cfg.database +
                      ";UID=" + cfg.username + ";PWD=" + cfg.password + ";";
        }

        // Connect to database
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

    bool executeQuery(const std::string& query, bool silent = false) {
        if (hstmt) {
            SQLFreeHandle(SQL_HANDLE_STMT, hstmt);
            hstmt = nullptr;
        }

        SQLRETURN ret = SQLAllocHandle(SQL_HANDLE_STMT, hdbc, &hstmt);
        if (!SQL_SUCCEEDED(ret)) {
            if (!silent) std::cerr << "Failed to allocate statement handle\n";
            return false;
        }

        ret = SQLExecDirect(hstmt, (SQLCHAR*)query.c_str(), SQL_NTS);
        if (!SQL_SUCCEEDED(ret)) {
            if (!silent) {
                SQLCHAR sqlstate[6], message[SQL_MAX_MESSAGE_LENGTH];
                SQLINTEGER native_error;
                SQLSMALLINT text_length;
                SQLGetDiagRec(SQL_HANDLE_STMT, hstmt, 1, sqlstate, &native_error,
                             message, sizeof(message), &text_length);
                std::cerr << "Query failed: " << message << "\n";
                std::cerr << "Query: " << query << "\n";
            }
            return false;
        }

        return true;
    }

    bool tableExists(const std::string& table_name) {
        std::string query = "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = '" + table_name + "'";
        if (!executeQuery(query, true)) {  // Silent query
            return false;
        }

        if (fetch()) {
            std::string count_str = fetchString(1);
            int count = std::stoi(count_str);
            return count > 0;
        }
        return false;
    }

    std::string fetchString(int col) {
        SQLCHAR buffer[4096];
        SQLLEN indicator;
        SQLRETURN ret = SQLGetData(hstmt, col, SQL_C_CHAR, buffer, sizeof(buffer), &indicator);
        if (SQL_SUCCEEDED(ret) && indicator != SQL_NULL_DATA) {
            return std::string((char*)buffer);
        }
        return "";
    }

    std::string fetchStringOrBinary(int col, bool is_binary_col = false) {
        if (!is_binary_col) {
            return fetchString(col);
        }

        // Fetch as binary and escape like Python
        SQLCHAR buffer[4096];
        SQLLEN indicator;
        SQLRETURN ret = SQLGetData(hstmt, col, SQL_C_BINARY, buffer, sizeof(buffer), &indicator);
        if (SQL_SUCCEEDED(ret) && indicator != SQL_NULL_DATA && indicator > 0) {
            std::stringstream ss;
            ss << "b'";
            for (SQLLEN i = 0; i < indicator; i++) {
                unsigned char c = buffer[i];
                if (c >= 32 && c < 127 && c != '\'' && c != '\\') {
                    ss << (char)c;
                } else {
                    ss << "\\x" << std::hex << std::setfill('0') << std::setw(2) << (int)c;
                }
            }
            ss << "'";
            return ss.str();
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

    std::vector<uint8_t> fetchBinary(int col) {
        SQLCHAR buffer[8192];
        SQLLEN indicator;
        SQLRETURN ret = SQLGetData(hstmt, col, SQL_C_BINARY, buffer, sizeof(buffer), &indicator);
        if (SQL_SUCCEEDED(ret) && indicator != SQL_NULL_DATA && indicator > 0) {
            return std::vector<uint8_t>(buffer, buffer + indicator);
        }
        return {};
    }

    bool fetch() {
        SQLRETURN ret = SQLFetch(hstmt);
        return SQL_SUCCEEDED(ret);
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

// SID (Security Identifier) parser
class SIDParser {
public:
    static std::string parseSID(const std::vector<uint8_t>& data, size_t offset) {
        if (offset + 8 > data.size()) return "";

        // Check SID structure: revision (1) + sub-authority count
        uint8_t revision = data[offset];
        if (revision != 1) return "";

        uint8_t sub_auth_count = data[offset + 1];
        if (sub_auth_count > 15) return "";  // Sanity check

        size_t expected_len = 8 + (sub_auth_count * 4);
        if (offset + expected_len > data.size()) return "";

        // Extract identifier authority (6 bytes, big-endian)
        uint64_t authority = 0;
        for (int i = 0; i < 6; i++) {
            authority = (authority << 8) | data[offset + 2 + i];
        }

        // Build SID string
        std::stringstream ss;
        ss << "S-" << (int)revision << "-" << authority;

        // Extract sub-authorities (4 bytes each, little-endian)
        for (int i = 0; i < sub_auth_count; i++) {
            size_t pos = offset + 8 + (i * 4);
            uint32_t sub_auth = data[pos] | (data[pos+1] << 8) |
                               (data[pos+2] << 16) | (data[pos+3] << 24);
            ss << "-" << sub_auth;
        }

        return ss.str();
    }

    static std::vector<std::string> findAllSIDs(const std::vector<uint8_t>& data) {
        std::vector<std::string> sids;
        std::set<std::string> unique_sids;

        for (size_t i = 0; i + 8 <= data.size(); i++) {
            if (data[i] == 1 && data[i+1] <= 15) {  // Revision=1, reasonable sub-auth count
                std::string sid = parseSID(data, i);
                if (!sid.empty() && sid.length() > 10 && unique_sids.find(sid) == unique_sids.end()) {
                    sids.push_back(sid);
                    unique_sids.insert(sid);
                }
            }
        }

        return sids;
    }
};

// CSV writer helper
class CSVWriter {
private:
    std::ofstream file;
    bool first_in_row = true;

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
        file.open(filename);
        if (!file.is_open()) {
            throw std::runtime_error("Cannot open file: " + filename);
        }
    }

    ~CSVWriter() {
        if (file.is_open()) file.close();
    }

    void writeField(const std::string& value) {
        if (!first_in_row) file << ",";
        file << escape(value);
        first_in_row = false;
    }

    void endRow() {
        file << "\n";
        first_in_row = true;
    }
};

// ACL/SID Parser
class ACLParser {
public:
    struct SIDInfo {
        std::string sid;
        int rid;  // -1 if not a domain SID
        bool is_everyone;
    };

    static std::vector<SIDInfo> parseSIDs(const std::vector<uint8_t>& data) {
        std::vector<SIDInfo> results;

        // Scan for SID patterns (starts with revision=1)
        for (size_t i = 0; i + 8 <= data.size(); i++) {
            if (data[i] == 0x01) {  // Revision 1
                uint8_t sub_auth_count = data[i + 1];

                if (sub_auth_count > 0 && sub_auth_count <= 15) {
                    size_t sid_size = 8 + (sub_auth_count * 4);
                    if (i + sid_size <= data.size()) {
                        auto sid_info = parseSID(data, i);
                        if (!sid_info.sid.empty()) {
                            results.push_back(sid_info);
                        }
                    }
                }
            }
        }

        return results;
    }

private:
    static SIDInfo parseSID(const std::vector<uint8_t>& data, size_t offset) {
        SIDInfo info;
        info.rid = -1;
        info.is_everyone = false;

        uint8_t revision = data[offset];
        uint8_t sub_auth_count = data[offset + 1];

        // Authority (6 bytes, big-endian)
        uint64_t authority = 0;
        for (int i = 0; i < 6; i++) {
            authority = (authority << 8) | data[offset + 2 + i];
        }

        // Build SID string
        std::stringstream ss;
        ss << "S-" << (int)revision << "-" << authority;

        // Sub-authorities (4 bytes each, little-endian)
        std::vector<uint32_t> sub_auths;
        for (int i = 0; i < sub_auth_count; i++) {
            size_t pos = offset + 8 + (i * 4);
            uint32_t sub_auth = data[pos] | (data[pos+1] << 8) |
                               (data[pos+2] << 16) | (data[pos+3] << 24);
            sub_auths.push_back(sub_auth);
            ss << "-" << sub_auth;
        }

        info.sid = ss.str();

        // Check if it's Everyone (S-1-1-0)
        if (info.sid == "S-1-1-0") {
            info.is_everyone = true;
        }

        // Extract RID from domain SIDs (S-1-5-21-domain1-domain2-domain3-RID)
        if (sub_auth_count >= 5 && sub_auths.size() >= 5 && sub_auths[0] == 21) {
            info.rid = sub_auths[sub_auth_count - 1];
        }

        return info;
    }
};

// Main extractor class
class UsersPermissionsExtractor {
private:
    Config cfg;
    ODBCConnection db;

    // RID maps for ACL decoding
    std::map<int, int> user_rid_map;   // RID -> USER_ID
    std::map<int, int> group_rid_map;  // RID -> GROUP_ID
    std::set<int> unmapped_rids;       // RIDs found in ACLs but not in database

    std::string getCurrentTimestamp() {
        auto now = std::time(nullptr);
        std::stringstream ss;
        ss << std::put_time(std::localtime(&now), "%Y-%m-%d %H:%M:%S");
        return ss.str();
    }

    std::string trim(const std::string& str) {
        size_t start = 0;
        size_t end = str.length();

        while (start < end && std::isspace((unsigned char)str[start])) {
            start++;
        }

        while (end > start && std::isspace((unsigned char)str[end - 1])) {
            end--;
        }

        return str.substr(start, end - start);
    }

    std::vector<std::string> parseCSVLine(const std::string& line) {
        std::vector<std::string> fields;
        std::string current;
        bool in_quotes = false;

        for (size_t i = 0; i < line.size(); i++) {
            char c = line[i];
            if (c == '"') {
                if (in_quotes && i + 1 < line.size() && line[i + 1] == '"') {
                    current += '"';
                    i++;
                } else {
                    in_quotes = !in_quotes;
                }
            } else if (c == ',' && !in_quotes) {
                fields.push_back(current);
                current.clear();
            } else {
                current += c;
            }
        }
        fields.push_back(current);
        return fields;
    }

    void buildRIDMaps() {
        if (!cfg.quiet) std::cout << "Building RID maps...\n";

        // Build user RID map
        std::string users_csv = cfg.output_dir + "/Users.csv";
        std::ifstream users_file(users_csv);
        if (users_file.is_open()) {
            std::string line;
            std::getline(users_file, line);  // Read header
            auto header = parseCSVLine(line);

            // Find USER_ID column index
            int user_id_col = -1;
            for (size_t i = 0; i < header.size(); i++) {
                if (header[i] == "USER_ID") {
                    user_id_col = i;
                    break;
                }
            }

            while (std::getline(users_file, line)) {
                if (line.empty()) continue;
                try {
                    auto fields = parseCSVLine(line);
                    if (user_id_col >= 0 && user_id_col < (int)fields.size()) {
                        std::string id_str = fields[user_id_col];
                        id_str.erase(std::remove(id_str.begin(), id_str.end(), ' '), id_str.end());
                        if (!id_str.empty() && std::all_of(id_str.begin(), id_str.end(), ::isdigit)) {
                            int user_id = std::stoi(id_str);
                            user_rid_map[user_id] = user_id;
                        }
                    }
                } catch (...) {
                    // Skip invalid lines
                }
            }
            users_file.close();
        }

        // Build group RID map
        std::string groups_csv = cfg.output_dir + "/UserGroups.csv";
        std::ifstream groups_file(groups_csv);
        if (groups_file.is_open()) {
            std::string line;
            std::getline(groups_file, line);  // Read header
            auto header = parseCSVLine(line);

            // Find GROUP_ID column index
            int group_id_col = -1;
            for (size_t i = 0; i < header.size(); i++) {
                if (header[i] == "GROUP_ID") {
                    group_id_col = i;
                    break;
                }
            }

            while (std::getline(groups_file, line)) {
                if (line.empty()) continue;
                try {
                    auto fields = parseCSVLine(line);
                    if (group_id_col >= 0 && group_id_col < (int)fields.size()) {
                        std::string id_str = fields[group_id_col];
                        id_str.erase(std::remove(id_str.begin(), id_str.end(), ' '), id_str.end());
                        if (!id_str.empty() && std::all_of(id_str.begin(), id_str.end(), ::isdigit)) {
                            int group_id = std::stoi(id_str);
                            group_rid_map[group_id] = group_id;
                        }
                    }
                } catch (...) {
                    // Skip invalid lines
                }
            }
            groups_file.close();
        }

        if (!cfg.quiet) {
            std::cout << "  Built RID maps: " << user_rid_map.size() << " users, "
                      << group_rid_map.size() << " groups\n";

            // Show first few group IDs for debugging
            if (cfg.testdata_mode && !group_rid_map.empty()) {
                std::cout << "  Sample group IDs in map: ";
                int shown = 0;
                for (const auto& pair : group_rid_map) {
                    if (shown++ >= 5) break;
                    std::cout << pair.first << " ";
                }
                std::cout << "...\n";
            }
        }
    }

public:
    UsersPermissionsExtractor(const Config& config) : cfg(config) {}

    bool connect() {
        return db.connect(cfg);
    }

    bool extractUsers() {
        if (!cfg.quiet) std::cout << "Extracting users...\n";

        // Try different table names (check existence first)
        std::vector<std::string> table_names = {"SCM_USERS", "USER_PROFILE", "USERS", "USER"};

        bool success = false;
        for (const auto& table_name : table_names) {
            if (db.tableExists(table_name)) {
                // Use SELECT * to get all columns dynamically
                std::string query = "SELECT * FROM " + table_name + " ORDER BY USER_ID";

                if (db.executeQuery(query)) {
                    std::string output_file = cfg.output_dir + "/Users.csv";
                    CSVWriter csv(output_file);

                    // Get column names from result set
                    auto column_names = db.getColumnNames();

                    // Write header
                    for (const auto& col : column_names) {
                        csv.writeField(col);
                    }
                    csv.endRow();

                    // Fetch and write all rows
                    int count = 0;
                    while (db.fetch()) {
                        for (size_t i = 1; i <= column_names.size(); i++) {
                            // Check if this is a PASSWORD column - fetch as binary
                            bool is_password = (column_names[i-1] == "PASSWORD");
                            csv.writeField(db.fetchStringOrBinary(i, is_password));
                        }
                        csv.endRow();
                        count++;
                    }

                    if (!cfg.quiet) std::cout << "  Extracted " << count << " users from " << table_name << "\n";
                    success = true;
                    break;
                }
            }
        }

        if (!success && !cfg.quiet) {
            std::cout << "  Could not find users table (tried SCM_USERS, USER_PROFILE, USERS, USER)\n";
        }

        return success;
    }

    bool extractGroups() {
        if (!cfg.quiet) std::cout << "Extracting groups...\n";

        // Try different table names (check existence first)
        std::vector<std::string> table_names = {"SCM_GROUPS", "SCM_USER_GROUP", "USER_GROUP", "USERGROUP", "GROUPS"};

        bool success = false;
        for (const auto& table_name : table_names) {
            if (db.tableExists(table_name)) {
                // Use SELECT * to get all columns dynamically
                std::string query = "SELECT * FROM " + table_name + " ORDER BY GROUP_ID";

                if (db.executeQuery(query)) {
                    std::string output_file = cfg.output_dir + "/UserGroups.csv";
                    CSVWriter csv(output_file);

                    // Get column names from result set
                    auto column_names = db.getColumnNames();

                    // Write header
                    for (const auto& col : column_names) {
                        csv.writeField(col);
                    }
                    csv.endRow();

                    // Fetch and write all rows
                    int count = 0;
                    while (db.fetch()) {
                        for (size_t i = 1; i <= column_names.size(); i++) {
                            csv.writeField(db.fetchString(i));
                        }
                        csv.endRow();
                        count++;
                    }

                    if (!cfg.quiet) std::cout << "  Extracted " << count << " groups from " << table_name << "\n";
                    success = true;
                    break;
                }
            }
        }

        if (!success) {
            if (!cfg.quiet) std::cout << "  Could not find groups table (tried SCM_GROUPS, SCM_USER_GROUP, USER_GROUP, USERGROUP, GROUPS)\n";
            return false;
        }

        return true;
    }

    bool extractUserGroupMemberships() {
        if (!cfg.quiet) std::cout << "Extracting user-group memberships...\n";

        // Try different table names (check existence first)
        std::vector<std::string> table_names = {"SCM_USER_GROUP", "USER_GROUP_MEMBERSHIP"};

        bool success = false;
        for (const auto& table_name : table_names) {
            if (db.tableExists(table_name)) {
                // Use SELECT * to get all columns dynamically
                std::string query = "SELECT * FROM " + table_name + " ORDER BY USER_ID, GROUP_ID";

                if (db.executeQuery(query)) {
                    std::string output_file = cfg.output_dir + "/UserGroupMemberships.csv";
                    CSVWriter csv(output_file);

                    // Get column names from result set
                    auto column_names = db.getColumnNames();

                    // Write header
                    for (const auto& col : column_names) {
                        csv.writeField(col);
                    }
                    csv.endRow();

                    // Fetch and write all rows
                    int count = 0;
                    while (db.fetch()) {
                        for (size_t i = 1; i <= column_names.size(); i++) {
                            csv.writeField(db.fetchString(i));
                        }
                        csv.endRow();
                        count++;
                    }

                    if (!cfg.quiet) std::cout << "  Extracted " << count << " memberships from " << table_name << "\n";
                    success = true;
                    break;
                }
            }
        }

        if (!success) {
            if (!cfg.quiet) std::cout << "  Could not find user-group membership table (tried SCM_USER_GROUP, USER_GROUP_MEMBERSHIP)\n";
            return false;
        }

        return true;
    }

    bool extractSections() {
        if (!cfg.quiet) std::cout << "Extracting sections...\n";

        // Try different table names (check existence first)
        std::vector<std::string> table_names = {"SECTION", "SECTIONS"};

        bool success = false;
        for (const auto& table_name : table_names) {
            if (db.tableExists(table_name)) {
                // Use SELECT * to get all columns dynamically
                std::string query = "SELECT * FROM " + table_name + " ORDER BY SECTION_ID";

                if (db.executeQuery(query)) {
                    std::string output_file = cfg.output_dir + "/Sections.csv";
                    CSVWriter csv(output_file);

                    // Get column names from result set
                    auto column_names = db.getColumnNames();

                    // Write header (rename NAME to SECTION_NAME)
                    for (const auto& col : column_names) {
                        if (col == "NAME") {
                            csv.writeField("SECTION_NAME");
                        } else {
                            csv.writeField(col);
                        }
                    }
                    csv.endRow();

                    // Fetch and write all rows
                    int count = 0;
                    while (db.fetch()) {
                        for (size_t i = 1; i <= column_names.size(); i++) {
                            std::string value = db.fetchString(i);
                            // Trim NAME/SECTION_NAME column values
                            if (column_names[i-1] == "NAME") {
                                value = trim(value);
                            }
                            csv.writeField(value);
                        }
                        csv.endRow();
                        count++;
                    }

                    if (!cfg.quiet) std::cout << "  Extracted " << count << " sections from " << table_name << "\n";
                    success = true;
                    break;
                }
            }
        }

        if (!success) {
            if (!cfg.quiet) std::cout << "  Could not find sections table (tried SECTION, SECTIONS)\n";
            return false;
        }

        return true;
    }

    bool extractPermissions() {
        if (!cfg.quiet) std::cout << "Extracting permissions from ACLs...\n";

        // Try different table names (check existence first)
        std::vector<std::string> table_names = {"STYPE_SECTION", "SECTION_SECURITY"};

        bool found = false;
        for (const auto& table_name : table_names) {
            if (db.tableExists(table_name)) {
                // Query for binary ACL data
                std::string query = "SELECT SECTION_ID, VALUE FROM " + table_name + " WHERE VALUE IS NOT NULL";

                if (db.executeQuery(query)) {
                    std::string output_file = cfg.output_dir + "/Permissions.csv";
                    CSVWriter csv(output_file);

                    csv.writeField("RESOURCE_TYPE");
                    csv.writeField("RESOURCE_ID");
                    csv.writeField("PRINCIPAL_SID");
                    csv.writeField("PRINCIPAL_TYPE");
                    csv.writeField("ACCESS_MASK");
                    csv.endRow();

                    int count = 0;
                    while (db.fetch()) {
                        std::string section_id = db.fetchString(1);
                        auto acl_data = db.fetchBinary(2);

                        if (!acl_data.empty()) {
                            auto sids = SIDParser::findAllSIDs(acl_data);
                            for (const auto& sid : sids) {
                                csv.writeField("SECTION");
                                csv.writeField(section_id);
                                csv.writeField(sid);
                                csv.writeField(inferPrincipalType(sid));
                                csv.writeField("UNKNOWN");  // Would need full ACE parsing
                                csv.endRow();
                                count++;
                            }
                        }
                    }

                    if (!cfg.quiet) std::cout << "  Extracted " << count << " permission entries from " << table_name << "\n";
                    found = true;
                    break;
                }
            }
        }

        if (!found) {
            if (!cfg.quiet) std::cout << "  No permissions table found, skipping\n";
        }

        return true;  // Not critical
    }

    bool extractSecurityDomains() {
        if (!cfg.quiet) std::cout << "Extracting security domains...\n";

        // Try different table names (check existence first)
        std::vector<std::string> table_names = {"SCM_SECURITYDOMAIN", "SECURITY_DOMAINS", "SECURITYDOMAIN"};

        bool found = false;
        for (const auto& table_name : table_names) {
            if (db.tableExists(table_name)) {
                // Use SELECT * to get all columns dynamically
                std::string query = "SELECT * FROM " + table_name + " ORDER BY SECURITYDOMAIN_ID";

                if (db.executeQuery(query)) {
                    std::string output_file = cfg.output_dir + "/SecurityDomains.csv";
                    CSVWriter csv(output_file);

                    // Get column names from result set
                    auto column_names = db.getColumnNames();

                    // Write header
                    for (const auto& col : column_names) {
                        csv.writeField(col);
                    }
                    csv.endRow();

                    // Fetch and write all rows
                    int count = 0;
                    while (db.fetch()) {
                        for (size_t i = 1; i <= column_names.size(); i++) {
                            csv.writeField(db.fetchString(i));
                        }
                        csv.endRow();
                        count++;
                    }

                    if (!cfg.quiet) std::cout << "  Extracted " << count << " security domains from " << table_name << "\n";
                    found = true;
                    break;
                }
            }
        }

        if (!found) {
            if (!cfg.quiet) std::cout << "  No security domains table found, skipping\n";
        }

        return true;  // Not critical
    }

    bool extractFolderPermissions() {
        if (!cfg.quiet) std::cout << "Extracting folder permissions...\n";

        std::vector<std::string> table_names = {"STYPE_FOLDER", "FOLDER_PERMISSION"};

        for (const auto& table_name : table_names) {
            if (db.tableExists(table_name)) {
                std::string query = "SELECT FOLDER_ID, VALUE FROM " + table_name + " WHERE VALUE IS NOT NULL ORDER BY FOLDER_ID";

                if (db.executeQuery(query)) {
                    std::string output_file = cfg.output_dir + "/STYPE_FOLDER_ACCESS.csv";
                    CSVWriter csv(output_file);

                    csv.writeField("FOLDER_ID");
                    csv.writeField("Group");
                    csv.writeField("User");
                    csv.writeField("RID");
                    csv.writeField("Everyone");
                    csv.endRow();

                    int count = 0;
                    while (db.fetch()) {
                        int folder_id = db.fetchInt(1);
                        auto acl_data = db.fetchBinary(2);

                        if (!acl_data.empty()) {
                            auto sids = ACLParser::parseSIDs(acl_data);

                            std::vector<int> groups, users, rids;
                            int everyone = 0;

                            for (const auto& sid_info : sids) {
                                if (sid_info.is_everyone) {
                                    everyone = 1;
                                } else if (sid_info.rid > 0) {
                                    rids.push_back(sid_info.rid);

                                    if (user_rid_map.count(sid_info.rid)) {
                                        users.push_back(sid_info.rid);
                                    }
                                    if (group_rid_map.count(sid_info.rid)) {
                                        groups.push_back(sid_info.rid);
                                    }
                                    if (!user_rid_map.count(sid_info.rid) && !group_rid_map.count(sid_info.rid) && cfg.testdata_mode) {
                                        unmapped_rids.insert(sid_info.rid);
                                    }
                                }
                            }

                            // Write row
                            csv.writeField(std::to_string(folder_id));

                            std::stringstream ss_groups, ss_users, ss_rids;
                            for (size_t i = 0; i < groups.size(); i++) {
                                if (i > 0) ss_groups << "|";
                                ss_groups << groups[i];
                            }
                            for (size_t i = 0; i < users.size(); i++) {
                                if (i > 0) ss_users << "|";
                                ss_users << users[i];
                            }
                            for (size_t i = 0; i < rids.size(); i++) {
                                if (i > 0) ss_rids << "|";
                                ss_rids << rids[i];
                            }

                            csv.writeField(ss_groups.str());
                            csv.writeField(ss_users.str());
                            csv.writeField(ss_rids.str());
                            csv.writeField(std::to_string(everyone));
                            csv.endRow();
                            count++;
                        }
                    }

                    if (!cfg.quiet) std::cout << "  Extracted " << count << " folder permissions from " << table_name << "\n";
                    return true;
                }
            }
        }

        if (!cfg.quiet) std::cout << "  No folder permission table found\n";
        return true;
    }

    bool extractReportSpeciesPermissions() {
        if (!cfg.quiet) std::cout << "Extracting report species permissions...\n";

        if (!db.tableExists("STYPE_REPORT_SPECIES")) {
            if (!cfg.quiet) std::cout << "  No STYPE_REPORT_SPECIES table found\n";
            return true;
        }

        std::string query = "SELECT REPORT_SPECIES_ID, VALUE FROM STYPE_REPORT_SPECIES WHERE VALUE IS NOT NULL ORDER BY REPORT_SPECIES_ID";

        if (!db.executeQuery(query)) {
            return true;
        }

        std::string output_file = cfg.output_dir + "/STYPE_REPORT_SPECIES_ACCESS.csv";
        CSVWriter csv(output_file);

        csv.writeField("REPORT_SPECIES_ID");
        csv.writeField("Group");
        csv.writeField("User");
        csv.writeField("RID");
        csv.writeField("Everyone");
        csv.endRow();

        int count = 0;
        while (db.fetch()) {
            int species_id = db.fetchInt(1);
            auto acl_data = db.fetchBinary(2);

            if (!acl_data.empty()) {
                auto sids = ACLParser::parseSIDs(acl_data);

                std::vector<int> groups, users, rids;
                int everyone = 0;

                for (const auto& sid_info : sids) {
                    if (sid_info.is_everyone) {
                        everyone = 1;
                    } else if (sid_info.rid > 0) {
                        rids.push_back(sid_info.rid);

                        if (user_rid_map.count(sid_info.rid)) {
                            users.push_back(sid_info.rid);
                        } else if (group_rid_map.count(sid_info.rid)) {
                            groups.push_back(sid_info.rid);
                        } else if (cfg.testdata_mode) {
                            unmapped_rids.insert(sid_info.rid);
                        }
                    }
                }

                csv.writeField(std::to_string(species_id));

                std::stringstream ss_groups, ss_users, ss_rids;
                for (size_t i = 0; i < groups.size(); i++) {
                    if (i > 0) ss_groups << "|";
                    ss_groups << groups[i];
                }
                for (size_t i = 0; i < users.size(); i++) {
                    if (i > 0) ss_users << "|";
                    ss_users << users[i];
                }
                for (size_t i = 0; i < rids.size(); i++) {
                    if (i > 0) ss_rids << "|";
                    ss_rids << rids[i];
                }

                csv.writeField(ss_groups.str());
                csv.writeField(ss_users.str());
                csv.writeField(ss_rids.str());
                csv.writeField(std::to_string(everyone));
                csv.endRow();
                count++;
            }
        }

        if (!cfg.quiet) std::cout << "  Extracted " << count << " report species permissions\n";
        return true;
    }

    bool extractSectionPermissions() {
        if (!cfg.quiet) std::cout << "Extracting section permissions...\n";

        if (!db.tableExists("STYPE_SECTION")) {
            if (!cfg.quiet) std::cout << "  No STYPE_SECTION table found\n";
            return true;
        }

        std::string query = "SELECT REPORT_SPECIES_ID, SECTION_ID, VALUE FROM STYPE_SECTION WHERE VALUE IS NOT NULL ORDER BY REPORT_SPECIES_ID, SECTION_ID";

        if (!db.executeQuery(query)) {
            return true;
        }

        std::string output_file = cfg.output_dir + "/STYPE_SECTION_ACCESS.csv";
        CSVWriter csv(output_file);

        csv.writeField("REPORT_SPECIES_ID");
        csv.writeField("SECTION_ID");
        csv.writeField("Group");
        csv.writeField("User");
        csv.writeField("RID");
        csv.writeField("Everyone");
        csv.endRow();

        int count = 0;
        while (db.fetch()) {
            int species_id = db.fetchInt(1);
            int section_id = db.fetchInt(2);
            auto acl_data = db.fetchBinary(3);

            if (!acl_data.empty()) {
                auto sids = ACLParser::parseSIDs(acl_data);

                std::vector<int> groups, users, rids;
                int everyone = 0;

                for (const auto& sid_info : sids) {
                    if (sid_info.is_everyone) {
                        everyone = 1;
                    } else if (sid_info.rid > 0) {
                        rids.push_back(sid_info.rid);

                        if (user_rid_map.count(sid_info.rid)) {
                            users.push_back(sid_info.rid);
                        } else if (group_rid_map.count(sid_info.rid)) {
                            groups.push_back(sid_info.rid);
                        } else if (cfg.testdata_mode) {
                            unmapped_rids.insert(sid_info.rid);
                        }
                    }
                }

                csv.writeField(std::to_string(species_id));
                csv.writeField(std::to_string(section_id));

                std::stringstream ss_groups, ss_users, ss_rids;
                for (size_t i = 0; i < groups.size(); i++) {
                    if (i > 0) ss_groups << "|";
                    ss_groups << groups[i];
                }
                for (size_t i = 0; i < users.size(); i++) {
                    if (i > 0) ss_users << "|";
                    ss_users << users[i];
                }
                for (size_t i = 0; i < rids.size(); i++) {
                    if (i > 0) ss_rids << "|";
                    ss_rids << rids[i];
                }

                csv.writeField(ss_groups.str());
                csv.writeField(ss_users.str());
                csv.writeField(ss_rids.str());
                csv.writeField(std::to_string(everyone));
                csv.endRow();
                count++;
            }
        }

        if (!cfg.quiet) std::cout << "  Extracted " << count << " section permissions\n";
        return true;
    }

    bool createUniqueSectionsAccess() {
        if (!cfg.quiet) std::cout << "Creating unique sections access...\n";

        if (!db.tableExists("STYPE_SECTION") || !db.tableExists("SECTION")) {
            if (!cfg.quiet) std::cout << "  Required tables not found\n";
            return true;
        }

        std::string query = "SELECT s.NAME, st.VALUE FROM STYPE_SECTION st "
                           "INNER JOIN SECTION s ON st.REPORT_SPECIES_ID = s.REPORT_SPECIES_ID AND st.SECTION_ID = s.SECTION_ID "
                           "WHERE st.VALUE IS NOT NULL ORDER BY s.NAME";

        if (!db.executeQuery(query)) {
            return true;
        }

        // Aggregate permissions by section name
        std::map<std::string, std::tuple<std::set<int>, std::set<int>, std::set<int>, int>> section_perms;

        while (db.fetch()) {
            std::string section_name = trim(db.fetchString(1));
            auto acl_data = db.fetchBinary(2);

            if (!acl_data.empty()) {
                auto sids = ACLParser::parseSIDs(acl_data);

                auto& perms = section_perms[section_name];

                for (const auto& sid_info : sids) {
                    if (sid_info.is_everyone) {
                        std::get<3>(perms) = 1;
                    } else if (sid_info.rid > 0) {
                        std::get<2>(perms).insert(sid_info.rid);  // RIDs

                        if (user_rid_map.count(sid_info.rid)) {
                            std::get<1>(perms).insert(sid_info.rid);  // Users
                        } else if (group_rid_map.count(sid_info.rid)) {
                            std::get<0>(perms).insert(sid_info.rid);  // Groups
                        }
                    }
                }
            }
        }

        // Write aggregated output
        std::string output_file = cfg.output_dir + "/Unique_Sections_Access.csv";
        CSVWriter csv(output_file);

        csv.writeField("SECTION_NAME");
        csv.writeField("Group");
        csv.writeField("User");
        csv.writeField("RID");
        csv.writeField("Everyone");
        csv.endRow();

        for (const auto& entry : section_perms) {
            const auto& groups = std::get<0>(entry.second);
            const auto& users = std::get<1>(entry.second);
            const auto& rids = std::get<2>(entry.second);
            int everyone = std::get<3>(entry.second);

            csv.writeField(entry.first);

            std::stringstream ss_groups, ss_users, ss_rids;
            bool first = true;
            for (int gid : groups) {
                if (!first) ss_groups << "|";
                ss_groups << gid;
                first = false;
            }
            first = true;
            for (int uid : users) {
                if (!first) ss_users << "|";
                ss_users << uid;
                first = false;
            }
            first = true;
            for (int rid : rids) {
                if (!first) ss_rids << "|";
                ss_rids << rid;
                first = false;
            }

            csv.writeField(ss_groups.str());
            csv.writeField(ss_users.str());
            csv.writeField(ss_rids.str());
            csv.writeField(std::to_string(everyone));
            csv.endRow();
        }

        if (!cfg.quiet) std::cout << "  Written " << section_perms.size() << " unique sections\n";
        return true;
    }

    bool generateTestData() {
        if (!cfg.quiet) {
            std::cout << "======================================================================\n";
            std::cout << "GENERATING TEST DATA TO CSV FILES\n";
            std::cout << "======================================================================\n";
            std::cout << "Found " << unmapped_rids.size() << " unmapped RIDs in ACLs\n";
        }

        // Initialize random number generator
        std::random_device rd;
        std::mt19937 gen(rd());

        // Read existing UserGroups.csv
        std::string groups_csv = cfg.output_dir + "/UserGroups.csv";
        std::vector<std::vector<std::string>> group_rows;
        std::vector<std::string> group_columns;
        std::set<int> existing_group_ids;

        std::ifstream groups_file(groups_csv);
        if (groups_file.is_open()) {
            std::string line;
            std::getline(groups_file, line);  // Read header
            std::stringstream ss(line);
            std::string col;
            while (std::getline(ss, col, ',')) {
                group_columns.push_back(col);
            }

            while (std::getline(groups_file, line)) {
                if (line.empty()) continue;
                std::vector<std::string> row;
                std::stringstream ss(line);
                std::string field;
                while (std::getline(ss, field, ',')) {
                    row.push_back(field);
                }
                if (!row.empty()) {
                    existing_group_ids.insert(std::stoi(row[0]));
                    group_rows.push_back(row);
                }
            }
            groups_file.close();
        }

        // Create test groups for unmapped RIDs
        std::vector<int> new_test_groups;
        for (int rid : unmapped_rids) {
            if (existing_group_ids.count(rid) == 0) {
                new_test_groups.push_back(rid);
                existing_group_ids.insert(rid);

                std::vector<std::string> row;
                for (const auto& col : group_columns) {
                    if (col == "GROUP_ID") {
                        row.push_back(std::to_string(rid));
                    } else if (col == "SECURITYDOMAIN_ID") {
                        row.push_back("1");
                    } else if (col == "GROUPNAME") {
                        row.push_back(std::to_string(rid));
                    } else if (col == "DESCRIPTION") {
                        row.push_back("TEST-" + std::to_string(rid));
                    } else if (col == "FLAGS") {
                        row.push_back("0");
                    } else {
                        row.push_back("");
                    }
                }
                group_rows.push_back(row);
            }
        }

        // Find max GROUP_ID for special group
        int max_group_id = 0;
        for (int gid : existing_group_ids) {
            if (gid > max_group_id) max_group_id = gid;
        }

        // Create special group
        int special_group_id = max_group_id + 1;
        std::vector<std::string> special_group_row;
        for (const auto& col : group_columns) {
            if (col == "GROUP_ID") {
                special_group_row.push_back(std::to_string(special_group_id));
            } else if (col == "SECURITYDOMAIN_ID") {
                special_group_row.push_back("1");
            } else if (col == "GROUPNAME") {
                special_group_row.push_back(cfg.testdata_special_group);
            } else if (col == "DESCRIPTION") {
                special_group_row.push_back("Special group for document management system users");
            } else if (col == "FLAGS") {
                special_group_row.push_back("0");
            } else {
                special_group_row.push_back("");
            }
        }
        group_rows.push_back(special_group_row);

        if (!cfg.quiet) {
            std::cout << "Created " << new_test_groups.size() << " new test groups for unmapped RIDs\n";
            std::cout << "Created special group: " << cfg.testdata_special_group << " (ID: " << special_group_id << ")\n";
        }

        // Write updated UserGroups.csv
        if (!cfg.testdata_dryrun) {
            std::ofstream groups_out(groups_csv);
            if (groups_out.is_open()) {
                for (size_t i = 0; i < group_columns.size(); i++) {
                    if (i > 0) groups_out << ",";
                    groups_out << group_columns[i];
                }
                groups_out << "\n";

                for (const auto& row : group_rows) {
                    for (size_t i = 0; i < row.size(); i++) {
                        if (i > 0) groups_out << ",";
                        groups_out << row[i];
                    }
                    groups_out << "\n";
                }
                groups_out.close();

                if (!cfg.quiet) {
                    std::cout << "Written " << group_rows.size() << " groups to UserGroups.csv\n";
                }
            } else {
                std::cerr << "ERROR: Failed to write UserGroups.csv\n";
                return false;
            }
        }

        // Read existing Users.csv to find max USER_ID
        std::string users_csv = cfg.output_dir + "/Users.csv";
        int max_user_id = 0;
        std::vector<std::vector<std::string>> user_rows;
        std::vector<std::string> user_columns;

        std::ifstream users_file(users_csv);
        if (users_file.is_open()) {
            std::string line;
            std::getline(users_file, line);
            std::stringstream ss(line);
            std::string col;
            while (std::getline(ss, col, ',')) {
                user_columns.push_back(col);
            }

            while (std::getline(users_file, line)) {
                if (line.empty()) continue;
                std::vector<std::string> row;
                std::stringstream ss(line);
                std::string field;
                while (std::getline(ss, field, ',')) {
                    row.push_back(field);
                }
                if (!row.empty()) {
                    int user_id = std::stoi(row[0]);
                    if (user_id > max_user_id) max_user_id = user_id;
                    user_rows.push_back(row);
                }
            }
            users_file.close();
        }

        // Generate test users
        int start_user_id = max_user_id + 1000;
        auto now = std::time(nullptr);
        char timestamp[64];
        std::strftime(timestamp, sizeof(timestamp), "%Y-%m-%d %H:%M:%S", std::localtime(&now));

        std::vector<std::vector<std::string>> assignments;

        for (int i = 1; i <= cfg.testdata_users; i++) {
            int user_id = start_user_id + i;
            char username[20];
            sprintf(username, "testuser%05d", i);

            std::vector<std::string> row;
            for (const auto& col : user_columns) {
                if (col == "USER_ID") {
                    row.push_back(std::to_string(user_id));
                } else if (col == "SECURITYDOMAIN_ID") {
                    row.push_back("1");
                } else if (col == "USERNAME") {
                    row.push_back(username);
                } else if (col == "FULLNAME") {
                    row.push_back("Test User " + std::to_string(i));
                } else if (col == "DESCRIPTION") {
                    row.push_back("Generated test user " + std::to_string(i));
                } else if (col == "PASSWORD") {
                    row.push_back("");
                } else if (col == "FLAGS") {
                    row.push_back("0");
                } else if (col == "CREATION_TIME" || col == "LAST_MODIFIED_TIME" || col == "PASSWORD_LAST_MODIFIED_TIME") {
                    row.push_back(timestamp);
                } else {
                    row.push_back("");
                }
            }
            user_rows.push_back(row);

            // Assign user to random test groups
            if (!new_test_groups.empty()) {
                int num_groups = std::uniform_int_distribution<>(cfg.testdata_min_groups, cfg.testdata_max_groups)(gen);
                std::vector<int> shuffled = new_test_groups;
                std::shuffle(shuffled.begin(), shuffled.end(), gen);
                int actual_groups = std::min(num_groups, (int)shuffled.size());

                for (int j = 0; j < actual_groups; j++) {
                    assignments.push_back({"1", std::to_string(user_id), std::to_string(shuffled[j]), "0"});
                }
            }

            // Assign to special group
            assignments.push_back({"1", std::to_string(user_id), std::to_string(special_group_id), "0"});
        }

        if (!cfg.quiet) {
            std::cout << "Generated " << cfg.testdata_users << " test users\n";
            std::cout << "Generated " << assignments.size() << " user-group assignments\n";
        }

        // Write updated Users.csv
        if (!cfg.testdata_dryrun) {
            std::ofstream users_out(users_csv);
            if (users_out.is_open()) {
                for (size_t i = 0; i < user_columns.size(); i++) {
                    if (i > 0) users_out << ",";
                    users_out << user_columns[i];
                }
                users_out << "\n";

                for (const auto& row : user_rows) {
                    for (size_t i = 0; i < row.size(); i++) {
                        if (i > 0) users_out << ",";
                        users_out << row[i];
                    }
                    users_out << "\n";
                }
                users_out.close();

                if (!cfg.quiet) {
                    std::cout << "Written " << user_rows.size() << " users to Users.csv\n";
                }
            } else {
                std::cerr << "ERROR: Failed to write Users.csv\n";
                return false;
            }
        }

        // Write UserGroupAssignments.csv
        if (!cfg.testdata_dryrun) {
            std::string assignments_csv = cfg.output_dir + "/UserGroupAssignments.csv";
            std::ofstream assign_out(assignments_csv);
            if (assign_out.is_open()) {
                // Read existing assignments first (if any)
                std::ifstream existing_assignments(assignments_csv);
                std::vector<std::vector<std::string>> all_assignments;
                if (existing_assignments.is_open()) {
                    std::string line;
                    std::getline(existing_assignments, line);  // Skip header
                    while (std::getline(existing_assignments, line)) {
                        auto fields = parseCSVLine(line);
                        if (fields.size() >= 4) {
                            all_assignments.push_back({fields[0], fields[1], fields[2], fields[3]});
                        }
                    }
                    existing_assignments.close();
                }

                // Add new assignments
                all_assignments.insert(all_assignments.end(), assignments.begin(), assignments.end());

                // Write all with proper columns
                assign_out << "SECURITYDOMAIN_ID,USER_ID,GROUP_ID,FLAGS\n";
                for (const auto& assign : all_assignments) {
                    assign_out << assign[0] << "," << assign[1] << "," << assign[2] << "," << assign[3] << "\n";
                }
                assign_out.close();

                if (!cfg.quiet) {
                    std::cout << "Written " << all_assignments.size() << " assignments to UserGroupAssignments.csv\n";
                }
            } else {
                std::cerr << "ERROR: Failed to write UserGroupAssignments.csv\n";
                return false;
            }
        }

        if (!cfg.quiet) {
            std::cout << "======================================================================\n";
            if (cfg.testdata_dryrun) {
                std::cout << "TEST DATA GENERATION DRY-RUN COMPLETE (No files modified)\n";
            } else {
                std::cout << "TEST DATA GENERATION TO CSV COMPLETE\n";
            }
            std::cout << "  Test Groups Added: " << (new_test_groups.size() + 1) << "\n";
            std::cout << "  Test Users Added: " << cfg.testdata_users << "\n";
            std::cout << "  User-Group Assignments: " << assignments.size() << "\n";
            std::cout << "======================================================================\n";
        }

        return true;
    }

    bool extractAll() {
        bool success = true;

        // Phase 1: Extract basic data
        success = extractUsers() && success;
        success = extractGroups() && success;
        success = extractUserGroupMemberships() && success;
        success = extractSections() && success;
        success = extractSecurityDomains() && success;

        // Phase 2: Build RID maps for ACL decoding
        buildRIDMaps();

        // Phase 3: Extract ACL permissions
        success = extractFolderPermissions() && success;
        success = extractReportSpeciesPermissions() && success;
        success = extractSectionPermissions() && success;
        success = createUniqueSectionsAccess() && success;
        success = extractPermissions() && success;  // Keep for backwards compatibility

        // Phase 4: Generate test data if enabled
        if (cfg.testdata_mode) {
            success = generateTestData() && success;

            // Rebuild RID maps with test data
            buildRIDMaps();

            // Re-extract ACL permissions with updated RID maps
            if (!cfg.quiet) std::cout << "Re-extracting ACL permissions with updated RID maps...\n";
            success = extractFolderPermissions() && success;
            success = extractReportSpeciesPermissions() && success;
            success = extractSectionPermissions() && success;
            success = createUniqueSectionsAccess() && success;
            if (!cfg.quiet) std::cout << "ACL permissions updated with test data groups\n";
        }

        return success;
    }

private:
    std::string inferPrincipalType(const std::string& sid) {
        // Well-known SIDs
        if (sid == "S-1-1-0") return "EVERYONE";
        if (sid.find("S-1-5-32-") == 0) return "BUILTIN_GROUP";
        if (sid.find("S-1-5-21-") == 0) {
            // Domain SID - check RID (last component)
            size_t last_dash = sid.rfind('-');
            if (last_dash != std::string::npos) {
                int rid = std::stoi(sid.substr(last_dash + 1));
                if (rid >= 1000) return "USER";  // Usually users have RID >= 1000
                return "GROUP";  // Well-known groups have RID < 1000
            }
        }
        return "UNKNOWN";
    }
};

void printUsage(const char* prog) {
    std::cout << "Usage: " << prog << " [OPTIONS]\n\n";
    std::cout << "Required:\n";
    std::cout << "  --server SERVER       MS SQL Server hostname or IP\n";
    std::cout << "  --database DATABASE   Database name\n";
    std::cout << "  --output OUTPUT_DIR   Output directory for CSV files\n\n";
    std::cout << "Authentication:\n";
    std::cout << "  --windows-auth        Use Windows Authentication (default)\n";
    std::cout << "  --user USERNAME       SQL Server username (if not using Windows auth)\n";
    std::cout << "  --password PASSWORD   SQL Server password (if not using Windows auth)\n\n";
    std::cout << "Options:\n";
    std::cout << "  --quiet               Suppress progress messages\n";
    std::cout << "  --help                Show this help message\n\n";
    std::cout << "Test Data Generation:\n";
    std::cout << "  --TESTDATA            Enable test data generation (writes to CSV files)\n";
    std::cout << "  --TESTDATA-DRYRUN     Preview test data generation without modifying CSV files\n";
    std::cout << "  --TESTDATA-USERS N    Number of test users to generate (default: 5000)\n";
    std::cout << "  --TESTDATA-MIN-GROUPS N  Min groups per test user (default: 1)\n";
    std::cout << "  --TESTDATA-MAX-GROUPS N  Max groups per test user (default: 3)\n";
    std::cout << "  --TESTDATA-SPECIAL-GROUP NAME  Special group name for all test users (default: DocMgmtUsers)\n\n";
    std::cout << "Examples:\n";
    std::cout << "  " << prog << " --server SQLSRV01 --database IntelliSTOR_SG --output ./output --windows-auth\n";
    std::cout << "  " << prog << " --server SQLSRV01 --database IntelliSTOR_SG --output ./output --windows-auth --TESTDATA\n";
    std::cout << "  " << prog << " --server SQLSRV01 --database IntelliSTOR_SG --output ./output --windows-auth --TESTDATA --TESTDATA-USERS 1000\n";
}

int main(int argc, char* argv[]) {
    Config cfg;
    cfg.windows_auth = true;  // Default to Windows auth

    // Parse command-line arguments
    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];

        if (arg == "--help" || arg == "-h") {
            printUsage(argv[0]);
            return EC_SUCCESS;
        } else if (arg == "--server" && i + 1 < argc) {
            cfg.server = argv[++i];
        } else if (arg == "--database" && i + 1 < argc) {
            cfg.database = argv[++i];
        } else if (arg == "--output" && i + 1 < argc) {
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
        } else if (arg == "--TESTDATA") {
            cfg.testdata_mode = true;
        } else if (arg == "--TESTDATA-DRYRUN") {
            cfg.testdata_mode = true;
            cfg.testdata_dryrun = true;
        } else if (arg == "--TESTDATA-USERS" && i + 1 < argc) {
            cfg.testdata_users = std::stoi(argv[++i]);
        } else if (arg == "--TESTDATA-MIN-GROUPS" && i + 1 < argc) {
            cfg.testdata_min_groups = std::stoi(argv[++i]);
        } else if (arg == "--TESTDATA-MAX-GROUPS" && i + 1 < argc) {
            cfg.testdata_max_groups = std::stoi(argv[++i]);
        } else if (arg == "--TESTDATA-SPECIAL-GROUP" && i + 1 < argc) {
            cfg.testdata_special_group = argv[++i];
        } else {
            std::cerr << "Unknown argument: " << arg << "\n";
            printUsage(argv[0]);
            return EC_INVALID_ARGS;
        }
    }

    // Validate required arguments
    if (cfg.server.empty() || cfg.database.empty() || cfg.output_dir.empty()) {
        std::cerr << "Error: Missing required arguments\n\n";
        printUsage(argv[0]);
        return EC_INVALID_ARGS;
    }

    // Create output directory if it doesn't exist
    try {
        fs::create_directories(cfg.output_dir);
    } catch (const std::exception& e) {
        std::cerr << "Error creating output directory: " << e.what() << "\n";
        return EC_OUTPUT_ERROR;
    }

    // Run extraction
    if (!cfg.quiet) {
        std::cout << "=================================================\n";
        std::cout << "IntelliSTOR Users & Permissions Extractor (Papyrus)\n";
        std::cout << "=================================================\n\n";

        if (cfg.testdata_mode) {
            if (cfg.testdata_dryrun) {
                std::cout << "TEST DATA DRY-RUN MODE: No CSV files will be modified\n";
            } else {
                std::cout << "TEST DATA MODE: Test users and groups will be written to CSV files\n";
            }
            std::cout << "  Test users to generate: " << cfg.testdata_users << "\n";
            std::cout << "  Groups per user: " << cfg.testdata_min_groups << "-" << cfg.testdata_max_groups << "\n";
            std::cout << "  Special group: " << cfg.testdata_special_group << "\n\n";
        }
    }

    UsersPermissionsExtractor extractor(cfg);

    if (!extractor.connect()) {
        std::cerr << "Failed to connect to database\n";
        return EC_DB_CONNECTION_FAILED;
    }

    if (!extractor.extractAll()) {
        std::cerr << "Extraction completed with errors\n";
        return EC_EXTRACTION_FAILED;
    }

    if (!cfg.quiet) {
        std::cout << "\n=================================================\n";
        std::cout << "Extraction completed successfully\n";
        std::cout << "Output directory: " << cfg.output_dir << "\n";
        std::cout << "=================================================\n";
    }

    return EC_SUCCESS;
}
