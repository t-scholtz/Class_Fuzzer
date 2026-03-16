#!/bin/bash
# build.sh — compile harness + forkserver and build instrumented pdftotext
set -e  # exit on any error

CLANG=/usr/bin/clang
CLANGPP=/usr/bin/clang++
OBJ8_DIR=$(pwd)
HARNESS_O="$OBJ8_DIR/harness/harness.o"
FORKSERVER_O="$OBJ8_DIR/harness/forkserver.o"
BUILD_DIR="$OBJ8_DIR/xpdf-4.06/build"

echo "[*] Step 1: Compiling harness..."
$CLANGPP -g \
  -fsanitize-coverage=inline-8bit-counters \
  -c harness/harness.cpp \
  -o harness/harness.o
echo "[+] harness.o built"

echo "[*] Step 2: Compiling forkserver..."
$CLANGPP -g \
  -fsanitize-coverage=inline-8bit-counters \
  -c harness/forkserver.cpp \
  -o harness/forkserver.o
echo "[+] forkserver.o built"

echo "[*] Step 3: Configuring xpdf with cmake..."
mkdir -p "$BUILD_DIR" && cd "$BUILD_DIR"
cmake -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=$CLANG \
  -DCMAKE_CXX_COMPILER=$CLANGPP \
  -DCMAKE_C_FLAGS="-fsanitize-coverage=inline-8bit-counters -Dmain=targetMain $HARNESS_O $FORKSERVER_O" \
  -DCMAKE_CXX_FLAGS="-fsanitize-coverage=inline-8bit-counters -Dmain=targetMain $HARNESS_O $FORKSERVER_O" \
  -DCMAKE_C_COMPILER_WORKS=1 \
  -DCMAKE_CXX_COMPILER_WORKS=1 \
  ../
echo "[+] cmake configured"

echo "[*] Step 4: Building xpdf..."
make -j$(nproc)
echo "[+] Build complete"

echo ""
echo "[*] Verifying instrumentation..."
BINARY="$BUILD_DIR/xpdf/pdftotext"
if [ ! -f "$BINARY" ]; then
  echo "[-] ERROR: pdftotext not found at $BINARY"
  exit 1
fi

COV_COUNT=$(objdump -D "$BINARY" | grep -c "sanitizer_cov" || true)
echo "[+] Found $COV_COUNT sanitizer_cov references in binary"

echo ""
echo "[+] All done. Binary at: $BINARY"