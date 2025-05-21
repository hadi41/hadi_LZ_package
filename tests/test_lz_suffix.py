import random
import sys
import os
import time
# import numpy as np # Not needed if we only extract dictionary_size from inefficient

# Adjust sys.path to allow importing modules from the project root
_project_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _project_root_dir not in sys.path:
    sys.path.insert(0, _project_root_dir)

try:
    from hadi_LZ_package.python_backend.lz_suffix import LZSuffixTree as PythonLZSuffixTree
    from hadi_LZ_package.lz_suffix_wrapper import LZSuffixTreeWrapper
    # We will copy the relevant LZ76 logic from lz_inefficient.py to avoid direct dependency on its numpy scaling for comparison
except ImportError as e:
    print(f"Error importing necessary modules: {e}")
    print(f"Current sys.path: {sys.path}")
    print(f"Attempted to add '{_project_root_dir}' to sys.path.")
    print("Please ensure the structure: project_root/hadi_LZ_package/[python_backend/lz_suffix.py, lz_suffix_wrapper.py] and project_root/tests/test_lz_suffix.py")
    sys.exit(1)

def generate_random_binary_string(min_len=30, max_len=100):
    length = random.randint(min_len, max_len)
    return "".join(random.choices(['0', '1'], k=length))


# Copied and modified from lz_inefficient.py to get raw dictionary_size (phrase count)
def get_inefficient_lz76_phrase_count(input_string: str) -> int:
    # n = len(input_string) # Not needed for raw dictionary_size
    current_word = ''
    parsed = ''
    remaining = input_string
    dictionary_size = 0
    while remaining != '':
        new_character = remaining[0]
        current_word += new_character
        remaining = remaining[1:]
        l_cw = len(current_word)
        included = False
        # Check if current_word is a substring of (parsed + current_word_prefix)
        # This is equivalent to checking if current_word has appeared before in the text processed so far in this manner.
        # The search text is effectively (parsed + current_word[:-1])
        # The text to search within should be `parsed` according to most LZ76 variant definitions focusing on unique phrases based on past *phrases*.
        # However, the specific implementation in lz_inefficient.LZ76 is:
        # for i in range(0, len(parsed)):
        #    if (parsed + current_word[:-1])[i:i+l_cw] == current_word:
        # This is checking against (parsed + current_word[:-1]).
        # A more standard check for if `current_word` is in `parsed` text:
        # if current_word in parsed: (This would be wrong for LZ76, which checks against the full text dynamically)
        # Let's stick to the provided logic for fair comparison against *that specific* inefficient version.
        
        # The loop in lz_inefficient.LZ76 seems to be trying to find `current_word` within `parsed_plus_prefix`.
        # `parsed_plus_prefix = parsed + current_word[:-1]`
        # The condition `parsed_plus_prefix[i:i+l_cw] == current_word` means `current_word` is a substring of `parsed_plus_prefix`.
        # This is the same as `current_word in (parsed + current_word[:-1])`
        # Note: `in` operator is efficient for this.

        search_text = parsed + (current_word[:-1] if len(current_word) > 0 else "")
        if current_word in search_text:
            included = True
        
        if not included:
            dictionary_size += 1
            parsed += current_word
            current_word = ''
            
    if current_word != '': # If loop finishes with a non-empty current_word
        dictionary_size += 1
    return dictionary_size


