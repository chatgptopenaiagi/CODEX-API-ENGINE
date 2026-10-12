#pragma once
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <bcrypt.h>
#include <nlohmann/json.hpp>
#include <algorithm>
#include <array>
#include <filesystem>
#include <fstream>
#include <map>
#include <regex>
#include <set>
#include <stdexcept>
#include <string>
#include <vector>

namespace cae {
using json = nlohmann::json;
class Error : public std::runtime_error {
public: explicit Error(const char* code) : std::runtime_error(code) {}
};
namespace detail {
struct Handle {
    HANDLE value;
    explicit Handle(HANDLE v) : value(v) {}
    ~Handle() { if (value && value != INVALID_HANDLE_VALUE) CloseHandle(value); }
    Handle(const Handle&) = delete;
    Handle& operator=(const Handle&) = delete;
};
inline void check(bool good) { if (!good) throw Error("broker_unavailable"); }
inline std::wstring wide(const std::string& text) {
    int count = MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, text.data(),
        static_cast<int>(text.size()), nullptr, 0);
    if (!count) throw Error("invalid_configuration");
    std::wstring result(count, L'\0');
    check(MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, text.data(),
        static_cast<int>(text.size()), result.data(), count) == count);
    return result;
}
inline json parse(const std::string& text) {
    std::map<int, std::set<std::string>> keys;
    try {
        return json::parse(text, [&keys](int depth, json::parse_event_t event, json& value) {
            if (depth > 64) throw Error("invalid_protocol");
            if (event == json::parse_event_t::object_start) keys[depth + 1].clear();
            if (event == json::parse_event_t::key &&
                !keys[depth].insert(value.get<std::string>()).second) throw Error("invalid_protocol");
            return true;
        });
    } catch (...) { throw Error("invalid_protocol"); }
}
inline void exact(const json& value, const std::set<std::string>& expected) {
    std::set<std::string> keys;
    if (!value.is_object()) throw Error("invalid_protocol");
    for (auto it = value.begin(); it != value.end(); ++it) keys.insert(it.key());
    if (keys != expected) throw Error("invalid_protocol");
}
inline std::string load(const std::filesystem::path& path) {
    if (!std::filesystem::is_regular_file(path) || std::filesystem::is_symlink(path) ||
        std::filesystem::file_size(path) > 65536) throw Error("invalid_configuration");
    std::ifstream file(path, std::ios::binary);
    if (!file) throw Error("invalid_configuration");
    return {std::istreambuf_iterator<char>(file), std::istreambuf_iterator<char>()};
}
inline std::vector<unsigned char> sid(HANDLE process) {
    HANDLE raw = nullptr;
    check(OpenProcessToken(process, TOKEN_QUERY, &raw) != 0);
    Handle token(raw);
    DWORD count = 0;
    GetTokenInformation(token.value, TokenUser, nullptr, 0, &count);
    check(count > 0 && count < 65536);
    std::vector<unsigned char> data(count);
    check(GetTokenInformation(token.value, TokenUser, data.data(), count, &count) != 0);
    auto source = reinterpret_cast<TOKEN_USER*>(data.data())->User.Sid;
    std::vector<unsigned char> result(GetLengthSid(source));
    check(CopySid(static_cast<DWORD>(result.size()), result.data(), source) != 0);
    return result;
}
inline std::string hex(const unsigned char* data, size_t count) {
    const char* digits = "0123456789abcdef";
    std::string result;
    for (size_t i = 0; i < count; ++i) { result += digits[data[i] >> 4]; result += digits[data[i] & 15]; }
    return result;
}
inline std::string hash(const std::wstring& path, ULONGLONG deadline) {
    Handle file(CreateFileW(path.c_str(), GENERIC_READ, FILE_SHARE_READ, nullptr,
        OPEN_EXISTING, FILE_FLAG_SEQUENTIAL_SCAN, nullptr));
    check(file.value != INVALID_HANDLE_VALUE);
    LARGE_INTEGER size;
    check(GetFileSizeEx(file.value, &size) && size.QuadPart <= 268435456);
    BCRYPT_ALG_HANDLE alg = nullptr;
    BCRYPT_HASH_HANDLE state = nullptr;
    check(BCryptOpenAlgorithmProvider(&alg, BCRYPT_SHA256_ALGORITHM, nullptr, 0) == 0);
    try {
        check(BCryptCreateHash(alg, &state, nullptr, 0, nullptr, 0, 0) == 0);
        std::array<unsigned char, 65536> buffer;
        DWORD count;
        while (true) {
            check(GetTickCount64() < deadline);
            check(ReadFile(file.value, buffer.data(), static_cast<DWORD>(buffer.size()), &count, nullptr));
            if (!count) break;
            check(BCryptHashData(state, buffer.data(), count, 0) == 0);
        }
        std::array<unsigned char, 32> digest;
        check(BCryptFinishHash(state, digest.data(), static_cast<ULONG>(digest.size()), 0) == 0);
        BCryptDestroyHash(state); state = nullptr;
        BCryptCloseAlgorithmProvider(alg, 0); alg = nullptr;
        return hex(digest.data(), digest.size());
    } catch (...) {
        if (state) BCryptDestroyHash(state);
        if (alg) BCryptCloseAlgorithmProvider(alg, 0);
        throw;
    }
}
inline void transfer(HANDLE pipe, char* bytes, size_t count, bool write, ULONGLONG deadline) {
    Handle event(CreateEventW(nullptr, TRUE, FALSE, nullptr));
    check(event.value != nullptr);
    size_t offset = 0;
    while (offset < count) {
        OVERLAPPED overlapped{};
        overlapped.hEvent = event.value;
        ResetEvent(event.value);
        DWORD done = 0;
        BOOL ok = write ? WriteFile(pipe, bytes + offset, static_cast<DWORD>(count - offset), &done, &overlapped)
                        : ReadFile(pipe, bytes + offset, static_cast<DWORD>(count - offset), &done, &overlapped);
        if (!ok) {
            check(GetLastError() == ERROR_IO_PENDING);
            auto now = GetTickCount64();
            DWORD remaining = now >= deadline ? 0 : static_cast<DWORD>(deadline - now);
            if (WaitForSingleObject(event.value, remaining) != WAIT_OBJECT_0) {
                CancelIoEx(pipe, &overlapped);
                GetOverlappedResult(pipe, &overlapped, &done, TRUE);
                throw Error("broker_unavailable");
            }
            check(GetOverlappedResult(pipe, &overlapped, &done, FALSE));
        }
        check(done > 0 && GetTickCount64() < deadline);
        offset += done;
    }
}
inline void send(HANDLE pipe, std::string body, ULONGLONG deadline) {
    if (body.empty() || body.size() > 65536) throw Error("invalid_protocol");
    uint32_t count = static_cast<uint32_t>(body.size()); // Windows x64 is little endian.
    transfer(pipe, reinterpret_cast<char*>(&count), 4, true, deadline);
    transfer(pipe, body.data(), body.size(), true, deadline);
}
inline std::string receive(HANDLE pipe, ULONGLONG deadline) {
    uint32_t count = 0;
    transfer(pipe, reinterpret_cast<char*>(&count), 4, false, deadline);
    if (!count || count > 65536) throw Error("invalid_protocol");
    std::string body(count, '\0');
    transfer(pipe, body.data(), count, false, deadline);
    return body;
}
} // namespace detail

