# Makefile for hadi_LZ_package C backend

# Compiler: Default to clang, user can override (e.g., make CC=gcc)
CC = clang

# CFLAGS: -fPIC for shared libraries, -O2 for optimization.
# Add -Wall for more warnings. Add -g for debugging symbols if needed.
CFLAGS = -fPIC -O2 -Wall

# LDFLAGS: -shared for creating shared libraries
LDFLAGS = -shared

# Shared library extension (specific to macOS here)
SHARED_LIB_EXT = .dylib

# Target directory for built libraries (current directory)
TARGET_DIR = .

# --- OpenMP settings for clang on macOS ---
# Assumes libomp installed via Homebrew.
# Verify paths with: brew info libomp
# If these paths are incorrect or libomp is not installed, compilation of lz_exhaustive will fail.
OMP_INCLUDE_DIR = /opt/homebrew/opt/libomp/include
OMP_LIB_DIR = /opt/homebrew/opt/libomp/lib

# OpenMP compiler and linker flags for clang.
# For GCC, OMP_CFLAGS and OMP_LDFLAGS might simply be -fopenmp.
OMP_CFLAGS = -Xpreprocessor -fopenmp
OMP_LDFLAGS = -lomp

# Check if OMP directories exist and add flags conditionally
# This requires GNU Make specific features for 'wildcard' and 'if'.
# For simplicity, we'll include them and user can comment out or fix if libomp is not at these paths.
# A more robust solution would involve configure scripts or CMake.
CFLAGS_OMP_INC = $(if $(wildcard $(OMP_INCLUDE_DIR)/omp.h),-I$(OMP_INCLUDE_DIR))
LDFLAGS_OMP_LIB = $(if $(wildcard $(OMP_LIB_DIR)/libomp$(SHARED_LIB_EXT)),-L$(OMP_LIB_DIR))


# --- Default Target: Build all libraries ---
all: $(TARGET_DIR)/liblzcore$(SHARED_LIB_EXT) \
     $(TARGET_DIR)/online_suffix$(SHARED_LIB_EXT) \
     $(TARGET_DIR)/lz_suffix_combined$(SHARED_LIB_EXT) \
     $(TARGET_DIR)/lz_exhaustive$(SHARED_LIB_EXT)

# --- Individual Library Build Rules ---

# liblzcore: from lz_core.c
$(TARGET_DIR)/liblzcore$(SHARED_LIB_EXT): lz_core.c lz_core.h
	$(CC) $(CFLAGS) $(OMP_CFLAGS) -I$(OMP_INCLUDE_DIR) $(LDFLAGS) -L$(OMP_LIB_DIR) $(OMP_LDFLAGS) -o $@ lz_core.c
	@echo "Built $@"

# online_suffix: from online_suffix.c
$(TARGET_DIR)/online_suffix$(SHARED_LIB_EXT): online_suffix.c online_suffix.h
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ online_suffix.c
	@echo "Built $@"

# lz_suffix_combined: from lz_suffix.c and online_suffix.c
$(TARGET_DIR)/lz_suffix_combined$(SHARED_LIB_EXT): lz_suffix.c lz_suffix.h online_suffix.c online_suffix.h
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ lz_suffix.c online_suffix.c
	@echo "Built $@"

# lz_exhaustive: from lz_exhaustive.c (requires OpenMP)
$(TARGET_DIR)/lz_exhaustive$(SHARED_LIB_EXT): lz_exhaustive.c lz_exhaustive.h
	$(CC) $(CFLAGS) $(OMP_CFLAGS) -I$(OMP_INCLUDE_DIR) $(LDFLAGS) -L$(OMP_LIB_DIR) $(OMP_LDFLAGS) -o $@ lz_exhaustive.c
	@echo "Built $@"

# --- Clean Target ---
clean:
	@echo "Cleaning build artifacts in $(TARGET_DIR)..."
	rm -f $(TARGET_DIR)/*$(SHARED_LIB_EXT) $(TARGET_DIR)/*.o
	@echo "Clean complete."

# Phony targets (targets that are not actual files)
.PHONY: all clean