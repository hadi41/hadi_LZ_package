'''Python wrapper for C-based exhaustive LZ76 calculations.

This module provides the `LZExhaustiveCalculator` class, which interfaces with
the compiled C library `lz_exhaustive` (e.g., `lz_exhaustive.dylib`).
This C library is responsible for calculating LZ76 phrase counts for *all* binary
strings of a given length `L`, or for calculating the distribution of these
phrase counts. These operations are computationally intensive.

The wrapper handles:
- Loading the `lz_exhaustive` C library.
- Defining `ctypes` signatures for the C functions.
- Preparing input arguments and result arrays for the C functions.
- Converting C array results back to `numpy` arrays.
- Providing warnings and basic safety checks for large values of `L`.
'''
import ctypes
import os
import sys
import numpy as np # For creating the results array easily

class LZExhaustiveCalculator:
    '''Wraps C functions for exhaustive LZ76 calculations over binary strings.

    Provides methods to:
    1. `calculate_all_lz76_counts(L)`: Get an array where index `i` stores the
       LZ76 phrase count for the binary string represented by `i` of length `L`.
    2. `get_lz76_complexity_distribution(L, ...)`: Get the distribution of
       LZ76 phrase counts for all 2^L binary strings.

    The C backend `lz_exhaustive` may use OpenMP for parallelization in the
    distribution calculation.

    Attributes:
        c_lib: `ctypes.CDLL` object for the loaded `lz_exhaustive` C library.
    '''
    def __init__(self):
        """Initializes the LZExhaustiveCalculator.

        Loads the `lz_exhaustive` C library and configures C function prototypes.

        Raises:
            OSError: If the C shared library (`lz_exhaustive`) cannot be loaded.
            AttributeError: If required C functions are not found in the library.
        """
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # This library will only contain lz_exhaustive.c object code
        lib_filename = "lz_exhaustive.so"
        if os.name == 'nt':
            lib_filename = "lz_exhaustive.dll"
        elif sys.platform == 'darwin':
            lib_filename = "lz_exhaustive.dylib"
        
        lib_path = os.path.join(script_dir, "c_backend", lib_filename)

        try:
            self.c_lib = ctypes.CDLL(lib_path)
        except OSError as e:
            lz_exhaustive_c_path = os.path.join("c_backend", "lz_exhaustive.c")
            output_lib_path = os.path.join("c_backend", lib_filename)
            error_message = (
                f"Failed to load C library '{lib_filename}' from {lib_path}.\n"
                f"Please ensure it is compiled (e.g., using 'make' in c_backend directory).\n"
                f"Source: '{lz_exhaustive_c_path}'. Target: '{output_lib_path}'.\n"
                f"Example compilation (ensure OpenMP flags if needed, see Makefile):\n"
                f"  gcc -shared -o '{output_lib_path}' -fPIC '{lz_exhaustive_c_path}' -fopenmp\n"
                f"Original error: {e}"
            )
            raise OSError(error_message)

        # Configure C function prototype from lz_exhaustive.h
        self.c_lib.lz76_exhaustive_generate.restype = None
        self.c_lib.lz76_exhaustive_generate.argtypes = [
            ctypes.c_int,                      # L
            ctypes.POINTER(ctypes.c_int)       # phrase_counts_output
        ]

        self.c_lib.lz76_exhaustive_distribution.restype = None
        self.c_lib.lz76_exhaustive_distribution.argtypes = [
            ctypes.c_int,                        # L
            ctypes.POINTER(ctypes.c_longlong),   # counts_by_complexity (long long*)
            ctypes.c_int,                        # max_complexity_to_track
            ctypes.c_int                         # num_threads
        ]

    def calculate_all_lz76_counts(self, L: int) -> np.ndarray | None:
        """Calculates LZ76 phrase counts for all 2^L binary strings of length L.

        Args:
            L: The length of binary strings to process.

        Returns:
            A numpy array of `np.int32` type, of size 2^L. The element at index `i`
            is the LZ76 phrase count for the binary string of length `L` whose
            integer representation is `i`.

        Raises:
            ValueError: If L is not a positive integer, or if L is excessively large
                        (>28), potentially leading to memory exhaustion.
        """
        if not (isinstance(L, int) and L > 0):
            raise ValueError("L must be a positive integer.")
        if L > 24: # Safety net, 2^24 is ~16 million. 2^20 is ~1 million.
                   # User requested test for L=20. L=30 is 1 billion.
            print(f"Warning: L={L} is large, this will require 2^{L} entries and significant time.", file=sys.stderr)
            if L > 28: # Extremely large, likely too much memory for results array in Python
                 raise ValueError(f"L={L} is too large, 2^{L} results array may exceed memory.")

        num_strings = 1 << L # 2^L
        
        # Create a numpy array to hold the results, pass its C-compatible pointer
        results_array_np = np.empty(num_strings, dtype=np.int32)
        results_array_c_ptr = results_array_np.ctypes.data_as(ctypes.POINTER(ctypes.c_int))

        print(f"Calling C lz76_exhaustive_generate for L={L} (2^{L} = {num_strings} strings)...", file=sys.stderr)
        self.c_lib.lz76_exhaustive_generate(ctypes.c_int(L), results_array_c_ptr)
        print(f"C lz76_exhaustive_generate finished for L={L}.", file=sys.stderr)
        
        return results_array_np 

    def get_lz76_complexity_distribution(self, L: int, max_complexity_to_track: int | None = None, num_threads: int | None = None, suppress_warnings: bool = False) -> np.ndarray | None:
        """Calculates the distribution of LZ76 phrase counts for all 2^L binary strings.

        Args:
            L: The length of binary strings.
            max_complexity_to_track: The maximum phrase count to track explicitly.
                                     Counts for complexities >= (max_complexity_to_track - 1)
                                     will be binned in the last entry of the returned array.
                                     If None, a sensible default (L + 5) is used.
            num_threads: Number of threads for parallel computation in C (if OpenMP enabled).
                         If None, defaults to `os.cpu_count()`. If 0 or invalid, C side may use its default.
            suppress_warnings: If True, suppresses warnings for large L values.

        Returns:
            A numpy array of `np.longlong` type. `array[c]` stores the number of
            binary strings of length `L` that have an LZ76 phrase count of `c`.
            The size of the array is `max_complexity_to_track`.

        Raises:
            ValueError: If L or max_complexity_to_track are invalid, or L is excessively large (>35).
        """
        if not (isinstance(L, int) and L > 0):
            raise ValueError("L must be a positive integer.")
        
        actual_num_threads = 1
        if num_threads is None:
            actual_num_threads = os.cpu_count() or 1 # Default to available CPUs
        elif isinstance(num_threads, int) and num_threads > 0:
            actual_num_threads = num_threads
        # If num_threads is 0 or invalid, it will default to 1 or OpenMP default in C if not set explicitly

        if max_complexity_to_track is None:
            # Max possible LZ76 phrase count for string of length L is L (each char new phrase) + 1 (if last word active)
            # So, array needs to be at least size L+2 to store counts for complexities 0 to L+1.
            max_complexity_to_track = L + 5 # Provide a bit of buffer, C side will use last bin as overflow
        elif not isinstance(max_complexity_to_track, int) or max_complexity_to_track <= 0:
            raise ValueError("max_complexity_to_track must be a positive integer.")
        if max_complexity_to_track <= L + 1 and L > 0:
             print(f"Warning: max_complexity_to_track={max_complexity_to_track} might be small for L={L}. Max LZ76 phrase count is typically <= {L+1}. Last bin is overflow.", file=sys.stderr)

        if not suppress_warnings:
            if L > 22:
                print(f"Warning: L={L} is large. Calculating distribution for 2^{L} strings will take significant time.", file=sys.stderr)
                if L > 35: # Practical limit for 2^L operations even if not storing all results
                    raise ValueError(f"L={L} is too large. 2^{L} operations are likely prohibitive.")

        num_strings_total = 1 << L
        print(f"Calling C lz76_exhaustive_distribution for L={L} (2^{L} = {num_strings_total} strings)...", file=sys.stderr)
        print(f"Tracking complexities up to {max_complexity_to_track-1} (last bin is overflow).", file=sys.stderr)

        # Create a numpy array of long longs, initialized to zero
        distribution_array_np = np.zeros(max_complexity_to_track, dtype=np.longlong)
        distribution_array_c_ptr = distribution_array_np.ctypes.data_as(ctypes.POINTER(ctypes.c_longlong))

        self.c_lib.lz76_exhaustive_distribution(
            ctypes.c_int(L), 
            distribution_array_c_ptr, 
            ctypes.c_int(max_complexity_to_track),
            ctypes.c_int(actual_num_threads)
        )
        print(f"C lz76_exhaustive_distribution finished for L={L}.", file=sys.stderr)
        
        return distribution_array_np 

