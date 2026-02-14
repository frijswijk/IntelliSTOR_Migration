// papyrus_export_indexed_fields.cpp
// Export indexed field definitions from IntelliSTOR MS SQL database to CSV
//
// Outputs all indexed fields with LINE_ID, FIELD_ID, field name, type,
// column positions, and line template for each report species.
//
// Compile: compile_fieldlist.bat (uses MinGW-w64 with ODBC)
//
// Usage:
//   papyrus_export_indexed_fields.exe --server localhost --database IntelliSTOR --user sa --password MyPassword
//   papyrus_export_indexed_fields.exe --server localhost --database IntelliSTOR --windows-auth
//   papyrus_export_indexed_fields.exe --server localhost --database IntelliSTOR --user sa --password MyPassword --output-dir C:\Output

#include <windows.h>
#include <sql.h>
#include <sqlext.h>
#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <sstream>
#include <ctime>
#include <filesystem>
#include <algorithm>
#include <set>
#include <cstring>

namespace fs = std::filesystem;

// Exit codes
enum ExitCode {
    EC_SUCCESS = 0,
    EC_INVALID_ARGS = 1,
    EC_DB_CONNECTION_FAILED = 2,
    EC_QUERY_FAILED = 3,
    EC_OUTPUT_FAILED = 4
};

// Configuration
struct Config {
    std::string server;
    std::string database;
    int port = 1433;
    std::string username;
    std::string password;
    bool windows_auth = false;
    std::string output_dir = ".";
    std::string output_file = "Indexed_Fields.csv";
    bool quiet = false;
};

// Database helper class (same pattern as papyrus_extract_instances.cpp)
class Database {
public:
    SQLHENV henv = nullptr;
    SQLHDBC hdbc = nullptr;
    SQLHSTMT hstmt = nullptr;
    bool connected = false;

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

        if (cfg.port != 1433) {
            // Insert port into server specification
            conn_str = "DRIVER={SQL Server};SERVER=" + cfg.server + "," + std::to_string(cfg.port) +
                      ";DATABASE=" + cfg.database;
            if (cfg.windows_auth) {
                conn_str += ";Trusted_Connection=yes;";
            } else {
                conn_str += ";UID=" + cfg.username + ";PWD=" + cfg.password + ";";
            }
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
            // Trim trailing spaces
            result.erase(result.find_last_not_of(" \t\n\r\f\v") + 1);
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
};

// Escape a CSV field (quotes if contains comma, quote, or newline)
std::string csvEscape(const std::string& value) {
    if (value.find(',') != std::string::npos ||
        value.find('"') != std::string::npos ||
        value.find('\n') != std::string::npos) {
        std::string escaped = value;
        size_t pos = 0;
        while ((pos = escaped.find('"', pos)) != std::string::npos) {
            escaped.insert(pos, "\"");
            pos += 2;
        }
        return "\"" + escaped + "\"";
    }
    return value;
}

void printUsage(const char* progname) {
    std::cout << "Usage: " << progname << " [options]\n\n"
              << "Export indexed field definitions from IntelliSTOR database to CSV.\n\n"
              << "Required:\n"
              << "  --server HOST          SQL Server host/IP address\n"
              << "  --database DB          Database name\n\n"
              << "Authentication (one required):\n"
              << "  --windows-auth         Use Windows Authentication\n"
              << "  --user USER            SQL Server username\n"
              << "  --password PASS        SQL Server password\n\n"
              << "Optional:\n"
              << "  --port PORT            SQL Server port (default: 1433)\n"
              << "  --output-dir DIR       Output directory (default: current)\n"
              << "  --output-file FILE     Output filename (default: Indexed_Fields.csv)\n"
              << "  --quiet                Minimal console output\n"
              << "  --help                 Show this help\n\n"
              << "Examples:\n"
              << "  " << progname << " --server SQLSERVER01 --database IntelliSTOR --windows-auth\n"
              << "  " << progname << " --server localhost --database IntelliSTOR --user sa --password MyPass\n"
              << "  " << progname << " --server localhost --database IntelliSTOR --user sa --password MyPass -o C:\\Output\n";
}

int main(int argc, char* argv[]) {
    Config cfg;

    // Parse arguments
    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];

