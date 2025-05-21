'''Pure Python implementation of LZ76 complexity using an online suffix tree.

This module defines the `LZSuffixTree` class, which inherits from `OnlineSuffixTree`
(from the `.online_suffix` module) and adapts it for calculating LZ76 complexity.
It maintains the LZ76 parsing state (current word, dictionary, active match point)
and uses the suffix tree (representing the dictionary of already processed phrases)
_to efficiently check if the current word is a new phrase.

This implementation is intended as a Python-based reference or for scenarios
where the C backend is not available or desired. For performance, the C-backed
wrappers should be used.
'''
from .online_suffix import OnlineSuffixTree # Suffix tree base class

class LZSuffixTree(OnlineSuffixTree):
    """Implements LZ76 complexity calculation using a Python-based OnlineSuffixTree.

    Inherits from `OnlineSuffixTree` to use its suffix tree construction and
    matching capabilities. This class adds specific logic for LZ76 parsing:
    - The suffix tree (`self.text` in parent) stores the concatenation of
      completed LZ phrases (i.e., the dictionary content).
    - `self.current_word` tracks the current phrase being built.
    - `self.last_char` is the latest character received, used to extend `current_word`.
    - An active matching point (`last_match_node`, `last_match_edge`, `last_match_length`)
      is maintained to efficiently check if `current_word` (after appending `last_char`)
      is present in the suffix tree (i.e., the dictionary).

    The core idea is that the `OnlineSuffixTree` (base class) will store the dictionary
    of seen phrases (S1S2...Sk-1). When a new character arrives, it extends the current
    word being formed (W). We then check if W is in the tree. If not, W (or W without
    the last char, depending on specific LZ76 variant logic) becomes a new phrase Sk,
    is added to the dictionary (and thus to the tree for future checks), and the current
    word is reset.
    """
    def __init__(self, initial_text: str = ""):
        """Initializes the LZSuffixTree for LZ76 calculation.

        Args:
            initial_text (str, optional): Optional initial text to process.
                                        Characters will be added one by one.
                                        Defaults to "".
        """
        # Initialize parent OnlineSuffixTree. The parent's self.text will store
        # the concatenation of phrases that form the LZ76 dictionary.
        # It is initialized empty because the LZ dictionary is initially empty.
        super().__init__("")
        
        # LZ76 specific state variables:
        self.current_word: str = ""  # The current phrase being built before it becomes a dictionary item.
        self.current_text: str = "" # The full text processed so far by add_character calls.
        self.last_char: str = ""     # The most recent character received via add_character.
        
        self.dictionary_size: int = 0 # Number of phrases in the LZ76 dictionary.
        self.dictionary: list[str] = [] # List of the actual phrases found.
        
        # Active point for matching self.current_word (potentially extended by self.last_char)
        # within the suffix tree (which represents self.dictionary text).
        # This is analogous to Ukkonen's active point but used for LZ matching, not tree construction.
        self.last_match_node = self.root  # Start matching from the root of the suffix tree.
        self.last_match_edge: str | None = None # The first character of the edge we are currently on in the suffix tree during matching.
        self.last_match_length: int = 0 # How far along that `last_match_edge` we have matched `current_word`.
        
        if initial_text:
            for char_val in initial_text:
                self.add_character(char_val)
    
    def add_character(self, char: str) -> bool:
        """Processes a single character for LZ76 complexity calculation.

        1. Appends `char` to `self.current_text` (full history) and sets `self.last_char`.
        2. The `previous_last_char` (if any) is added to the `OnlineSuffixTree` (parent),
           which means it becomes part of the dictionary represented by the tree.
        3. It then checks if `self.current_word` extended by `char` (i.e., `self.current_word` + `char`)
           can be found in the suffix tree using `is_current_word_in_tree()`.
           `is_current_word_in_tree()` updates the LZ active match point.
        4. If found: The current phrase (`self.current_word`) is extended with `char`.
        5. If not found: `self.current_word + self.last_char` forms a new LZ phrase.
           - `self.dictionary_size` is incremented.
           - The new phrase is added to `self.dictionary` list.
           - `self.current_word` is reset (it effectively becomes empty, as the next char will start it).
           - The LZ active match point is reset to the root.
        
        Args:
            char (str): The character to add.
            
        Returns:
            bool: True if adding this character resulted in completing a new LZ phrase,
                  False otherwise.
        """
        if not isinstance(char, str) or len(char) != 1:
            raise ValueError("Input must be a single character string.")

        new_phrase_completed = False
        
        self.current_text += char
        previous_last_char = self.last_char # Character to potentially add to suffix tree
        self.last_char = char # Current character being processed by LZ logic
        
        # The suffix tree (self.text in parent) should contain the concatenation of
        # *completed* dictionary phrases. So, add `previous_last_char` to the tree.
        if previous_last_char:
            super().add_char(previous_last_char) # Add to the suffix tree (dictionary)
        
        # Now, try to match `self.current_word + self.last_char` in the tree.
        # `is_current_word_in_tree` attempts to match `self.last_char` from the current
        # LZ active point (self.last_match_node, .edge, .length).
        if self.is_current_word_in_tree():
            # Match successful: self.last_char extends the current_word in the dictionary.
            # The LZ active point was updated by is_current_word_in_tree.
            self.current_word += self.last_char # Extend current word being built
        else:
            # Match failed: `self.current_word + self.last_char` is a new phrase.
            self.dictionary_size += 1
            self.dictionary.append(self.current_word + self.last_char) # Add completed phrase
            self.current_word = ""  # Reset current_word for the *next* phrase
                                   # (which starts with the *next* call to add_character)
            
            # Reset LZ active match point to the root for the new phrase search.
            self.last_match_node = self.root
            self.last_match_edge = None
            self.last_match_length = 0
            new_phrase_completed = True
        
        return new_phrase_completed
    
    def is_current_word_in_tree(self) -> bool:
        """Checks if `self.last_char` extends the current match from LZ active point.

        This method attempts to find `self.last_char` in the suffix tree (`self.text`
        of the parent class, representing the dictionary), starting from the current
        LZ active match point (`self.last_match_node`, `self.last_match_edge`,
        `self.last_match_length`).

        If a match is found, the LZ active match point is updated.

        Returns:
            bool: True if `self.last_char` extends the match, False otherwise.
        """
        if not self.last_char: # Should not happen if called after add_character sets it.
            return True # Or False, depending on desired behavior for empty last_char. Let's assume it means no extension possible.

        # Case 1: We are currently in the middle of an edge in the suffix tree.
        if self.last_match_edge and self.last_match_length > 0:
            # Ensure the edge still exists from the active node.
            if self.last_match_edge not in self.last_match_node.children:
                # This indicates an inconsistent state, e.g. tree modified unexpectedly or bug.
                # Resetting active point might be a recovery strategy.
                # For now, assume this means no match.
                # This can happen if the tree structure changed due to `super().add_char()`
                # in a way that invalidates the old `last_match_edge` from `last_match_node`.
                # A robust implementation might re-verify/re-trace from root if inconsistency is detected.
                # Given current logic, let's try to re-evaluate from current last_match_node: 
                self.last_match_edge = None 
                self.last_match_length = 0 
                # Fall through to node logic (Case 2)
            else:
                edge_obj = self.last_match_node.children[self.last_match_edge]
                # `self.global_end` in parent refers to `len(self.text) - 1` of parent tree.
                current_edge_actual_len = edge_obj.length(self.global_end) 

                if self.last_match_length < current_edge_actual_len:
                    # We are still on this edge. Check the next character on the edge.
                    # The character in the tree is self.text[edge_obj.start + self.last_match_length]
                    if self.text[edge_obj.start + self.last_match_length] == self.last_char:
                        self.last_match_length += 1 # Extend match along this edge.
                        return True
                    else:
                        return False # Mismatch on the edge.
                else: # self.last_match_length == current_edge_actual_len
                    # Reached the end of the current `last_match_edge`.
                    # Transition to the destination node of this edge.
                    self.last_match_node = edge_obj.dest
                    self.last_match_edge = None # Now at a node.
                    self.last_match_length = 0
                    # Fall through to Case 2 (node logic) to find self.last_char from this new node.
        
        # Case 2: We are at a node (`self.last_match_node`).
        # Try to find an outgoing edge starting with `self.last_char`.
        if self.last_char in self.last_match_node.children:
            self.last_match_edge = self.last_char # Edge is identified by its first char.
            self.last_match_length = 1 # Matched one character along this new edge.
            # self.last_match_node remains the source of this new edge.
            return True
        
        return False # No matching edge found from the current node.
    
    def reset_current_word(self): #This method seems redundant with logic in add_character.
        """Resets the current LZ word and the LZ active match point.
        
        This is typically called after a new phrase is completed and added to the dictionary.
        Note: The original Python implementation had `self.dictionary.append(self.current_word)` here.
        This is now handled in `add_character` to ensure correct phrase is appended.
        """
        # self.dictionary.append(self.current_word) # Moved to add_character
        self.current_word = ''
        self.last_match_node = self.root
        self.last_match_edge = None
        self.last_match_length = 0
    
    def get_current_tree_text(self) -> str:
        """Returns the text currently stored in the underlying suffix tree.
        
        This text represents the concatenation of all completed LZ dictionary phrases.
        It corresponds to `self.text` from the `OnlineSuffixTree` parent class.

        Returns:
            str: The text content of the suffix tree.
        """
        return self.text # Accesses parent's text attribute
    
    def compute_lz76_complexity(self) -> int:
        """Computes the LZ76 complexity based on the current state.
        
        LZ76 complexity is the number of phrases in the dictionary (`self.dictionary_size`).
        If there is an active `self.current_word` being built (which is not yet in the
        dictionary list but would be the next phrase), it is also counted.
        
        Returns:
            int: The LZ76 complexity.
        """
        # The C version (get_lz_complexity_c) returns C.dictionary_size + (1 if C.current_word_len > 0 else 0).
        # Here, self.dictionary_size tracks completed phrases.
        # self.current_word tracks the phrase currently being formed.
        complexity = self.dictionary_size
        if self.current_word: # If there's an unfinished phrase, it counts as one more.
            complexity += 1
        return complexity
    
    def return_dictionary(self) -> list[str]:
        """Returns the list of LZ76 phrases found so far.

        This includes all completed phrases stored in `self.dictionary` and also
        the `self.current_word` if it's non-empty (representing the phrase currently
        being formed).

        Returns:
            list[str]: The list of LZ76 dictionary phrases.
        """
        # Make a copy to avoid external modification of internal list.
        full_dictionary = list(self.dictionary) 
        if self.current_word: 
            full_dictionary.append(self.current_word)
        return full_dictionary
    
    def reset(self) -> None:
        """Resets the LZSuffixTree to its initial empty state.
        
        This involves resetting the parent `OnlineSuffixTree` and all LZ76-specific
        state variables of this class.
        """
        super().__init__("") # Reset parent OnlineSuffixTree (clears text, root, active point etc.)
        
        # Reset LZ-specific state variables
        self.current_word = ""
        self.current_text = ""
        self.last_char = ""
        self.dictionary_size = 0
        self.dictionary = []
        
        self.last_match_node = self.root # Should be new root from super().__init__
        self.last_match_edge = None
        self.last_match_length = 0
    
    def display_status(self) -> None:
        """Prints the current status of the LZ suffix tree processing.
        
        Includes the current word being built, the full text processed, the text
        in the underlying suffix tree (dictionary content), dictionary size, and
        details about the current LZ active match point.
        """
        print("---- LZ Suffix Tree Status (Python) ----")
        print(f"Full Text Processed: '{self.current_text}'")
        print(f"Current Word (being built): '{self.current_word}'")
        print(f"Dictionary Phrases: {self.dictionary}")
        print(f"Dictionary Size: {self.dictionary_size}")
        print(f"Computed LZ76 Complexity: {self.compute_lz76_complexity()}")
        print(f"Text in Suffix Tree (dictionary content): '{self.text}'") # From parent
        
        print(f"Last Char Processed by LZ: '{self.last_char}'")
        active_node_type = 'root' if self.last_match_node == self.root else 'internal'
        print(f"LZ Active Match Node: {active_node_type} (id: {id(self.last_match_node)})")
        
        if self.last_match_edge:
            if self.last_match_node and self.last_match_edge in self.last_match_node.children:
                edge_obj = self.last_match_node.children[self.last_match_edge]
                # Use parent's global_end for correct edge length calculation
                real_end = edge_obj.end if edge_obj.end != float('inf') else self.global_end 
                edge_str_segment = self.text[edge_obj.start : min(real_end, self.global_end) + 1] if self.text and real_end >= edge_obj.start else "<edge error>"
                print(f"LZ Active Match Edge: starts with '{self.last_match_edge}', label in tree: '{edge_str_segment}', matched length: {self.last_match_length}")
            else:
                print(f"LZ Active Match Edge: '{self.last_match_edge}' (but not found in current node children - state might be inconsistent or just after node transition)")
        else:
            print("LZ Active Match Edge: None (at a node)")
        print("----------------------------------------")

    def display_graphviz(self, view_now=False):
        """Generates a Graphviz visualization of the underlying suffix tree.
        
        Highlights the current LZ active match path if applicable.
        This method calls the parent `OnlineSuffixTree.display_graphviz`.

        Args:
            view_now (bool): If True, attempts to render and view the graph immediately.
                             Defaults to False.
        Returns:
            graphviz.Digraph or None: The graph object if graphviz is available, else None.
        """
        # Attempt to reconstruct the path of self.current_word in the tree for highlighting.
        # This path is relative to the suffix tree's content (self.text).
        highlight_path_nodes = [] 
        current_highlight_node = self.root
        matched_len = 0

        if self.current_word and self.text: # Only try if current_word and tree text exist
            highlight_path_nodes.append((current_highlight_node, None)) # Start at root
            word_to_trace = self.current_word

            while matched_len < len(word_to_trace):
                char_to_find = word_to_trace[matched_len]
                if char_to_find in current_highlight_node.children:
                    edge = current_highlight_node.children[char_to_find]
                    highlight_path_nodes[-1] = (current_highlight_node, char_to_find) # Mark edge taken
                    
                    edge_label_in_tree = self.text[edge.start : min(edge.end, self.global_end) + 1]
                    len_on_edge = 0
                    for i in range(len(edge_label_in_tree)):
                        if matched_len + i < len(word_to_trace) and \
                           word_to_trace[matched_len + i] == edge_label_in_tree[i]:
                            len_on_edge += 1
                        else:
                            break # Mismatch or end of word_to_trace on this edge
                    
                    matched_len += len_on_edge
                    if len_on_edge == len(edge_label_in_tree) and matched_len < len(word_to_trace):
                        # Traversed full edge and more of word_to_trace remains
                        current_highlight_node = edge.dest
                        highlight_path_nodes.append((current_highlight_node, None)) # Arrived at new node
                    else:
                        # Word ends on this edge or mismatched
                        break 
                else:
                    break # No edge for char_to_find
        
        # Call parent's display_graphviz with the constructed highlight path.
        # The parent method should handle the actual graphviz object creation.
        try:
            # Assuming parent class `OnlineSuffixTree` has `display_graphviz`
            # that accepts `highlight_path` (list of (node, edge_char_or_None) tuples)
            # and `view_now`.
            dot = super().display_graphviz(highlight_path=highlight_path_nodes, view_now=False) 
            if dot:
                # Add custom title for LZ Suffix Tree status
                title_parts = [
                    f"LZ Suffix Tree Status",
                    f"Full Text: '{self.current_text}'",
                    f"Current LZ Word: '{self.current_word}'",
                    f"Dictionary Size: {self.dictionary_size}", 
                    f"Computed LZ76: {self.compute_lz76_complexity()}",
                    f"Tree Text (LZ Dict): '{self.text}'"]
                dot.attr(label='\n'.join(title_parts), labelloc='t')
                if view_now:
                    dot.view() # Attempt to render and open
            return dot
        except AttributeError:
            print("Graphviz display not available or parent method missing.", file=sys.stderr)
            return None
        except Exception as e:
            print(f"Error during Graphviz generation: {e}", file=sys.stderr)
            return None

