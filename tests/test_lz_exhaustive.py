'''Test suite for LZ76 exhaustive calculation functionalities.

This script tests the `LZExhaustiveCalculator` wrapper and the underlying C functions
from `lz_exhaustive.c`. It includes tests for:

1.  **Correctness of `lz76_exhaustive_generate`**: 
    Compares the phrase counts for all 2^L binary strings obtained from the
    `lz_exhaustive_generate` C function (via `calculate_all_lz76_counts` wrapper)
    against results obtained by processing each string individually using the 
    `lz_core.c` implementation (via `LZProcessor`). This is done for a moderately
    sized L (e.g., L=16 by default).

2.  **Correctness of `lz76_exhaustive_distribution`**: 
    For a small L (e.g., L=10), it first computes all individual phrase counts,
    builds a reference distribution from these counts, and then compares it against
    the distribution obtained directly from the `get_lz76_complexity_distribution`
    wrapper method (which calls the `lz76_exhaustive_distribution` C function).

3.  **Execution of `lz76_exhaustive_distribution` for large L**: 
    Provides a way to run the distribution calculation for larger L values where
    full verification is not feasible due to the 2^L complexity. This is primarily
    for observing performance and generating large distributions.

Command-line arguments allow specifying L values for different tests and optionally
the number of threads for OpenMP-enabled C functions.

Usage Examples:
  - `python test_lz_exhaustive.py`: Runs benchmark (L=16) and distribution verification (L=10).
  - `python test_lz_exhaustive.py 18`: Runs benchmark for L=18.
  - `python test_lz_exhaustive.py distribution_only 24`: Runs large L distribution for L=24.
  - `python test_lz_exhaustive.py distribution_only 22 4`: Runs large L distribution for L=22 with 4 threads.
'''
import sys
import os
import time
import math
import numpy as np

# --- Path Setup ---
# Add the project root to sys.path to allow importing from hadi_LZ_package
_project_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _project_root_dir not in sys.path:
    sys.path.insert(0, _project_root_dir)

try:
    from hadi_LZ_package.lz_exhaustive_wrapper import LZExhaustiveCalculator
    from hadi_LZ_package.lz_wrapper import LZProcessor # For access to lz_core.c implementations
except ImportError as e:
    print(f"ERROR: Could not import necessary modules from hadi_LZ_package: {e}")
    print("Ensure that hadi_LZ_package is installed or properly added to your PYTHONPATH.")
    print(f"Current sys.path: {sys.path}")
    sys.exit(1)

def int_to_binary_string(number: int, L: int) -> str:
    """Converts an integer to its L-bit binary string representation.

    Args:
        number: The integer to convert.
        L: The desired length of the binary string (padded with leading zeros if needed).

    Returns:
        The L-bit binary string.
    """
    return format(number, f'0{L}b')

