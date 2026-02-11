// papyrus_extract_instances.cpp
// Full-featured C++ version of Extract_Instances.py
// Extracts report instances from IntelliSTOR MS SQL database with all Python features

#include <windows.h>
#include <sql.h>
#include <sqlext.h>
#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <map>
#include <sstream>
#include <iomanip>
#include <ctime>
#include <filesystem>
#include <algorithm>
#include <cstring>

namespace fs = std::filesystem;

// Exit codes
enum ExitCode {
    EC_SUCCESS = 0,
    EC_INVALID_ARGS = 1,
    EC_DB_CONNECTION_FAILED = 2,
    EC_INPUT_FILE_ERROR = 3,
    EC_EXTRACTION_FAILED = 4
};

// Timezone offset mapping (simplified - static offsets, not DST-aware)
struct TimezoneInfo {
    std::string name;
    int offset_minutes;  // Offset from UTC in minutes
};

static const std::map<std::string, TimezoneInfo> TIMEZONES = {
    {"UTC", {"UTC", 0}},
    {"Asia/Singapore", {"Asia/Singapore", 480}},      // UTC+8
    {"Asia/Hong_Kong", {"Asia/Hong_Kong", 480}},      // UTC+8
    {"America/New_York", {"America/New_York", -300}}, // UTC-5 (EST, ignoring DST)
    {"Europe/London", {"Europe/London", 0}},          // UTC+0 (GMT, ignoring BST)
    {"Asia/Tokyo", {"Asia/Tokyo", 540}},              // UTC+9
    {"Australia/Sydney", {"Australia/Sydney", 600}}   // UTC+10 (ignoring DST)
};

// Configuration
struct Config {
    std::string server;
    std::string database;
    std::string input_csv;
    std::string output_dir;
    std::string rptfolder;
    std::string timezone;
    int start_year;
    int end_year = 0;
    bool year_from_filename = false;
    bool windows_auth = false;
    std::string username;
    std::string password;
    bool quiet = false;
};

// Report species info
struct ReportSpecies {
    int report_species_id;
    std::string report_species_name;
    std::string report_species_displayname;
    std::string country_code;
    int in_use;
};

// Report instance
struct ReportInstance {
    int report_species_id;
    int rpt_file_id;
    std::string filename;
    std::string as_of_timestamp;
};

// Section entry from RPT file
struct SectionEntry {
    int section_id;
    int start_page;
    int page_count;
};

// RPT file header
struct RptHeader {
    int domain_id;
    int report_species_id;
    std::string timestamp;
    int page_count;
    int section_count;
    int section_data_offset;
};

// RPT Section Reader (C++ port of rpt_section_reader.py)
class RPTSectionReader {
public:
    static std::pair<RptHeader*, std::vector<SectionEntry>> readSectionHdr(const std::string& filepath) {
        std::ifstream file(filepath, std::ios::binary);
        if (!file.is_open()) {
            return {nullptr, {}};
        }

        // Read header (first 512 bytes)
        char header_data[512];
        file.read(header_data, 512);
        std::streamsize bytes_read = file.gcount();

        if (bytes_read < 512) {
            return {nullptr, {}};
        }

        // Parse header
        RptHeader* header = parseHeader(header_data, 512);
        if (!header) {
            return {nullptr, {}};
        }

        // Find SECTIONHDR marker
        std::vector<SectionEntry> sections;

        // Strategy 1: Scan near section_data_offset
        if (header->section_data_offset > 0) {
            file.seekg(std::max(0, header->section_data_offset - 16));
            char region[4096];
            file.read(region, 4096);
            std::streamsize region_size = file.gcount();

            const char* marker = findMarker(region, region_size, "SECTIONHDR");
            if (marker) {
                const char* data_start = marker + 13;  // Skip "SECTIONHDR\0\0\0"
                int data_offset = data_start - region;

                if (data_offset + header->section_count * 12 <= region_size) {
                    sections = parseSections(data_start, header->section_count);
                } else {
                    // Re-read from file
                    int abs_pos = std::max(0, header->section_data_offset - 16) + (marker - region) + 13;
                    file.seekg(abs_pos);
                    char section_data[12000];
                    file.read(section_data, header->section_count * 12);
                    sections = parseSections(section_data, header->section_count);
                }

                if (!sections.empty()) {
                    header->section_count = sections.size();
                    return {header, sections};
                }
            }
        }

        // Strategy 2: Full file scan
        file.seekg(0, std::ios::end);
        std::streamsize file_size = file.tellg();
        file.seekg(0);

        std::vector<char> full_data(file_size);
        file.read(full_data.data(), file_size);

        const char* marker = findMarker(full_data.data(), file_size, "SECTIONHDR");
        if (marker) {
            const char* data_start = marker + 13;
            const char* enddata = findMarker(data_start, file_size - (data_start - full_data.data()), "ENDDATA");

            int section_bytes;
            if (enddata) {
                section_bytes = enddata - data_start;
            } else {
                section_bytes = file_size - (data_start - full_data.data());
            }

            int num_triplets = section_bytes / 12;
            sections = parseSections(data_start, num_triplets);
        }

        header->section_count = sections.size();
        return {header, sections};
    }

