'''Python wrapper for C-based LZ complexity and Block Entropy calculations.

This module provides Python classes `LZProcessor` and `EntropyProcessor` that use a 
compiled C library (liblzcore.dylib) for efficient computation of Lempel-Ziv
complexity (LZ76, LZ78) and block entropy measures on lists of strings.

It leverages ctypes for interfacing with the C code and numpy for numerical results.
The C library functions are parallelized using OpenMP for improved performance on
multi-core systems when processing batches of strings.
'''
import os
from ctypes import CDLL, POINTER, c_char_p, c_size_t, c_double, c_int
import numpy as np
from typing import List, Optional

# --- ctypes Library Loading and Function Signature Definitions ---

# Construct the absolute path to the C library file.
# __file__ is the path to the current Python file (lz_wrapper.py).
# os.path.dirname(__file__) gives the directory of this file.
# Then, join with the relative path to the C library within the package structure.
_clib_path = os.path.join(os.path.dirname(__file__), "c_backend/liblzcore.dylib")
try:
    _lib = CDLL(_clib_path)
except OSError as e:
    # Provide a more informative error message if the library fails to load.
    # This can happen if the .dylib is not found or not compiled for the correct architecture.
    print(f"Error loading C library from {_clib_path}: {e}")
    print(f"Please ensure the C library is compiled (e.g., using 'make' in the c_backend directory) ")
    print(f"and that the path is correct.")
    raise # Re-raise the exception to halt execution if the library is critical.


# Define argument types (argtypes) and return types (restype) for LZ complexity functions from the C library.
# This is crucial for ctypes to correctly call the C functions and interpret their results.
_lz_function_signatures = {
    'lz76_complexity': ([c_char_p, c_size_t], c_double),
    'lz78_complexity': ([c_char_p, c_size_t], c_double),
    'symmetric_lz78_complexity': ([c_char_p, c_size_t], c_double),
    'lz76_complexity_parallel_original': ([
        POINTER(c_char_p),    # char** input_strings
        POINTER(c_size_t),    # size_t* lengths
        POINTER(c_double),    # double* results
        c_size_t,             # size_t n_strings
        c_int                 # int n_threads
    ], None), # Parallel functions typically return void, results are via pointer
    'symmetric_lz76_parallel_original': ([
        POINTER(c_char_p), POINTER(c_size_t), POINTER(c_double), c_size_t, c_int
    ], None),
    'lz78_complexity_parallel': ([
        POINTER(c_char_p), POINTER(c_size_t), POINTER(c_double), c_size_t, c_int
    ], None),
    'symmetric_lz78_parallel': ([
        POINTER(c_char_p), POINTER(c_size_t), POINTER(c_double), c_size_t, c_int
    ], None)
}

for func_name, (arg_types, res_type) in _lz_function_signatures.items():
    try:
        func = getattr(_lib, func_name)
        func.argtypes = arg_types
        if res_type is not None:
            func.restype = res_type
    except AttributeError:
        print(f"Warning: Function {func_name} not found in C library at {_clib_path}.")

# Define argument types for entropy functions
try:
    _lib.block_entropy.argtypes = [c_char_p, c_size_t, c_size_t]
    _lib.block_entropy.restype = c_double

    _lib.symmetric_block_entropy.argtypes = [c_char_p, c_size_t, c_size_t]
    _lib.symmetric_block_entropy.restype = c_double

    _lib.block_entropy_parallel.argtypes = [
        POINTER(c_char_p),    # char** input_strings
        POINTER(c_size_t),    # size_t* lengths
        c_size_t,             # size_t dimension (block_size)
        POINTER(c_double),    # double* results
        c_size_t,             # size_t n_strings
        c_int                 # int n_threads
    ]
    # No restype for parallel (void return)

    _lib.symmetric_block_entropy_parallel.argtypes = [
        POINTER(c_char_p),    # char** input_strings
        POINTER(c_size_t),    # size_t* lengths
        c_size_t,             # size_t dimension
        POINTER(c_double),    # double* results
        c_size_t,             # size_t n_strings
        c_int                 # int n_threads
    ]
except AttributeError:
    print(f"Warning: One or more entropy functions not found in C library at {_clib_path}.")

