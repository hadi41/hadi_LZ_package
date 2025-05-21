'''Benchmarks different LZ76 implementations against each other.

This script compares the performance of two C-based LZ76 implementations:
1.  `LZSuffixTreeWrapper`: Uses `lz_suffix_combined.c`, which implements LZ76
    using an online suffix tree.
2.  `LZProcessor`: Uses `lz_core.c`, which contains a more direct (non-suffix-tree)
    parallelized LZ76 calculation.

The benchmark generates batches of random binary strings of specified lengths and
measures the time taken by each implementation to process these batches.
It also performs a verification step by comparing the phrase counts obtained from
`LZSuffixTreeWrapper` with the estimated phrase counts derived from `LZProcessor`\'s
output (which is complexity scaled by log2(length)).

Usage:
    python benchmark_lz_implementations.py [num_strings_per_length] [comma_separated_lengths]

Example:
    python benchmark_lz_implementations.py 100000 30,50,100
    python benchmark_lz_implementations.py 1000 50,100,500,1000
'''
import random
import sys
import os
import time
import math
import numpy as np # For array operations if needed, though not heavily used here

# --- Path Setup --- 
# Add the project root to sys.path to allow importing from hadi_LZ_package
_project_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _project_root_dir not in sys.path:
    sys.path.insert(0, _project_root_dir)

try:
    from hadi_LZ_package.lz_suffix_wrapper import LZSuffixTreeWrapper
    from hadi_LZ_package.lz_wrapper import LZProcessor # Wraps lz_core.c
except ImportError as e:
    print(f"ERROR: Could not import necessary LZ wrappers: {e}")
    print(f"Ensure hadi_LZ_package is installed or in PYTHONPATH, and all C libraries are compiled.")
    print(f"Current sys.path: {sys.path}")
    sys.exit(1)

def generate_random_binary_strings_batch(num_strings: int, length: int) -> list[str]:
    """Generates a batch of random binary strings.

    Args:
        num_strings: The number of strings to generate in the batch.
        length: The length of each binary string.

    Returns:
        A list of randomly generated binary strings.
        Returns an empty list if num_strings is not positive.
        If length is 0, returns a list of empty strings.
    """
    if num_strings <= 0:
        return []
    if length == 0:
        return ["" for _ in range(num_strings)]
        
    batch = []
    for _ in range(num_strings):
        # random.choices is efficient for generating strings from an alphabet
        s = "".join(random.choices(['0', '1'], k=length))
        batch.append(s)
    return batch