class CAEClient {
    std::wstring pipe_, image_;
    std::string sha256_;
    DWORD timeout_;
public:
    explicit CAEClient(std::filesystem::path connection = {}, DWORD timeout_ms = 35000) : timeout_(timeout_ms) {
        try {
            if (connection.empty()) {
                wchar_t path[32768];
                DWORD size = GetEnvironmentVariableW(L"CAE_CONNECTION_FILE", path, 32768);
                if (!size || size >= 32768) throw Error("invalid_configuration");
                connection = path;
            }
            auto value = detail::parse(detail::load(connection));
            detail::exact(value, {"pipe", "server_image", "server_sha256"});
            auto pipe = value.at("pipe").get<std::string>();
            auto image = detail::wide(value.at("server_image").get<std::string>());
            sha256_ = value.at("server_sha256").get<std::string>();
            if (!std::regex_match(pipe, std::regex("cae-[a-z0-9][a-z0-9-]{0,63}")) ||
                !std::regex_match(sha256_, std::regex("[a-f0-9]{64}")) ||
                !std::filesystem::path(image).is_absolute() || !timeout_ || timeout_ > 120000)
                throw Error("invalid_configuration");
            pipe_ = L"\\\\.\\pipe\\" + detail::wide(pipe);
            image_ = std::filesystem::weakly_canonical(image).wstring();
        } catch (...) { throw Error("invalid_configuration"); }
    }