def run_exhaustive_test(L: int = 16):
    """Tests `lz76_exhaustive_generate` against individual `lz_core.c` calculations.

    For a given length `L`:
    1. Calls `LZExhaustiveCalculator.calculate_all_lz76_counts(L)` to get phrase counts
       for all 2^L binary strings using the `lz_exhaustive.c` backend.
    2. For each of the 2^L strings, calculates its LZ76 complexity (phrase count)
       using the `LZProcessor` (which calls `lz_core.c`). The raw complexity value
       from `lz_core.c` (dict_size * log2(L)) is converted back to phrase count.
    3. Compares the two sets of results for mismatches.

    Args:
        L (int, optional): The length of binary strings to test. Defaults to 16.
                           Recommended L <= 20 for reasonable execution time.
    """
    print(f"--- LZ76 Exhaustive Correctness Test for L={L} ---")
    if L > 20:
        print(f"Warning: L={L} is > 20. This test involves 2^{L+1} LZ computations and may be very slow.", file=sys.stderr)
    
    num_total_strings = 1 << L
    print(f"Total strings to process: {num_total_strings:,}")

    # 1. Get results from lz_exhaustive_generate (via wrapper)
    print(f"\n1. Calling LZExhaustiveCalculator.calculate_all_lz76_counts(L={L})...")
    exhaustive_calculator = LZExhaustiveCalculator()
    exhaustive_phrase_counts: np.ndarray | None = None
    
    start_time_exhaustive = time.perf_counter()
    try:
        exhaustive_phrase_counts = exhaustive_calculator.calculate_all_lz76_counts(L)
        if exhaustive_phrase_counts is None: 
            print("  ERROR: calculate_all_lz76_counts returned None unexpectedly.")
            return # Cannot proceed with verification
    except Exception as e:
        print(f"  ERROR calling calculate_all_lz76_counts: {e}")
        return # Cannot proceed
    time_exhaustive = time.perf_counter() - start_time_exhaustive
    print(f"  calculate_all_lz76_counts completed in {time_exhaustive:.4f} seconds.")
    if num_total_strings > 0 and time_exhaustive > 0:
        print(f"  Avg time per string (amortized by lz_exhaustive.c): {time_exhaustive/num_total_strings:.10e}s")

    # 2. Get results from lz_core.c (via LZProcessor) for each string for verification.
    print(f"\n2. Calculating LZ76 phrase counts for {num_total_strings:,} strings individually using LZProcessor (lz_core.c backend)... ")
    core_lz_processor = LZProcessor() # Uses default number of threads
    core_derived_phrase_counts = np.empty(num_total_strings, dtype=np.int32)
    
    # Generate all binary strings of length L to pass to LZProcessor
    all_binary_strings = [int_to_binary_string(i, L) for i in range(num_total_strings)]

    start_time_core_batch = time.perf_counter()
    error_in_core_processing = False
    # Process in batches to avoid passing extremely large Python lists to LZProcessor at once
    # although LZProcessor itself batches to C. This is more about managing Python side memory for `all_binary_strings` if L is huge.
    # For L=20, 1 million strings. A batch of 2^18 = 262144 seems reasonable.
    batch_size_for_core_verification = 1 << 18 if num_total_strings > (1 << 18) else num_total_strings
    if batch_size_for_core_verification == 0 and num_total_strings > 0 : batch_size_for_core_verification = num_total_strings

    processed_count = 0
    for i in range(0, num_total_strings, batch_size_for_core_verification):
        current_batch_strings = all_binary_strings[i : min(i + batch_size_for_core_verification, num_total_strings)]
        if not current_batch_strings: continue

        try:
            # LZProcessor.process_strings returns LZ76 complexity = dictionary_size * log2(L)
            scaled_complexity_values = core_lz_processor.process_strings(
                current_batch_strings, symmetric=False, algorithm='lz76'
            )
            
            if len(scaled_complexity_values) != len(current_batch_strings):
                print(f"  ERROR: LZProcessor batch result length mismatch. Expected {len(current_batch_strings)}, got {len(scaled_complexity_values)} for batch starting at index {i}")
                for k_idx_in_batch in range(len(current_batch_strings)):
                    core_derived_phrase_counts[i + k_idx_in_batch] = -98 # Error code
                error_in_core_processing = True
                continue # Skip to next batch

            # Convert scaled complexity back to phrase count (dictionary_size)
            log2_L_val = math.log2(L) if L > 1 else 0 # log2(1)=0. For L=1, phrase count = complexity.
            if L == 1 and log2_L_val == 0 : log2_L_val = 1 # Avoid division by zero if L=1, treat as if log2(L) effectively 1 for scaling

            for j_batch, scaled_val in enumerate(scaled_complexity_values):
                global_string_idx = i + j_batch
                if L == 0: # Empty string case (should not happen if L > 0)
                    core_derived_phrase_counts[global_string_idx] = 0 
                elif scaled_val < 0: # Error from C
                    core_derived_phrase_counts[global_string_idx] = int(scaled_val) - 100 # Propagate distinct error
                elif log2_L_val == 0: # Handles L=1 or if complexity was already phrase count
                    core_derived_phrase_counts[global_string_idx] = int(round(scaled_val))
                else:
                    core_derived_phrase_counts[global_string_idx] = int(round(scaled_val / log2_L_val))
        except Exception as e_proc:
            print(f"  ERROR processing batch with LZProcessor (start_idx {i}): {e_proc}")
            for k_idx_in_batch in range(len(current_batch_strings)):
                 core_derived_phrase_counts[i + k_idx_in_batch] = -99 # Error code
            error_in_core_processing = True
        
        processed_count += len(current_batch_strings)
        # Print progress for large L
        if L >=16 and ( (i // batch_size_for_core_verification) % max(1, (num_total_strings // batch_size_for_core_verification) // 10 ) == 0 or processed_count == num_total_strings) :
             progress = (processed_count / num_total_strings) * 100
             print(f"  LZProcessor verification progress: {progress:.1f}% ({processed_count:,}/{num_total_strings:,} strings processed)")

    time_core_batch = time.perf_counter() - start_time_core_batch
    print(f"  Individual LZ76 calculations (batched) completed in {time_core_batch:.4f} seconds.")
    if num_total_strings > 0 and time_core_batch > 0:
        print(f"  Avg time per string (LZProcessor individual): {time_core_batch/num_total_strings:.10e}s")

    # 3. Verification
    print("\n3. Verifying results between `lz_exhaustive_generate` and individual `lz_core` calculations...")
    mismatches = 0
    if error_in_core_processing:
        print("  WARNING: Verification potentially compromised due to errors during individual LZProcessor calculations.")

    if len(exhaustive_phrase_counts) != num_total_strings:
        print(f"  CRITICAL ERROR: Length mismatch for exhaustive_results. Expected {num_total_strings}, got {len(exhaustive_phrase_counts)}")
        mismatches = num_total_strings # Fail all if lengths don't match
    else:
        for i in range(num_total_strings):
            if exhaustive_phrase_counts[i] != core_derived_phrase_counts[i]:
                if mismatches < 10: # Print details for the first few mismatches
                    bin_str_for_mismatch = int_to_binary_string(i, L)
                    print(f"  MISMATCH for string index {i} (binary: {bin_str_for_mismatch}):")
                    print(f"    lz_exhaustive_generate result: {exhaustive_phrase_counts[i]}")
                    print(f"    lz_core.c derived phrase count: {core_derived_phrase_counts[i]}")
                mismatches += 1

    if mismatches == 0 and not error_in_core_processing:
        print(f"  Verification PASSED for L={L}: All {num_total_strings:,} phrase counts match!")
    else:
        print(f"  Verification FAILED for L={L}: {mismatches:,}/{num_total_strings:,} mismatches found.")

    print(f"--- Exhaustive Correctness Test for L={L} Finished ---")


def run_distribution_test_and_verify(L_small: int = 10):
    """Tests `lz76_exhaustive_distribution` against a manually constructed distribution.

    For a small `L` (default 10):
    1. Gets all 2^L phrase counts using `calculate_all_lz76_counts`.
    2. Constructs a reference distribution from these counts.
    3. Calls `get_lz76_complexity_distribution` to get the distribution directly.
    4. Compares the two distributions.

    Args:
        L_small (int, optional): The length L for this test. Defaults to 10.
    """
    print(f"\n--- LZ76 Exhaustive Distribution Correctness Test for L={L_small} ---")
    num_total_strings = 1 << L_small
    print(f"Verifying distribution function using 2^{L_small} = {num_total_strings:,} strings.")
    
    try:
        exhaustive_calculator = LZExhaustiveCalculator()
    except Exception as e_init:
        print(f"ERROR: Could not initialize LZExhaustiveCalculator for distribution test: {e_init}")
        return

    # 1. Get full results for L_small to build a reference distribution.
    print(f"1. Calculating all individual phrase counts for L={L_small} to build reference distribution...")
    try:
        all_phrase_counts_for_ref = exhaustive_calculator.calculate_all_lz76_counts(L_small)
        if all_phrase_counts_for_ref is None:
            print("  ERROR: Failed to get all phrase counts for reference distribution.")
            return
    except Exception as e_calc_all:
        print(f"  ERROR calculating all phrase counts for L={L_small}: {e_calc_all}")
        return
        
    # Determine the maximum observed complexity to size the reference distribution array.
    max_observed_complexity = 0
    if len(all_phrase_counts_for_ref) > 0:
        max_observed_complexity = np.max(all_phrase_counts_for_ref)
    
    # `max_complexity_to_track` for the C function needs to be at least max_observed_complexity + 1.
    # The wrapper for get_lz76_complexity_distribution defaults to L+5, which is usually fine.
    # We use a slightly larger size for our reference to be safe.
    ref_dist_size = max(L_small + 5, int(max_observed_complexity) + 2) 

    reference_distribution = np.zeros(ref_dist_size, dtype=np.longlong)
    for count_val in all_phrase_counts_for_ref:
        if 0 <= count_val < ref_dist_size -1: # Check bounds for safety
            reference_distribution[count_val] += 1
        elif count_val >= ref_dist_size -1: # Put into overflow bin
             reference_distribution[ref_dist_size - 1] += 1
        # Negative counts from errors in calculate_all_lz76_counts are ignored here.

    print(f"  Reference distribution constructed for L={L_small} (size: {ref_dist_size}):")
    # for c, num in enumerate(reference_distribution): # Can be verbose
    #     if num > 0: print(f"    Complexity {c}: {num:,} strings")

    # 2. Get distribution directly using the lz76_exhaustive_distribution C function.
    print(f"\n2. Calculating distribution directly for L={L_small} via get_lz76_complexity_distribution...")
    direct_distribution_from_c: np.ndarray | None = None
    try:
        # Use the same ref_dist_size for max_complexity_to_track for fair comparison.
        direct_distribution_from_c = exhaustive_calculator.get_lz76_complexity_distribution(
            L_small, 
            max_complexity_to_track=ref_dist_size, 
            num_threads=os.cpu_count() # Use multiple threads if available
        )
        if direct_distribution_from_c is None:
            print("  ERROR: get_lz76_complexity_distribution returned None.")
            return
    except Exception as e_direct_dist:
        print(f"  ERROR calling get_lz76_complexity_distribution for L={L_small}: {e_direct_dist}")
        return

    print(f"  Directly calculated distribution from C function for L={L_small} (size: {len(direct_distribution_from_c)}):")
    # for c, num in enumerate(direct_distribution_from_c):
    #     if num > 0: print(f"    Complexity {c}: {num:,} strings")

    # 3. Verify that the two distributions match.
    print("\n3. Verifying distributions match...")
    # Ensure both arrays are of the same effective length for comparison if one is shorter but ends in zeros.
    len_ref = len(reference_distribution)
    len_direct = len(direct_distribution_from_c)
    max_len_for_compare = max(len_ref, len_direct)
    
    ref_padded = np.pad(reference_distribution, (0, max_len_for_compare - len_ref), 'constant')
    direct_padded = np.pad(direct_distribution_from_c, (0, max_len_for_compare - len_direct), 'constant')

    if np.array_equal(ref_padded, direct_padded):
        print(f"  Distribution Verification PASSED for L={L_small}!")
    else:
        print(f"  Distribution Verification FAILED for L={L_small}.")
        # Find first mismatch for detailed output
        mismatch_idx = -1
        for i in range(max_len_for_compare):
            if ref_padded[i] != direct_padded[i]:
                mismatch_idx = i
                break
        print(f"    Mismatch found at complexity index: {mismatch_idx}" if mismatch_idx !=-1 else "    Mismatch details complex.")
        print(f"    Reference (len {len_ref}): {reference_distribution[:min(len_ref, 20)]} ...")
        print(f"    Direct C (len {len_direct}): {direct_distribution_from_c[:min(len_direct,20)]} ...")
    print(f"--- Distribution Correctness Test for L={L_small} Finished ---")


def run_large_L_distribution_only(L_target_large: int, num_threads: int | None = None):
    """Runs only the `get_lz76_complexity_distribution` for a large L.
    
    This is primarily for performance testing or generating distributions where
    full verification against individual string complexities is too slow.

    Args:
        L_target_large: The large L value.
        num_threads (int | None, optional): Number of threads to use. Defaults to wrapper default.
    """
    # This function is now part of run_large_lz_distribution.py, keeping a stub here for potential direct call if needed.
    print(f"\nRedirecting to run_large_lz_distribution.py functionality for L={L_target_large}.")
    print("Please use that script directly for large L distribution runs:")
    print(f"  python tests/run_large_lz_distribution.py {L_target_large} {num_threads if num_threads is not None else ''}")
    # For a direct minimal run here (less verbose than the dedicated script):
    # try:
    #     calculator = LZExhaustiveCalculator()
    #     print(f"Minimal run for L={L_target_large} distribution...")
    #     dist = calculator.get_lz76_complexity_distribution(L_target_large, num_threads=num_threads)
    #     if dist is not None:
    #         print(f"Distribution for L={L_target_large} calculated (first 10 bins): {dist[:10]}")
    #     else:
    #         print("Failed to get distribution.")
    # except Exception as e:
    #     print(f"Error in minimal large L run: {e}")

if __name__ == "__main__":
    # Default L for the main correctness test (exhaustive_results vs core_results_phrases)
    L_param_correctness_test = 16 
    # Default L for distribution verification (reference_distribution vs direct_distribution)
    L_param_dist_verification_test = 10 

    # Command-line argument parsing
    if len(sys.argv) > 1 and sys.argv[1].lower() == "distribution_only":
        # Mode: Run only large L distribution (delegated or minimal example)
        L_dist_large_run = 24 # Default L for this mode
        threads_dist_large_run = None
        if len(sys.argv) > 2:
            try:
                L_dist_large_run = int(sys.argv[2])
                if not (1 <= L_dist_large_run <= 35):
                    print("ERROR: For 'distribution_only' mode, L must be between 1 and 35.")
                    sys.exit(1)
                if len(sys.argv) > 3:
                    threads_dist_large_run = int(sys.argv[3])
                    if threads_dist_large_run <= 0:
                        print("ERROR: Number of threads must be positive.")
                        sys.exit(1)
            except ValueError:
                print("Usage: python test_lz_exhaustive.py distribution_only [L (1-35)] [num_threads (optional)]")
                sys.exit(1)
        # Note: The run_large_L_distribution_only function in this file now mostly points to the other script.
        # For a true large run, the user should use run_large_lz_distribution.py.
        # Here, we will just call it to show the redirection message.
        run_large_L_distribution_only(L_target_large=L_dist_large_run, num_threads=threads_dist_large_run)
    
    elif len(sys.argv) > 1:
        # Mode: Run correctness test with specified L
        try:
            L_param_correctness_test = int(sys.argv[1])
            if not (1 <= L_param_correctness_test <= 20): # Max L for this test due to 2*2^L operations
                print(f"ERROR: For correctness test, L must be between 1 and 20. Provided: {L_param_correctness_test}")
                sys.exit(1)
            # Distribution verification L will remain default or could also be made an argument.
        except ValueError:
            print(f"Usage: python {sys.argv[0]} [L_for_correctness_test (1-20)]")
            print(f"   or: python {sys.argv[0]} distribution_only [L_for_large_dist (1-35)] [threads]")
            sys.exit(1)
        
        print(f"Running Correctness Test with L={L_param_correctness_test}")
        run_exhaustive_test(L=L_param_correctness_test) 
        print("\n" + "="*80 + "\n")
        # Distribution verification test will run with its default L unless also parameterized.
        print(f"Running Distribution Verification Test with default L={L_param_dist_verification_test}")
        run_distribution_test_and_verify(L_small=L_param_dist_verification_test)
    else:
        # Default Mode: Run both tests with default L values
        print(f"Running Correctness Test with default L={L_param_correctness_test}")
        run_exhaustive_test(L=L_param_correctness_test) 
        print("\n" + "="*80 + "\n")
        print(f"Running Distribution Verification Test with default L={L_param_dist_verification_test}")
        run_distribution_test_and_verify(L_small=L_param_dist_verification_test)
    
    print("\n" + "="*80)
    print("All specified tests in test_lz_exhaustive.py finished.") 