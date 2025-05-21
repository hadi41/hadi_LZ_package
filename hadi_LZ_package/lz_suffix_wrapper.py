'''Python wrapper for LZ76 complexity calculation using a C-backed suffix tree.

This module provides the `LZSuffixTreeWrapper` class, an interface to the C functions
defined in `lz_suffix.c` (and `online_suffix.c`), which are compiled together into
a shared library (e.g., `lz_suffix_combined.dylib`).

It allows for online calculation of LZ76 complexity by adding characters one by one
to an internal state that uses a suffix tree for efficient phrase detection.
It also supports batch processing of multiple strings.

The wrapper handles:
- Loading the compiled C library (`lz_suffix_combined`).
- Defining `ctypes` for C function signatures from `lz_suffix.h`.
- Managing the C `LZSuffixTreeCState` object lifecycle.
- Python-side tracking of the current LZ phrase and dictionary for inspection.
- UTF-8 encoding for string data passed to C.
'''
import ctypes
import os
import sys # For sys.platform

class LZSuffixTreeWrapper:
    '''Wraps C functions for LZ76 complexity using a suffix tree.

    This class provides methods to add characters sequentially to build a string
    and compute its LZ76 complexity, leveraging a C implementation that uses
    an online suffix tree for efficiency. It also provides a batch processing method.

    Python-side attributes like `current_word` and `dictionary` are maintained
    to mirror the conceptual state of the LZ76 parsing process, allowing for
    inspection and status display similar to a pure Python implementation.

    Attributes:
        c_lib: `ctypes.CDLL` object for the loaded `lz_suffix_combined` C library.
        _c_lz_tree_state: C pointer (`ctypes.c_void_p`) to the `LZSuffixTreeCState` struct in C.
        current_word (str): The current LZ phrase being built (Python-side tracking).
        dictionary (List[str]): List of completed LZ phrases (Python-side tracking).
        current_text_py (str): The full text processed so far (Python-side tracking).
    '''
    def __init__(self, initial_text: str = ""):
        """Initializes the LZSuffixTreeWrapper.

        Loads the `lz_suffix_combined` C library, configures C function prototypes,
        creates the C `LZSuffixTreeCState`, and optionally processes an initial text.

        Args:
            initial_text: An optional string to initialize the LZ processor with.

        Raises:
            OSError: If the C shared library cannot be loaded.
            MemoryError: If the C library fails to create the `LZSuffixTreeCState`.
            AttributeError: If a required C function is not found in the library.
        """
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Library name for the combined lz_suffix and online_suffix functionalities.
        lib_filename = "lz_suffix_combined.so" 
        if os.name == 'nt':
            lib_filename = "lz_suffix_combined.dll"
        elif sys.platform == 'darwin':
            lib_filename = "lz_suffix_combined.dylib"
        
        lib_path = os.path.join(script_dir, "c_backend", lib_filename)

        try:
            self.c_lib = ctypes.CDLL(lib_path)
        except OSError as e:
            online_suffix_c_path = os.path.join("c_backend", "online_suffix.c")
            lz_suffix_c_path = os.path.join("c_backend", "lz_suffix.c")
            output_lib_path = os.path.join("c_backend", lib_filename)
            error_message = (
                f"Failed to load C library '{lib_filename}' from {lib_path}.\n"
                f"Please ensure it is compiled and in the correct location.\n"
                f"This library should combine '{online_suffix_c_path}' and '{lz_suffix_c_path}'.\n"
                f"Check the Makefile in c_backend or compile manually, e.g., on Linux/macOS:\n"
                f"  gcc -shared -o '{output_lib_path}' -fPIC '{online_suffix_c_path}' '{lz_suffix_c_path}'\n"
                f"Original error: {e}"
            )
            raise OSError(error_message)

        self.CLZSuffixTreeStatePtr = ctypes.c_void_p # Opaque pointer type

        # Configure C function prototypes from lz_suffix.h
        try:
            self.c_lib.create_lz_suffix_tree_c.restype = self.CLZSuffixTreeStatePtr
            self.c_lib.create_lz_suffix_tree_c.argtypes = []

            self.c_lib.free_lz_suffix_tree_c.restype = None
            self.c_lib.free_lz_suffix_tree_c.argtypes = [self.CLZSuffixTreeStatePtr]

            self.c_lib.add_char_lz_c.restype = ctypes.c_bool # Returns true if new phrase completed
            self.c_lib.add_char_lz_c.argtypes = [self.CLZSuffixTreeStatePtr, ctypes.c_char]

            self.c_lib.get_lz_complexity_c.restype = ctypes.c_int
            self.c_lib.get_lz_complexity_c.argtypes = [self.CLZSuffixTreeStatePtr]

            self.c_lib.reset_lz_suffix_tree_c.restype = None
            self.c_lib.reset_lz_suffix_tree_c.argtypes = [self.CLZSuffixTreeStatePtr]
            
            self.c_lib.process_lz_batch_c.restype = None # Void return, results via pointer
            self.c_lib.process_lz_batch_c.argtypes = [
                self.CLZSuffixTreeStatePtr,          # LZSuffixTreeCState* lz_tree_state
                ctypes.POINTER(ctypes.c_char_p),  # const char** strings_array
                ctypes.c_int,                     # int num_strings
                ctypes.POINTER(ctypes.c_int)      # int* results_array
            ]
        except AttributeError as e:
            raise AttributeError(f"A required function from lz_suffix.h was not found in '{lib_filename}'.\nOriginal error: {e}")

        self._c_lz_tree_state = self.c_lib.create_lz_suffix_tree_c()
        if not self._c_lz_tree_state:
            raise MemoryError("Failed to create C LZSuffixTreeCState (C function returned NULL).")

        # Python-side state variables for richer status and compatibility with pure Python logic.
        self.current_word = ""
        self.dictionary = []    
        self.current_text_py = "" # Full text processed string for display

        if initial_text:
            for char_val in initial_text:
                self.add_character(char_val)

    def add_character(self, char: str) -> bool:
        """Adds a single character to the LZ processor and updates LZ76 state.

        The character is processed by the C backend. Python-side attributes
        `current_word` and `dictionary` are updated based on whether the C
        function indicates a new LZ phrase was completed.

        Args:
            char: The character to add. Must be a single character string.

        Returns:
            bool: True if adding this character completed a new LZ phrase, False otherwise.

        Raises:
            ValueError: If `char` is not a single-byte encodable character string.
            UnicodeEncodeError: If `char` cannot be UTF-8 encoded.
        """
        if not isinstance(char, str) or len(char) != 1:
            raise ValueError("Input must be a single character string.")
        
        try:
            byte_char_array = char.encode('utf-8')
            if len(byte_char_array) != 1:
                raise ValueError(f"Character '{char}' (UTF-8: {byte_char_array.hex()}) is multi-byte. \nThe C backend for LZ suffix tree currently expects single-byte chars.")
            c_char_val = byte_char_array[0]
        except UnicodeEncodeError:
            raise ValueError(f"Character '{char}' could not be encoded to UTF-8.")

        self.current_text_py += char
        
        # Conceptual current word *before* C processing determines if it forms a new dictionary item.
        # If new_word_added_to_dict_c is true, it means `self.current_word + char` was the phrase.
        word_that_would_be_added = self.current_word + char

        new_word_added_to_dict_c = self.c_lib.add_char_lz_c(self._c_lz_tree_state, ctypes.c_char(c_char_val))

        if new_word_added_to_dict_c:
            self.dictionary.append(word_that_would_be_added) 
            self.current_word = ""  # Reset for the next phrase (which starts with the *next* char)
        else:
            # Character extended the current ongoing phrase
            self.current_word = word_that_would_be_added
        
        return new_word_added_to_dict_c

    def compute_lz76_complexity(self) -> int:
        """Computes and returns the current LZ76 complexity.

        The complexity is retrieved from the C backend state.
        It accounts for completed phrases and any current, unfinished phrase.

        Returns:
            int: The LZ76 complexity count.
        """
        if not self._c_lz_tree_state: 
            # This should ideally not happen if __init__ succeeded.
            raise RuntimeError("C LZ Suffix Tree State is not initialized.")
        return self.c_lib.get_lz_complexity_c(self._c_lz_tree_state)

    def reset(self) -> None:
        """Resets the LZ processor state to its initial empty state.
        
        Both the C backend state and Python-side tracking variables are reset.
        """
        if not self._c_lz_tree_state: return
        self.c_lib.reset_lz_suffix_tree_c(self._c_lz_tree_state)
        self.current_word = ""
        self.dictionary = []
        self.current_text_py = ""

    def compute_lz76_complexity_batch(self, strings: list[str]) -> list[int]:
        """Computes LZ76 complexity for a batch of strings using the C backend.

        The C function `process_lz_batch_c` is called, which reuses the
        internal C `LZSuffixTreeCState`, resetting it for each string.

        Args:
            strings: A list of Python strings to process.

        Returns:
            A list of integers, where each integer is the LZ76 complexity
            for the corresponding input string.

        Raises:
            RuntimeError: If the C tree state is not available.
            TypeError: If any item in the input list is not a string.
        """
        if not self._c_lz_tree_state:
            raise RuntimeError("C LZ Tree State is not available for batch processing.")
        if not strings: # Handle empty list of strings
            return []

        num_strings = len(strings)

        # Prepare C-compatible array of char pointers (const char**)
        c_strings_array_type = ctypes.c_char_p * num_strings
        c_strings_array = c_strings_array_type()
        
        # Keep Python references to the encoded byte strings to prevent them from being garbage collected
        # before ctypes is done with the pointers.
        encoded_strings_references = [] 
        for i, s_val in enumerate(strings):
            if not isinstance(s_val, str):
                raise TypeError(f"All items in strings list must be str, got {type(s_val)} at index {i}.")
            # Handle empty strings for C layer: use a placeholder like "0" or ensure C handles NULL/empty.
            # The C batch function for lz_suffix should ideally handle empty strings gracefully (e.g., complexity 0 or 1).
            # For now, let's assume C handles empty strings. If not, they should be processed as e.g. "0".
            encoded_s = s_val.encode('utf-8')
            encoded_strings_references.append(encoded_s) 
            c_strings_array[i] = encoded_s

        # Prepare C-compatible integer array for results (int*)
        results_array_c_type = ctypes.c_int * num_strings
        results_array_c = results_array_c_type()

        # Call the C batch processing function
        self.c_lib.process_lz_batch_c(
            self._c_lz_tree_state, 
            c_strings_array, 
            ctypes.c_int(num_strings), 
            results_array_c
        )

        return list(results_array_c) # Convert ctypes array to Python list

    def return_dictionary(self) -> list[str]:
        """Returns the list of phrases in the LZ76 dictionary.
        
        This includes all completed phrases and the current, potentially
        unfinished phrase being built.

        Returns:
            list[str]: The LZ76 dictionary phrases.
        """
        final_dict = list(self.dictionary) # Start with a copy of completed phrases
        if self.current_word: # Append the active phrase if it exists
            final_dict.append(self.current_word)
        return final_dict

    def display_status(self):
        """Prints the current status of the LZ Suffix Tree Wrapper.
        
        Includes Python-tracked `current_word`, `current_text_py`, overall LZ76 complexity
        from C, and the Python-tracked dictionary content.
        """
        print("---- LZ Suffix Tree Wrapper Status ----")
        if not self._c_lz_tree_state:
            print("C LZ Suffix Tree State is not available.")
            return

        c_complexity = self.compute_lz76_complexity()
        
        print(f"Current text processed (Python tracking): '{self.current_text_py}'")
        print(f"Current word being built (Python tracking): '{self.current_word}'")
        print(f"Completed dictionary phrases (Python tracking): {self.dictionary}")
        print(f"Full dictionary for display (Python tracking): {self.return_dictionary()}")
        print(f"LZ76 Complexity (from C): {c_complexity}")
        print("-------------------------------------")

    def __del__(self):
        """Ensures the C `LZSuffixTreeCState` is freed when the wrapper object is deleted."""
        if hasattr(self, 'c_lib') and self.c_lib and \
           hasattr(self, '_c_lz_tree_state') and self._c_lz_tree_state:
            self.c_lib.free_lz_suffix_tree_c(self._c_lz_tree_state)
            self._c_lz_tree_state = None # Mark as freed