    json request(const std::string& operation, const json& args = json::object()) const {
        try {
            std::array<unsigned char, 16> random;
            detail::check(BCryptGenRandom(nullptr, random.data(), static_cast<ULONG>(random.size()),
                BCRYPT_USE_SYSTEM_PREFERRED_RNG) == 0);
            auto id = detail::hex(random.data(), random.size());
            auto body = json{{"v", 1}, {"id", id}, {"op", operation}, {"args", args}}.dump();
            if (body.size() > 65536 || operation.size() > 32 || !args.is_object()) throw Error("invalid_protocol");
            auto deadline = GetTickCount64() + timeout_;
            auto connect_deadline = GetTickCount64() + std::min<DWORD>(timeout_, 3000);
            HANDLE raw = INVALID_HANDLE_VALUE;
            while (raw == INVALID_HANDLE_VALUE) {
                raw = CreateFileW(pipe_.c_str(), GENERIC_READ | GENERIC_WRITE, 0, nullptr, OPEN_EXISTING,
                    FILE_FLAG_OVERLAPPED | SECURITY_SQOS_PRESENT | SECURITY_IDENTIFICATION, nullptr);
                if (raw != INVALID_HANDLE_VALUE) break;
                auto error = GetLastError();
                detail::check((error == ERROR_FILE_NOT_FOUND || error == ERROR_PIPE_BUSY) &&
                    GetTickCount64() < connect_deadline);
                Sleep(20);
            }
            detail::Handle pipe(raw);
            ULONG pid;
            detail::check(GetNamedPipeServerProcessId(pipe.value, &pid));
            detail::Handle process(OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, FALSE, pid));
            detail::check(process.value != nullptr);
            std::wstring name(32768, L'\0');
            DWORD size = static_cast<DWORD>(name.size());
            detail::check(QueryFullProcessImageNameW(process.value, 0, name.data(), &size));
            name.resize(size);
            auto peer = detail::sid(process.value), self = detail::sid(GetCurrentProcess());
            detail::check(EqualSid(peer.data(), self.data()) &&
                _wcsicmp(std::filesystem::weakly_canonical(name).c_str(), image_.c_str()) == 0);
            detail::check(detail::hash(image_, deadline) == sha256_);
            detail::send(pipe.value, body, deadline);
            auto result = detail::parse(detail::receive(pipe.value, deadline));
            detail::send(pipe.value, "OK", deadline);
            detail::exact(result, {"v", "id", "ok", "result", "error", "broker_pid"});
            if (!result["v"].is_number_integer() || result["v"] != 1 || result["id"] != id ||
                !result["ok"].is_boolean() || !result["broker_pid"].is_number_integer() ||
                result["broker_pid"] != pid || !result["result"].is_object()) throw Error("invalid_protocol");
            if (!result["ok"].get<bool>()) {
                const std::set<std::string> codes = {"access_denied", "invalid_protocol", "invalid_configuration",
                    "daily_request_limit", "credential_operation_failed", "credential_missing", "api_request_failed",
                    "unsupported_operation", "audit_unavailable", "broker_unavailable"};
                if (result["error"].is_string()) {
                    auto code = result["error"].get<std::string>();
                    if (codes.contains(code)) throw Error(code.c_str());
                }
                throw Error("broker_request_failed");
            }
            if (!result["error"].is_null()) throw Error("invalid_protocol");
            return result["result"];
        } catch (const Error&) { throw; }
          catch (...) { throw Error("invalid_protocol"); }
    }
    json connect() const { return request("status"); }
    json health(const std::string& provider = "openai") const { return request("health", {{"provider", provider}}); }
    json models(const std::string& provider = "openai") const { return request("models", {{"provider", provider}}); }
    json capabilities() const { return request("providers"); }
    json diagnostics(const std::string& provider = "openai") const { return request("diagnostics", {{"provider", provider}}); }
};
} // namespace cae
