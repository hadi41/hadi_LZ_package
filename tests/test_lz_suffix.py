'''Test suite for LZ76 suffix tree implementations.

This script compares the correctness and performance of three different LZ76
implementations for calculating phrase counts (dictionary size):

1.  **PythonLZSuffixTree**: A pure Python implementation using an online suffix tree
    (from `hadi_LZ_package.python_backend.lz_suffix`).
2.  **LZSuffixTreeWrapper (Single Mode)**: The C-backed suffix tree implementation
    (from `hadi_LZ_package.lz_suffix_wrapper`, using `lz_suffix_combined.c`),
    processing strings by adding characters one by one.
3.  **LZSuffixTreeWrapper (Batch Mode)**: The same C-backed wrapper, but using its
    `compute_lz76_complexity_batch` method.
4.  **Reference Inefficient Python LZ76**: A direct, less optimized Python LZ76
    phrase counting function (`get_inefficient_lz76_phrase_count` copied from
    `lz_inefficient.py` and adapted here) used as a baseline for correctness.

The script generates random binary strings, processes them with each method,
compares the resulting phrase counts, and reports timing information.

Command-line arguments can be used to specify the number of test strings and
their minimum/maximum lengths.

Usage:
    python test_lz_suffix.py [num_strings] [min_len] [max_len]

Example:
    python test_lz_suffix.py 1000 50 150
'''
import random
import sys
import os
import time
# import numpy as np # Not strictly needed here as we compare integer phrase counts.

# --- Path Setup --- 
# Add the project root to sys.path to allow importing from hadi_LZ_package
_project_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _project_root_dir not in sys.path:
    sys.path.insert(0, _project_root_dir)

try:
    from hadi_LZ_package.python_backend.lz_suffix import LZSuffixTree as PythonLZSuffixTree
    from hadi_LZ_package.lz_suffix_wrapper import LZSuffixTreeWrapper
    # The reference lz_inefficient.py LZ76 logic is copied directly into this file
    # as get_inefficient_lz76_phrase_count to avoid external dependencies for this test script
    # and to ensure it calculates raw phrase counts without numpy scaling.
except ImportError as e:
    print(f"ERROR: Could not import necessary LZ wrapper classes: {e}")
    print("Ensure hadi_LZ_package is installed or in PYTHONPATH, and all modules are accessible.")
    print(f"Current sys.path: {sys.path}")
    sys.exit(1)

def generate_random_binary_string(min_len: int = 30, max_len: int = 100) -> str:
    """Generates a random binary string of a specified length range.

    Args:
        min_len (int, optional): Minimum length of the string. Defaults to 30.
        max_len (int, optional): Maximum length of the string. Defaults to 100.

    Returns:
        str: A randomly generated binary string.
             Returns an empty string if max_len < min_len or if max_len is < 0.
    """
    if max_len < min_len or max_len < 0:
        return ""
    length = random.randint(min_len, max_len)
    if length == 0: 
        return ""
    return "".join(random.choices(['0', '1'], k=length))


# Copied and modified from lz_inefficient.py to get raw dictionary_size (phrase count).
# This serves as a baseline Python implementation for LZ76 phrase counting.
def get_inefficient_lz76_phrase_count(input_string: str) -> int:
    """Calculates LZ76 phrase count using a basic, less optimized Python approach.
    
    This function mimics the core logic of an inefficient LZ76 parsing to count
    the number of phrases (dictionary size). It's used here as a reference for
    verifying the suffix tree based implementations.

    The logic: iterate through the string, building a `current_word`. If this
    `current_word` is not found as a substring in the history of (`parsed_text` + 
    `current_word` without its last character), then `current_word` becomes a new phrase,
    is added to `parsed_text`, and `dictionary_size` is incremented.

    Args:
        input_string (str): The string to analyze.

    Returns:
        int: The number of phrases in the LZ76 dictionary (phrase count).
    """
    if not input_string: # Handle empty string explicitly
        return 0

    current_word = ''
    parsed_text_history = '' # Concatenation of completed phrases
    remaining_string = input_string
    dictionary_size = 0
    
    while remaining_string != '':
        next_character = remaining_string[0]
        current_word += next_character
        remaining_string = remaining_string[1:]
        # No l_cw needed for `in` operator

        # Search space is previously parsed phrases + current word prefix
        search_space = parsed_text_history + current_word[:-1]
        
        is_substring_in_history = current_word in search_space
        
        if not is_substring_in_history:
            dictionary_size += 1
            parsed_text_history += current_word
            current_word = '' # Reset for the next phrase
            
    if current_word != '': # Account for the last phrase if any
        dictionary_size += 1
    return dictionary_size

