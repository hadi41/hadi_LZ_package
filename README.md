# hadi_LZ_package: Lempel-Ziv Complexity and Entropy Measures

`hadi_LZ_package` is a Python package with a C backend for efficiently computing Lempel-Ziv (LZ) complexity measures (LZ76, LZ78), block entropy, and related information-theoretic quantities for strings. It offers both performant C-backed computations for batches of strings and pure Python implementations for reference and flexibility.

## Features

*   **LZ76 Complexity**: 
    *   Standard LZ76 complexity.
    *   Symmetric LZ76 complexity.
    *   Conditional LZ76 complexity (approximated as K(Y|X) ~ K(XY) - K(X)).
    *   C-backed parallel processing for batches of strings via `LZProcessor`.
    *   Pure Python implementation using an online suffix tree (`python_backend.LZSuffixTree`).
    *   Exhaustive LZ76 calculations for all binary strings of a given length `L` via `LZExhaustiveCalculator` (C-backed, uses OpenMP).
*   **LZ78 Complexity**:
    *   Standard LZ78 complexity.
    *   Symmetric LZ78 complexity.
    *   Conditional LZ78 complexity (approximated as K(Y|X) ~ K(XY) - K(X)).
    *   C-backed parallel processing for batches of strings via `LZProcessor`.
    *   Pure Python implementation (`python_backend.lz_inefficient.LZ78`).
*   **Block Entropy**:
    *   Standard block entropy.
    *   Symmetric block entropy.
    *   C-backed parallel processing for batches of strings via `EntropyProcessor`.
    *   Pure Python implementation (`python_backend.lz_inefficient.block_entropy`).
*   **Online Suffix Tree Implementations**:
    *   C-backed online suffix tree (`online_suffix_wrapper.OnlineSuffixTreeWrapper`).
    *   Pure Python online suffix tree (`python_backend.online_suffix.OnlineSuffixTree`).
    *   Not recommended over the default LZ76 complexity calculator except for really really long strings, containing thousands or tens of thousands of characters. Theoretically, the suffix tree approach should be better (has linear asymptotic complexity). But in practice, the simple implementation wins out for all the lengths we've tested. 
*   **Efficiency**: The C backend uses OpenMP for parallelization of batch processing tasks, significantly speeding up computations for large datasets.

## Installation

### Prerequisites

*   Python 3.x
*   A C compiler (e.g., `clang` or `gcc`) that supports OpenMP.
*   `make` utility for building the C backend.
*   (macOS with clang) `libomp` for OpenMP support. Install via Homebrew: `brew install libomp`.

### Steps

1.  **Clone the repository (if applicable)**:
    ```bash
    git clone <repository_url>
    cd hadi_LZ_package
    ```

2.  **Build the C Backend**:
    Navigate to the C code directory and compile the shared libraries using the provided Makefile:
    ```bash
    cd hadi_LZ_package/c_backend/
    make
    ```
    This will compile the necessary `.dylib` (macOS) or `.so` (Linux) files (e.g., `liblzcore.dylib`, `online_suffix.dylib`, `lz_suffix_combined.dylib`, `lz_exhaustive.dylib`) and place them in the `hadi_LZ_package/hadi_LZ_package/c_backend/` directory. These compiled libraries are then used by the Python wrappers.

    *   **C Standard**: The C code targets a modern C standard (e.g., C99 or later) and relies on the default standard supported by your compiler (Clang or GCC).
    *   **Compiler**: The `Makefile` defaults to using `clang` as the compiler. If you wish to use `gcc` or another compiler, you can specify it when running make: `make CC=gcc`.
    *   **OpenMP**: For parallelized functionalities, OpenMP is used. 
        *   On macOS with `clang`, `libomp` (installable via `brew install libomp`) is expected. The `Makefile` includes paths for Homebrew's `libomp` installation (defaulting to `/opt/homebrew/opt/libomp` for ARM macOS; adjust `OMP_BASE_DIR` in the Makefile if your path differs, e.g., for Intel macOS).
        *   With `gcc`, OpenMP support is usually enabled with the `-fopenmp` flag, which the Makefile attempts to use if `CC=gcc`.
    *   **Customization**: For more advanced compiler flag customizations or if you encounter build issues, please see the comments and variable definitions at the top of the `hadi_LZ_package/c_backend/Makefile`.

