# Windows PE Binary Build Notes

This document explains the Windows PE (Portable Executable) build system for AgentRE-Bench, platform-specific porting decisions, and known limitations.

## Overview

The Windows build system cross-compiles C source files to Windows PE32+ (64-bit) executables using MinGW-w64 (GNU Compiler Collection targeting Windows). The build process is implemented in Rust for cross-platform compatibility and robust error handling.

## Build Architecture

### Toolchain Options

**Option 1: Native MinGW (Recommended for CI/CD)**
- Install MinGW-w64 on Linux/macOS
- Compiler: `x86_64-w64-mingw32-gcc`
- Direct compilation without Docker overhead
- Fastest build times

**Option 2: Docker Cross-Compilation (Fallback)**
- Uses `Dockerfile.mingw` with Ubuntu 22.04 + MinGW-w64
- Works on any platform with Docker Desktop
- Automatic fallback when MinGW not installed
- Slightly slower due to container overhead

### Compilation Flags

Standard flags for all samples:
```bash
x86_64-w64-mingw32-gcc \
  -O0                          # No optimization (easier to analyze)
  -fno-stack-protector         # Disable stack canaries
  -static                      # Static linking (no runtime DLLs)
  -Wl,--subsystem,console      # Windows console application
  -lws2_32                     # Link WinSock2 library
  -o output.exe \
  source.c
```

**Rationale:**
- **`-O0`**: Preserves function calls and control flow for reverse engineering analysis
- **`-fno-stack-protector`**: Removes stack canary checks (standard for RE benchmarks)
- **`-static`**: Avoids runtime DLL dependencies (MSVCRT, etc.)
- **`-Wl,--subsystem,console`**: Ensures PE subsystem is CONSOLE, not GUI
- **`-lws2_32`**: Links WinSock2 API for network functionality

## Platform-Specific API Mappings

The Windows ports replace POSIX APIs with Windows equivalents:

### Networking (POSIX → WinSock2)

| POSIX API | Windows API | Notes |
|-----------|-------------|-------|
| `socket()` | `WSASocket()` + `WSAStartup()` | Requires initialization |
| `connect()` | `connect()` | Same function name, different header |
| `send()` / `recv()` | Same | Compatible API |
| `close()` | `closesocket()` | Different function name |
| `inet_pton()` | `inet_pton()` | Available in WinSock2 (Vista+) |
| `getaddrinfo()` | `getaddrinfo()` | Cross-platform API |
| `gethostbyname()` | Deprecated | Use `getaddrinfo()` instead |

**Required headers:**
```c
#include <winsock2.h>
#include <ws2tcpip.h>
#pragma comment(lib, "ws2_32.lib")  // MSVC only
```

**Initialization pattern:**
```c
WSADATA wsa;
if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
    return 1;  // Failed to initialize WinSock
}
// ... use sockets ...
WSACleanup();  // Cleanup
```

### Process Creation (POSIX → Windows)

| POSIX API | Windows API | Complexity |
|-----------|-------------|------------|
| `fork()` | `CreateProcess()` | High - no direct equivalent |
| `execve()` | `CreateProcess()` | Medium - different paradigm |
| `dup2()` | `STARTUPINFO.hStd*` handles | Medium - handle redirection |
| `system()` | `CreateProcess()` or `_popen()` | Low |
| `popen()` | `_popen()` | Low - portable |

**`fork()` → `CreateProcess()` Pattern:**

Linux (fork + exec):
```c
if (fork() == 0) {
    execve("/bin/sh", NULL, NULL);
}
```

Windows (CreateProcess):
```c
STARTUPINFOA si;
PROCESS_INFORMATION pi;
ZeroMemory(&si, sizeof(si));
si.cb = sizeof(si);
CreateProcessA("C:\\Windows\\System32\\cmd.exe", NULL, NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi);
CloseHandle(pi.hProcess);
CloseHandle(pi.hThread);
```

**I/O Redirection (`dup2()` → STARTUPINFO handles):**

Linux:
```c
dup2(sock, 0);  // stdin
dup2(sock, 1);  // stdout
dup2(sock, 2);  // stderr
execve("/bin/sh", NULL, NULL);
```

Windows:
```c
STARTUPINFOA si;
ZeroMemory(&si, sizeof(si));
si.cb = sizeof(si);
si.dwFlags = STARTF_USESTDHANDLES;
si.hStdInput = (HANDLE)sock;
si.hStdOutput = (HANDLE)sock;
si.hStdError = (HANDLE)sock;
CreateProcessA("C:\\Windows\\System32\\cmd.exe", NULL, NULL, NULL, TRUE, 0, NULL, NULL, &si, &pi);
```

### Thread Creation (POSIX → Windows)

| POSIX API | Windows API | Notes |
|-----------|-------------|-------|
| `pthread_create()` | `CreateThread()` | Different signature |
| `pthread_join()` | `WaitForSingleObject()` | Different paradigm |
| `pthread_mutex_*` | `CRITICAL_SECTION` or `Mutex` | Different locking primitives |