# Example usage:
if __name__ == "__main__":
    print("--- LZSuffixTree (Python) Example ---")
    lz_tree = LZSuffixTree() # Initialize empty
    
    test_word = "0101010101" 
    print(f"Processing string: '{test_word}'")
    
    for char_idx, char_val in enumerate(test_word):
        new_phrase_added = lz_tree.add_character(char_val)
        print(f"\nAdded '{char_val}' (char {char_idx+1}/{len(test_word)}):")
        if new_phrase_added:
            print(f"  >> New phrase completed. Dictionary size: {lz_tree.dictionary_size}")
        else:
            print(f"  >> Current phrase extended. Dictionary size: {lz_tree.dictionary_size}")
        lz_tree.display_status()
        # For debugging, view tree at each step (requires graphviz)
        # lz_tree.display_graphviz(view_now=True) 
        # input("Press Enter to continue...")

    final_complexity = lz_tree.compute_lz76_complexity()
    print(f"\n--- Final State for '{test_word}' ---")
    lz_tree.display_status()
    print(f"Final Computed LZ76 Complexity: {final_complexity}")
    print(f"Final Dictionary Phrases: {lz_tree.return_dictionary()}")

    # Expected for "0101010101": S1=0, S2=1, S3=01, S4=010, S5=10101 -> 5 phrases
    # Or, if logic is S1=0, S2=1, S3=01, S4=010, S5=10, S6=101 -> 6 phrases
    # The implementation logic of add_character / is_current_word_in_tree determines this.
    # Current: S1=0, S2=1, S3=01, S4=010, S5=10101 (length 5)
    # Dictionary: ['0', '1', '01', '010', '10101'] -> size 5. No current_word left.
    # So complexity should be 5.

    print("\nTesting reset...")
    lz_tree.reset()
    lz_tree.add_character('a')
    lz_tree.add_character('b')
    lz_tree.add_character('a')
    lz_tree.add_character('c')
    print(f"After 'abac': Complexity = {lz_tree.compute_lz76_complexity()}, Dict = {lz_tree.return_dictionary()}")
    lz_tree.display_status()

    # Test with a string that might have interesting suffix tree structure
    print("\nTesting with 'bananaabandana$'...")
    lz_tree_banana = LZSuffixTree("bananaabandana$")
    lz_tree_banana.display_status()
    print(f"LZ76 for 'bananaabandana$': {lz_tree_banana.compute_lz76_complexity()}")
    print(f"Dictionary: {lz_tree_banana.return_dictionary()}")
    
    # If graphviz is installed, generate a visualization of the final banana tree
    # print("Attempting to generate Graphviz for banana tree...")
    # dot_banana = lz_tree_banana.display_graphviz(view_now=False)
    # if dot_banana:
    #     try:
    #         dot_banana.render("lz_suffix_tree_banana", format="png", cleanup=True)
    #         print("Visualization 'lz_suffix_tree_banana.png' saved.")
    #     except Exception as e_gv:
    #         print(f"Could not render graphviz: {e_gv}")

