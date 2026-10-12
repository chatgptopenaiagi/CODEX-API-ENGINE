#include "cae_client.hpp"
#include <iostream>

int wmain(int argc, wchar_t** argv) {
    try {
        if (argc != 2) return 2;
        if (std::wstring(argv[1]) == L"--probe") {
            try { cae::CAEClient({}, 1000).connect(); std::cout << "ok\n"; }
            catch (const cae::Error& e) { std::cout << e.what() << '\n'; }
            return 0;
        }
        cae::CAEClient client;
        std::filesystem::path output(argv[1]);
        while (!std::filesystem::exists(output.wstring() + L".stop")) {
            try {
                auto status = client.connect();
                client.health("lab");
                auto models = client.models("lab"), capabilities = client.capabilities();
                bool denied = false, malformed = false, restricted = false;
                try { client.request("stop"); }
                catch (const cae::Error& e) { denied = std::string(e.what()) == "access_denied"; }
                try { client.request("status", {{"app", "admin"}}); }
                catch (const cae::Error& e) { malformed = std::string(e.what()) == "invalid_protocol"; }
                try { client.request("chat", {{"provider", "lab"}, {"model", "lab-model"}, {"text", "test"}}); }
                catch (const cae::Error& e) { restricted = std::string(e.what()) == "access_denied"; }
                cae::json routing = nullptr;
                wchar_t routingFlag[2] = {};
                if (GetEnvironmentVariableW(L"CAE_LAB_ROUTING", routingFlag, 2) == 1 && routingFlag[0] == L'1') {
                    routing = client.request("route", {{"contract_version", 1}, {"capability", "chat_generation"},
                        {"model", "route-model"}, {"input", "synthetic"}, {"routing_mode", "LOCAL_ONLY"}});
                    client.request("capabilities");
                }
                cae::json result = {{"status", status}, {"models", models}, {"capabilities", capabilities}, {"routing", routing},
                    {"denied", denied}, {"malformed", malformed}, {"restricted", restricted},
                    {"client_pid", GetCurrentProcessId()}};
                auto temp = output.wstring() + L".new";
                { std::ofstream file(std::filesystem::path(temp), std::ios::binary); file << result.dump(); }
                if (!MoveFileExW(temp.c_str(), output.c_str(), MOVEFILE_REPLACE_EXISTING)) return 3;
            } catch (const cae::Error&) { /* Independent reads recover on next iteration. */ }
            Sleep(500);
        }
        return 0;
    } catch (...) { std::cerr << "lab_client_failed\n"; return 1; }
}