## MVP Implementation (5 Samples)

### Tier 1: Easy Ports (Current Status)

✅ **Level 1: TCP Server** - `level1_TCPServer.c`
- **Changes**: WinSock2 initialization, `CreateProcess()` for cmd.exe, handle redirection
- **API Replacements**: `socket()` → `WSASocket()`, `execve()` → `CreateProcess()`
- **Complexity**: Low (2-3 hours)

✅ **Level 2: XOR Encoded Strings** - `level2_XorEncodedStrings.c`
- **Changes**: WinSock2 + XOR decoding (same logic as Linux)
- **API Replacements**: Same as Level 1 + XOR function (unchanged)
- **Complexity**: Low (2-3 hours)
- **Note**: Shell path XOR-encoded as `C:\\Windows\\System32\\cmd.exe`

✅ **Level 4: Polymorphic Reverse Shell** - `level4_polymorphicReverseShell.c`
- **Changes**: WinSock2 + polymorphic shellcode generation (NOP sled unchanged)
- **API Replacements**: `malloc()` + `CreateProcess()`
- **Complexity**: Low-Medium (3-4 hours)
- **Note**: Shellcode template simplified (no direct syscalls on Windows)

✅ **Level 7: DNS Tunnel Reverse Shell** - `level7_DNS_TunnelReverseShell.c`
- **Changes**: WinSock2 initialization, `getaddrinfo()` (cross-platform), `_popen()` instead of `popen()`
- **API Replacements**: `sleep()` → `Sleep()`, `popen()` → `_popen()`
- **Complexity**: Low-Medium (3-4 hours)

✅ **Level 11: Fork Bomb Reverse Shell** - `level11_ForkBombReverseShell.c`
- **Changes**: `fork()` → `CreateProcess()` recursive, `CreateThread()` for reverse shell
- **API Replacements**: `fork()` → `CreateProcess()` + `GetModuleFileName()`
- **Complexity**: Medium (4-5 hours)
- **Note**: Uses `GetModuleFileName()` to get own path for recursive spawning

## Known Limitations (Out of Scope for MVP)

### Skipped Samples (Platform-Specific Complexity)

❌ **Level 3: Anti-debugging Reverse Shell**
- **Reason**: Uses `ptrace(PTRACE_TRACEME)` (Linux-specific)
- **Windows Alternative**: `IsDebuggerPresent()`, `CheckRemoteDebuggerPresent()`
- **Complexity**: Medium (4-5 hours)

❌ **Level 5: Multistage Reverse Shell**
- **Reason**: HTTP staging + complex state management
- **Windows Alternative**: Same logic, just WinSock2 + CreateProcess
- **Complexity**: Medium (5-6 hours)

❌ **Level 6: ICMP Covert Channel Shell**
- **Reason**: Raw ICMP socket handling (Linux `struct iphdr`, `struct icmphdr`)
- **Windows Alternative**: `IcmpCreateFile()`, `IcmpSendEcho()` (complex API)
- **Complexity**: High (8-10 hours)

❌ **Level 8: Process Hollowing Reverse Shell**
- **Reason**: Uses `ptrace()` for process injection (Linux-specific)
- **Windows Alternative**: `CreateProcess()` + `WriteProcessMemory()` + `ResumeThread()`
- **Complexity**: High (10-12 hours)

❌ **Level 9: Shared Object Injection**
- **Reason**: Skipped for MVP (DLL injection adds complexity, low educational value)
- **Windows Alternative**: Build as `.dll` with `LoadLibrary()` + `GetProcAddress()`
- **Complexity**: Medium (6-8 hours)

❌ **Level 10: AES Encrypted Shell**
- **Reason**: Memory allocation differences
- **Windows Alternative**: `VirtualAlloc()` instead of `mmap()` for RWX memory
- **Complexity**: Medium (5-6 hours)

❌ **Level 12: JIT Compiled Shellcode**
- **Reason**: Memory protection differences
- **Windows Alternative**: `VirtualAlloc()` + `VirtualProtect()` for executable memory
- **Complexity**: Medium (5-6 hours)

❌ **Level 13: Metamorphic Dropper**
- **Reason**: Heavy `ptrace()` + syscall usage (Linux-specific)
- **Windows Alternative**: `IsDebuggerPresent()` + `VirtualProtect()` + `CreateProcess()`
- **Complexity**: Very High (12-15 hours)

## Ground Truth Modifications for Windows

### Changed Fields

1. **`file_type`**: `"ELF64"` → `"PE32+"`
2. **`shell_path`**: `"/bin/sh"` → `"C:\\Windows\\System32\\cmd.exe"`
3. **`techniques`**: Updated API names
   - `"socket_connect"` → `"winsock2_socket"`
   - `"dup2_redirect"` → `"handle_redirect"`
   - `"execve_shell"` → `"createprocess_spawn"` + `"cmd_shell"`
   - `"fork_exec"` → `"createprocess_recursive"`
   - `"popen"` → `"_popen"`

### Unchanged Fields

