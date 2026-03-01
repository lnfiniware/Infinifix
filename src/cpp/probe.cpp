#include <array>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <sys/utsname.h>
#include <vector>

static std::string trim(std::string value) {
    while (!value.empty() && (value.back() == '\n' || value.back() == '\r' || value.back() == ' ' || value.back() == '\t')) {
        value.pop_back();
    }
    size_t start = 0;
    while (start < value.size() && (value[start] == ' ' || value[start] == '\t')) {
        ++start;
    }
    return value.substr(start);
}

static std::string read_first_line(const std::string& path) {
    std::ifstream file(path);
    if (!file.good()) {
        return "";
    }
    std::string line;
    std::getline(file, line);
    return trim(line);
}

static std::string json_escape(const std::string& input) {
    std::ostringstream out;
    for (char c : input) {
        switch (c) {
            case '\\':
                out << "\\\\";
                break;
            case '"':
                out << "\\\"";
                break;
            case '\n':
                out << "\\n";
                break;
            case '\r':
                out << "\\r";
                break;
            case '\t':
                out << "\\t";
                break;
            default:
                out << c;
                break;
        }
    }
    return out.str();
}

static std::vector<std::string> run_lines(const std::string& command) {
    std::vector<std::string> lines;
    std::array<char, 4096> buffer{};
    FILE* handle = popen(command.c_str(), "r");
    if (!handle) {
        return lines;
    }
    while (fgets(buffer.data(), static_cast<int>(buffer.size()), handle) != nullptr) {
        lines.emplace_back(trim(buffer.data()));
    }
    pclose(handle);
    return lines;
}

static void print_json_array(const std::string& key, const std::vector<std::string>& values, bool trailing_comma) {
    std::cout << "  \"" << key << "\": [\n";
    for (size_t i = 0; i < values.size(); ++i) {
        std::cout << "    \"" << json_escape(values[i]) << "\"";
        if (i + 1 < values.size()) {
            std::cout << ",";
        }
        std::cout << "\n";
    }
    std::cout << "  ]";
    if (trailing_comma) {
        std::cout << ",";
    }
    std::cout << "\n";
}

int main() {
    struct utsname uts {};
    std::string kernel = "";
    if (uname(&uts) == 0) {
        kernel = uts.release;
    }

    const std::string vendor = read_first_line("/sys/class/dmi/id/sys_vendor");
    const std::string product = read_first_line("/sys/class/dmi/id/product_name");
    const std::string version = read_first_line("/sys/class/dmi/id/product_version");
    const std::string bios = read_first_line("/sys/class/dmi/id/bios_version");

    const auto lspci = run_lines("lspci 2>/dev/null");
    const auto lsusb = run_lines("lsusb 2>/dev/null");

    std::cout << "{\n";
    std::cout << "  \"dmi_vendor\": \"" << json_escape(vendor) << "\",\n";
    std::cout << "  \"dmi_product_name\": \"" << json_escape(product) << "\",\n";
    std::cout << "  \"dmi_product_version\": \"" << json_escape(version) << "\",\n";
    std::cout << "  \"bios_version\": \"" << json_escape(bios) << "\",\n";
    std::cout << "  \"kernel\": \"" << json_escape(kernel) << "\",\n";
    print_json_array("lspci", lspci, true);
    print_json_array("lsusb", lsusb, false);
    std::cout << "}\n";
    return 0;
}

