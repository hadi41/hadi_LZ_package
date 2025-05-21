# Makefile for hadi_LZ_package C backend

# --- Compiler and Flags Configuration ---

# Compiler: Default to clang. User can override by calling make with CC=gcc, for example.
CC = clang

# CFLAGS: Standard C compiler flags.
# -fPIC: Generate Position Independent Code, necessary for shared libraries.
# -O2: Level 2 optimization.
# -Wall: Enable all warnings (recommended for development).
# Consider adding -g for debugging symbols if needed: CFLAGS = -fPIC -O2 -Wall -g
CFLAGS = -fPIC -O2 -Wall

# LDFLAGS: Linker flags.
# -shared: Create a shared library.
LDFLAGS = -shared

# SHARED_LIB_EXT: Extension for shared libraries. This is specific to the OS.
# .dylib for macOS, .so for Linux.
SHARED_LIB_EXT = .dylib # macOS specific
# SHARED_LIB_EXT = .so # Linux specific - uncomment and adjust if needed

# TARGET_DIR: Directory where the compiled shared libraries will be placed.
TARGET_DIR = . # Current directory

# --- OpenMP Configuration (for clang on macOS with libomp from Homebrew) ---
# OpenMP is used for parallelizing lz_core and lz_exhaustive.
# These paths assume libomp is installed via Homebrew at the default location for arm64 macOS.
# For Intel macOS or different libomp installations, these paths might need adjustment.
# To check your libomp installation paths (if installed via Homebrew): `brew info libomp`
OMP_BASE_DIR = /opt/homebrew/opt/libomp # Common base for Homebrew on ARM macOS
# OMP_BASE_DIR = /usr/local/opt/libomp # Common base for Homebrew on Intel macOS - uncomment if needed

OMP_INCLUDE_DIR = $(OMP_BASE_DIR)/include
OMP_LIB_DIR = $(OMP_BASE_DIR)/lib

# OpenMP compiler and linker flags for clang.
# For GCC, these are typically just -fopenmp for both CFLAGS and LDFLAGS.
OMP_CFLAGS_CLANG = -Xpreprocessor -fopenmp # Tells clang preprocessor to enable OpenMP
OMP_LDFLAGS_CLANG = -lomp                   # Links against the OpenMP library (libomp)

# Select OpenMP flags based on compiler (basic check for clang vs gcc)
ifeq ($(CC),gcc)
    OMP_CFLAGS = -fopenmp
    OMP_LDFLAGS = -fopenmp
    # For GCC, OMP_INCLUDE_DIR and OMP_LIB_DIR might not be needed if OpenMP is built-in.
    # If using a specific GCC libgomp, adjust paths similar to libomp if necessary.
else
    # Default to clang style OpenMP flags
    OMP_CFLAGS = $(OMP_CFLAGS_CLANG) -I$(OMP_INCLUDE_DIR)
    OMP_LDFLAGS = -L$(OMP_LIB_DIR) $(OMP_LDFLAGS_CLANG)
endif

# --- Targets ---

# Default Target: `make` or `make all` will build all specified shared libraries.
# The order can matter if one library depends on another, though here they are mostly independent C source compilations.
all: $(TARGET_DIR)/liblzcore$(SHARED_LIB_EXT) \
     $(TARGET_DIR)/online_suffix$(SHARED_LIB_EXT) \
     $(TARGET_DIR)/lz_suffix_combined$(SHARED_LIB_EXT) \
     $(TARGET_DIR)/lz_exhaustive$(SHARED_LIB_EXT)

# --- Individual Library Build Rules ---
# Each rule specifies how to build a target shared library from its source files.
# $< refers to the first prerequisite (the .c file).
# $@ refers to the target file name.

# liblzcore: Core LZ76, LZ78, Block Entropy. Uses OpenMP.
$(TARGET_DIR)/liblzcore$(SHARED_LIB_EXT): lz_core.c lz_core.h
	$(CC) $(CFLAGS) $(OMP_CFLAGS) $(LDFLAGS) -o $@ lz_core.c $(OMP_LDFLAGS)
	@echo "Built $@"

# online_suffix: Suffix tree implementation (Ukkonen's algorithm). Does not use OpenMP itself.
$(TARGET_DIR)/online_suffix$(SHARED_LIB_EXT): online_suffix.c online_suffix.h
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ online_suffix.c
	@echo "Built $@"

# lz_suffix_combined: LZ76 implementation using suffix trees. Links online_suffix.c sources.
# This creates a single shared library from lz_suffix.c and online_suffix.c.
$(TARGET_DIR)/lz_suffix_combined$(SHARED_LIB_EXT): lz_suffix.c lz_suffix.h online_suffix.c online_suffix.h
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ lz_suffix.c online_suffix.c
	@echo "Built $@"

# lz_exhaustive: Exhaustive LZ76 calculation for all binary strings. Uses OpenMP.
$(TARGET_DIR)/lz_exhaustive$(SHARED_LIB_EXT): lz_exhaustive.c lz_exhaustive.h
	$(CC) $(CFLAGS) $(OMP_CFLAGS) $(LDFLAGS) -o $@ lz_exhaustive.c $(OMP_LDFLAGS)
	@echo "Built $@"

# --- Clean Target ---
# `make clean` removes compiled libraries and object files from TARGET_DIR.
clean:
	@echo "Cleaning build artifacts in $(TARGET_DIR)..."
	rm -f $(TARGET_DIR)/*$(SHARED_LIB_EXT) $(TARGET_DIR)/*.o
	@echo "Clean complete."

# --- Phony Targets ---
# .PHONY declares targets that are not actual files. `all` and `clean` are common examples.
# This prevents make from getting confused if a file named 'all' or 'clean' exists.
.PHONY: all clean