- `decoded_c2`, `c2_ip`, `c2_port` - Same C2 infrastructure
- `c2_protocol` - Same protocols (TCP, DNS)
- `encoded_strings`, `encryption_key` - Same encoding schemes
- `difficulty` - Same difficulty ratings

## Testing Strategy

### Build Verification (Automated)

```bash
# Build all MVP samples
cargo run --bin build_binaries_windows

# Check PE format
file binaries_windows/*.exe
# Expected: "PE32+ executable (console) x86-64, for MS Windows"

# Verify MZ header
xxd binaries_windows/level1_TCPServer.exe | head -1
# Expected: 00000000: 4d5a 9000 ... (MZ magic bytes)

# Check file sizes
du -h binaries_windows/
# Expected: 50KB - 500KB per binary
```

### Functional Testing (Optional - Requires Windows VM)

```powershell
# On Windows 10/11:
# 1. Copy binaries to Windows VM
# 2. Run each binary (won't connect to C2, but shouldn't crash)
.\level1_TCPServer.exe

# 3. Use Windows RE tools
strings64.exe .\level1_TCPServer.exe | Select-String "192.168"
certutil -hashfile .\level1_TCPServer.exe SHA256
```

### Benchmark Integration Testing

```bash
# Run single task
python run_benchmark.py --task level1_TCPServer_windows -v

# Verify pefile tool works
# Should see PE header analysis in output
cat results/transcripts/level1_TCPServer_windows.json | \
  jq '.messages[] | select(.tool_name == "pefile")'
```

## Future Expansion Roadmap

### Phase 2: Tier 2 Samples (Medium Complexity)

**Estimated effort: 2-3 weeks**
- Level 5: Multistage reverse shell (WinSock2 + HTTP staging)
- Level 9: DLL injection (build as .dll with LoadLibrary/GetProcAddress)
- Level 10: AES encrypted shell (VirtualAlloc for RWX memory)
- Level 12: JIT compiled shellcode (VirtualAlloc + VirtualProtect)

### Phase 3: Tier 3 Samples (High Complexity)

**Estimated effort: 3-4 weeks**
- Level 3: Anti-debugging (IsDebuggerPresent, CheckRemoteDebuggerPresent)
- Level 6: ICMP covert channel (IcmpCreateFile, IcmpSendEcho)
- Level 8: Process hollowing (CreateProcess + WriteProcessMemory + ResumeThread)
- Level 13: Metamorphic dropper (process injection + code morphing)

### Phase 4: CLI Enhancements

**Estimated effort: 1 week**
- `--platform` flag in `run_benchmark.py` for automatic task filtering
- Multi-platform benchmark runs (compare agent performance across OSes)
- Automated ground truth generation script
- Parallel platform builds (ELF + PE + MACH-O)

### Phase 5: CI/CD Integration

**Estimated effort: 1 week**
- GitHub Actions workflow with MinGW cross-compilation
- Automated Windows VM testing (Wine on Linux or Windows runner)
- PE binary comparison tools (deterministic build verification)
- Binary artifact publishing for releases

## Common Issues and Solutions

### Issue: `WSAStartup` not found
**Cause**: Missing `-lws2_32` linker flag
**Solution**: Add `-lws2_32` to compilation command

### Issue: Binary crashes immediately on Windows
**Cause**: Static linking might fail, or handle inheritance issues
**Solution**: Check `STARTUPINFO.dwFlags` includes `STARTF_USESTDHANDLES` and `TRUE` for `bInheritHandles`

### Issue: Docker image not found
**Cause**: Docker image not built
**Solution**: Run `docker build --platform linux/amd64 -t agentre-bench-mingw:latest -f Dockerfile.mingw .`

### Issue: MinGW not detected
**Cause**: `x86_64-w64-mingw32-gcc` not in PATH
**Solution**: Install MinGW-w64:
- Ubuntu/Debian: `sudo apt install mingw-w64`
- macOS: `brew install mingw-w64`
- Or use `--docker-only` flag to force Docker mode

### Issue: PE format validation fails
**Cause**: Compilation produced invalid PE file
**Solution**: Check stderr output for linker errors, ensure all libraries linked correctly

## Resources

### Windows API Documentation
- [WinSock2 Reference](https://learn.microsoft.com/en-us/windows/win32/api/winsock2/)
- [Process and Thread Functions](https://learn.microsoft.com/en-us/windows/win32/procthread/process-and-thread-functions)
- [CreateProcess Function](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessa)

### PE Format Documentation
- [PE Format Specification (Microsoft)](https://learn.microsoft.com/en-us/windows/win32/debug/pe-format)
- [pefile Python Library](https://github.com/erocarrera/pefile)

### MinGW-w64 Resources
- [MinGW-w64 Official](https://www.mingw-w64.org/)
- [Cross-Compilation Guide](https://fedoraproject.org/wiki/MinGW/CrossCompilerFramework)

## Contributors

Initial Windows port developed for AgentRE-Bench MVP (5 samples).
See [CLAUDE.md](CLAUDE.md) for project overview and [README.md](README.md) for usage instructions.