# Define argument types for conditional complexity functions
_conditional_lz_function_names = ['conditional_lz76_parallel', 'conditional_lz78_parallel']
for func_name in _conditional_lz_function_names:
    try:
        func = getattr(_lib, func_name)
        func.argtypes = [
            POINTER(c_char_p),    # char** x_strings
            POINTER(c_char_p),    # char** y_strings
            POINTER(c_size_t),    # size_t* x_lengths
            POINTER(c_size_t),    # size_t* y_lengths
            POINTER(c_double),    # double* results
            c_size_t,             # size_t n_strings
            c_int                 # int n_threads
        ]
        # No restype for parallel (void return)
    except AttributeError:
        print(f"Warning: Function {func_name} not found in C library at {_clib_path}.")


class LZProcessor:
    '''Processes lists of strings to calculate LZ76 or LZ78 complexity.

    This class provides a high-level interface to the C library's LZ complexity
    functions. It handles batch processing of strings and can utilize multiple
    threads for parallel computation via OpenMP in the C backend.

    Attributes:
        n_threads (int): The number of threads to use for parallel processing.
                         Defaults to the number of CPU cores available.
    '''
    def __init__(self, n_threads: Optional[int] = None):
        """Initializes the LZProcessor.

        Args:
            n_threads: The number of threads to use for parallel computations.
                       If None, defaults to the number of CPU cores detected by os.cpu_count().
        """
        self.n_threads = n_threads if n_threads is not None else os.cpu_count()
        if self.n_threads is None: # Fallback if os.cpu_count() returns None
            self.n_threads = 1 

    def process_strings(self, strings: List[str], symmetric: bool = False, algorithm: str = 'lz76') -> np.ndarray:
        '''Calculates LZ complexity for a list of strings.

        Args:
            strings: A list of strings to process.
            symmetric: If True, calculates symmetric LZ complexity (average of string and its reverse).
                       Defaults to False.
            algorithm: The LZ algorithm to use. Can be 'lz76' or 'lz78'.
                       Defaults to 'lz76'.

        Returns:
            A numpy array of LZ complexity values for each input string.

        Raises:
            ValueError: If an invalid algorithm is specified.
            AttributeError: If the required C library function is not found (e.g., due to compilation issues).
        '''
        if not strings:
            return np.array([])

        processed_strings_bytes = []
        lengths = []
        for s in strings:
            # LZ complexity is typically not well-defined for empty strings.
            # The C code might handle it, but here we ensure non-empty by providing a default.
            # This also ensures consistent length for the C backend.
            effective_s = s if s else "0" # Use "0" for empty strings
            processed_strings_bytes.append(effective_s.encode('utf-8'))
            lengths.append(len(effective_s))

        # Create C-compatible arrays
        str_array = (c_char_p * len(processed_strings_bytes))(*processed_strings_bytes)
        lengths_array = (c_size_t * len(lengths))(*lengths)
        results_array = (c_double * len(strings))() # Output array

        # Select the appropriate C function based on algorithm and symmetry
        if algorithm == 'lz76':
            func = _lib.symmetric_lz76_parallel_original if symmetric else _lib.lz76_complexity_parallel_original
        elif algorithm == 'lz78':
            func = _lib.symmetric_lz78_parallel if symmetric else _lib.lz78_complexity_parallel
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}. Choose 'lz76' or 'lz78'.")
            
        # Call the C function
        func(str_array, lengths_array, results_array, len(strings), c_int(self.n_threads))
        
        return np.array(list(results_array)) # Convert c_double array to numpy array

    def process_conditional(self, x_strings: List[str], y_strings: List[str], 
                          algorithm: str = 'lz76') -> np.ndarray:
        '''Calculate conditional LZ complexity K(Y|X) for pairs of strings.

        The conditional complexity K(Y|X) is approximated as K(XY) - K(X), where K
        is the chosen LZ complexity measure (LZ76 or LZ78).
        This measures the complexity of string Y given string X.

        Args:
            x_strings: A list of primary strings (X).
            y_strings: A list of conditional strings (Y), corresponding to each X.
            algorithm: The LZ algorithm ('lz76' or 'lz78') to use for K.
                       Defaults to 'lz76'.

        Returns:
            A numpy array of conditional complexity values K(Y_i|X_i) for each pair.

        Raises:
            ValueError: If x_strings and y_strings have different lengths, or if an
                        invalid algorithm is specified.
            AttributeError: If the required C library function is not found.
        '''
        if len(x_strings) != len(y_strings):
            raise ValueError("x_strings and y_strings must have the same length")
        if not x_strings: # If lists are empty
            return np.array([])
        
        processed_x_bytes = []
        processed_y_bytes = []
        x_lengths = []
        y_lengths = []
        
        for x, y in zip(x_strings, y_strings):
            # Handle empty strings: C(Y|empty_X) or C(empty_Y|X) might need specific definitions.
            # Current C code for conditional returns 0 if x_length is 0, or if y_length is 0 and using K(XY)-K(X).
            # For K(Y|X) = K(XY) - K(X): if X is empty, result is K(Y) - K(empty). if Y is empty, result is K(X) - K(X) = 0.
            # Using "0" as a placeholder for empty strings for robustness with C layer.
            effective_x = x if x else "0"
            effective_y = y if y else "0"

            processed_x_bytes.append(effective_x.encode('utf-8'))
            processed_y_bytes.append(effective_y.encode('utf-8'))
            x_lengths.append(len(effective_x))
            y_lengths.append(len(effective_y))

        # Create C-compatible arrays
        x_array = (c_char_p * len(processed_x_bytes))(*processed_x_bytes)
        y_array = (c_char_p * len(processed_y_bytes))(*processed_y_bytes)
        x_lengths_array = (c_size_t * len(x_lengths))(*x_lengths)
        y_lengths_array = (c_size_t * len(y_lengths))(*y_lengths)
        results_array = (c_double * len(x_strings))() # Output array

        # Choose the C function based on the algorithm
        if algorithm == 'lz76':
            func = _lib.conditional_lz76_parallel
        elif algorithm == 'lz78':
            func = _lib.conditional_lz78_parallel
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}. Choose 'lz76' or 'lz78'.")
        
        # Call the C function
        func(x_array, y_array, x_lengths_array, y_lengths_array,
             results_array, len(x_strings), c_int(self.n_threads))
        
        return np.array(list(results_array))

