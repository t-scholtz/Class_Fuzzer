# Step 1: compile the harness into an object file
clang++ -c harness/harness.cpp -o harness/harness.o

# Step 2: configure xpdf, passing harness.o to the linker via FLAGS
mkdir -p xpdf-4.06/build && cd xpdf-4.06/build && \
cmake -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER=clang \
  -DCMAKE_CXX_COMPILER=clang++ \
  -DCMAKE_C_FLAGS="-fsanitize-coverage=inline-8bit-counters $(pwd)/../../harness/harness.o" \
  -DCMAKE_CXX_FLAGS="-fsanitize-coverage=inline-8bit-counters $(pwd)/../../harness/harness.o" \
  ../

# Step 3: build
make -j$(nproc)