import ctypes
import os

class OnlineSuffixTreeWrapper:
    def __init__(self, initial_text: str = ""):
        # Determine library path relative to this file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Adjust based on OS - .so for Linux, .dylib for macOS, .dll for Windows
        lib_filename = "online_suffix.so" # Default to .so
        if os.name == 'nt':
            lib_filename = "online_suffix.dll"
        elif sys.platform == 'darwin':
            lib_filename = "online_suffix.dylib"
        
        lib_path = os.path.join(script_dir, "c_backend", lib_filename)

        try:
            self.c_lib = ctypes.CDLL(lib_path)
        except OSError as e:
            # Constructing the path for the example command carefully
            example_c_file_path = os.path.join("c_backend", "online_suffix.c")
            example_output_path = os.path.join("c_backend", lib_filename)
            
            error_message = (
                f"Failed to load C library at {lib_path}. "
                f"Please ensure it is compiled and in the correct location. "
                f"For example, on Linux/macOS: "
                f"gcc -shared -o '{example_output_path}' -fPIC '{example_c_file_path}'"
                f"Original error: {e}"
            )
            raise OSError(error_message)

        # Opaque pointer type for SuffixTreeCState
        self.CSuffixTreeStatePtr = ctypes.c_void_p

        # Configure C function prototypes
        self.c_lib.create_suffix_tree_c.restype = self.CSuffixTreeStatePtr
        self.c_lib.create_suffix_tree_c.argtypes = []

        self.c_lib.free_suffix_tree_c.restype = None
        self.c_lib.free_suffix_tree_c.argtypes = [self.CSuffixTreeStatePtr]

        self.c_lib.add_char_c.restype = None
        self.c_lib.add_char_c.argtypes = [self.CSuffixTreeStatePtr, ctypes.c_char]

        self.c_lib.find_c.restype = ctypes.c_bool
        self.c_lib.find_c.argtypes = [self.CSuffixTreeStatePtr, ctypes.c_char_p]

        self.c_lib.get_text_len_c.restype = ctypes.c_int
        self.c_lib.get_text_len_c.argtypes = [self.CSuffixTreeStatePtr]

        self.c_lib.get_text_char_at_c.restype = ctypes.c_char
        self.c_lib.get_text_char_at_c.argtypes = [self.CSuffixTreeStatePtr, ctypes.c_int]

        # Initialize the C suffix tree state
        self._c_tree_state = self.c_lib.create_suffix_tree_c()
        if not self._c_tree_state:
            raise MemoryError("Failed to create C suffix tree state.")

        # Populate with initial text
        if initial_text:
            for char_val in initial_text:
                self.add_char(char_val)

    def add_char(self, ch: str) -> None:
        if not isinstance(ch, str) or len(ch) != 1:
            raise ValueError("Input must be a single character string.")
        
        # Encode to byte. Assuming UTF-8, and that add_char_c expects a single byte.
        # This is a simplification. If multi-byte chars are needed, C side must change.
        try:
            byte_char = ch.encode('utf-8')
            if len(byte_char) != 1:
                # This happens for multi-byte UTF-8 characters.
                # The original Python code handles Unicode characters naturally in strings.
                # The C `char` typically expects a single byte.
                # For this implementation, we'll restrict to chars that are single bytes in UTF-8 (like ASCII).
                raise ValueError(f"Character '{ch}' is multi-byte in UTF-8 and not supported by this C backend's char type.")
        except UnicodeEncodeError:
            raise ValueError(f"Character '{ch}' could not be encoded to UTF-8.")

        self.c_lib.add_char_c(self._c_tree_state, byte_char[0])

    def find(self, pattern: str) -> bool:
        if not isinstance(pattern, str):
            raise TypeError("Pattern must be a string.")
        
        byte_pattern = pattern.encode('utf-8') # Ensure consistent encoding with C side
        return self.c_lib.find_c(self._c_tree_state, byte_pattern)

    def add_terminator(self, terminator_char: str = "$") -> None:
        # Ensure terminator is also a single-byte character
        self.add_char(terminator_char)

    def get_internal_text(self) -> str:
        """Retrieves the text currently stored in the C suffix tree state."""
        if not self._c_tree_state: return ""
        text_len = self.c_lib.get_text_len_c(self._c_tree_state)
        chars = []
        for i in range(text_len):
            # Assuming UTF-8 for decoding, consistent with encoding in add_char
            chars.append(self.c_lib.get_text_char_at_c(self._c_tree_state, i).decode('utf-8', errors='replace'))
        return "".join(chars)

    def __del__(self):
        if hasattr(self, 'c_lib') and hasattr(self, '_c_tree_state') and self._c_tree_state:
            self.c_lib.free_suffix_tree_c(self._c_tree_state)
            self._c_tree_state = None

    # It might be useful to expose a way to get the current global_end or text_len from Python
    @property
    def text_len(self) -> int:
        if not self._c_tree_state: return 0
        return self.c_lib.get_text_len_c(self._c_tree_state)

    @property
    def global_end(self) -> int:
        if not self._c_tree_state: return -1
        length = self.c_lib.get_text_len_c(self._c_tree_state)
        return length - 1 if length > 0 else -1

# Required for lib_filename logic in __init__
import sys 