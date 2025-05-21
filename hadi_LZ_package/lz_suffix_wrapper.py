import ctypes
import os
import sys # For sys.platform

class LZSuffixTreeWrapper:
    def __init__(self, initial_text: str = ""):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        lib_filename = "lz_suffix_combined.so" # Default, will be combined lib
        if os.name == 'nt':
            lib_filename = "lz_suffix_combined.dll"
        elif sys.platform == 'darwin':
            lib_filename = "lz_suffix_combined.dylib"
        
        lib_path = os.path.join(script_dir, "c_backend", lib_filename)

        try:
            self.c_lib = ctypes.CDLL(lib_path)
        except OSError as e:
            # More detailed compilation instruction for combined library
            online_suffix_c_path = os.path.join("c_backend", "online_suffix.c")
            lz_suffix_c_path = os.path.join("c_backend", "lz_suffix.c")
            output_lib_path = os.path.join("c_backend", lib_filename)
            error_message = (
                f"Failed to load C library at {lib_path}. "
                f"Please ensure it is compiled and in the correct location. "
                f"The library must combine both online_suffix.c and lz_suffix.c. "
                f"For example, on Linux/macOS: "
                f"gcc -shared -o '{output_lib_path}' -fPIC '{online_suffix_c_path}' '{lz_suffix_c_path}'"
                f"Original error: {e}"
            )
            raise OSError(error_message)

        # Opaque pointer types
        self.CLZSuffixTreeStatePtr = ctypes.c_void_p

        # Configure C function prototypes from lz_suffix.h
        self.c_lib.create_lz_suffix_tree_c.restype = self.CLZSuffixTreeStatePtr
        self.c_lib.create_lz_suffix_tree_c.argtypes = []

        self.c_lib.free_lz_suffix_tree_c.restype = None
        self.c_lib.free_lz_suffix_tree_c.argtypes = [self.CLZSuffixTreeStatePtr]

        self.c_lib.add_char_lz_c.restype = ctypes.c_bool
        self.c_lib.add_char_lz_c.argtypes = [self.CLZSuffixTreeStatePtr, ctypes.c_char]

        self.c_lib.get_lz_complexity_c.restype = ctypes.c_int
        self.c_lib.get_lz_complexity_c.argtypes = [self.CLZSuffixTreeStatePtr]

        self.c_lib.reset_lz_suffix_tree_c.restype = None
        self.c_lib.reset_lz_suffix_tree_c.argtypes = [self.CLZSuffixTreeStatePtr]
        
        self.c_lib.process_lz_batch_c.restype = None
        self.c_lib.process_lz_batch_c.argtypes = [
            self.CLZSuffixTreeStatePtr, 
            ctypes.POINTER(ctypes.c_char_p), 
            ctypes.c_int, 
            ctypes.POINTER(ctypes.c_int)
        ]

        # Helper from online_suffix.h might be needed if exposing internal state, e.g. base_tree text
        # For now, only LZ specific functions are wrapped directly for the API.
        # self.c_lib.get_text_len_c.restype = ctypes.c_int
        # self.c_lib.get_text_len_c.argtypes = [ctypes.c_void_p] # Assuming SuffixTreeCState* from base_tree
        # self.c_lib.get_text_char_at_c.restype = ctypes.c_char
        # self.c_lib.get_text_char_at_c.argtypes = [ctypes.c_void_p, ctypes.c_int]


        # Initialize the C LZ suffix tree state
        self._c_lz_tree_state = self.c_lib.create_lz_suffix_tree_c()
        if not self._c_lz_tree_state:
            raise MemoryError("Failed to create C LZ suffix tree state.")

        # For Python compatibility, we need to store the current_word and dictionary list for display/status if desired
        self.current_word = "" # Python equivalent, derived from C state if needed or tracked separately
        self.dictionary = []    # Python equivalent, if needed for display_status
        self.current_text_py = "" # Python equivalent of full text stream

        if initial_text:
            for char_val in initial_text:
                self.add_character(char_val)

    def add_character(self, char: str) -> bool:
        if not isinstance(char, str) or len(char) != 1:
            raise ValueError("Input must be a single character string.")
        
        try:
            byte_char = char.encode('utf-8')
            if len(byte_char) != 1:
                raise ValueError(f"Character '{char}' is multi-byte in UTF-8 and not supported.")
        except UnicodeEncodeError:
            raise ValueError(f"Character '{char}' could not be encoded to UTF-8.")

        self.current_text_py += char # Keep track of full text stream for potential status display
        
        # The C function add_char_lz_c handles the logic of current_word internally (current_word_buffer)
        # and whether a new phrase was added to the dictionary (dictionary_size).
        # The Python version's `current_word` and `dictionary` list are mostly for inspection or higher-level logic.
        
        # If a new word was added, the Python version appends `self.current_word` to `self.dictionary`
        # *before* clearing `self.current_word`.
        # The C side just increments dictionary_size and clears its internal current_word_buffer.
        # We need to mirror this logic for `self.current_word` and `self.dictionary` if they are to be exposed.

        # Before calling C, `char` is about to be added to the current conceptual Python `self.current_word`
        potential_current_word_for_dict = self.current_word + char

        new_word_added_to_dict_c = self.c_lib.add_char_lz_c(self._c_lz_tree_state, byte_char[0])

        if new_word_added_to_dict_c:
            self.dictionary.append(potential_current_word_for_dict) # The word that just completed
            self.current_word = ""  # Start a new word
        else:
            self.current_word = potential_current_word_for_dict # Word continues
        
        return new_word_added_to_dict_c

    def compute_lz76_complexity(self) -> int:
        if not self._c_lz_tree_state: return 0
        return self.c_lib.get_lz_complexity_c(self._c_lz_tree_state)

    def reset(self) -> None:
        if not self._c_lz_tree_state: return
        self.c_lib.reset_lz_suffix_tree_c(self._c_lz_tree_state)
        # Reset Python-side tracking variables as well
        self.current_word = ""
        self.dictionary = []
        self.current_text_py = ""

    def compute_lz76_complexity_batch(self, strings: list[str]) -> list[int]:
        if not self._c_lz_tree_state:
            raise RuntimeError("C LZ Tree State is not available for batch processing.")
        if not strings:
            return []

        num_strings = len(strings)

        # Prepare array of C strings (char*)
        c_strings_array = (ctypes.c_char_p * num_strings)()
        encoded_strings = [] # Keep references to encoded bytes to prevent garbage collection
        for i, s_val in enumerate(strings):
            if not isinstance(s_val, str):
                raise TypeError(f"All items in strings list must be str, got {type(s_val)} at index {i}")
            encoded_s = s_val.encode('utf-8')
            encoded_strings.append(encoded_s) # Keep a reference
            c_strings_array[i] = encoded_s

        # Prepare results array (int*)
        results_array_c_type = ctypes.c_int * num_strings
        results_array_c = results_array_c_type()

        # Call the C batch function
        # The C function reuses the _c_lz_tree_state, resetting it for each string
        self.c_lib.process_lz_batch_c(
            self._c_lz_tree_state, 
            c_strings_array, 
            num_strings, 
            results_array_c
        )

        return list(results_array_c)

    def return_dictionary(self) -> list[str]:
        # Python's return_dictionary includes the current_word if it's not empty
        # The self.dictionary list tracks completed words.
        final_dict = list(self.dictionary) # Make a copy
        if self.current_word:             # Append the active phrase if any
            final_dict.append(self.current_word)
        return final_dict

    # display_status is requested on the python wrapper end
    def display_status(self):
        print(f"---- LZ Suffix Tree Wrapper Status ----")
        if not self._c_lz_tree_state:
            print("C LZ Tree State is not available.")
            return

        # Info from Python-side tracking (consistent with Python original)
        print(f"Current word (Python wrapper): '{self.current_word}'")
        print(f"Full text processed (Python wrapper): '{self.current_text_py}'")
        
        # Info from C side
        c_dict_size = "N/A"
        c_current_word_len = "N/A"
        c_complexity = self.compute_lz76_complexity()
        
        # To get C dictionary_size and current_word_len directly, we'd need accessors in C API
        # For now, we infer based on Python version logic and complexity
        # (This part is a bit of an approximation for display without more C accessors)
        actual_c_dict_size = self.c_lib.get_lz_complexity_c(self._c_lz_tree_state)
        if self.current_word: # If python wrapper has an active current_word
            actual_c_dict_size -=1 # The complexity includes +1 for it
        
        print(f"Dictionary size (from C via complexity): {actual_c_dict_size}")
        print(f"Current word length (Python wrapper tracking): {len(self.current_word)}")
        print(f"LZ76 Complexity (from C): {c_complexity}")
        print(f"Dictionary content (Python wrapper): {self.return_dictionary()}")
        
        # We can't easily display base_tree.text or lz_active_point from C without more helpers.
        # print(f"Base tree text (from C): ... ")
        print(f"-------------------------------------")

    def __del__(self):
        if hasattr(self, 'c_lib') and hasattr(self, '_c_lz_tree_state') and self._c_lz_tree_state:
            self.c_lib.free_lz_suffix_tree_c(self._c_lz_tree_state)
            self._c_lz_tree_state = None