def run_benchmark(num_strings_per_length: int = 100000, 
                  lengths_to_test: list[int] = [30, 50, 100, 500]):
    """Runs the LZ76 implementation benchmark.

    Compares `LZSuffixTreeWrapper` (C suffix tree based) against `LZProcessor`
    (C direct LZ76, potentially parallelized with OpenMP via `lz_core.c`).
    Measures execution time and verifies consistency of results (phrase counts).

    Args:
        num_strings_per_length (int, optional): Number of random strings to generate
                                                for each specified length.
                                                Defaults to 100,000.
        lengths_to_test (list[int], optional): A list of string lengths to benchmark.
                                               Defaults to [30, 50, 100, 500].
    """
    print(f"--- Starting LZ76 Implementations Benchmark --- ")
    print(f"Number of strings per length: {num_strings_per_length:,}")
    print(f"String lengths to test: {lengths_to_test}")
    print("Comparing: LZSuffixTreeWrapper (lz_suffix_combined.c) vs. LZProcessor (lz_core.c)")

    try:
        # Instantiate wrappers once. Their internal C states are managed by them.
        # LZSuffixTreeWrapper.compute_lz76_complexity_batch uses a persistent C state,
        # which is reset internally by its C code for each string in the batch.
        suffix_tree_wrapper = LZSuffixTreeWrapper()
        core_lz_processor = LZProcessor() # LZProcessor also handles its C resources.
    except Exception as e_init:
        print(f"ERROR: Could not initialize LZ wrappers: {e_init}. Aborting benchmark.")
        return

    for length in lengths_to_test:
        if length <= 0:
            print(f"\nSkipping invalid length: {length}. Length must be positive.")
            continue

        print(f"\n--- Benchmarking for String Length: {length} ---")
        
        print(f"Generating {num_strings_per_length:,} random binary strings of length {length}...")
        test_strings = generate_random_binary_strings_batch(num_strings_per_length, length)
        if not test_strings:
            print("No test strings generated (num_strings_per_length might be 0). Skipping length.")
            continue
        print("String generation complete.")

        # 1. Benchmark LZSuffixTreeWrapper (lz_suffix_combined.c)
        # This wrapper's batch method directly returns integer phrase counts.
        print(f"Running LZSuffixTreeWrapper.compute_lz76_complexity_batch()...")
        results_suffix_phrases: list[int] = []
        start_time_suffix = time.perf_counter()
        try:
            results_suffix_phrases = suffix_tree_wrapper.compute_lz76_complexity_batch(test_strings)
        except Exception as e_suffix:
            print(f"  ERROR during LZSuffixTreeWrapper execution: {e_suffix}")
            results_suffix_phrases = [-1] * num_strings_per_length # Placeholder for error
        time_suffix = time.perf_counter() - start_time_suffix
        print(f"  LZSuffixTreeWrapper finished in {time_suffix:.4f} seconds.")
        if num_strings_per_length > 0 and time_suffix > 0:
            print(f"  Avg time per string (LZSuffixTreeWrapper): {time_suffix/num_strings_per_length:.8e}s")

        # 2. Benchmark LZProcessor (lz_core.c wrapper)
        # This wrapper's process_strings returns scaled complexities: phrase_count * log2(length).
        print(f"Running LZProcessor.process_strings() (lz_core.c backend)... ")
        scaled_results_core: np.ndarray | list[float] = []
        start_time_core = time.perf_counter()
        try:
            scaled_results_core = core_lz_processor.process_strings(test_strings, symmetric=False, algorithm='lz76')
        except Exception as e_core:
            print(f"  ERROR during LZProcessor execution: {e_core}")
            scaled_results_core = [-1.0] * num_strings_per_length # Placeholder for error
        time_core = time.perf_counter() - start_time_core
        print(f"  LZProcessor finished in {time_core:.4f} seconds.")
        if num_strings_per_length > 0 and time_core > 0:
            print(f"  Avg time per string (LZProcessor): {time_core/num_strings_per_length:.8e}s")

        # Convert LZProcessor's scaled results to estimated phrase counts for verification.
        estimated_core_phrases: list[int] = []
        if length > 0: # log2 is defined for length > 0.
            # log2(1) is 0. If length is 1, phrase count is typically the complexity itself.
            log2_L_divisor = math.log2(length) if length > 1 else 1.0 
                                                # Treat as 1 to avoid div by zero if length is 1.
                                                # C code lz76_complexity returns dict_size * log2(length).
                                                # If L=1, log2(L)=0. C returns dict_size * 0 = 0. Phrase count would be 1.
                                                # The C code for lz76_complexity needs careful check for L=1.
                                                # python_backend/lz_inefficient.py LZ76 for n<=1 returns float(dict_size).
                                                # Let's assume for L=1, phrase count is directly the result from LZProcessor if it doesn't scale by log2(1)=0.
                                                # However, lz_core.c returns dictionary_size * log2((double)length), so for L=1, it will be 0.
                                                # This makes comparison tricky for L=1.
                                                # For this benchmark, lengths are >=30, so log2_L_divisor will be > 0.

            for scaled_res_val in scaled_results_core:
                if scaled_res_val < 0: # Error from LZProcessor
                    estimated_core_phrases.append(int(scaled_res_val) - 10) # Distinct error code
                elif log2_L_divisor == 0: # Should only happen if length was 1 AND we didn't guard above.
                     # This case needs specific handling based on how LZProcessor output for L=1 is defined.
                     # If LZProcessor returns raw phrase count for L=1, then this is it.
                     # If it returns 0 due to log2(1)=0, we need to infer phrase count (likely 1).
                     # For lengths >=30 in this benchmark, this branch won't be hit.
                    estimated_core_phrases.append(int(round(scaled_res_val))) 
                else:
                    estimated_core_phrases.append(int(round(scaled_res_val / log2_L_divisor)))
        else: # length == 0
            estimated_core_phrases = [0] * num_strings_per_length # LZ of empty string is 0 phrases.

        # 3. Verification of results between the two implementations.
        print("Verifying results (phrase counts)...")
        mismatches = 0
        if len(results_suffix_phrases) == num_strings_per_length and len(estimated_core_phrases) == num_strings_per_length:
            for i in range(num_strings_per_length):
                if results_suffix_phrases[i] != estimated_core_phrases[i]:
                    if mismatches < 5: # Print details for the first few mismatches.
                        print(f"  MISMATCH for string #{i+1} (length {length}):")
                        # print(f"    String: '{test_strings[i][:60]}...'") # Uncomment for string details, can be verbose.
                        print(f"    LZSuffixTreeWrapper phrase count: {results_suffix_phrases[i]}")
                        print(f"    LZProcessor (lz_core.c) estimated phrase count: {estimated_core_phrases[i]} (from scaled value: {scaled_results_core[i]})")
                    mismatches += 1
            
            if mismatches == 0:
                print("  Verification PASSED: Phrase counts match between implementations.")
            else:
                print(f"  Verification FAILED: {mismatches}/{num_strings_per_length} mismatches found.")
        else:
            print("  Verification SKIPPED due to result list length mismatch:")
            print(f"    LZSuffixTreeWrapper results length: {len(results_suffix_phrases)}")
            print(f"    LZProcessor estimated results length: {len(estimated_core_phrases)}")

    print("\n--- Benchmark Finished ---")

if __name__ == "__main__":
    # Default benchmark parameters
    num_strings_arg = 100000
    lengths_arg_str = "30,50,100,200" # Default lengths
    
    # Override with command line arguments if provided
    if len(sys.argv) > 1:
        try:
            num_strings_arg = int(sys.argv[1])
            if num_strings_arg <= 0:
                raise ValueError("Number of strings must be positive.")
            if len(sys.argv) > 2:
                lengths_arg_str = sys.argv[2]
        except ValueError as e:
            print(f"Invalid argument: {e}")
            print("Usage: python benchmark_lz_implementations.py [num_strings_per_length (int > 0)] [comma_separated_lengths (e.g., 30,50,100)]")
            sys.exit(1)
            
    try:
        lengths_to_run = [int(l.strip()) for l in lengths_arg_str.split(',') if l.strip()]
        if not lengths_to_run or any(l <= 0 for l in lengths_to_run):
            raise ValueError("Lengths must be positive integers.")
    except ValueError as e:
        print(f"Invalid lengths argument: '{lengths_arg_str}'. {e}")
        print("Please provide comma-separated positive integers for lengths.")
        sys.exit(1)
            
    run_benchmark(num_strings_per_length=num_strings_arg, lengths_to_test=lengths_to_run) 