    static std::string formatSegments(const std::vector<SectionEntry>& sections) {
        if (sections.empty()) return "";

        std::stringstream ss;
        for (size_t i = 0; i < sections.size(); ++i) {
            if (i > 0) ss << "|";
            ss << sections[i].section_id << "#" << sections[i].start_page << "#" << sections[i].page_count;
        }
        return ss.str();
    }

private:
    static RptHeader* parseHeader(const char* data, int size) {
        if (size < 512 || std::memcmp(data, "RPTFILEHDR", 10) != 0) {
            return nullptr;
        }

        RptHeader* header = new RptHeader();

        // Parse header line
        int header_end = 0;
        for (int i = 0; i < 192; ++i) {
            if (data[i] == '\x1a' || data[i] == '\0') {
                header_end = i;
                break;
            }
        }
        if (header_end == 0) header_end = 192;

        std::string header_line(data, header_end);
        std::vector<std::string> parts;
        std::stringstream ss(header_line);
        std::string part;
        while (std::getline(ss, part, '\t')) {
            parts.push_back(part);
        }

        // Parse domain:species
        if (parts.size() >= 2) {
            size_t colon = parts[1].find(':');
            if (colon != std::string::npos) {
                try {
                    header->domain_id = std::stoi(parts[1].substr(0, colon));
                    header->report_species_id = std::stoi(parts[1].substr(colon + 1));
                } catch (...) {
                    delete header;
                    return nullptr;
                }
            }
        }

        if (parts.size() >= 3) {
            header->timestamp = parts[2];
        }

        // Read table directory at 0x1D0
        if (size >= 0x200) {
            std::memcpy(&header->page_count, data + 0x1D4, 4);
            std::memcpy(&header->section_count, data + 0x1E4, 4);
            std::memcpy(&header->section_data_offset, data + 0x1E8, 4);
        }

        return header;
    }

    static const char* findMarker(const char* data, int size, const char* marker) {
        int marker_len = std::strlen(marker);
        for (int i = 0; i <= size - marker_len; ++i) {
            if (std::memcmp(data + i, marker, marker_len) == 0) {
                return data + i;
            }
        }
        return nullptr;
    }

    static std::vector<SectionEntry> parseSections(const char* data, int max_count) {
        std::vector<SectionEntry> sections;

        for (int i = 0; i < max_count; ++i) {
            SectionEntry entry;
            std::memcpy(&entry.section_id, data + i * 12, 4);
            std::memcpy(&entry.start_page, data + i * 12 + 4, 4);
            std::memcpy(&entry.page_count, data + i * 12 + 8, 4);

            if (entry.start_page >= 1 && entry.page_count >= 1) {
                sections.push_back(entry);
            } else if (entry.section_id == 0 && entry.start_page == 0 && entry.page_count == 0) {
                break;
            }
        }

        return sections;
    }
};

