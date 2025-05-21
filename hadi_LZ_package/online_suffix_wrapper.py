'''Python wrapper for the C implementation of an Online Suffix Tree.

This module provides the `OnlineSuffixTreeWrapper` class, which acts as a Python
interface to the C functions defined in `online_suffix.c` (compiled into a shared
library, e.g., `online_suffix.dylib` or `online_suffix.so`).

It allows for creating an online suffix tree, adding characters one by one (which
updates the tree using Ukkonen\'s algorithm as implemented in C), and searching for
patterns within the constructed tree.

The wrapper handles:
- Loading the compiled C library (`.dylib`, `.so`, or `.dll` based on OS).
- Defining `ctypes` argument and return types for the C functions.
- Managing the lifecycle of the C SuffixTreeCState object (creation and freeing).
- Converting Python strings to C-compatible byte strings and vice-versa where needed.

Typical usage involves creating an instance, adding characters or a string, and then
using the `find` method.
'''
import ctypes
import os
import sys # Moved from bottom to top for standard practice

class OnlineSuffixTreeWrapper:
    '''A Python wrapper for an online suffix tree implemented in C.

    This class manages a suffix tree state in C, allowing characters to be added
    incrementally and patterns to be searched. It uses `ctypes` to interface with
    the compiled C shared library (`online_suffix.dylib`/`.so`/`.dll`).

    Attributes:
        c_lib: A `ctypes.CDLL` object representing the loaded C library.
        _c_tree_state: A C pointer (ctypes.c_void_p) to the SuffixTreeCState struct
                       managed by the C library.
    '''
    def __init__(self, initial_text: str = ""):
        """Initializes the OnlineSuffixTreeWrapper.

        Loads the C shared library, configures function prototypes, creates the
        C suffix tree state, and optionally populates it with an initial text.

        Args:
            initial_text: An optional string to initialize the suffix tree with.
                          Characters from this string will be added one by one.

        Raises:
            OSError: If the C shared library cannot be loaded (e.g., not found,
                     not compiled, or wrong architecture).
            MemoryError: If the C library fails to allocate the SuffixTreeCState.
        """
        # Determine library path relative to this file (online_suffix_wrapper.py)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Determine the correct shared library filename based on the operating system.
        lib_filename = "online_suffix.so"  # Default for Linux
        if os.name == 'nt': # Windows
            lib_filename = "online_suffix.dll"
        elif sys.platform == 'darwin': # macOS
            lib_filename = "online_suffix.dylib"
        
        # Construct the full path to the C library.
        # Assumes c_backend is a subdirectory relative to this wrapper file.
        lib_path = os.path.join(script_dir, "c_backend", lib_filename)

        try:
            self.c_lib = ctypes.CDLL(lib_path)
        except OSError as e:
            # Provide a detailed error message to help diagnose loading issues.
            example_c_file_path = os.path.join("c_backend", "online_suffix.c") # Relative to project root for example
            example_output_path = os.path.join("c_backend", lib_filename) # Relative to project root for example
            
            error_message = (
                f"Failed to load C library from {lib_path}. \n"
                f"Please ensure the library is compiled and in the correct location.\n"
                f"The C source is expected at: {example_c_file_path}\n"
                f"And the compiled library at: {example_output_path}\n"
                f"You might need to run 'make' in the 'hadi_LZ_package/hadi_LZ_package/c_backend' directory.\n"
                f"Example compilation command (adjust for your system if not using Makefile):\n"
                f"  gcc -shared -o '{example_output_path}' -fPIC '{example_c_file_path}'\n"
                f"Original error: {e}"
            )
            raise OSError(error_message)

        # Define an opaque pointer type for SuffixTreeCState. 
        # The actual struct definition is in C.
        self.CSuffixTreeStatePtr = ctypes.c_void_p

        # Configure C function prototypes (argument types and return types).
        # This is essential for ctypes to correctly call the C functions.
        try:
            self.c_lib.create_suffix_tree_c.restype = self.CSuffixTreeStatePtr
            self.c_lib.create_suffix_tree_c.argtypes = []

            self.c_lib.free_suffix_tree_c.restype = None
            self.c_lib.free_suffix_tree_c.argtypes = [self.CSuffixTreeStatePtr]

            self.c_lib.add_char_c.restype = None # add_char_c in C returns void
            self.c_lib.add_char_c.argtypes = [self.CSuffixTreeStatePtr, ctypes.c_char]

            self.c_lib.find_c.restype = ctypes.c_bool
            self.c_lib.find_c.argtypes = [self.CSuffixTreeStatePtr, ctypes.c_char_p]

            self.c_lib.get_text_len_c.restype = ctypes.c_int
            self.c_lib.get_text_len_c.argtypes = [self.CSuffixTreeStatePtr]

            self.c_lib.get_text_char_at_c.restype = ctypes.c_char # Returns a single byte
            self.c_lib.get_text_char_at_c.argtypes = [self.CSuffixTreeStatePtr, ctypes.c_int]
        except AttributeError as e:
            raise AttributeError(f"A required function was not found in the C library at {lib_path}.\nEnsure all functions (create_suffix_tree_c, free_suffix_tree_c, etc.) are compiled.\nOriginal error: {e}")

        # Initialize the C suffix tree state by calling the C constructor.
        self._c_tree_state = self.c_lib.create_suffix_tree_c()
        if not self._c_tree_state:
            # This indicates a failure within the C create_suffix_tree_c function (e.g., malloc failed).
            raise MemoryError("Failed to create C suffix tree state (C function returned NULL).")

        # Populate the tree with any initial text provided.
        if initial_text:
            for char_val in initial_text:
                self.add_char(char_val)

    def add_char(self, ch: str) -> None:
        """Adds a single character to the suffix tree.

        The character is encoded to UTF-8. This wrapper currently assumes that
        the C function `add_char_c` expects a single byte (`char`).
        Multi-byte characters will raise a ValueError.

        Args:
            ch: The character to add. Must be a single character string.

        Raises:
            ValueError: If `ch` is not a single character string, or if it encodes
                        to multiple bytes in UTF-8 (unsupported by C `char` type).
            UnicodeEncodeError: If the character cannot be UTF-8 encoded.
        """
        if not isinstance(ch, str) or len(ch) != 1:
            raise ValueError("Input to add_char must be a single character string.")
        
        try:
            byte_char_array = ch.encode('utf-8')
            if len(byte_char_array) != 1:
                # The C side `add_char_c` takes a `char`, which is typically 1 byte.
                # If a Python character encodes to multiple UTF-8 bytes, it cannot be passed directly.
                raise ValueError(f"Character '{ch}' (UTF-8: {byte_char_array.hex()}) encodes to {len(byte_char_array)} bytes.\nThe C backend currently supports only single-byte characters for add_char_c.")
            c_char_val = byte_char_array[0] # Extract the single byte
        except UnicodeEncodeError:
            # Should be rare for single characters but good practice to handle.
            raise ValueError(f"Character '{ch}' could not be encoded to UTF-8.")

        self.c_lib.add_char_c(self._c_tree_state, ctypes.c_char(c_char_val))

    def find(self, pattern: str) -> bool:
        """Checks if a given pattern exists in the suffix tree.

        The pattern is UTF-8 encoded before being passed to the C function.

        Args:
            pattern: The string pattern to search for.

        Returns:
            True if the pattern is found in the tree, False otherwise.
        
        Raises:
            TypeError: If pattern is not a string.
        """
        if not isinstance(pattern, str):
            raise TypeError("Pattern must be a string.")
        
        byte_pattern = pattern.encode('utf-8') # Encode to bytes for C char*
        return self.c_lib.find_c(self._c_tree_state, byte_pattern)

    def add_terminator(self, terminator_char: str = "$") -> None:
        """Adds a terminator character to the text in the suffix tree.
        
        Useful for ensuring all suffixes are explicit if the C implementation
        relies on unique terminators for certain properties.

        Args:
            terminator_char: The terminator character to add. Defaults to "$".
                             Must be a single-byte encodable character.
        """
        # add_char will handle validation (single char, single byte encoding)
        self.add_char(terminator_char)

    def get_internal_text(self) -> str:
        """Retrieves the full text currently stored within the C suffix tree state.
        
        The text is reconstructed by calling C helper functions to get its length
        and individual characters, then decoded from UTF-8.

        Returns:
            The current text in the suffix tree as a Python string.
            Returns an empty string if the C state is not valid.
        """
        if not self._c_tree_state: 
            return "" # Or raise an error if state should always be valid
        
        text_len = self.c_lib.get_text_len_c(self._c_tree_state)
        if text_len <= 0:
            return ""
            
        byte_chars = []
        for i in range(text_len):
            # get_text_char_at_c returns a C char (byte)
            byte_chars.append(self.c_lib.get_text_char_at_c(self._c_tree_state, i))
        
        # Convert list of bytes to a bytes object, then decode to string.
        # Assuming text in C is effectively a sequence of bytes that form a UTF-8 string.
        return b"".join(byte_chars).decode('utf-8', errors='replace')

    def __del__(self):
        """Ensures the C suffix tree state is freed when the wrapper object is deleted."""
        if hasattr(self, 'c_lib') and self.c_lib and \
           hasattr(self, '_c_tree_state') and self._c_tree_state:
            # print(f"Freeing SuffixTreeCState: {self._c_tree_state}") # For debugging
            self.c_lib.free_suffix_tree_c(self._c_tree_state)
            self._c_tree_state = None # Mark as freed

    @property
    def text_len(self) -> int:
        """int: The current length of the text in the suffix tree."""
        if not self._c_tree_state: 
            return 0
        return self.c_lib.get_text_len_c(self._c_tree_state)

    @property
    def global_end(self) -> int:
        """int: The index of the last character added (global_end in Ukkonen's).
        Returns -1 if the tree is empty.
        """
        if not self._c_tree_state: 
            return -1
        length = self.c_lib.get_text_len_c(self._c_tree_state)
        return length - 1 # If length is 0, returns -1, which is correct for empty.

