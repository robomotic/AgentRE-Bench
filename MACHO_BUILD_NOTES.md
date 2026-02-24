# MACH-O Build Notes

## Overview

The `build_binaries_macho.sh` script compiles the AgentRE-Bench samples as MACH-O x86_64 binaries for macOS analysis. However, **only 9 out of 13 samples** can be successfully compiled as MACH-O due to Linux-specific system calls and kernel structures.

## Build Status

### ✅ Successfully Compiled (9/13)

These samples use portable C APIs and compile cleanly on macOS:

1. **level1_TCPServer** - Basic TCP socket server
2. **level2_XorEncodedStrings** - XOR-encoded string obfuscation
3. **level4_polymorphicReverseShell** - Self-mutating shellcode
4. **level5_MultistageReverseShell** - Multi-stage payload loader
5. **level7_DNS_TunnelReverseShell** - DNS tunneling exfiltration
6. **level9_SharedObjectInjectionReverseShell** - Dynamic library injection (compiled as `.dylib`)
7. **level10_fully_obfuscated_AES_Encrypted_Shell** - AES-encrypted C2 traffic
8. **level11_ForkBombReverseShell** - Fork bomb DoS technique
9. **level12_JIT_Compiled_Shellcode** - Runtime code generation

### ❌ Failed to Compile (4/13)

These samples use Linux-specific kernel APIs that have no macOS equivalent:

#### level3_anti-debugging_reverseShell
- **Issue**: Uses `PTRACE_TRACEME` constant
- **Why**: macOS ptrace uses different constants (`PT_TRACE_ME`, `PT_DENY_ATTACH`)
- **Impact**: Anti-debugging checks would need macOS-specific rewrite

#### level6_ICMP_CovertChannelShell
- **Issue**: Uses `struct iphdr` and `struct icmphdr` from `<netinet/ip.h>` and `<netinet/ip_icmp.h>`
- **Why**: macOS networking headers use different structures (`struct ip`, `struct icmp`)
- **Impact**: Raw ICMP packet crafting requires platform-specific code

#### level8_Process_hollowing_reverse_shell
- **Issue**: Uses `struct user_regs_struct` and ptrace constants (`PTRACE_GETREGS`, `PTRACE_SETREGS`, `PTRACE_POKETEXT`)
- **Why**: macOS does not expose register manipulation via ptrace; uses Mach APIs instead
- **Impact**: Process hollowing requires completely different implementation on macOS

#### level13_MetamorphicDropper (Bonus Level)
- **Issue**: Uses `PTRACE_TRACEME`, `PTRACE_DETACH`, and deprecated `syscall()` with `SYS_openat`, `SYS_write`, `SYS_close`
- **Why**: macOS deprecated `syscall()` in 10.12 and uses different ptrace constants
- **Impact**: Complex anti-analysis requires macOS-specific syscall and tracing APIs

## Platform Differences Summary

| API Category | Linux | macOS |
|--------------|-------|-------|
| Process tracing | `ptrace()` with `PTRACE_*` constants | `ptrace()` with `PT_*` constants, or Mach task APIs |
| Register access | `struct user_regs_struct` | Mach thread state APIs (`thread_get_state`) |
| Raw IP headers | `struct iphdr` | `struct ip` |
| Raw ICMP headers | `struct icmphdr` | `struct icmp` |
| Direct syscalls | `syscall(SYS_*)` supported | Deprecated in 10.12+, use libc wrappers |

## Usage

### Building MACH-O Binaries

```bash
# Make script executable
chmod +x build_binaries_macho.sh

# Build all compatible samples
./build_binaries_macho.sh
```

Output: `binaries_macho/` directory with 9 MACH-O executables + 1 `.dylib`

### Analyzing MACH-O Binaries

Use macOS-native analysis tools:

```bash
# File type identification
file binaries_macho/level1_TCPServer

# Display Mach-O headers
otool -h binaries_macho/level1_TCPServer

# Disassemble code
otool -tV binaries_macho/level1_TCPServer

# List symbols
nm -a binaries_macho/level1_TCPServer

# Display load commands and segments
otool -l binaries_macho/level1_TCPServer

# Extract strings
strings binaries_macho/level1_TCPServer

# Hex dump
xxd binaries_macho/level1_TCPServer | head -n 20
```

## Tool Equivalents: ELF vs MACH-O

| Task | Linux (ELF) | macOS (MACH-O) |
|------|-------------|----------------|
| Display headers | `readelf -h` | `otool -h` |
| List sections | `readelf -S` | `otool -l` (segments/sections) |
| Show symbols | `readelf -s` or `nm` | `nm -a` |
| Disassemble | `objdump -d` | `otool -tV` |
| Show imports | `readelf -d` | `otool -L` |
| Hex dump | `xxd`, `hexdump` | `xxd`, `hexdump` (same) |
| Extract strings | `strings` | `strings` (same) |

## Limitations for Benchmark Use

1. **Incomplete coverage**: Only 69% (9/13) of samples compile
2. **Missing bonus level**: Level 13 (bonus level worth 1.0 pt) cannot be compiled
3. **Scoring impact**: Maximum achievable score on MACH-O binaries is ~0.69 pts (levels 1-12) instead of 2.0 pts
4. **Tool sandboxing**: The Docker-based tool sandboxing in `harness/sandbox.py` is designed for ELF binaries - MACH-O analysis would need `--no-docker` mode with native macOS tools

## Recommendations

### For MACH-O Analysis Practice
Use the 9 successfully compiled binaries to practice macOS reverse engineering with native tools (`otool`, `nm`, `codesign`, `class-dump`, etc.)

### For Full Benchmark Evaluation
Use the original ELF binaries on Linux/x86-64, as they represent the complete benchmark with all 13 tasks and platform-agnostic scoring.

### For Cross-Platform Support
The 4 failed samples would require:
- Complete rewrites of platform-specific code (anti-debugging, process injection, raw networking)
- This violates the "no improvements to malware" guideline
- Better approach: Create separate MACH-O-native samples with equivalent techniques

## Future Enhancements

To achieve full MACH-O support:

1. **Create macOS-native variants** of levels 3, 6, 8, 13 using:
   - Mach task APIs instead of ptrace for process manipulation
   - BSD socket APIs with proper macOS network structures
   - Modern macOS syscall interfaces (not deprecated `syscall()`)

2. **Update tool schemas** in `harness/tools.py`:
   - Add `otool`, `nm`, `codesign` tool definitions
   - Map ELF analysis tasks to MACH-O equivalents
   - Support both formats in `ToolExecutor`

3. **Extend sandbox** in `harness/sandbox.py`:
   - Add MACH-O binary detection
   - Route to native macOS tools when `--no-docker` is used
   - Maintain same security isolation principles

## Notes

- All successfully compiled binaries are **64-bit x86_64 MACH-O executables**
- Level 9 outputs a `.dylib` (macOS shared library) instead of `.so`
- Compiled with Clang on macOS with `-O0 -fno-stack-protector -arch x86_64`
- Binaries are **not stripped** (symbols retained for analysis practice)