def run_lz_tests(num_strings: int = 10000, min_str_len: int = 30, max_str_len: int = 100):
    """Runs tests comparing Python and C LZ76 suffix tree implementations.

    Generates random binary strings and processes them using:
    - Pure Python LZSuffixTree (single character additions).
    - C-backed LZSuffixTreeWrapper (single character additions).
    - C-backed LZSuffixTreeWrapper (batch processing).
    - A reference inefficient Python LZ76 phrase counter.

    Compares phrase counts and reports timing for each method.

    Args:
        num_strings (int, optional): Number of random strings for testing. Defaults to 10,000.
        min_str_len (int, optional): Minimum length of generated strings. Defaults to 30.
        max_str_len (int, optional): Maximum length of generated strings. Defaults to 100.
    """
    print(f"--- Starting LZ76 Suffix Tree Implementation Tests ---")
    print(f"Number of test strings: {num_strings:,}")
    print(f"String length range: {min_str_len} - {max_str_len}")
    
    overall_success_count = 0
    overall_fail_count = 0
    
    total_py_st_time_single = 0
    total_c_st_wrapper_time_single = 0
    total_inefficient_py_time_single = 0

    # Generate all test strings upfront for consistent comparison
    print(f"\nGenerating {num_strings:,} test strings...")
    batch_test_strings = []
    for _ in range(num_strings):
        s = generate_random_binary_string(min_len=min_str_len, max_len=max_str_len)
        # Ensure non-empty for consistent testing, though LZ76 can handle empty.
        if not s and (min_str_len > 0 or max_str_len > 0): 
            s = "0" # Default to "0" if generation unexpectedly yields empty for non-zero length request
        batch_test_strings.append(s)
    print("Test string generation complete.")

    # --- Test Single String Processing (character by character) --- 
    print("\n--- Stage 1: Single String Processing (Character by Character) --- ")
    single_mode_results_python_st = []
    single_mode_results_c_wrapper = []
    single_mode_results_inefficient = []

    for i, test_str in enumerate(batch_test_strings):
        current_iter_failed = False
        # 1. Pure Python LZSuffixTree
        py_lz_st_instance = PythonLZSuffixTree() # Fresh instance each time
        start_t = time.perf_counter()
        try:
            for char_s in test_str:
                py_lz_st_instance.add_character(char_s)
            py_st_phrase_count = py_lz_st_instance.compute_lz76_complexity()
            single_mode_results_python_st.append(py_st_phrase_count)
        except Exception as e_py_st:
            print(f"  ERROR (PythonLZSuffixTree, str {i+1}): {e_py_st} for '{test_str[:30]}...'")
            single_mode_results_python_st.append(-1)
            current_iter_failed = True
        total_py_st_time_single += (time.perf_counter() - start_t)

        # 2. C-backed LZSuffixTreeWrapper (single char mode)
        c_lz_wrapper_instance_single = LZSuffixTreeWrapper() # Fresh instance
        start_t = time.perf_counter()
        try:
            for char_s in test_str:
                c_lz_wrapper_instance_single.add_character(char_s)
            c_wrapper_phrase_count_single = c_lz_wrapper_instance_single.compute_lz76_complexity()
            single_mode_results_c_wrapper.append(c_wrapper_phrase_count_single)
        except Exception as e_c_single:
            print(f"  ERROR (LZSuffixTreeWrapper single, str {i+1}): {e_c_single} for '{test_str[:30]}...'")
            single_mode_results_c_wrapper.append(-2)
            current_iter_failed = True
        total_c_st_wrapper_time_single += (time.perf_counter() - start_t)

        # 3. Reference Inefficient Python LZ76
        start_t = time.perf_counter()
        try:
            inefficient_ref_count = get_inefficient_lz76_phrase_count(test_str)
            single_mode_results_inefficient.append(inefficient_ref_count)
        except Exception as e_ineff:
            print(f"  ERROR (Inefficient Python LZ76, str {i+1}): {e_ineff} for '{test_str[:30]}...'")
            single_mode_results_inefficient.append(-3)
            current_iter_failed = True
        total_inefficient_py_time_single += (time.perf_counter() - start_t)

        # Comparison for this string (only if all succeeded so far for this string)
        if not current_iter_failed:
            if not (py_st_phrase_count == c_wrapper_phrase_count_single == inefficient_ref_count):
                print(f"  MISMATCH (Single, str {i+1}) for '{test_str[:70]}...':")
                print(f"    PythonLZSuffixTree: {py_st_phrase_count}")
                print(f"    LZSuffixTreeWrapper (single): {c_wrapper_phrase_count_single}")
                print(f"    Inefficient Python Ref: {inefficient_ref_count}")
                overall_fail_count += 1
            else:
                overall_success_count += 1
        else:
            overall_fail_count += 1 # Count if any part of this iteration failed
        
        if (i + 1) % max(1, num_strings // 20) == 0 or (i+1) == num_strings: # Print progress ~20 times
            print(f"  Single processing progress: {((i + 1) / num_strings) * 100:.1f}% ({i+1}/{num_strings}) S:{overall_success_count} F:{overall_fail_count}")

    print("--- Stage 1 Finished ---")

    # --- Test Batch Processing (LZSuffixTreeWrapper only) ---
    print("\n--- Stage 2: Batch String Processing (LZSuffixTreeWrapper) --- ")
    c_lz_wrapper_batch_instance = LZSuffixTreeWrapper() # One instance for all batch strings
    start_t_batch = time.perf_counter()
    batch_results_c_wrapper: list[int] = []
    try:
        batch_results_c_wrapper = c_lz_wrapper_batch_instance.compute_lz76_complexity_batch(batch_test_strings)
    except Exception as e_batch:
        print(f"  ERROR during LZSuffixTreeWrapper batch processing: {e_batch}")
        # Mark all batch results as failed if the batch call itself fails
        batch_results_c_wrapper = [-4] * num_strings 
    total_c_st_wrapper_time_batch = time.perf_counter() - start_t_batch
    
    # Compare batch results with the reference (inefficient Python results from single mode)
    batch_mode_success_count = 0
    batch_mode_fail_count = 0
    if len(batch_results_c_wrapper) == num_strings:
        for i in range(num_strings):
            if single_mode_results_inefficient[i] >= 0: # Only compare if reference was good
                if batch_results_c_wrapper[i] == single_mode_results_inefficient[i]:
                    batch_mode_success_count += 1
                else:
                    print(f"  MISMATCH (Batch C vs. InefficientPy, str {i+1}) for '{batch_test_strings[i][:50]}...':")
                    print(f"    Batch C Wrapper: {batch_results_c_wrapper[i]}, Inefficient Ref: {single_mode_results_inefficient[i]}")
                    batch_mode_fail_count += 1
            elif batch_results_c_wrapper[i] < 0: # Both reference and batch item show error
                batch_mode_fail_count +=1 # Count as failure for batch consistency check
    else:
        print(f"  ERROR: Batch result length mismatch. Expected {num_strings}, got {len(batch_results_c_wrapper)}.")
        batch_mode_fail_count = num_strings # All fail if lengths differ
    
    overall_success_count += batch_mode_success_count
    overall_fail_count += batch_mode_fail_count
    print("--- Stage 2 Finished ---")

    # --- Summary --- 
    print(f"\n--- Test Summary for LZ76 Suffix Tree Implementations ({num_strings} strings) ---")
    print(f"Overall Successes: {overall_success_count}")
    print(f"Overall Failures: {overall_fail_count}")
    print("\nAverage Times Per String (Single Processing Mode):")
    if num_strings > 0:
        print(f"  PythonLZSuffixTree (char-by-char):   {total_py_st_time_single/num_strings:.8e}s")
        print(f"  LZSuffixTreeWrapper (char-by-char): {total_c_st_wrapper_time_single/num_strings:.8e}s")
        print(f"  Inefficient Python LZ76 (ref):     {total_inefficient_py_time_single/num_strings:.8e}s")
    print("\nTotal Time for Batch Processing (LZSuffixTreeWrapper):")
    print(f"  Total for {num_strings:,} strings: {total_c_st_wrapper_time_batch:.4f}s")
    if num_strings > 0 and total_c_st_wrapper_time_batch > 0:
        print(f"  Avg per string (batch mode): {total_c_st_wrapper_time_batch/num_strings:.8e}s")

    if overall_fail_count == 0 and num_strings > 0:
        print("\nAll tests passed successfully!")
    elif num_strings == 0:
        print("\nNo tests run (num_strings was 0).")
    else:
        print(f"\n{overall_fail_count} test(s) failed. Please review mismatches above.")
        # sys.exit(1) # Exit with error code if any test fails

if __name__ == "__main__":
    num_test_strings_arg = 1000  # Default to smaller number for quick __main__ test
    min_len_arg = 20
    max_len_arg = 50
    
    if len(sys.argv) > 1:
        try:
            num_test_strings_arg = int(sys.argv[1])
            if num_test_strings_arg <=0: raise ValueError("Number of strings must be positive.")
            if len(sys.argv) > 2: 
                min_len_arg = int(sys.argv[2])
                if min_len_arg <=0: raise ValueError("Min length must be positive.")
            if len(sys.argv) > 3: 
                max_len_arg = int(sys.argv[3])
                if max_len_arg < min_len_arg: raise ValueError("Max length must be >= min length.")
        except ValueError as e:
            print(f"Invalid argument: {e}")
            print("Usage: python test_lz_suffix.py [num_strings (int>0)] [min_len (int>0)] [max_len (int>=min_len)]")
            sys.exit(1)

    run_lz_tests(num_strings=num_test_strings_arg, min_str_len=min_len_arg, max_str_len=max_len_arg) 