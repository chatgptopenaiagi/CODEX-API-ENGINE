// Resolve the stable Node-API from the actual Node/Electron host executable.
#include <windows.h>
#include <delayimp.h>
#include <cstring>

static FARPROC WINAPI host_module(unsigned notification, PDelayLoadInfo info) {
    if (notification == dliNotePreLoadLibrary && std::strcmp(info->szDll, "node.exe") == 0)
        return reinterpret_cast<FARPROC>(GetModuleHandleW(nullptr));
    return nullptr;
}
extern "C" {
const PfnDliHook __pfnDliNotifyHook2 = host_module;
}