class EntropyProcessor:
    '''Processes lists of strings to calculate block entropy.

    This class provides a high-level interface to the C library's block entropy
    functions. It handles batch processing and can utilize multiple threads.

    Attributes:
        n_threads (int): The number of threads for parallel processing.
    '''
    def __init__(self, n_threads: Optional[int] = None):
        """Initializes the EntropyProcessor.

        Args:
            n_threads: Number of threads for parallel computations.
                       Defaults to CPU count.
        """
        self.n_threads = n_threads if n_threads is not None else os.cpu_count()
        if self.n_threads is None:  # Fallback
            self.n_threads = 1

    def process_strings(self, strings: List[str], symmetric: bool = False, block_size: int = 1) -> np.ndarray:
        '''Calculates block entropy for a list of strings.

        Args:
            strings: A list of strings to process.
            symmetric: If True, calculates symmetric block entropy (average of string and its reverse).
                       Defaults to False.
            block_size: The dimension (size) of blocks for entropy calculation.
                        Defaults to 1.

        Returns:
            A numpy array of block entropy values for each input string.
        
        Raises:
            ValueError: If block_size is not positive.
            AttributeError: If the required C library function is not found.
        '''
        if not strings:
            return np.array([])
        if block_size <= 0:
            raise ValueError("block_size must be a positive integer.")

        processed_strings_bytes = []
        lengths = []
        for s in strings:
            effective_s = s if s else "0" # Use "0" for empty strings
            # Block entropy C code might require length >= block_size.
            # This check should ideally be in C, but a basic check here can prevent issues.
            if len(effective_s) < block_size and len(effective_s) > 0: # if not empty but shorter than block
                # Option 1: Pad string (might alter entropy meaning)
                # Option 2: Skip or return error/NaN (C code currently returns 0 for dim > len)
                # Option 3: Let C code handle it (it returns 0.0 if dimension > length)
                pass # Assuming C code handles this case by returning 0.0 as per lz_core.c

            processed_strings_bytes.append(effective_s.encode('utf-8'))
            lengths.append(len(effective_s))

        str_array = (c_char_p * len(processed_strings_bytes))(*processed_strings_bytes)
        lengths_array = (c_size_t * len(lengths))(*lengths)
        results_array = (c_double * len(strings))()

        if symmetric:
            func = _lib.symmetric_block_entropy_parallel
        else:
            func = _lib.block_entropy_parallel
        
        func(str_array, lengths_array, c_size_t(block_size), results_array, len(strings), c_int(self.n_threads))
        
        return np.array(list(results_array))

