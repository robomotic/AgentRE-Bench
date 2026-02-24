#!/usr/bin/env bash
#
# build_binaries_macho.sh — Compile all 13 C samples to MACH-O x86_64 binaries.
#
# Requires: macOS with native Clang/GCC toolchain
# Output: binaries_macho/ directory with 13 MACH-O executables
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SAMPLES_DIR="$SCRIPT_DIR/samples"
BINARIES_DIR="$SCRIPT_DIR/binaries_macho"

# Common compilation flags for MACH-O
# Note: macOS doesn't support -z execstack or -no-pie in the same way
# -fno-stack-protector: disable stack canaries
# -O0: no optimization
# -Wl,-no_pie: disable PIE (position independent executable)
CFLAGS="-O0 -fno-stack-protector -arch x86_64"

mkdir -p "$BINARIES_DIR"

# Check for macOS and compiler
if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "Error: This script requires macOS to build MACH-O binaries."
    echo "Current OS: $(uname -s)"
    exit 1
fi

if ! command -v clang &>/dev/null && ! command -v gcc &>/dev/null; then
    echo "Error: No compiler found (clang or gcc required)."
    echo "Install Xcode Command Line Tools: xcode-select --install"
    exit 1
fi

# Prefer clang on macOS
COMPILER="clang"
if ! command -v clang &>/dev/null; then
    COMPILER="gcc"
fi

echo "=== AgentRE-Bench: Building MACH-O x86_64 binaries ==="
echo "Samples dir:  $SAMPLES_DIR"
echo "Output dir:   $BINARIES_DIR"
echo "Compiler:     $COMPILER ($($COMPILER --version | head -1))"
echo ""

# Function to map source filename to output binary name
map_filename() {
    case "$1" in
        "level1_TCPServer") echo "level1_TCPServer" ;;
        "level2_XorEncodedStrings") echo "level2_XorEncodedStrings" ;;
        "level3_anti-debugging_reverseShell") echo "level3_anti-debugging_reverseShell" ;;
        "level4_polymorphicReverseShell") echo "level4_polymorphicReverseShell" ;;
        "level5_MultistageReverseShell") echo "level5_MultistageReverseShell" ;;
        "level6_ICMP Covert Channel Shell") echo "level6_ICMP_CovertChannelShell" ;;
        "level7_DNS_TunnelReverse Shell") echo "level7_DNS_TunnelReverseShell" ;;
        "level8_Process_hollowing_reverse_shell") echo "level8_Process_hollowing_reverse_shell" ;;
        "level9_SharedObjectInjectionReverseShell") echo "level9_SharedObjectInjectionReverseShell" ;;
        "level10_fully_obfuscated_AES_Encrypted Shell") echo "level10_fully_obfuscated_AES_Encrypted_Shell" ;;
        "level11_ForkBombReverseShell") echo "level11_ForkBombReverseShell" ;;
        "level12_JIT_Compiled_Shellcode") echo "level12_JIT_Compiled_Shellcode" ;;
        "level13_MetamorphicDropper") echo "level13_MetamorphicDropper" ;;
        *) echo "$1" ;;
    esac
}

SUCCESS=0
FAIL=0

for SRC in "$SAMPLES_DIR"/*.c; do
    # Extract base name without extension
    BASENAME="$(basename "$SRC" .c)"
    OUTNAME="$(map_filename "$BASENAME")"

    echo -n "Building $OUTNAME ... "

    # Level 9 is a shared object (dylib on macOS)
    EXTRA_FLAGS=""
    BUILD_CFLAGS="$CFLAGS"
    OUTPUT_PATH="$BINARIES_DIR/$OUTNAME"

    if [[ "$BASENAME" == *"level9"* ]]; then
        # macOS shared library flags
        EXTRA_FLAGS="-dynamiclib -undefined dynamic_lookup"
        OUTPUT_PATH="$BINARIES_DIR/$OUTNAME.dylib"
    fi

    if $COMPILER $BUILD_CFLAGS $EXTRA_FLAGS -o "$OUTPUT_PATH" "$SRC" -lm 2>&1; then
        echo "OK"
        SUCCESS=$((SUCCESS + 1))
    else
        echo "FAILED"
        FAIL=$((FAIL + 1))
    fi
done

echo ""
echo "=== Build complete: $SUCCESS succeeded, $FAIL failed ==="
echo "Binaries in: $BINARIES_DIR"

# Verify MACH-O format
echo ""
echo "=== Verifying MACH-O format ==="
for BIN in "$BINARIES_DIR"/*; do
    if [ -f "$BIN" ]; then
        FILETYPE=$(file "$BIN" | cut -d: -f2)
        echo "$(basename "$BIN"): $FILETYPE"
    fi
done

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
