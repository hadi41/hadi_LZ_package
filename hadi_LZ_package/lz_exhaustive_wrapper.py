import ctypes
import os
import sys
import numpy as np # For creating the results array easily

class LZExhaustiveCalculator:
    def __init__(self):
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
                f"Failed to load C library at {lib_path}. "
                f"Please ensure it is compiled. Example for Linux/macOS: "
                f"gcc -shared -o '{output_lib_path}' -fPIC '{lz_exhaustive_c_path}'"
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