# --- Example Usage ---
if __name__ == '__main__':
    print("Running LZProcessor and EntropyProcessor examples...")

    # Test strings
    test_strings_varied = [
        "0100101011", 
        "ababababab", 
        "abcde", 
        "aaaaa", 
        "0", 
        "" # Empty string test
    ]
    num_varied_strings = len(test_strings_varied)

    # --- LZProcessor Example ---
    print("\n--- LZProcessor --- ")
    lz_proc = LZProcessor(n_threads=4)

    print("\nCalculating LZ76...")
    results_lz76 = lz_proc.process_strings(test_strings_varied, symmetric=False, algorithm='lz76')
    for s, r in zip(test_strings_varied, results_lz76):
        print(f"LZ76('{s if s else '<empty>'}'): {r:.3f}")

    print("\nCalculating Symmetric LZ78...")
    results_sym_lz78 = lz_proc.process_strings(test_strings_varied, symmetric=True, algorithm='lz78')
    for s, r in zip(test_strings_varied, results_sym_lz78):
        print(f"Symmetric LZ78('{s if s else '<empty>'}'): {r:.3f}")

    # --- Conditional LZProcessor Example ---
    print("\n--- Conditional LZProcessor --- ")
    x_cond_strings = ["00000", "ababab", "cat", "", "10101"]
    y_cond_strings = ["11111", "abacaba", "dog", "nonempty", "01010"]
    
    print("\nCalculating Conditional LZ76 K(Y|X)...")
    cond_results_lz76 = lz_proc.process_conditional(x_cond_strings, y_cond_strings, algorithm='lz76')
    for x, y, r in zip(x_cond_strings, y_cond_strings, cond_results_lz76):
        print(f"CondLZ76('{y if y else '<empty>'}'|'{x if x else '<empty>'}'): {r:.3f}")

    # --- EntropyProcessor Example ---
    print("\n--- EntropyProcessor --- ")
    entropy_proc = EntropyProcessor(n_threads=4)

    print("\nCalculating Block Entropy (block_size=1)...")
    results_ent_b1 = entropy_proc.process_strings(test_strings_varied, symmetric=False, block_size=1)
    for s, r in zip(test_strings_varied, results_ent_b1):
        print(f"BlockEntropy(b=1, '{s if s else '<empty>'}'): {r:.3f}")

    print("\nCalculating Symmetric Block Entropy (block_size=2)...")
    results_sym_ent_b2 = entropy_proc.process_strings(test_strings_varied, symmetric=True, block_size=2)
    for s, r in zip(test_strings_varied, results_sym_ent_b2):
        # Note: C code might return 0 for strings shorter than block_size.
        print(f"SymBlockEntropy(b=2, '{s if s else '<empty>'}'): {r:.3f}")

    # --- Performance Benchmark Example (Optional) ---
    # print("\n--- Performance Benchmark (LZ76) ---")
    # num_perf_strings = 100000
    # perf_test_strings = ['01001010111010100101' for _ in range(num_perf_strings)] # Longer strings
    # processor_perf = LZProcessor(n_threads=os.cpu_count())
    
    # import time
    # start_time_perf = time.time()
    # results_perf = processor_perf.process_strings(perf_test_strings, algorithm='lz76', symmetric=False)
    # elapsed_perf = time.time() - start_time_perf
    
    # print(f"Processed {len(perf_test_strings)} strings for benchmark.")
    # print(f"Time taken: {elapsed_perf:.3f} seconds")
    # print(f"Strings per second: {len(perf_test_strings) / elapsed_perf:.0f}")
    # print(f"Mean complexity: {results_perf.mean():.3f}")