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

def generate_random_binary_string(min_len=30, max_len=100):
    length = random.randint(min_len, max_len)
    return "".join(random.choices(['0', '1'], k=length))

def get_all_substrings(s):
    n = len(s)
    substrings = set()
    if not s: # Handle empty string case
        substrings.add("") # Empty string is a substring of itself
        return list(substrings)
    for i in range(n):
        for j in range(i, n):
            substrings.add(s[i:j+1])
    substrings.add("") # Add empty string as a pattern to test
    return list(substrings)

def run_tests(num_strings=10_000, min_str_len=30, max_str_len=100):
    print(f"Starting tests with {num_strings} strings (length {min_str_len}-{max_str_len})...")
    success_count = 0
    fail_count = 0
    total_py_time = 0
    total_c_time = 0

    for i in range(num_strings):
        test_string = generate_random_binary_string(min_len=min_str_len, max_len=max_str_len)
        
        current_test_failed = False

        # Test Python version
        start_time = time.perf_counter()
        py_tree = PythonOnlineSuffixTree()
        try:
            for char_val in test_string:
                py_tree.add_char(char_val)
            # py_tree.add_terminator() # Original test did not specify terminator, matching behavior
        except Exception as e:
            print(f"String {i+1}/{num_strings} FAILED (Python version) during add_char for string '{test_string}'. Error: {e}")
            fail_count += 1
            continue # Skip to next test string
        total_py_time += (time.perf_counter() - start_time)

        # Test C wrapper version
        start_time = time.perf_counter()
        try:
            c_tree_wrapper = OnlineSuffixTreeWrapper()
            for char_val in test_string:
                c_tree_wrapper.add_char(char_val)
            # c_tree_wrapper.add_terminator() # Match Python version
        except Exception as e:
            print(f"String {i+1}/{num_strings} FAILED (C wrapper) during add_char for string '{test_string}'. Error: {e}")
            # If C version fails creation or add_char, we can't compare further with this string.
            # Check if Python version also failed for this string; if so, it might be a problematic string.
            fail_count +=1
            continue
        total_c_time += (time.perf_counter() - start_time)

        # Test 1: Accumulated text (if the wrapper exposes it and it's meaningful for comparison)
        # py_text = py_tree.text
        # c_text_via_wrapper = c_tree_wrapper.get_internal_text()
        # if py_text != c_text_via_wrapper:
        #     print(f"String {i+1} FAILED: Text mismatch.")
        #     print(f"  Original: '{test_string}'")
        #     print(f"  Python:   '{py_text}'")
        #     print(f"  C (wrapper): '{c_text_via_wrapper}'")
        #     fail_count += 1
        #     current_test_failed = True
        #     # continue # Don't skip further checks for this string if text fails

        # Test 2: `find` method for all substrings and some non-substrings
        all_subs = get_all_substrings(test_string)
        possible_chars = ['0', '1', '$'] # Use binary chars, potentially terminator too
        non_subs = []
        # Generate a few small random binary strings as likely non-substrings
        for _ in range(5): # Generate 5 small random non-substrings
            non_sub_len = random.randint(3, 7)
            small_random_non_sub = "".join(random.choices(['0', '1'], k=non_sub_len))
            # Only add if it's not already a known substring for very short test_strings
            # and not already added.
            if small_random_non_sub not in all_subs and small_random_non_sub not in non_subs:
                 non_subs.append(small_random_non_sub)

        if test_string:
            non_subs.extend([
                test_string + random.choice(possible_chars),
                random.choice(possible_chars) + test_string,
                "abab", # A generic non-binary or unlikely string
                "01001000100001000001", # A longer fixed non-substring
            ])
            if '00000' not in test_string: non_subs.append('00000')
            if '11111' not in test_string: non_subs.append('11111')
        else: # for empty test_string
            non_subs.extend(["0", "1", "a"])
        
        patterns_to_test = all_subs + [s for s in non_subs if s and len(s) < 2*max_str_len] # Keep patterns reasonable
        patterns_to_test = list(set(patterns_to_test)) # Unique patterns

        for p_idx, p_to_test in enumerate(patterns_to_test):
            try:
                py_found = py_tree.find(p_to_test)
            except Exception as e:
                print(f"String {i+1} FAILED: Python find() raised an error for pattern '{p_to_test}' on string '{test_string}'. Error: {e}")
                if not current_test_failed: fail_count += 1
                current_test_failed = True
                break # Stop testing patterns for this string
            
            try:
                c_found = c_tree_wrapper.find(p_to_test)
            except Exception as e:
                print(f"String {i+1} FAILED: C wrapper find() raised an error for pattern '{p_to_test}' on string '{test_string}'. Error: {e}")
                if not current_test_failed: fail_count += 1
                current_test_failed = True
                break # Stop testing patterns for this string

            if py_found != c_found:
                print(f"String {i+1} FAILED: `find` mismatch for pattern '{p_to_test}'.")
                print(f"  Original string: '{test_string}' (len {len(test_string)})")
                print(f"  Python found: {py_found}, C wrapper found: {c_found}")
                # print(f"  Python text: '{py_tree.text}'")
                # print(f"  C wrap text: '{c_tree_wrapper.get_internal_text()}'")
                # py_tree.display() # This could be very verbose
                if not current_test_failed: fail_count += 1
                current_test_failed = True
                break 
        
        if not current_test_failed:
            success_count += 1
        
        if (i + 1) % (num_strings // 100 if num_strings >=100 else 1) == 0:
            progress = ((i + 1) / num_strings) * 100
            print(f"Progress: {progress:.2f}% ({i+1}/{num_strings}). Success: {success_count}, Fail: {fail_count}")

    print(f"\nTest Summary:")
    print(f"Total strings tested: {num_strings}")
    print(f"Successes: {success_count}")
    print(f"Failures: {fail_count}")
    print(f"Average Python add_char time: {total_py_time/num_strings:.6f}s" if num_strings > 0 else "N/A")
    print(f"Average C wrapper add_char time: {total_c_time/num_strings:.6f}s" if num_strings > 0 else "N/A")

    if fail_count == 0 and num_strings > 0:
        print("All tests passed!")
    elif num_strings == 0:
        print("No tests were run.")
    else:
        print(f"{fail_count} tests failed.")
        sys.exit(1) # Indicate failure

if __name__ == "__main__":
    # Check if C library exists, otherwise the wrapper will fail loudly.
    # The wrapper itself tries to load it and gives a hint.
    num_test_strings = 10_000
    min_len = 30
    max_len = 100
    
    # Allow overriding from command line for quick tests
    if len(sys.argv) > 1:
        try:
            num_test_strings = int(sys.argv[1])
            if len(sys.argv) > 2: min_len = int(sys.argv[2])
            if len(sys.argv) > 3: max_len = int(sys.argv[3])
        except ValueError:
            print("Usage: python test_online_suffix.py [num_strings] [min_len] [max_len]")
            sys.exit(1)

    run_tests(num_strings=num_test_strings, min_str_len=min_len, max_str_len=max_len)
