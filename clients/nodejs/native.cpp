#include <node_api.h>
#include "cae_client.hpp"

static napi_value request(napi_env env, napi_callback_info info) {
    try {
        size_t argc = 1;
        napi_value argv[1];
        if (napi_get_cb_info(env, info, &argc, argv, nullptr, nullptr) != napi_ok || argc != 1)
            throw cae::Error("invalid_protocol");
        size_t count;
        if (napi_get_value_string_utf8(env, argv[0], nullptr, 0, &count) != napi_ok || count > 131072)
            throw cae::Error("invalid_protocol");
        std::string input(count + 1, '\0');
        if (napi_get_value_string_utf8(env, argv[0], input.data(), input.size(), &count) != napi_ok)
            throw cae::Error("invalid_protocol");
        input.resize(count);
        auto value = cae::detail::parse(input);
        cae::CAEClient client(cae::detail::wide(value.at("connection").get<std::string>()),
            value.at("timeout").get<DWORD>());
        auto output = client.request(value.at("operation").get<std::string>(), value.at("args")).dump();
        napi_value result;
        if (napi_create_string_utf8(env, output.c_str(), output.size(), &result) != napi_ok)
            throw cae::Error("broker_unavailable");
        return result;
    } catch (const cae::Error& error) { napi_throw_error(env, nullptr, error.what()); }
      catch (...) { napi_throw_error(env, nullptr, "invalid_protocol"); }
    return nullptr;
}
static napi_value init(napi_env env, napi_value exports) {
    napi_value fn;
    if (napi_create_function(env, "request", NAPI_AUTO_LENGTH, request, nullptr, &fn) != napi_ok ||
        napi_set_named_property(env, exports, "request", fn) != napi_ok) return nullptr;
    return exports;
}
NAPI_MODULE(NODE_GYP_MODULE_NAME, init)
