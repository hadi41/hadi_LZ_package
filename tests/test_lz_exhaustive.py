import sys
import os
import time
import math
import numpy as np

# Adjust sys.path
_project_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _project_root_dir not in sys.path:
    sys.path.insert(0, _project_root_dir)

try:
    from hadi_LZ_package.lz_exhaustive_wrapper import LZExhaustiveCalculator
    from hadi_LZ_package.lz_wrapper import LZProcessor # For lz_core.c access
except ImportError as e:
    print(f"ERROR: Could not import necessary modules: {e}")
    print(f"Sys.path: {sys.path}")
    sys.exit(1)

def int_to_binary_string(number, L):
    return format(number, f'0{L}b')

def run_exhaustive_test(L=20):
    print(f"--- LZ76 Exhaustive Test for L={L} ---")
    num_total_strings = 1 << L
    print(f"Total strings to process: {num_total_strings}")

    # 1. Using lz_exhaustive_generate
    print(f"\n1. Running lz_exhaustive_generate(L={L})...")
    exhaustive_calculator = LZExhaustiveCalculator()
    exhaustive_results = np.empty(num_total_strings, dtype=np.int32)
    
    start_time_exhaustive = time.perf_counter()
    try:
        # The wrapper already creates the numpy array and calls C.
        # Let's use the wrapper's method.
        exhaustive_results = exhaustive_calculator.calculate_all_lz76_counts(L)
        if exhaustive_results is None: # Should not happen if L is valid
            raise Exception("calculate_all_lz76_counts returned None")
    except Exception as e:
        print(f"  ERROR in lz_exhaustive_generate: {e}")
        # In case of C error, results might not be filled or partially filled.
        # For safety, we can't proceed with verification if this fails badly.
        return
    time_exhaustive = time.perf_counter() - start_time_exhaustive
    print(f"  lz_exhaustive_generate completed in {time_exhaustive:.4f} seconds.")
    if num_total_strings > 0: 
        print(f"  Avg time per string (amortized by exhaustive): {time_exhaustive/num_total_strings:.10f}s")

    # 2. Using lz_core.c via LZProcessor (individual calls for verification)
    print(f"\n2. Running lz_core.c (via LZProcessor) for {num_total_strings} strings in batches...")
    core_lz_processor = LZProcessor()
    core_results_phrases = np.empty(num_total_strings, dtype=np.int32)
    
    # Generate all strings for lz_core batch processing first
    all_lz_core_test_strings = [int_to_binary_string(i, L) for i in range(num_total_strings)]

    start_time_core_batch = time.perf_counter()
    error_in_core_processing = False
    batch_size_for_core = 1048576 # Process in batches
    
    processed_count = 0
    for i in range(0, num_total_strings, batch_size_for_core):
        current_batch_strings = all_lz_core_test_strings[i : min(i + batch_size_for_core, num_total_strings)]
        if not current_batch_strings: continue

        try:
            scaled_complexity_batch = core_lz_processor.process_strings(current_batch_strings, symmetric=False, algorithm='lz76')
            
            if len(scaled_complexity_batch) != len(current_batch_strings):
                print(f"  ERROR: LZProcessor batch result length mismatch. Expected {len(current_batch_strings)}, got {len(scaled_complexity_batch)}")
                # Fill with error codes for this batch
                for k_idx in range(len(current_batch_strings)):
                    core_results_phrases[i + k_idx] = -98
                error_in_core_processing = True
                continue

            for j, scaled_complexity in enumerate(scaled_complexity_batch):
                string_idx_global = i + j
                if L == 0:
                    core_results_phrases[string_idx_global] = 0 if not current_batch_strings[j] else 1
                elif scaled_complexity < 0:
                    core_results_phrases[string_idx_global] = int(scaled_complexity) - 20
                else:
                    log_2_L = math.log2(L) if L > 0 else 1
                    if log_2_L == 0 and L==1: log_2_L = 1
                    if log_2_L == 0:
                        core_results_phrases[string_idx_global] = int(scaled_complexity)
                    else:
                        core_results_phrases[string_idx_global] = round(scaled_complexity / log_2_L)
        except Exception as e:
            print(f"  ERROR processing batch starting at index {i} with LZProcessor: {e}")
            for k_idx in range(len(current_batch_strings)):
                 core_results_phrases[i + k_idx] = -99
            error_in_core_processing = True
        
        processed_count += len(current_batch_strings)
        if (processed_count % (max(1, num_total_strings // 100) * batch_size_for_core if num_total_strings >=100 else batch_size_for_core)) < batch_size_for_core and processed_count > 0:
             progress = (processed_count / num_total_strings) * 100
             print(f"  lz_core.c batched processing progress: {progress:.2f}% ({processed_count}/{num_total_strings})")

    time_core_batch = time.perf_counter() - start_time_core_batch
    print(f"  lz_core.c batched processing completed in {time_core_batch:.4f} seconds.")
    if num_total_strings > 0:
        print(f"  Avg time per string (lz_core batched): {time_core_batch/num_total_strings:.10f}s")

    # 3. Verification
    print("\n3. Verifying results...")
    mismatches = 0
    if error_in_core_processing:
        print("  Verification potentially compromised due to errors in lz_core.c processing.")

    if len(exhaustive_results) != num_total_strings:
        print(f"  ERROR: Length mismatch for exhaustive_results. Expected {num_total_strings}, got {len(exhaustive_results)}")
        mismatches = num_total_strings # Consider all failed if length is wrong
    else:
        for i in range(num_total_strings):
            if exhaustive_results[i] != core_results_phrases[i]:
                if mismatches < 10: # Print first few mismatches
                    print(f"  MISMATCH for string index {i} (binary: {int_to_binary_string(i,L)}):")
                    print(f"    lz_exhaustive result: {exhaustive_results[i]}")
                    print(f"    lz_core estimated phrase count: {core_results_phrases[i]}")
                mismatches += 1

    if mismatches == 0:
        print("  Verification PASSED: All phrase counts match!")
    else:
        print(f"  Verification FAILED: {mismatches}/{num_total_strings} mismatches found.")

    print("\nExhaustive Test Finished.")


def run_distribution_test_and_verify(L_small=10):
    print(f"\n--- LZ76 Exhaustive Distribution Test for L={L_small} ---")
    num_total_strings = 1 << L_small
    
    exhaustive_calculator = LZExhaustiveCalculator()

    # 1. Get full results for small L to build reference distribution
    print(f"1. Calculating all phrase counts for L={L_small} to build reference distribution...")
    try:
        full_results_for_dist_calc = exhaustive_calculator.calculate_all_lz76_counts(L_small)
        if full_results_for_dist_calc is None:
            print("  ERROR: Failed to get full results for L_small.")
            return
    except Exception as e:
        print(f"  ERROR getting full results for L_small={L_small}: {e}")
        return
        
    max_obs_complexity_small = 0
    if len(full_results_for_dist_calc) > 0:
        max_obs_complexity_small = np.max(full_results_for_dist_calc)
    
    # Determine a reasonable max_complexity_to_track for the distribution function
    # Max possible LZ76 phrase count is L+1. So L_small + 2 is a safe minimum size.
    max_complexity_to_track_for_dist_func = max(L_small + 5, int(max_obs_complexity_small) + 2) 

    reference_distribution = np.zeros(max_complexity_to_track_for_dist_func, dtype=np.longlong)
    for count_val in full_results_for_dist_calc:
        if count_val < max_complexity_to_track_for_dist_func -1:
            reference_distribution[count_val] += 1
        else:
            reference_distribution[max_complexity_to_track_for_dist_func - 1] += 1 # Overflow bin
    print(f"  Reference distribution for L={L_small} (max_complexity_tracked={max_complexity_to_track_for_dist_func}):")
    for c, num in enumerate(reference_distribution):
        if num > 0: print(f"    Complexity {c}: {num} strings")

    # 2. Get distribution directly using the new C function
    print(f"\n2. Calculating distribution directly for L={L_small} using new C function...")
    try:
        direct_distribution = exhaustive_calculator.get_lz76_complexity_distribution(L_small, max_complexity_to_track_for_dist_func)
        if direct_distribution is None:
            print("  ERROR: Failed to get direct distribution.")
            return
    except Exception as e:
        print(f"  ERROR getting direct distribution for L={L_small}: {e}")
        return

    print(f"  Directly calculated distribution for L={L_small}:")
    for c, num in enumerate(direct_distribution):
        if num > 0: print(f"    Complexity {c}: {num} strings")

    # 3. Verify distributions match
    print("\n3. Verifying distributions...")
    if np.array_equal(reference_distribution, direct_distribution):
        print("  Distribution Verification PASSED for L={L_small}!")
    else:
        print("  Distribution Verification FAILED for L={L_small}.")
        print("    Reference (from full results):", reference_distribution)
        print("    Directly calculated:          ", direct_distribution)


def run_large_L_distribution_only(L_large=24, num_threads: int | None = None):
    print(f"\n--- LZ76 Exhaustive Distribution Only for L={L_large} (Threads: {num_threads if num_threads is not None else 'default'}) ---")
    print(f"(Verification against lz_core.c is not feasible for this L value due to 2^{L_large} individual computations)")
    num_total_strings = 1 << L_large
    print(f"Total strings to process implicitly: {num_total_strings}")

    exhaustive_calculator = LZExhaustiveCalculator()
    
    # Max possible LZ76 phrase count for string of length L is L+1.
    # So, array needs to be at least size L+2 to store counts for complexities 0 to L+1.
    max_complexity_to_track = L_large + 5 # Python wrapper also defaults to L+5

    print(f"Running lz76_exhaustive_distribution(L={L_large}, max_complexity_track={max_complexity_to_track}, num_threads={num_threads if num_threads is not None else 'default'})...")
    start_time = time.perf_counter()
    try:
        distribution = exhaustive_calculator.get_lz76_complexity_distribution(L_large, max_complexity_to_track, num_threads=num_threads)
        if distribution is None:
            print("  ERROR: Failed to get distribution for large L.")
            return
    except Exception as e:
        print(f"  ERROR calculating distribution for L={L_large}: {e}")
        return
    time_taken = time.perf_counter() - start_time
    print(f"  lz76_exhaustive_distribution for L={L_large} completed in {time_taken:.4f} seconds.")
    if num_total_strings > 0:
         print(f"  Effective avg time per string (amortized): {time_taken/num_total_strings:.12f}s")

    print(f"\n  LZ76 Phrase Count Distribution for L={L_large}:")
    for complexity_val, count in enumerate(distribution):
        if count > 0:
            print(f"    Complexity {complexity_val}: {count} strings")
    print("  (Note: Last bin is an overflow for complexities >= its index)")


if __name__ == "__main__":
    # --- Original benchmark for lz_exhaustive vs lz_core (batched) ---
    L_param_benchmark = 16 # Keep this smaller for quicker combined script run
    if len(sys.argv) > 1 and sys.argv[1] != "distribution_only":
        try:
            L_param_benchmark = int(sys.argv[1])
            if not (1 <= L_param_benchmark <= 20): 
                print("For benchmark mode, please choose L between 1 and 20.")
                sys.exit(1)
        except ValueError:
            print("Usage for benchmark: python test_lz_exhaustive.py [L_for_benchmark (1-20)]")
            sys.exit(1)
    print(f"Running benchmark for L={L_param_benchmark}")
    run_exhaustive_test(L=L_param_benchmark) 
    print("\n" + "="*70 + "\n")

    # --- Test for the distribution function ---
    # Verify distribution logic with a small L
    L_dist_verify = 10 # Small L for quick verification of distribution function itself
    print(f"Running distribution function verification for L={L_dist_verify}")
    run_distribution_test_and_verify(L_small=L_dist_verify)
    print("\n" + "="*70 + "\n")
    
    # Example of running distribution for a larger L (as requested, L=28 is too big for direct cmd line run)
    # You can call this specifically if needed, e.g. by modifying the script or from another script.
    # For command line, let's add a flag for it.
    if len(sys.argv) > 1 and sys.argv[1] == "distribution_only":
        L_dist_large = 24 # Default for "distribution_only" mode, up to L=28 is feasible for single run.
        threads_for_dist = None # Default to os.cpu_count() in wrapper
        if len(sys.argv) > 2:
            try:
                L_dist_large = int(sys.argv[2])
                if not (1 <= L_dist_large <= 28): # Max L for reasonable run time/memory for distribution array
                    print("For distribution_only mode, please choose L between 1 and 28.")
                    sys.exit(1)
                if len(sys.argv) > 3:
                    threads_for_dist = int(sys.argv[3])
                    if threads_for_dist <= 0:
                        print("Number of threads must be positive.")
                        sys.exit(1)
            except ValueError:
                print("Usage for distribution_only: python test_lz_exhaustive.py distribution_only [L_for_distribution (1-28)] [num_threads (optional)]")
                sys.exit(1)
        run_large_L_distribution_only(L_large=L_dist_large, num_threads=threads_for_dist)
    else:
        print(f"To run distribution for a large L (e.g., L=24), use: python {__file__} distribution_only [L_value] [num_threads_optional]") 