        if (arg == "--help") {
            printUsage(argv[0]);
            return EC_SUCCESS;
        } else if (arg == "--server" && i + 1 < argc) {
            cfg.server = argv[++i];
        } else if (arg == "--database" && i + 1 < argc) {
            cfg.database = argv[++i];
        } else if (arg == "--port" && i + 1 < argc) {
            cfg.port = std::stoi(argv[++i]);
        } else if (arg == "--user" && i + 1 < argc) {
            cfg.username = argv[++i];
            cfg.windows_auth = false;
        } else if (arg == "--password" && i + 1 < argc) {
            cfg.password = argv[++i];
            cfg.windows_auth = false;
        } else if (arg == "--windows-auth") {
            cfg.windows_auth = true;
        } else if ((arg == "--output-dir" || arg == "-o") && i + 1 < argc) {
            cfg.output_dir = argv[++i];
        } else if (arg == "--output-file" && i + 1 < argc) {
            cfg.output_file = argv[++i];
        } else if (arg == "--quiet") {
            cfg.quiet = true;
        } else {
            std::cerr << "Unknown argument: " << arg << "\n";
            printUsage(argv[0]);
            return EC_INVALID_ARGS;
        }
    }

    // Validate required args
    if (cfg.server.empty() || cfg.database.empty()) {
        std::cerr << "Error: --server and --database are required.\n\n";
        printUsage(argv[0]);
        return EC_INVALID_ARGS;
    }

    if (!cfg.windows_auth && (cfg.username.empty() || cfg.password.empty())) {
        std::cerr << "Error: Either --windows-auth OR both --user and --password must be provided.\n\n";
        printUsage(argv[0]);
        return EC_INVALID_ARGS;
    }

    // Create output directory
    try {
        fs::create_directories(cfg.output_dir);
    } catch (const std::exception& e) {
        std::cerr << "Error creating output directory: " << e.what() << "\n";
        return EC_OUTPUT_FAILED;
    }

    fs::path output_path = fs::path(cfg.output_dir) / cfg.output_file;

    // Connect to database
    Database db;
    if (!db.connect(cfg)) {
        std::cerr << "Failed to connect to " << cfg.server << "/" << cfg.database << "\n";
        return EC_DB_CONNECTION_FAILED;
    }

    // Check required tables
    const std::vector<std::string> required_tables = {"FIELD", "REPORT_INSTANCE", "REPORT_SPECIES_NAME", "LINE"};
    for (const auto& table : required_tables) {
        if (!db.tableExists(table)) {
            std::cerr << "Error: Required table '" << table << "' not found in database.\n";
            db.disconnect();
            return EC_QUERY_FAILED;
        }
    }
    if (!cfg.quiet) {
        std::cout << "All required tables verified.\n";
    }

    // Execute the indexed fields query
    std::string query = R"(
SELECT
    RTRIM(COALESCE(rsn1.NAME, rsn0.NAME)) AS REPORT_SPECIES_NAME,
    RTRIM(rsn0.NAME) AS REPORT_SPECIES_DISPLAYNAME,
    ri.REPORT_SPECIES_ID,
    f.STRUCTURE_DEF_ID,
    f.LINE_ID,
    f.FIELD_ID,
    RTRIM(f.NAME) AS FIELD_NAME,
    RTRIM(f.FIELD_TYPE_NAME) AS FIELD_TYPE,
    f.START_COLUMN,
    f.END_COLUMN,
    (f.END_COLUMN - f.START_COLUMN + 1) AS FIELD_WIDTH,
    f.IS_SIGNIFICANT,
    f.IS_INDEXED,
    RTRIM(l.NAME) AS LINE_NAME,
    RTRIM(l.TEMPLATE) AS LINE_TEMPLATE