# Example Usage:
if __name__ == '__main__':
    print("LZExhaustiveCalculator Example")
    calculator = LZExhaustiveCalculator()

    try:
        # --- Test calculate_all_lz76_counts --- 
        L_counts = 4 # Small L for quick test
        print(f"\nCalculating all LZ76 counts for L={L_counts}...")
        all_counts = calculator.calculate_all_lz76_counts(L_counts)
        if all_counts is not None:
            print(f"Results for L={L_counts} (length: {len(all_counts)}):")
            for i, count in enumerate(all_counts):
                binary_string = format(i, f'0{L_counts}b')
                print(f"  String: {binary_string}, LZ76 Phrase Count: {count}")
        
        # --- Test get_lz76_complexity_distribution --- 
        L_dist = 10 # A moderate L for distribution
        # Max complexity for L=10 is 10 (e.g. 0101010101) or 11. Tracking up to L+5=15 should be fine.
        max_c_track = L_dist + 5 
        print(f"\nCalculating LZ76 complexity distribution for L={L_dist} (tracking up to complexity {max_c_track-1})...")
        distribution = calculator.get_lz76_complexity_distribution(L_dist, max_complexity_to_track=max_c_track, num_threads=os.cpu_count())
        if distribution is not None:
            print(f"Distribution for L={L_dist}:")
            for complexity_val, num_with_complexity in enumerate(distribution):
                if num_with_complexity > 0:
                    print(f"  LZ76 Complexity {complexity_val}: {num_with_complexity} strings")
            if distribution[max_c_track-1] > 0:
                 print(f"  (Note: Counts for complexity >= {max_c_track-1} are in the last bin)")

        # Example with a larger L to show warning (but suppress it for automated tests if needed)
        # L_large_dist = 22
        # print(f"\nCalculating LZ76 complexity distribution for L={L_large_dist} (this will take time)...")
        # distribution_large = calculator.get_lz76_complexity_distribution(L_large_dist, num_threads=os.cpu_count(), suppress_warnings=False)
        # if distribution_large is not None:
        #     print(f"First few entries of distribution for L={L_large_dist}:")
        #     for c, n_c in enumerate(distribution_large[:15]): # Print first 15 bins
        #         if n_c > 0: print(f"  LZ C={c}: {n_c}")

    except ValueError as ve:
        print(f"ValueError in example: {ve}", file=sys.stderr)
    except OSError as oe:
        print(f"OSError in example (library loading issue?): {oe}", file=sys.stderr)
    except Exception as e:
        print(f"An unexpected error occurred in example: {e}", file=sys.stderr) 