// Timezone utilities
class TimezoneConverter {
public:
    static std::string convertToUTC(const std::string& timestamp, const std::string& source_tz) {
        if (timestamp.empty()) return "";

        auto it = TIMEZONES.find(source_tz);
        if (it == TIMEZONES.end()) {
            return "";  // Unknown timezone
        }

        int offset_minutes = it->second.offset_minutes;

        // Parse timestamp (format: YYYY-MM-DD HH:MM:SS or YYYY-MM-DD HH:MM:SS.mmm)
        struct tm tm = {};
        int year, month, day, hour, minute, second;
        if (sscanf(timestamp.c_str(), "%d-%d-%d %d:%d:%d", &year, &month, &day, &hour, &minute, &second) != 6) {
            return "";
        }

        tm.tm_year = year - 1900;
        tm.tm_mon = month - 1;
        tm.tm_mday = day;
        tm.tm_hour = hour;
        tm.tm_min = minute;
        tm.tm_sec = second;
        tm.tm_isdst = -1;

        // Convert to UTC by subtracting offset
        time_t t = mktime(&tm);
        t -= offset_minutes * 60;

        struct tm* utc_tm = gmtime(&t);
        char buffer[64];
        strftime(buffer, sizeof(buffer), "%Y-%m-%d %H:%M:%S", utc_tm);

        return std::string(buffer);
    }
};

// Julian date converter
class JulianDateConverter {
public:
    static std::string convertJulianDate(const std::string& filename) {
        if (filename.size() < 5) return "";

        try {
            int year_prefix = std::stoi(filename.substr(0, 2));
            int day_of_year = std::stoi(filename.substr(2, 3));

            int year = 2000 + year_prefix;

            struct tm tm = {};
            tm.tm_year = year - 1900;
            tm.tm_mon = 0;
            tm.tm_mday = 1;
            tm.tm_isdst = -1;

            time_t t = mktime(&tm);
            t += (day_of_year - 1) * 86400;

            struct tm* result_tm = localtime(&t);
            char buffer[32];
            strftime(buffer, sizeof(buffer), "%Y-%m-%d", result_tm);

            return std::string(buffer);
        } catch (...) {
            return "";
        }
    }
};

