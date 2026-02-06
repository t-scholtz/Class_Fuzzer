# Compiler and flags
CLANG   = clang-17
CFLAGS  = -g -fsanitize-coverage=trace-pc-guard
LDFLAGS =

# Build artifacts
BUILD   = build
TARGET  = sut

# Sources
HARNESS_SRC = $(BUILD)/harness.c
SUT_SRC     = $(BUILD)/target.c

# Objects
HARNESS_OBJ = $(BUILD)/harness.o
SUT_OBJ     = $(BUILD)/target.o

# Default target
all: $(TARGET)

# Final binary
$(TARGET): $(HARNESS_OBJ) $(SUT_OBJ)
	$(CLANG) $(HARNESS_OBJ) $(SUT_OBJ) -o $(TARGET) $(LDFLAGS)

# Compile harness
$(HARNESS_OBJ): $(HARNESS_SRC)
	$(CLANG) $(CFLAGS) -c $< -o $@

# Compile SUT
$(SUT_OBJ): $(SUT_SRC)
	$(CLANG) $(CFLAGS) -c $< -o $@

# Clean up
clean:
	rm -f $(TARGET) $(BUILD)/*.o *.bin