FROM FIELD f
INNER JOIN (
    SELECT ri2.REPORT_SPECIES_ID, ri2.STRUCTURE_DEF_ID,
           ROW_NUMBER() OVER (PARTITION BY ri2.REPORT_SPECIES_ID ORDER BY ri2.AS_OF_TIMESTAMP DESC) AS rn
    FROM REPORT_INSTANCE ri2
) ri ON ri.STRUCTURE_DEF_ID = f.STRUCTURE_DEF_ID AND ri.rn = 1
INNER JOIN REPORT_SPECIES_NAME rsn0
    ON rsn0.REPORT_SPECIES_ID = ri.REPORT_SPECIES_ID AND rsn0.ITEM_ID = 0
LEFT JOIN REPORT_SPECIES_NAME rsn1
    ON rsn1.REPORT_SPECIES_ID = ri.REPORT_SPECIES_ID
    AND rsn1.DOMAIN_ID = rsn0.DOMAIN_ID AND rsn1.ITEM_ID = 1
LEFT JOIN LINE l ON l.STRUCTURE_DEF_ID = f.STRUCTURE_DEF_ID AND l.LINE_ID = f.LINE_ID
WHERE f.IS_INDEXED = 1
ORDER BY COALESCE(rsn1.NAME, rsn0.NAME), f.LINE_ID, f.FIELD_ID
    )";

    if (!cfg.quiet) {
        std::cout << "Executing indexed fields query...\n";
    }

    auto start_time = std::chrono::steady_clock::now();

    if (!db.executeQuery(query)) {
        std::cerr << "Failed to execute indexed fields query.\n";
        db.disconnect();
        return EC_QUERY_FAILED;
    }

    // Open output file
    std::ofstream outfile(output_path.string());
    if (!outfile.is_open()) {
        std::cerr << "Error: Could not open output file: " << output_path.string() << "\n";
        db.disconnect();
        return EC_OUTPUT_FAILED;
    }

    // Write CSV header
    outfile << "REPORT_SPECIES_NAME,REPORT_SPECIES_DISPLAYNAME,REPORT_SPECIES_ID,"
            << "STRUCTURE_DEF_ID,LINE_ID,FIELD_ID,FIELD_NAME,FIELD_TYPE,"
            << "START_COLUMN,END_COLUMN,FIELD_WIDTH,IS_SIGNIFICANT,IS_INDEXED,"
            << "LINE_NAME,LINE_TEMPLATE\n";

    // Fetch and write rows
    int row_count = 0;
    std::set<std::string> species_set;

    while (db.fetch()) {
        std::string species_name = db.fetchString(1);
        std::string display_name = db.fetchString(2);
        int species_id = db.fetchInt(3);
        int structure_def_id = db.fetchInt(4);
        int line_id = db.fetchInt(5);
        int field_id = db.fetchInt(6);
        std::string field_name = db.fetchString(7);
        std::string field_type = db.fetchString(8);
        int start_col = db.fetchInt(9);
        int end_col = db.fetchInt(10);
        int field_width = db.fetchInt(11);
        int is_significant = db.fetchInt(12);
        int is_indexed = db.fetchInt(13);
        std::string line_name = db.fetchString(14);
        std::string line_template = db.fetchString(15);

        species_set.insert(species_name);

        outfile << csvEscape(species_name) << ","
                << csvEscape(display_name) << ","
                << species_id << ","
                << structure_def_id << ","
                << line_id << ","
                << field_id << ","
                << csvEscape(field_name) << ","
                << csvEscape(field_type) << ","
                << start_col << ","
                << end_col << ","
                << field_width << ","
                << is_significant << ","
                << is_indexed << ","
                << csvEscape(line_name) << ","
                << csvEscape(line_template) << "\n";

        row_count++;
    }

    outfile.close();

    auto end_time = std::chrono::steady_clock::now();
    double elapsed = std::chrono::duration<double>(end_time - start_time).count();

    if (!cfg.quiet) {
        std::cout << "Exported " << row_count << " indexed fields across "
                  << species_set.size() << " species\n"
                  << "Output: " << output_path.string() << "\n"
                  << "Completed in " << std::fixed << std::setprecision(1) << elapsed << "s\n";
    } else {
        std::cout << "Completed: " << output_path.string()
                  << " (" << row_count << " rows, " << species_set.size() << " species)\n";
    }

    db.disconnect();
    return EC_SUCCESS;
}