# Example Usage:
if __name__ == '__main__':
    print("LZSuffixTreeWrapper Example")
    try:
        wrapper = LZSuffixTreeWrapper("banana")
        wrapper.display_status()

        print("\nAdding characters: 'b', 'a', '$'...")
        wrapper.add_character('b')
        wrapper.display_status()
        wrapper.add_character('a')
        wrapper.display_status()
        wrapper.add_character('$') # Terminator
        wrapper.display_status()

        print(f"\nFinal LZ76 Complexity for '{wrapper.current_text_py}': {wrapper.compute_lz76_complexity()}")
        print(f"Final Dictionary: {wrapper.return_dictionary()}")

        # Test reset
        print("\nResetting wrapper...")
        wrapper.reset()
        wrapper.display_status()
        print(f"Complexity after reset: {wrapper.compute_lz76_complexity()}")
        wrapper.add_character('a')
        wrapper.add_character('b')
        wrapper.add_character('a')
        print(f"After adding 'aba' post-reset: Complexity = {wrapper.compute_lz76_complexity()}, Dict = {wrapper.return_dictionary()}")
        wrapper.display_status()

        # Test batch processing
        print("\n--- Batch Processing Test ---")
        test_strings_batch = ["010101", "abcabc", "aaaaaa", "", "0"]
        # Create a new instance or reset the existing one for batch processing,
        # as the C state is reused and reset internally per string by process_lz_batch_c.
        batch_wrapper = LZSuffixTreeWrapper() 
        batch_results = batch_wrapper.compute_lz76_complexity_batch(test_strings_batch)
        print("Batch results:")
        for s, res in zip(test_strings_batch, batch_results):
            print(f"  LZ76('{s if s else \'<empty>\'}'): {res}")
        
        # Ensure the batch_wrapper state is clean after batch (it should be, due to internal resets)
        print("State of batch_wrapper after batch operation:")
        batch_wrapper.display_status() # Should show an empty state

    except OSError as oe:
        print(f'OSError during example: {oe}')
    except Exception as e:
        print(f'An unexpected error occurred during example: {e}')

