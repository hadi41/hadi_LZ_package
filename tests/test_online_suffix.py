'''Test suite for Online Suffix Tree implementations (Python vs. C-wrapper).

This script tests and compares two implementations of an online suffix tree:
1.  `PythonOnlineSuffixTree`: A pure Python implementation from the `python_backend`.
2.  `OnlineSuffixTreeWrapper`: A Python wrapper around a C implementation 
    (presumably `online_suffix.c` compiled to a shared library).

The primary test (`run_tests`) performs the following for a number of randomly
generated binary strings:
    - Builds a suffix tree using both the Python and C-wrapper implementations by
      adding characters one by one.
    - Generates all substrings of the test string and a set of likely non-substrings.
    - For each of these patterns, it calls the `find()` method on both trees and
      verifies that their results (found or not found) are identical.
    - Measures and reports the average time taken for character addition by each
      implementation.

Command-line arguments can be used to specify the number of test strings and their
minimum/maximum lengths.

Usage:
    python test_online_suffix.py [num_strings] [min_len] [max_len]

Example:
    python test_online_suffix.py 1000 50 150
'''
import random
import sys
import os
import time

# Determine the project root directory (parent of 'tests' and 'hadi_LZ_package' package dir)
# __file__ is expected to be /path/to/project_root/tests/test_online_suffix.py
# So, project_root should be /path/to/project_root
_project_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _project_root_dir not in sys.path:
    sys.path.insert(0, _project_root_dir)

try:
    # Assuming 'hadi_LZ_package' is the package directory inside _project_root_dir
    from hadi_LZ_package.python_backend.online_suffix import OnlineSuffixTree as PythonOnlineSuffixTree
    from hadi_LZ_package.online_suffix_wrapper import OnlineSuffixTreeWrapper
except ImportError as e:
    print(f"Error importing necessary modules: {e}")
    print(f"Current sys.path: {sys.path}")
    print(f"Attempted to add '{_project_root_dir}' to sys.path for relative imports.")
    print("Please ensure the project structure is: ")
    print("project_root/")
    print("├── hadi_LZ_package/  (the package)")
    print("│   ├── python_backend/online_suffix.py")
    print("│   └── online_suffix_wrapper.py")
    print("└── tests/")
    print("    └── test_online_suffix.py (this file)")
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

def get_all_substrings(s: str) -> list[str]:
    """Generates a list of all unique substrings of a given string, including empty string.

    Args:
        s: The input string.

    Returns:
        A list of all unique substrings of `s`.
    """
    n = len(s)
    substrings = set() # Use a set to store unique substrings
    # Add empty string as per original logic, it's a valid pattern for find()
    substrings.add("") 
    
    if not s: # If input string is empty, only empty string is a substring.
        return list(substrings)
        
    for i in range(n):
        for j in range(i, n):
            substrings.add(s[i:j+1])
    return list(substrings)

