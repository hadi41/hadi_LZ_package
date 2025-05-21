import os
from ctypes import CDLL, POINTER, c_char_p, c_size_t, c_double, c_int
import numpy as np
from typing import List, Optional

# Load the C library
_lib = CDLL(os.path.join(os.path.dirname(__file__), "c_backend/liblzcore.dylib"))

# Define argument types for LZ functions
for func_name in [
    'lz76_complexity',
    'lz76_complexity_parallel_original',
    'symmetric_lz76_parallel_original',
    'lz78_complexity',
    'symmetric_lz78_complexity',
    'lz78_complexity_parallel',
    'symmetric_lz78_parallel'
]:
    func = getattr(_lib, func_name)
    if func_name in ['lz76_complexity', 'lz78_complexity', 'symmetric_lz78_complexity']:
        func.argtypes = [c_char_p, c_size_t]
        func.restype = c_double
    else:
        func.argtypes = [
            POINTER(c_char_p),    # char** input_strings
            POINTER(c_size_t),    # size_t* lengths
            POINTER(c_double),    # double* results
            c_size_t,            # size_t n_strings
            c_int                # int n_threads
        ]

# Define argument types for entropy functions
_lib.block_entropy.argtypes = [c_char_p, c_size_t, c_size_t]
_lib.block_entropy.restype = c_double

_lib.symmetric_block_entropy.argtypes = [c_char_p, c_size_t, c_size_t]
_lib.symmetric_block_entropy.restype = c_double

_lib.block_entropy_parallel.argtypes = [
    POINTER(c_char_p),    # char** input_strings
    POINTER(c_size_t),    # size_t* lengths
    c_size_t,            # size_t dimension
    POINTER(c_double),    # double* results
    c_size_t,            # size_t n_strings
    c_int                # int n_threads
]

_lib.symmetric_block_entropy_parallel.argtypes = [
    POINTER(c_char_p),    # char** input_strings
    POINTER(c_size_t),    # size_t* lengths
    c_size_t,            # size_t dimension
    POINTER(c_double),    # double* results
    c_size_t,            # size_t n_strings
    c_int                # int n_threads
]

# Add conditional complexity function definitions
for func_name in ['conditional_lz76_parallel', 'conditional_lz78_parallel']:
    func = getattr(_lib, func_name)
    func.argtypes = [
        POINTER(c_char_p),    # char** x_strings
        POINTER(c_char_p),    # char** y_strings
        POINTER(c_size_t),    # size_t* x_lengths
        POINTER(c_size_t),    # size_t* y_lengths
        POINTER(c_double),    # double* results
        c_size_t,            # size_t n_strings
        c_int                # int n_threads
    ]

class LZProcessor:
    def __init__(self, n_threads: Optional[int] = None):
        self.n_threads = n_threads if n_threads is not None else os.cpu_count()

    def process_strings(self, strings: List[str], symmetric: bool = False, algorithm: str = 'lz76') -> np.ndarray:
        processed_strings = []
        lengths = []
        for s in strings:
            if not s:
                s = "0"
            processed_strings.append(s.encode('utf-8'))
            lengths.append(len(s))

        str_array = (c_char_p * len(processed_strings))(*processed_strings)
        lengths_array = (c_size_t * len(lengths))(*lengths)
        results = (c_double * len(strings))()

        if algorithm == 'lz76':
            func = _lib.symmetric_lz76_parallel_original if symmetric else _lib.lz76_complexity_parallel_original
        else:  # lz78
            func = _lib.symmetric_lz78_parallel if symmetric else _lib.lz78_complexity_parallel
            
        func(str_array, lengths_array, results, len(strings), c_int(self.n_threads))
        
        return np.array(results)

    def process_conditional(self, x_strings: List[str], y_strings: List[str], 
                          algorithm: str = 'lz76') -> np.ndarray:
        """Calculate conditional complexity K(y|x) for pairs of strings."""
        if len(x_strings) != len(y_strings):
            raise ValueError("x_strings and y_strings must have the same length")
        
        # Process input strings
        processed_x = []
        processed_y = []
        x_lengths = []
        y_lengths = []
        
        for x, y in zip(x_strings, y_strings):
            if not x: x = "0"
            if not y: y = "0"
            processed_x.append(x.encode('utf-8'))
            processed_y.append(y.encode('utf-8'))
            x_lengths.append(len(x))
            y_lengths.append(len(y))

        # Create C arrays
        x_array = (c_char_p * len(processed_x))(*processed_x)
        y_array = (c_char_p * len(processed_y))(*processed_y)
        x_lengths_array = (c_size_t * len(x_lengths))(*x_lengths)
        y_lengths_array = (c_size_t * len(y_lengths))(*y_lengths)
        results = (c_double * len(x_strings))()

        # Choose function based on algorithm
        func = (_lib.conditional_lz78_parallel if algorithm == 'lz78' 
                else _lib.conditional_lz76_parallel)
        
        # Process strings
        func(x_array, y_array, x_lengths_array, y_lengths_array,
             results, len(x_strings), c_int(self.n_threads))
        
        return np.array(results)

class EntropyProcessor:
    def __init__(self, n_threads: Optional[int] = None):
        self.n_threads = n_threads if n_threads is not None else os.cpu_count()

    def process_strings(self, strings: List[str], symmetric: bool = False, block_size: int = 1) -> np.ndarray:
        processed_strings = []
        lengths = []
        for s in strings:
            if not s:
                s = "0"
            processed_strings.append(s.encode('utf-8'))
            lengths.append(len(s))

        str_array = (c_char_p * len(processed_strings))(*processed_strings)
        lengths_array = (c_size_t * len(lengths))(*lengths)
        results = (c_double * len(strings))()

        func = _lib.symmetric_block_entropy_parallel if symmetric else _lib.block_entropy_parallel
        func(str_array, lengths_array, block_size, results, len(strings), c_int(self.n_threads))
        
        return np.array(results)

# Usage example:
if __name__ == '__main__':
    # Test the parallel implementation
    test_strings = ['0100101011' for _ in range(100000)]
    processor = LZProcessor(n_threads=4)
    
    import time
    start_time = time.time()
    results = processor.process_strings(test_strings)
    elapsed = time.time() - start_time
    
    print(f"\nProcessed {len(test_strings)} strings")
    print(f"Time: {elapsed:.3f} seconds")
    print(f"Strings per second: {len(test_strings) / elapsed:.0f}")
    print(f"Mean complexity: {results.mean():.3f}")