// ODBC connection (same as before)
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
        if (!SQL_SUCCEEDED(ret)) return false;

        return true;
    }

    std::string fetchString(int col) {
        SQLCHAR buffer[4096];
        SQLLEN indicator;
        SQLRETURN ret = SQLGetData(hstmt, col, SQL_C_CHAR, buffer, sizeof(buffer), &indicator);
        if (SQL_SUCCEEDED(ret) && indicator != SQL_NULL_DATA) {
            std::string result((char*)buffer);
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

// CSV handler with IN_USE update support
class CSVHandler {
public:
    static std::vector<ReportSpecies> readReportSpecies(const std::string& filename) {
        std::vector<ReportSpecies> results;
        std::ifstream file(filename);
        if (!file.is_open()) {
            throw std::runtime_error("Cannot open file: " + filename);
        }

        std::string line;
        std::getline(file, line);  // Skip header

        while (std::getline(file, line)) {
            if (line.empty()) continue;

            std::vector<std::string> fields = parseCSVLine(line);

            if (fields.size() >= 5) {
                try {
                    ReportSpecies rs;
                    rs.report_species_id = std::stoi(fields[0]);
                    rs.report_species_name = fields[1];
                    rs.report_species_displayname = fields[2];
                    rs.country_code = fields[3];
                    rs.in_use = std::stoi(fields[4]);
                    results.push_back(rs);
                } catch (const std::exception& e) {
                    std::cerr << "Warning: Skipping invalid CSV row (stoi failed on '" << fields[0] << "' or '" << fields[4] << "'): " << line << "\n";
                }
            }
        }

        return results;
    }

    static void updateInUse(const std::string& filename, int report_species_id, int new_in_use) {
        std::vector<ReportSpecies> records = readReportSpecies(filename);

        // Update the record
        for (auto& rec : records) {
            if (rec.report_species_id == report_species_id) {
                rec.in_use = new_in_use;
                break;
            }
        }

        // Write back
        std::string temp_file = filename + ".tmp";
        std::ofstream out(temp_file);
        if (!out.is_open()) {
            throw std::runtime_error("Cannot open temp file: " + temp_file);
        }

        out << "REPORT_SPECIES_ID,REPORT_SPECIES_NAME,REPORT_SPECIES_DISPLAYNAME,COUNTRY_CODE,IN_USE\n";
        for (const auto& rec : records) {
            out << rec.report_species_id << ","
                << escape(rec.report_species_name) << ","
                << escape(rec.report_species_displayname) << ","
                << escape(rec.country_code) << ","
                << rec.in_use << "\n";
        }

        out.close();
        fs::remove(filename);
        fs::rename(temp_file, filename);
    }

    static void writeInstancesCSV(const std::string& filename,
                                   const std::string& report_name,
                                   const std::string& country,
                                   const std::vector<ReportInstance>& instances,
                                   const Config& cfg,
                                   std::map<std::string, std::string>& segments_cache) {
        std::ofstream file(filename);
        if (!file.is_open()) {
            throw std::runtime_error("Cannot open file: " + filename);
        }

        file << "REPORT_SPECIES_NAME,FILENAME,RPT_FILENAME,COUNTRY,YEAR,REPORT_DATE,AS_OF_TIMESTAMP,UTC,SEGMENTS,REPORT_FILE_ID\n";

        for (const auto& inst : instances) {
            std::string rpt_filename = inst.filename;
            std::string filename_display = getBasename(rpt_filename);
            if (filename_display.size() > 4 && filename_display.substr(filename_display.size() - 4) == ".RPT") {
                filename_display = filename_display.substr(0, filename_display.size() - 4);
            }

            std::string year = cfg.year_from_filename ?
                extractYearFromFilename(getBasename(rpt_filename)) :
                extractYearFromTimestamp(inst.as_of_timestamp);

            std::string report_date = JulianDateConverter::convertJulianDate(getBasename(rpt_filename));
            std::string utc = TimezoneConverter::convertToUTC(inst.as_of_timestamp, cfg.timezone);

            std::string segments;
            if (!cfg.rptfolder.empty()) {
                std::string cache_key = getBasename(rpt_filename);
                std::transform(cache_key.begin(), cache_key.end(), cache_key.begin(), ::toupper);

                if (segments_cache.find(cache_key) != segments_cache.end()) {
                    segments = segments_cache[cache_key];
                } else {
                    segments = getRPTSegments(cfg.rptfolder, getBasename(rpt_filename));
                    segments_cache[cache_key] = segments;
                }
            }

            file << escape(report_name) << ","
                 << escape(filename_display) << ","
                 << escape(rpt_filename) << ","
                 << escape(country) << ","
                 << year << ","
                 << report_date << ","
                 << escape(inst.as_of_timestamp) << ","
                 << escape(utc) << ","
                 << escape(segments) << ","
                 << inst.rpt_file_id << "\n";
        }
    }

private:
    static std::vector<std::string> parseCSVLine(const std::string& line) {
        std::vector<std::string> fields;
        std::string current;
        bool in_quotes = false;

        for (size_t i = 0; i < line.size(); ++i) {
            char c = line[i];

            if (c == '"') {
                if (in_quotes && i + 1 < line.size() && line[i + 1] == '"') {
                    current += '"';
                    ++i;
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

    static std::string escape(const std::string& s) {
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

    static std::string getBasename(const std::string& path) {
        size_t pos = path.find_last_of("\\/");
        if (pos != std::string::npos) {
            return path.substr(pos + 1);
        }
        return path;
    }

    static std::string extractYearFromTimestamp(const std::string& timestamp) {
        if (timestamp.size() >= 4) {
            return timestamp.substr(0, 4);
        }
        return "";
    }

    static std::string extractYearFromFilename(const std::string& filename) {
        if (filename.size() >= 2) {
            try {
                int year_prefix = std::stoi(filename.substr(0, 2));
                return "20" + filename.substr(0, 2);
            } catch (...) {
                return "";
            }
        }
        return "";
    }

    static std::string getRPTSegments(const std::string& rptfolder, const std::string& filename) {
        std::string rpt_filename = filename;
        std::transform(rpt_filename.begin(), rpt_filename.end(), rpt_filename.begin(), ::toupper);
        if (rpt_filename.size() < 4 || rpt_filename.substr(rpt_filename.size() - 4) != ".RPT") {
            rpt_filename += ".RPT";
        }

        std::string rpt_path = rptfolder + "/" + rpt_filename;

        if (!fs::exists(rpt_path)) {
            return "";
        }

        auto result = RPTSectionReader::readSectionHdr(rpt_path);
        if (result.first == nullptr) {
            return "";
        }

        delete result.first;
        return RPTSectionReader::formatSegments(result.second);
    }
};

// Progress tracker
class ProgressTracker {
private:
    std::string progress_file;

public:
    ProgressTracker(const std::string& output_dir) {
        progress_file = output_dir + "/progress.txt";
    }

    int readProgress() {
        std::ifstream file(progress_file);
        if (!file.is_open()) {
            return 0;
        }

        int last_id;
        file >> last_id;
        return last_id;
    }

    void writeProgress(int report_species_id) {
        std::ofstream file(progress_file);
        if (file.is_open()) {
            file << report_species_id;
        }
    }
};

// Main extractor
class InstancesExtractor {
private:
    Config cfg;
    ODBCConnection db;
    std::vector<ReportSpecies> report_species;
    ProgressTracker progress_tracker;
    std::map<std::string, std::string> segments_cache;

    int total_processed = 0;
    int total_exported = 0;
    int total_skipped = 0;

public:
    InstancesExtractor(const Config& config) : cfg(config), progress_tracker(config.output_dir) {}

    bool connect() {
        return db.connect(cfg);
    }

    bool loadReportSpecies() {
        if (!cfg.quiet) std::cout << "Loading Report_Species.csv...\n";

        try {
            report_species = CSVHandler::readReportSpecies(cfg.input_csv);
            if (!cfg.quiet) {
                std::cout << "  Loaded " << report_species.size() << " report species\n";
            }
            return true;
        } catch (const std::exception& e) {
            std::cerr << "Failed to load Report_Species.csv: " << e.what() << "\n";
            return false;
        }
    }

    std::vector<ReportInstance> queryInstances(int report_species_id) {
        std::vector<ReportInstance> results;

        // Check if required tables exist
        if (!db.tableExists("REPORT_INSTANCE")) {
            if (!cfg.quiet) std::cerr << "  Warning: REPORT_INSTANCE table does not exist\n";
            return results;
        }

        std::stringstream query;
        query << "SELECT ri.REPORT_SPECIES_ID, rfi.RPT_FILE_ID, RTRIM(rf.FILENAME) AS FILENAME, ri.AS_OF_TIMESTAMP "
              << "FROM REPORT_INSTANCE ri "
              << "LEFT JOIN RPTFILE_INSTANCE rfi ON ri.DOMAIN_ID = rfi.DOMAIN_ID "
              << "  AND ri.REPORT_SPECIES_ID = rfi.REPORT_SPECIES_ID "
              << "  AND ri.AS_OF_TIMESTAMP = rfi.AS_OF_TIMESTAMP "
              << "  AND ri.REPROCESS_IN_PROGRESS = rfi.REPROCESS_IN_PROGRESS "
              << "LEFT JOIN RPTFILE rf ON rfi.RPT_FILE_ID = rf.RPT_FILE_ID "
              << "WHERE ri.REPORT_SPECIES_ID = " << report_species_id
              << " AND ri.AS_OF_TIMESTAMP >= '" << cfg.start_year << "-01-01 00:00:00'";

        if (cfg.end_year > 0) {
            query << " AND ri.AS_OF_TIMESTAMP < '" << (cfg.end_year + 1) << "-01-01 00:00:00'";
        }

        query << " ORDER BY ri.AS_OF_TIMESTAMP ASC";

        if (!db.executeQuery(query.str())) {
            if (!cfg.quiet) std::cerr << "  Warning: Query failed for report species " << report_species_id << "\n";
            return results;
        }

        while (db.fetch()) {
            ReportInstance inst;
            inst.report_species_id = db.fetchInt(1);
            inst.rpt_file_id = db.fetchInt(2);
            inst.filename = db.fetchString(3);
            inst.as_of_timestamp = db.fetchString(4);
            results.push_back(inst);
        }

        return results;
    }

    bool extractAll() {
        int last_processed_id = progress_tracker.readProgress();

        // Filter reports to process
        std::vector<ReportSpecies> to_process;
        for (const auto& rs : report_species) {
            if (rs.report_species_id > last_processed_id) {
                to_process.push_back(rs);
            }
        }

        if (!cfg.quiet) {
            std::cout << "Processing " << to_process.size() << " report species";
            if (last_processed_id > 0) {
                std::cout << " (resuming from ID " << last_processed_id << ")";
            }
            std::cout << "\n";
            std::cout << "Year filter: " << cfg.start_year;
            if (cfg.end_year > 0) {
                std::cout << "-" << cfg.end_year;
            } else {
                std::cout << "+";
            }
            std::cout << "\n";
            std::cout << "YEAR column from: " << (cfg.year_from_filename ? "filename" : "AS_OF_TIMESTAMP") << "\n";
            std::cout << "Timezone: " << cfg.timezone << " (converting to UTC)\n";
            if (!cfg.rptfolder.empty()) {
                std::cout << "SEGMENTS source: RPT file SECTIONHDR from " << cfg.rptfolder << "\n";
            } else {
                std::cout << "SEGMENTS source: none (--rptfolder not provided)\n";
            }
            std::cout << "\n";
        }

        for (size_t i = 0; i < to_process.size(); ++i) {
            const auto& rs = to_process[i];

            if (!cfg.quiet) {
                std::cout << "Processing " << (i + 1) << "/" << to_process.size()
                         << ": " << rs.report_species_name
                         << " (ID: " << rs.report_species_id << ")\n";
            }

            auto instances = queryInstances(rs.report_species_id);

            if (!instances.empty()) {
                std::stringstream output_filename;
                output_filename << rs.report_species_name << "_" << cfg.start_year;
                if (cfg.end_year > 0) {
                    output_filename << "_" << cfg.end_year;
                }
                output_filename << ".csv";

                std::string output_path = cfg.output_dir + "/" + output_filename.str();

                try {
                    CSVHandler::writeInstancesCSV(output_path, rs.report_species_name,
                                                  rs.country_code, instances, cfg, segments_cache);
                    if (!cfg.quiet) {
                        std::cout << "  Exported " << instances.size() << " instances to "
                                 << output_filename.str() << "\n";
                    }
                    total_exported++;
                } catch (const std::exception& e) {
                    std::cerr << "  Error writing output: " << e.what() << "\n";
                }
            } else {
                // Update IN_USE=0
                if (!cfg.quiet) {
                    std::cout << "  No instances found, updating IN_USE=0\n";
                }
                try {
                    CSVHandler::updateInUse(cfg.input_csv, rs.report_species_id, 0);
                } catch (const std::exception& e) {
                    std::cerr << "  Error updating IN_USE: " << e.what() << "\n";
                }
                total_skipped++;
            }

            // Update progress
            progress_tracker.writeProgress(rs.report_species_id);
            total_processed++;

            if (cfg.quiet && (i + 1) % 10 == 0) {
                std::cout << "\rProgress: " << (i + 1) << "/" << to_process.size()
                         << " | Exported: " << total_exported
                         << " | Skipped: " << total_skipped << std::flush;
            }
        }

        if (cfg.quiet) {
            std::cout << "\n";
        }

        return true;
    }

    void printSummary() {
        if (!cfg.quiet) {
            std::cout << "\n==================================================\n";
            std::cout << "Extraction completed\n";
            std::cout << "  Total processed: " << total_processed << "\n";
            std::cout << "  Exported: " << total_exported << "\n";
            std::cout << "  Skipped (no instances, IN_USE=0): " << total_skipped << "\n";
            std::cout << "==================================================\n";
        } else {
            std::cout << "\nCompleted: " << total_processed << " processed | "
                     << total_exported << " exported | "
                     << total_skipped << " skipped\n";
        }
    }
};

void printUsage(const char* prog) {
    std::cout << "Usage: " << prog << " [OPTIONS]\n\n";
    std::cout << "Required:\n";
    std::cout << "  --server SERVER         MS SQL Server hostname\n";
    std::cout << "  --database DATABASE     Database name\n";
    std::cout << "  --start-year YEAR       Start year (e.g., 2023)\n\n";
    std::cout << "Authentication:\n";
    std::cout << "  --windows-auth          Use Windows Authentication\n";
    std::cout << "  --user USERNAME         SQL Server username\n";
    std::cout << "  --password PASSWORD     SQL Server password\n\n";
    std::cout << "Options:\n";
    std::cout << "  --input CSV             Input Report_Species.csv (default: Report_Species.csv)\n";
    std::cout << "  --output-dir DIR        Output directory (default: current)\n";
    std::cout << "  --end-year YEAR         Optional end year\n";
    std::cout << "  --year-from-filename    Extract YEAR from filename instead of timestamp\n";
    std::cout << "  --timezone TZ           Timezone for UTC conversion (default: Asia/Singapore)\n";
    std::cout << "  --rptfolder DIR         Directory with RPT files for SEGMENTS extraction\n";
    std::cout << "  --quiet                 Quiet mode (minimal output)\n";
    std::cout << "  --help                  Show this help\n\n";
    std::cout << "Example:\n";
    std::cout << "  " << prog << " --server SQLSRV01 --database IntelliSTOR_SG --windows-auth --start-year 2023 --rptfolder C:\\RPT\n";
}

int main(int argc, char* argv[]) {
    Config cfg;
    cfg.input_csv = "Report_Species.csv";
    cfg.output_dir = ".";
    cfg.timezone = "Asia/Singapore";
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
        } else if (arg == "--start-year" && i + 1 < argc) {
            std::string val = argv[++i];
            try { cfg.start_year = std::stoi(val); }
            catch (...) { std::cerr << "Error: --start-year requires a numeric value, got '" << val << "'\n"; return EC_INVALID_ARGS; }
        } else if (arg == "--end-year" && i + 1 < argc) {
            std::string val = argv[++i];
            if (val.empty() || val[0] == '-') { --i; }  // skip empty or next flag
            else {
                try { cfg.end_year = std::stoi(val); }
                catch (...) { std::cerr << "Error: --end-year requires a numeric value, got '" << val << "'\n"; return EC_INVALID_ARGS; }
            }
        } else if (arg == "--input" && i + 1 < argc) {
            cfg.input_csv = argv[++i];
        } else if (arg == "--output-dir" && i + 1 < argc) {
            cfg.output_dir = argv[++i];
        } else if (arg == "--rptfolder" && i + 1 < argc) {
            cfg.rptfolder = argv[++i];
        } else if (arg == "--timezone" && i + 1 < argc) {
            cfg.timezone = argv[++i];
        } else if (arg == "--year-from-filename") {
            cfg.year_from_filename = true;
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

    if (cfg.server.empty() || cfg.database.empty() || cfg.start_year == 0) {
        std::cerr << "Error: Missing required arguments\n\n";
        printUsage(argv[0]);
        return EC_INVALID_ARGS;
    }

    // Validate timezone
    if (TIMEZONES.find(cfg.timezone) == TIMEZONES.end()) {
        std::cerr << "Error: Invalid timezone: " << cfg.timezone << "\n";
        std::cerr << "Supported timezones: ";
        for (const auto& pair : TIMEZONES) {
            std::cerr << pair.first << " ";
        }
        std::cerr << "\n";
        return EC_INVALID_ARGS;
    }

    try {
        fs::create_directories(cfg.output_dir);
    } catch (const std::exception& e) {
        std::cerr << "Error creating output directory: " << e.what() << "\n";
        return EC_INVALID_ARGS;
    }

    if (!cfg.quiet) {
        std::cout << "==================================================\n";
        std::cout << "Papyrus Instances Extractor (Full-Featured)\n";
        std::cout << "==================================================\n\n";
    }

    InstancesExtractor extractor(cfg);

    if (!extractor.loadReportSpecies()) {
        return EC_INPUT_FILE_ERROR;
    }

    if (!extractor.connect()) {
        std::cerr << "Failed to connect to database\n";
        return EC_DB_CONNECTION_FAILED;
    }

    if (!extractor.extractAll()) {
        std::cerr << "Extraction failed\n";
        return EC_EXTRACTION_FAILED;
    }

    extractor.printSummary();

    return EC_SUCCESS;
}