def run_tests(num_strings: int = 10000, min_str_len: int = 30, max_str_len: int = 100):
    """Runs correctness and timing tests for Python vs C-wrapped suffix tree.

    For each generated random string, it:
    1. Builds the suffix tree using `PythonOnlineSuffixTree`.
    2. Builds the suffix tree using `OnlineSuffixTreeWrapper` (C backend).
    3. Generates a set of test patterns (all substrings and some non-substrings).
    4. Compares the `find()` results for all patterns between the two trees.
    5. Accumulates timing data for `add_char` operations.

    Args:
        num_strings (int, optional): Number of random strings for testing. Defaults to 10,000.
        min_str_len (int, optional): Minimum length of generated strings. Defaults to 30.
        max_str_len (int, optional): Maximum length of generated strings. Defaults to 100.
    """
    print(f"--- Starting Online Suffix Tree Correctness & Performance Tests ---")
    print(f"Number of test strings: {num_strings:,}")
    print(f"String length range: {min_str_len}-{max_str_len}")
    
    success_count = 0
    fail_count = 0
    total_py_add_char_time = 0
    total_c_wrapper_add_char_time = 0

    for i in range(num_strings):
        test_string = generate_random_binary_string(min_len=min_str_len, max_len=max_str_len)
        current_test_iteration_failed = False # Tracks if any part of *this* string's test fails

        # --- Test Python Suffix Tree --- 
        py_tree = PythonOnlineSuffixTree()
        start_py_build_time = time.perf_counter()
        try:
            for char_val in test_string:
                py_tree.add_char(char_val)
        except Exception as e_py_build:
            print(f"  ERROR (PythonOnlineSuffixTree build, str {i+1}): {e_py_build} for '{test_string[:50]}...'")
            fail_count += 1
            current_test_iteration_failed = True # Mark this iteration failed
            # Continue to next string as we can't compare if build fails.
            # Ensure time isn't added if it failed mid-way if that makes sense for avg.
            # Here, we add time up to failure point for build, find won't run.
            total_py_add_char_time += (time.perf_counter() - start_py_build_time)
            continue 
        total_py_add_char_time += (time.perf_counter() - start_py_build_time)

        # --- Test C-Wrapped Suffix Tree --- 
        c_tree_wrapper = None # Ensure it's defined for finally block
        start_c_build_time = time.perf_counter()
        try:
            c_tree_wrapper = OnlineSuffixTreeWrapper()
            for char_val in test_string:
                c_tree_wrapper.add_char(char_val)
        except Exception as e_c_build:
            print(f"  ERROR (OnlineSuffixTreeWrapper build, str {i+1}): {e_c_build} for '{test_string[:50]}...'")
            if not current_test_iteration_failed: fail_count += 1 # Avoid double count if Python also failed
            current_test_iteration_failed = True
            total_c_wrapper_add_char_time += (time.perf_counter() - start_c_build_time)
            if c_tree_wrapper and hasattr(c_tree_wrapper, '_c_tree_state') and c_tree_wrapper._c_tree_state:
                 c_tree_wrapper.c_lib.free_suffix_tree_c(c_tree_wrapper._c_tree_state)
                 c_tree_wrapper._c_tree_state = None
            continue
        total_c_wrapper_add_char_time += (time.perf_counter() - start_c_build_time)

        # --- Test 1: Accumulated text (Optional, as primary test is `find`) ---
        # Note: `get_internal_text()` can be slow if called many times.
        # py_text_content = py_tree.text
        # c_text_content_wrapper = c_tree_wrapper.get_internal_text()
        # if py_text_content != c_text_content_wrapper:
        #     print(f"  MISMATCH (Text, str {i+1}) for '{test_string[:50]}...'")
        #     # ... (details) ...
        #     if not current_test_iteration_failed: fail_count += 1
        #     current_test_iteration_failed = True

        # --- Test 2: `find` method for all substrings and some non-substrings ---
        # Generate patterns once per test_string
        all_substrings_of_test_str = get_all_substrings(test_string)
        
        # Generate some likely non-substrings
        non_substrings_generated = []
        for _ in range(min(5, len(test_string) + 2)): # Generate a few, relative to string length
            len_non_sub = random.randint(1, max(1, len(test_string) // 2)) # Shorter non-substrings
            potential_non_sub = "".join(random.choices(['0', '1', 'x'], k=len_non_sub)) # Include 'x' to ensure it is non-binary
            if potential_non_sub not in all_substrings_of_test_str and potential_non_sub not in non_substrings_generated:
                non_substrings_generated.append(potential_non_sub)
        if test_string: # Add specific non-substrings if string is not empty
             non_substrings_generated.extend([
                test_string + random.choice(['0','1','$']),
                random.choice(['0','1','$']) + test_string,
                "alpha", "beta01"
            ])
        else: # For empty test_string, non-substrings are any non-empty string.
            non_substrings_generated.extend(["0", "1", "a"])
        
        patterns_for_find_test = list(set(all_substrings_of_test_str + non_substrings_generated))
        # Limit number of patterns to test if it becomes too large, e.g. for very long strings.
        if len(patterns_for_find_test) > 2 * len(test_string) + 10 and len(test_string) > 50:
            patterns_for_find_test = random.sample(patterns_for_find_test, 2 * len(test_string) + 10)

        for pattern_idx, pattern_to_test in enumerate(patterns_for_find_test):
            py_found_result, c_found_result = False, False # Default if error occurs
            try:
                py_found_result = py_tree.find(pattern_to_test)
            except Exception as e_py_find:
                print(f"  ERROR (Python find, str {i+1}, pattern '{pattern_to_test}'): {e_py_find}")
                if not current_test_iteration_failed: fail_count += 1
                current_test_iteration_failed = True; break 
            
            try:
                c_found_result = c_tree_wrapper.find(pattern_to_test)
            except Exception as e_c_find:
                print(f"  ERROR (C wrapper find, str {i+1}, pattern '{pattern_to_test}'): {e_c_find}")
                if not current_test_iteration_failed: fail_count += 1
                current_test_iteration_failed = True; break

            if py_found_result != c_found_result:
                print(f"  MISMATCH (find(), str {i+1}) for pattern '{pattern_to_test}' on string '{test_string[:70]}...'")
                print(f"    PythonOnlineSuffixTree found: {py_found_result}")
                print(f"    OnlineSuffixTreeWrapper found: {c_found_result}")
                if not current_test_iteration_failed: fail_count += 1
                current_test_iteration_failed = True; break 
        
        if not current_test_iteration_failed:
            success_count += 1
        
        # Cleanup C-wrapper instance for this iteration to free C memory if not using __del__ reliably
        if c_tree_wrapper and hasattr(c_tree_wrapper, '_c_tree_state') and c_tree_wrapper._c_tree_state:
            c_tree_wrapper.c_lib.free_suffix_tree_c(c_tree_wrapper._c_tree_state)
            c_tree_wrapper._c_tree_state = None

        if (i + 1) % max(1, num_strings // 20) == 0 or (i+1) == num_strings:
            progress = ((i + 1) / num_strings) * 100
            print(f"  Progress: {progress:.1f}% ({i+1}/{num_strings}). Current Success: {success_count}, Fail: {fail_count}")

    print(f"\n--- Online Suffix Tree Test Summary ---")
    print(f"Total strings tested: {num_strings:,}")
    print(f"Successful string tests (all patterns matched): {success_count:,}")
    print(f"Failed string tests (build error or pattern mismatch): {fail_count:,}")
    if num_strings > 0:
        print(f"Average PythonOnlineSuffixTree add_char time per string: {total_py_add_char_time/num_strings:.6e}s")
        print(f"Average OnlineSuffixTreeWrapper add_char time per string: {total_c_wrapper_add_char_time/num_strings:.6e}s")

    if fail_count == 0 and num_strings > 0:
        print("\nAll online suffix tree tests passed!")
    elif num_strings == 0:
        print("\nNo tests were run (num_strings was 0).")
    else:
        print(f"\n{fail_count} string test(s) failed. Please review mismatches or errors above.")
        # sys.exit(1) # Optionally exit with error code if tests fail

if __name__ == "__main__":
    # Check if C library exists, otherwise the wrapper will fail loudly.
    # The wrapper itself tries to load it and gives a hint.
    num_test_strings_arg = 1000 # Default to a smaller number for quick __main__ execution
    min_len_arg = 10
    max_len_arg = 50
    
    # Allow overriding from command line for quick tests
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
        except ValueError as e_args:
            print(f"Invalid argument: {e_args}")
            print("Usage: python test_online_suffix.py [num_strings (int>0)] [min_len (int>0)] [max_len (int>=min_len)]")
            sys.exit(1)

    run_tests(num_strings=num_test_strings_arg, min_str_len=min_len_arg, max_str_len=max_len_arg)