3.  **Install Python Dependencies**:
    Install `numpy` using pip. It's recommended to use a virtual environment.
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    pip install -r requirements.txt 
    ```
    The `requirements.txt` file primarily contains:
    ```
    numpy>=1.20.0
    ```

4.  **(Optional) For Suffix Tree Visualization**: 
    If you wish to use the `display_graphviz()` methods in the Python suffix tree implementations, install the `graphviz` Python library and ensure Graphviz executables are installed on your system:
    ```bash
    pip install graphviz
    # System-wide Graphviz installation (e.g., on macOS: brew install graphviz)
    ```

5.  **Install the package**: 
    From the root directory of the `hadi_LZ_package` (where `setup.py` is located):
    ```bash
    pip install .
    ```
    Or, for development mode:
    ```bash
    pip install -e .
    ```

## Usage

Here are some basic usage examples. It's generally recommended to process strings in batches for better performance due to the Python-C interface overhead.

### LZ Complexity (LZ76/LZ78) using `LZProcessor`

```python
from hadi_LZ_package import LZProcessor

strings_to_process = ["0101010101", "ababababab", "000111000111"]

# Initialize the processor (n_threads defaults to os.cpu_count())
# You can specify the number of threads, e.g., LZProcessor(n_threads=4)
lz_proc = LZProcessor()

# Calculate LZ76 complexities (default)
results_lz76 = lz_proc.process_strings(strings_to_process, algorithm='lz76', symmetric=False)
print("LZ76 Results:", results_lz76)

# Calculate symmetric LZ78 complexities
results_sym_lz78 = lz_proc.process_strings(strings_to_process, algorithm='lz78', symmetric=True)
print("Symmetric LZ78 Results:", results_sym_lz78)

# Calculate conditional LZ76 K(Y|X)
x_strings = ["000", "111"]
y_strings = ["000111", "111000"]
cond_results_lz76 = lz_proc.process_conditional(x_strings, y_strings, algorithm='lz76')
print("Conditional LZ76 K(Y|X) Results:", cond_results_lz76)
```

### Block Entropy using `EntropyProcessor`

```python
from hadi_LZ_package import EntropyProcessor

strings_to_process = ["01010101010100001111", "ababababccabababcc"]

# Initialize the processor
entropy_proc = EntropyProcessor()

# Calculate block entropy with block_size = 2
results_be = entropy_proc.process_strings(strings_to_process, block_size=2, symmetric=False)
print("Block Entropy (block_size=2) Results:", results_be)

# Calculate symmetric block entropy with block_size = 3
results_sym_be = entropy_proc.process_strings(strings_to_process, block_size=3, symmetric=True)
print("Symmetric Block Entropy (block_size=3) Results:", results_sym_be)
```

### LZ76 using Suffix Tree Wrapper (Online or Batch)

```python
from hadi_LZ_package import LZSuffixTreeWrapper

# Online processing (character by character)
lz_st_online = LZSuffixTreeWrapper()
lz_st_online.add_character('b')
lz_st_online.add_character('a')
lz_st_online.add_character('n')
lz_st_online.add_character('a')
lz_st_online.add_character('n')
lz_st_online.add_character('a')
complexity_online = lz_st_online.compute_lz76_complexity()
print(f"LZ76 complexity for 'banana' (online): {complexity_online}")
print(f"Dictionary: {lz_st_online.return_dictionary()}")

# Batch processing
lz_st_batch = LZSuffixTreeWrapper() # Can reuse or create new
strings_for_batch = ["00110011", "10101010"]
batch_complexities = lz_st_batch.compute_lz76_complexity_batch(strings_for_batch)
print(f"LZ76 complexities for batch: {batch_complexities}")
```

### Exhaustive LZ76 Calculations for Binary Strings

```python
from hadi_LZ_package import LZExhaustiveCalculator

calculator = LZExhaustiveCalculator()

# Calculate LZ76 phrase counts for all binary strings of length L=4
L = 4
print(f"Calculating all LZ76 phrase counts for L={L}...")
all_counts = calculator.calculate_all_lz76_counts(L)
if all_counts is not None:
    for i, count in enumerate(all_counts):
        binary_string = format(i, f'0{L}b')
        print(f"  String: {binary_string}, LZ76 Phrase Count: {count}")

