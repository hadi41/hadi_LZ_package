import random
import sys
import os
import time
import math

# Adjust sys.path to allow importing modules from the project root
_project_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _project_root_dir not in sys.path:
    sys.path.insert(0, _project_root_dir)

try:
    from hadi_LZ_package.lz_suffix_wrapper import LZSuffixTreeWrapper
    from hadi_LZ_package.lz_wrapper import LZProcessor # This wraps lz_core.c
except ImportError as e:
    print(f"Error importing necessary modules: {e}")
    print(f"Current sys.path: {sys.path}")
    print(f"Attempted to add '{_project_root_dir}' to sys.path.")
    print("Please ensure all wrapper classes are correctly defined and accessible.")
    sys.exit(1)

def generate_random_binary_strings_batch(num_strings, length):
    batch = []
    for _ in range(num_strings):
        s = "".join(random.choices(['0', '1'], k=length))
        if not s and length > 0 : # Should not happen with k=length > 0
            s = '0' * length 
        elif not s and length == 0:
            # LZ complexities are tricky for empty strings, often default to 0 or 1.
            # For this benchmark, let's ensure non-empty if length > 0.
            # If length is 0, many LZ defs are 0. Our wrappers might handle it.
            pass # Allow empty string if length is 0, though test lengths are > 0
        batch.append(s)
    return batch

def run_benchmark(num_strings_per_length=100_000, lengths_to_test=[30, 50, 100]):
    print(f"Starting LZ76 Benchmark: {num_strings_per_length} strings for each length {lengths_to_test}")
    print("Comparing: lz_suffix_wrapper (our suffix tree C) vs. LZProcessor (lz_core.c wrapper)")

    # Instantiate wrappers once
    # lz_suffix_wrapper uses a persistent C state for batch, which is reset per string internally by C code.
    suffix_tree_wrapper = LZSuffixTreeWrapper()
    # lz_core_wrapper (LZProcessor) likely creates/manages its resources per call or internally.
    core_lz_processor = LZProcessor() 

    for length in lengths_to_test:
        print(f"\n--- Benchmarking for string length: {length} ---")
        test_strings = generate_random_binary_strings_batch(num_strings_per_length, length)
        if not test_strings: continue

        # 1. Benchmark lz_suffix_wrapper (our suffix tree C implementation)
        print(f"Running lz_suffix_wrapper for {num_strings_per_length} strings of length {length}...")
        start_time_suffix = time.perf_counter()
        try:
            results_suffix = suffix_tree_wrapper.compute_lz76_complexity_batch(test_strings)
        except Exception as e:
            print(f"  ERROR in lz_suffix_wrapper: {e}")
            results_suffix = [-1] * num_strings_per_length # Error placeholder
        time_suffix = time.perf_counter() - start_time_suffix
        print(f"  lz_suffix_wrapper finished in {time_suffix:.4f} seconds.")
        if num_strings_per_length > 0: 
            print(f"  Avg time per string (lz_suffix): {time_suffix/num_strings_per_length:.8f}s")

        # 2. Benchmark LZProcessor (lz_core.c wrapper)
        print(f"Running LZProcessor (lz_core.c) for {num_strings_per_length} strings of length {length}...")
        start_time_core = time.perf_counter()
        try:
            # LZProcessor.process_strings returns scaled complexities (result * log2(len))
            scaled_results_core = core_lz_processor.process_strings(test_strings, symmetric=False, algorithm='lz76')
        except Exception as e:
            print(f"  ERROR in LZProcessor: {e}")
            scaled_results_core = [-1.0] * num_strings_per_length # Error placeholder
        time_core = time.perf_counter() - start_time_core
        print(f"  LZProcessor finished in {time_core:.4f} seconds.")
        if num_strings_per_length > 0:
            print(f"  Avg time per string (lz_core): {time_core/num_strings_per_length:.8f}s")

        # Convert lz_core results to estimated phrase counts for comparison
        # phrase_count = result_double / log2(length)
        # Ensure length > 1 for log2(length) to be non-zero, and length > 0 for log2 to be defined.
        # Our benchmark lengths are >= 30, so this is fine.
        estimated_results_core_phrases = []
        log_2_length = math.log2(length) if length > 0 else 1 # Avoid log(0) or div by zero if length is 1 (though not for these tests)
        if log_2_length == 0 and length == 1: log_2_length = 1 # Avoid division by zero if log2(1)=0

        for scaled_res in scaled_results_core:
            if scaled_res < 0: # Error from LZProcessor
                 estimated_results_core_phrases.append(int(scaled_res) -10) # Distinct error placeholder
            elif log_2_length == 0: # Should not happen for length >=30
                 estimated_results_core_phrases.append(0) # Or handle as error/special case
            else:
                estimated_results_core_phrases.append(round(scaled_res / log_2_length))

        # 3. Verification
        mismatches = 0
        if len(results_suffix) == num_strings_per_length and len(estimated_results_core_phrases) == num_strings_per_length:
            for i in range(num_strings_per_length):
                if results_suffix[i] != estimated_results_core_phrases[i]:
                    if mismatches < 5: # Print first few mismatches
                        print(f"  MISMATCH for string #{i+1} (len {length}):")
                        # print(f"    String: '{test_strings[i][:60]}...'") # Can be verbose
                        print(f"    lz_suffix phrase count: {results_suffix[i]}")
                        print(f"    lz_core estimated phrase count: {estimated_results_core_phrases[i]} (from scaled: {scaled_results_core[i]})")
                    mismatches += 1
            if mismatches == 0:
                print("  Verification PASSED: Results match between lz_suffix and estimated lz_core.")
            else:
                print(f"  Verification FAILED: {mismatches}/{num_strings_per_length} mismatches found.")
        else:
            print("  Verification SKIPPED: Result list length mismatch.")
            if len(results_suffix) != num_strings_per_length:
                print(f"    lz_suffix results length: {len(results_suffix)}")
            if len(estimated_results_core_phrases) != num_strings_per_length:
                 print(f"    lz_core estimated results length: {len(estimated_results_core_phrases)}")

    print("\nBenchmark finished.")

if __name__ == "__main__":
    num_str = 100_000
    # For quicker test runs during development, reduce num_str:
    # num_str = 1000 
    lengths = [30, 50, 100, 1000]
    
    # Allow overriding from command line for quick tests
    if len(sys.argv) > 1:
        try:
            num_str = int(sys.argv[1])
            if len(sys.argv) > 2:
                lengths = [int(l) for l in sys.argv[2].split(',')]
        except ValueError:
            print("Usage: python benchmark_lz_implementations.py [num_strings_per_length] [comma_separated_lengths]")
            print("Example: python benchmark_lz_implementations.py 10000 30,50")
            sys.exit(1)
            
    run_benchmark(num_strings_per_length=num_str, lengths_to_test=lengths) 