def run_lz_tests(num_strings=10_000, min_str_len=30, max_str_len=100):
    print(f"Starting LZ complexity tests (single and batch) with {num_strings} strings (length {min_str_len}-{max_str_len})...")
    success_count_single = 0
    fail_count_single = 0
    total_py_time = 0
    total_c_time = 0
    total_inefficient_time = 0

    # For batch test, prepare a list of strings first
    batch_test_strings = []
    for _ in range(num_strings):
        s = generate_random_binary_string(min_len=min_str_len, max_len=max_str_len)
        if not s: s = "0"
        batch_test_strings.append(s)

    # --- Test single processing --- (Loop for timing and comparison consistency)
    print("\n--- Testing Single String Processing ---")
    single_results_py = []
    single_results_c_wrapper = []
    single_results_inefficient = []

    for i, test_string in enumerate(batch_test_strings):
        current_test_failed_single = False
        # Python Suffix Tree version
        py_lz_tree = PythonLZSuffixTree()
        start_py_time_s = time.perf_counter()
        try:
            for char_val in test_string:
                py_lz_tree.add_character(char_val)
            py_complexity = py_lz_tree.compute_lz76_complexity()
            single_results_py.append(py_complexity)
        except Exception as e:
            print(f"String {i+1}/{num_strings} FAILED (Python SuffixTree LZ) for string '{test_string[:50]}...'. Error: {e}")
            fail_count_single += 1; current_test_failed_single = True
            single_results_py.append(-1) # Error placeholder
        total_py_time += (time.perf_counter() - start_py_time_s)

        # C wrapper Suffix Tree version
        c_lz_wrapper_s = LZSuffixTreeWrapper() # New instance for single test to be fair with batch re-use
        start_c_time_s = time.perf_counter()
        try:
            for char_val in test_string:
                c_lz_wrapper_s.add_character(char_val)
            c_complexity = c_lz_wrapper_s.compute_lz76_complexity()
            single_results_c_wrapper.append(c_complexity)
        except Exception as e:
            print(f"String {i+1}/{num_strings} FAILED (C SuffixTree LZ Wrapper - Single) for string '{test_string[:50]}...'. Error: {e}")
            if not current_test_failed_single: fail_count_single += 1; current_test_failed_single = True
            single_results_c_wrapper.append(-2) # Error placeholder
        total_c_time += (time.perf_counter() - start_c_time_s)

        # Inefficient Python version
        start_inefficient_time_s = time.perf_counter()
        try:
            inefficient_phrase_count = get_inefficient_lz76_phrase_count(test_string)
            single_results_inefficient.append(inefficient_phrase_count)
        except Exception as e:
            print(f"String {i+1}/{num_strings} FAILED (Inefficient Python LZ) for string '{test_string[:50]}...'. Error: {e}")
            if not current_test_failed_single: fail_count_single += 1; current_test_failed_single = True
            single_results_inefficient.append(-3) # Error placeholder
        total_inefficient_time += (time.perf_counter() - start_inefficient_time_s)

        if not current_test_failed_single:
            if not (py_complexity == c_complexity == inefficient_phrase_count):
                print(f"String {i+1} FAILED (Single Processing): LZ Phrase Count mismatch for string '{test_string[:70]}...'.")
                print(f"  Python SuffixTree: {py_complexity}, C Wrapper: {c_complexity}, Inefficient: {inefficient_phrase_count}")
                fail_count_single += 1; current_test_failed_single = True
            else:
                success_count_single += 1
        
        if (i + 1) % (num_strings // 100 if num_strings >=100 else 1) == 0:
            print(f"Single Progress: {((i + 1) / num_strings) * 100:.2f}% ({i+1}/{num_strings}). Success: {success_count_single}, Fail: {fail_count_single}")

    # --- Test batch processing --- 
    print("\n--- Testing Batch String Processing ---")
    c_lz_wrapper_batch = LZSuffixTreeWrapper() # Single wrapper instance for batch processing
    start_batch_time = time.perf_counter()
    try:
        batch_results_c = c_lz_wrapper_batch.compute_lz76_complexity_batch(batch_test_strings)
    except Exception as e:
        print(f"Batch processing FAILED. Error: {e}")
        batch_results_c = [-4] * num_strings # Error placeholder
        fail_count_single = num_strings # Mark all as failed for summary consistency if batch itself fails
    total_batch_c_time = time.perf_counter() - start_batch_time

    # Compare batch results with single inefficient results (as a reference)
    batch_success_count = 0
    batch_fail_count = 0
    if len(batch_results_c) == num_strings:
        for i in range(num_strings):
            if single_results_inefficient[i] >= 0: # If inefficient didn't fail for this string
                if batch_results_c[i] == single_results_inefficient[i]:
                    batch_success_count += 1
                else:
                    print(f"String {i+1} FAILED (Batch vs Inefficient): Mismatch for '{batch_test_strings[i][:50]}...'")
                    print(f"  Batch C Result: {batch_results_c[i]}, Inefficient Py Result: {single_results_inefficient[i]}")
                    batch_fail_count +=1
            elif batch_results_c[i] < 0: # Both seem to have errored (inefficient already marked)
                pass # Avoid double counting failure if inefficient was already problematic
    else:
        print(f"Batch result length mismatch: expected {num_strings}, got {len(batch_results_c)}")
        batch_fail_count = num_strings

    print(f"\nLZ Phrase Count Test Summary:")
    print(f"Total strings tested: {num_strings}")
    print(f"-- Single Processing Mode --")
    print(f"  Successes: {success_count_single}")
    print(f"  Failures: {fail_count_single}")
    print(f"  Avg Python SuffixTree time: {total_py_time/num_strings:.6f}s")
    print(f"  Avg C SuffixTree Wrapper (single) time: {total_c_time/num_strings:.6f}s")
    print(f"  Avg Inefficient Python LZ76 time: {total_inefficient_time/num_strings:.6f}s")
    print(f"-- Batch Processing Mode (C Wrapper) --")
    print(f"  Successes (vs Inefficient): {batch_success_count}")
    print(f"  Failures (vs Inefficient or batch error): {batch_fail_count}")
    print(f"  Total C Wrapper Batch time for {num_strings} strings: {total_batch_c_time:.6f}s")
    if num_strings > 0 : print(f"  Avg C Wrapper Batch time per string: {total_batch_c_time/num_strings:.8f}s")


    if fail_count_single == 0 and batch_fail_count == 0 and num_strings > 0:
        print("\nAll LZ phrase count tests (single and batch) passed!")
    elif num_strings == 0:
        print("\nNo LZ tests were run.")
    else:
        print(f"\n{fail_count_single + batch_fail_count} LZ tests failed in total.")
        sys.exit(1) # Indicate failure

if __name__ == "__main__":
    num_test_strings = 10_000 
    min_len = 30 
    max_len = 100
    
    if len(sys.argv) > 1:
        try:
            num_test_strings = int(sys.argv[1])
            if len(sys.argv) > 2: min_len = int(sys.argv[2])
            if len(sys.argv) > 3: max_len = int(sys.argv[3])
        except ValueError:
            print("Usage: python test_lz_suffix.py [num_strings] [min_len] [max_len]")
            sys.exit(1)

    run_lz_tests(num_strings=num_test_strings, min_str_len=min_len, max_str_len=max_len) 