# Calculate LZ76 complexity distribution for L=10
L_dist = 10
print(f"\nCalculating LZ76 complexity distribution for L={L_dist}...")
# num_threads defaults to os.cpu_count() in the wrapper if OpenMP is used by C code
distribution = calculator.get_lz76_complexity_distribution(L_dist, num_threads=4)
if distribution is not None:
    for complexity_val, num_strings_with_complexity in enumerate(distribution):
        if num_strings_with_complexity > 0:
            print(f"  LZ76 Complexity {complexity_val}: {num_strings_with_complexity} strings")
```

### Using Pure Python Backend (Reference Implementations)

These are generally slower but can be useful for understanding or when C compilation is an issue.

```python
from hadi_LZ_package.python_backend.lz_inefficient import LZ76 as LZ76_python, LZ78 as LZ78_python
from hadi_LZ_package.python_backend.lz_suffix import LZSuffixTree as PythonLZSuffixTreeOnline

text = "01010010001"

# Inefficient Python LZ76 (returns scaled complexity)
complexity_ineff_lz76 = LZ76_python(text)
print(f"Inefficient Python LZ76 for '{text}': {complexity_ineff_lz76:.3f}")

# Python LZ78 (returns dictionary and phrase count)
phrases_py_lz78, count_py_lz78 = LZ78_python(text)
print(f"Python LZ78 for '{text}': phrases={phrases_py_lz78}, count={count_py_lz78}")

# Python LZ76 using Suffix Tree (online)
py_st_lz = PythonLZSuffixTreeOnline()
for char_py_st in text:
    py_st_lz.add_character(char_py_st)
print(f"Python Suffix Tree LZ76 for '{text}': {py_st_lz.compute_lz76_complexity()}")
```

## Development & Testing

-   **C Backend**: Source code is in `hadi_LZ_package/c_backend/`. Use `make` to build.
-   **Python Wrappers**: Located in `hadi_LZ_package/` (e.g., `lz_wrapper.py`, `online_suffix_wrapper.py`).
-   **Pure Python Backend**: In `hadi_LZ_package/python_backend/`.
-   **Tests**: Located in the `tests/` directory. These scripts compare implementations, benchmark performance, and verify correctness.
    -   `test_online_suffix.py`: Tests Python vs C suffix tree `find()`.
    -   `test_lz_suffix.py`: Tests Python vs C LZ76-with-suffix-tree phrase counts.
    -   `test_lz_exhaustive.py`: Tests exhaustive LZ76 C functions.
    -   `benchmark_lz_implementations.py`: Benchmarks `lz_suffix_combined.c` vs `lz_core.c` LZ76.
    -   `run_large_lz_distribution.py`: Utility to run large L distribution calculations.

To run tests, navigate to the `tests/` directory or run them as modules from the project root if the package is installed in editable mode.

## Structure

```
hadi_LZ_package/
├── hadi_LZ_package/              # Main package source
│   ├── __init__.py
│   ├── c_backend/                # C source code and compiled libraries
│   │   ├── *.c, *.h, Makefile
│   │   └── *.dylib / *.so        # Compiled shared libraries
│   ├── python_backend/           # Pure Python implementations
│   │   ├── __init__.py
│   │   ├── online_suffix.py
│   │   ├── lz_suffix.py
│   │   └── lz_inefficient.py
│   ├── lz_wrapper.py             # Ctypes wrapper for lz_core.c
│   ├── online_suffix_wrapper.py  # Ctypes wrapper for online_suffix.c
│   ├── lz_suffix_wrapper.py      # Ctypes wrapper for lz_suffix_combined.c
│   └── lz_exhaustive_wrapper.py  # Ctypes wrapper for lz_exhaustive.c
├── tests/                        # Test scripts
│   └── *.py
├── README.md                     # This file
├── requirements.txt
└── setup.py
```

## Contributing

Contributions, issues, and feature requests are welcome. Please refer to a standard contributing guide if one is provided, or open an issue to discuss changes.

## License

(Specify your license here, e.g., MIT License)