# Example usage:
if __name__ == '__main__':
    print("OnlineSuffixTreeWrapper Example")
    try:
        # Create with initial text
        tree = OnlineSuffixTreeWrapper("banana")
        print(f"Initial text: '{tree.get_internal_text()}' (len: {tree.text_len}, global_end: {tree.global_end})")

        # Add more characters
        tree.add_char('b')
        tree.add_char('a')
        print(f"After adding 'ba': '{tree.get_internal_text()}'")

        # Add a terminator
        tree.add_terminator('$')
        print(f"After adding terminator '$': '{tree.get_internal_text()}'")

        # Test find method
        patterns_to_find = ["ban", "ana", "nana", "apple", "bana", "a$", "banana%", ""]
        for p in patterns_to_find:
            is_found = tree.find(p)
            print(f"Pattern '{p}': {'Found' if is_found else 'Not Found'}")
        
        # Test with an empty tree initially
        empty_tree = OnlineSuffixTreeWrapper()
        print(f"Empty tree text: '{empty_tree.get_internal_text()}' (len: {empty_tree.text_len}, global_end: {empty_tree.global_end})")
        empty_tree.add_char('a')
        empty_tree.add_char('b')
        empty_tree.add_char('a')
        print(f"Empty tree after 'aba': '{empty_tree.get_internal_text()}'")
        print(f"Find 'ab' in empty_tree after 'aba': {empty_tree.find('ab')}")

        # Example of trying to add a multi-byte character (should raise ValueError)
        try:
            print("\nAttempting to add a multi-byte character (e.g., €)...")
            tree.add_char('€')
        except ValueError as ve:
            print(f"Caught expected error: {ve}")

    except OSError as oe:
        print(f"OSError during example: {oe}")
    except Exception as e:
        print(f"An unexpected error occurred during example: {e}") 