from .online_suffix import OnlineSuffixTree

class LZSuffixTree(OnlineSuffixTree):
    def __init__(self, initial_text=""):
        """
        Initialize an LZ-optimized suffix tree with optional initial text.
        This suffix tree will only contain text[:-1] (all characters except the last one),
        while keeping track of the full text as current_word.
        
        Args:
            initial_text (str): Optional initial text to add to the tree.
        
        LZ76 hidden variables:
            last_match_node is the node we're on when parsing new word
            last_match_edge is the first character of the edge we're on.
            last_match_length is how far along the edge we are.

        !! Note:
            We use a character, rather than start and end of the edge.
            This is because sometimes we split the edge we're on while building the suffix tree. 
            In that case, the split happens exactly at our current position.
            If we still assume the old edge end, we'd continue walking on an edge that no longer existed.
            Then we'd sometimes find "no match" even though there is now a match, along a newly created branch. 
        """

        # Initialize parent class with an empty string
        super().__init__("")
        
        # Current word is the full text (all characters)
        self.current_word = ""
        
        # Track all characters received so far
        self.current_text = ""
        
        # Last character (not in the tree)
        self.last_char = ""
        
        # Dictionary size for LZ76 complexity
        self.dictionary_size = 0
        self.dictionary = []
        
        # Tracking variables for efficient matching (similar to Ukkonen's active point)
        self.last_match_node = self.root  # Similar to active_node
        self.last_match_edge = None       # Is the first character of the edge we're on
        self.last_match_length = 0        # How far along the edge we are
        
        # Add initial text if provided
        if initial_text:
            for char in initial_text:
                self.add_character(char)
    
    def add_character(self, char):
        """
        Add a character to current_word, update the tree with all but the last character,
        and automatically compute LZ complexity. Uses Ukkonen-style tracking.
        
        Args:
            char (str): The character to add
            
        Returns:
            bool: True if a new word was added to the dictionary, False otherwise
        """
        # Store the result of whether a new word was added
        added_new_word = False
        
        # Add the character to current_word and current_text
        self.current_word += char
        self.current_text += char
        
        # Store the previous last character
        previous_last = self.last_char
        self.last_char = char
        
        # If we have a previous character, add it to the tree
        if previous_last:
            super().add_char(previous_last)
        
        # Check if the new character can be found in the tree from our current position
        if self.is_current_word_in_tree():
            # Character found - continue the current word
            pass
        else:
            # Character not found - add to dictionary and reset
            self.dictionary_size += 1
            
            # Reset tracking to start from root
            self.last_match_node = self.root
            self.last_match_edge = None
            self.last_match_length = 0
            
            # Reset current_word to be empty
            self.reset_current_word()
            
            # Indicate that we've added a new word
            added_new_word = True
        
        return added_new_word
    
    def is_current_word_in_tree(self):
        """
        Check if next character is a valid continuation from our current position in the tree.
        Uses a Ukkonen-style active point tracking for efficiency.
        
        Returns:
            bool: True if pattern still matches in the tree, False otherwise
        """
        # If we're at the root and don't have a last character yet
        if not self.last_char:
            return True
            
        # If we're in the middle of an edge
        if self.last_match_edge and self.last_match_length > 0:
            # Get the edge information
            edge_obj = self.last_match_node.children[self.last_match_edge]
            start, end, _ = edge_obj.start, edge_obj.end, edge_obj.dest
            
            # Calculate the real end of the edge
            real_end = end if end != float('inf') else self.global_end # In OnlineSuffixTree, global_end is the index
            
            # If we're not at the end of the edge yet
            # The edge length logic uses global_end, which is text_len -1.
            # An edge is text[start...real_end]. Length is real_end - start + 1.
            # Comparison: text[start + current_match_length_on_this_edge]
            # self.last_match_length is 1-indexed length along the conceptual match
            # Edge characters are text[edge_obj.start] to text[edge_obj.start + edge_len -1]
            # So the char to compare is text[edge_obj.start + self.last_match_length]
            
            # Original Python's edge.length() implies self.end includes global_end itself for open edges
            # Edge.length(current_end) -> real_end = current_end; return real_end - self.start + 1
            # This means an edge from start to global_end has length global_end - start + 1.
            # The characters are text[start], text[start+1], ..., text[global_end]
            # If self.last_match_length is 1, we check text[start+1]. If length is L, check text[start+L].
            
            # Let's use edge_obj.length method to be sure.
            current_edge_len = edge_obj.length(self.global_end)

            if self.last_match_length < current_edge_len: # If current match length is less than full edge length
                # Check if the next character matches on the current edge
                if self.text[edge_obj.start + self.last_match_length] == self.last_char:
                    # It matches, so update the length and return True
                    self.last_match_length += 1
                    return True
                else:
                    # No match - reset position (will be handled by caller by returning False)
                    return False
            else: # self.last_match_length == current_edge_len. We are at the end of this edge.
                # We've reached the end of this edge, so we're at a node
                self.last_match_node = edge_obj.dest
                self.last_match_edge = None # We are now at a node, not on an edge
                self.last_match_length = 0  # Reset length as we are at a node
                # Fall through to the node logic below to find the self.last_char from this new node
        
        # If we're at a node (either root or after traversing an edge fully)
        # Check if there's an edge that starts with the last character
        if self.last_char in self.last_match_node.children:
            # Get the edge
            self.last_match_edge = self.last_char # Store the first char of the new edge
            self.last_match_length = 1 # We've matched 1 char along this new edge
            # The active node for this new edge is still self.last_match_node
            return True
        
        # No matching edge found - the pattern doesn't exist
        return False
    
    def reset_current_word(self):
        """
        Reset the current word to empty.
        
        Returns:
            None
        """
        self.dictionary.append(self.current_word)
        self.current_word = ''
        # Reset tracking
        self.last_match_node = self.root
        self.last_match_edge = None
        self.last_match_length = 0
    
    def get_current_tree_text(self):
        """
        Get the text currently in the suffix tree (excludes the last character).
        
        Returns:
            str: The text in the tree
        """
        return self.text
    
    def compute_lz76_complexity(self):
        """
        Compute the LZ76 complexity of the current text.
        
        LZ76 complexity is the dictionary size plus 1 if there's an active word being processed.
        This accounts for the fact that when compressing, we need to describe the current
        word we're actively working on.
        
        Returns:
            int: The LZ76 complexity (dictionary size + 1 if current_word is not empty)
        """
        # If we have an active word being processed, add 1 to the dictionary size
        if self.current_word:
            return self.dictionary_size + 1
        # Otherwise, just return the dictionary size
        return self.dictionary_size
    
    def return_dictionary(self):
        """
        Return the dictionary.
        """
        if self.current_word:
            return self.dictionary + [self.current_word]
        else:
            return self.dictionary
    
    def reset(self):
        """
        Reset the tree and all associated variables.
        
        Returns:
            None
        """
        # Reset parent class
        super().__init__("")
        
        # Reset LZ-specific variables
        self.current_word = ""
        self.current_text = ""
        self.last_char = ""
        self.dictionary_size = 0
        
        # Reset tracking variables
        self.last_match_node = self.root
        self.last_match_edge = None
        self.last_match_length = 0
    
    def display_status(self):
        """
        Display the current status of the LZ suffix tree.
        
        Returns:
            None
        """
        print(f"Current word: '{self.current_word}'")
        print(f"Current text: '{self.current_text}'")
        print(f"Text in tree: '{self.text}'")
        print(f"Dictionary size: {self.dictionary_size}")
        
        # Display tracking info
        print(f"Last character: '{self.last_char}'")
        print(f"Match position: node at {'root' if self.last_match_node == self.root else 'internal node'}")
        if self.last_match_edge:
            edge_obj = self.last_match_node.children[self.last_match_edge]
            edge_start, edge_end, _ = edge_obj.start, edge_obj.end, edge_obj.dest
            real_end = edge_end if edge_end != float('inf') else self.global_end
            edge_str = self.text[edge_start:real_end+1] if self.text and real_end >= edge_start else ""
            print(f"Match edge: '{edge_str}', position: {self.last_match_length}")
        else:
            print("No active edge")
            
        print("Tree structure:")
        self.display()

    def display_graphviz(self):
        """
        Create a graphviz visualization of the suffix tree with the current parsing path highlighted.
        
        Returns:
            graphviz.Digraph: The graphviz plot object with highlighted parsing path
        """
        # Get the path to highlight based on our current position
        highlight_path = []
        
        # If we have an active match position
        if self.current_word:
            # Start from root
            current_node_for_viz = self.root
            
            # This reconstruction needs to be careful based on Python's LZ logic.
            # The Python version's self.last_match_node, self.last_match_edge, self.last_match_length
            # describe the end of the *longest match of current_word[:-1]* in the tree.
            # And `is_current_word_in_tree` then tries to extend with `self.last_char` (current_word[-1]).
            
            # For highlighting, we want to show the path of current_word as much as it exists.
            # This is complex because the highlight_path in parent display_graphviz expects a sequence
            # of (node, edge_char_from_node) or (node, None).

            # Simpler approach for now: Highlight up to last_match_node.
            # If last_match_edge is set, it means current_word[-1] made a match along that edge.

            # Simplified highlighting: just show the last_match_node and the edge if one was taken for last_char
            # This might not fully trace current_word if it's long.
            # A more accurate highlight would re-trace current_word from root.
            # Let's try to re-trace current_word for highlighting.
            
            path_trace_node = self.root
            path_idx = 0
            
            # Add root
            highlight_path.append((path_trace_node, None))
            
            temp_match_length = 0 # Tracks how much of current_word is matched for highlighting

            while temp_match_length < len(self.current_word):
                char_to_find_in_highlight = self.current_word[temp_match_length]
                if char_to_find_in_highlight in path_trace_node.children:
                    edge_obj_viz = path_trace_node.children[char_to_find_in_highlight]
                    highlight_path[-1] = (path_trace_node, char_to_find_in_highlight) # Mark edge taken from current node
                    
                    edge_text_viz = self.text[edge_obj_viz.start : min(edge_obj_viz.end, self.global_end) + 1]
                    
                    can_traverse_full_edge = True
                    for k in range(len(edge_text_viz)):
                        if temp_match_length + k >= len(self.current_word) or self.current_word[temp_match_length + k] != edge_text_viz[k]:
                            # current_word ends or mismatches on this edge
                            # highlight only up to temp_match_length + k on this edge
                            # The graphviz highlight highlights the whole edge if (node, edge_char) is given.
                            # This detail is hard to show with parent's current highlight_path format.
                            can_traverse_full_edge = False
                            break 
                        
                    if can_traverse_full_edge:
                        temp_match_length += len(edge_text_viz)
                        path_trace_node = edge_obj_viz.dest
                        highlight_path.append((path_trace_node, None)) # Arrived at new node
                    else:
                        # current_word ends midway on this edge or mismatches.
                        # The edge is highlighted, and we stop.
                        # temp_match_length would have been updated by the inner loop not shown here.
                        # For simplicity, we just say the edge was taken.
                        break 
                else:
                    # No edge for this char_to_find_in_highlight from path_trace_node
                    break # current_word cannot be traced further

        # Create the visualization with highlighted path
        dot = super().display_graphviz(highlight_path=highlight_path)
        
        if dot:
            # Add a title showing current state
            title = f"Current word: {self.current_word}\n"
            title += f"Last match position:\n"
            title += f"Node: {'root' if self.last_match_node == self.root else 'internal'}\n"
            if self.last_match_edge:
                edge_obj = self.last_match_node.children[self.last_match_edge]
                edge_start, edge_end, _ = edge_obj.start, edge_obj.end, edge_obj.dest
                real_end = edge_end if edge_end != float('inf') else self.global_end
                edge_str = self.text[edge_start:real_end+1] if self.text and real_end >= edge_start else ""
                title += f"Edge: '{edge_str}', position: {self.last_match_length}"
            else:
                title += "No active edge"
            dot.attr(label=title)
        
        return dot

# Example usage
if __name__ == "__main__":
    # Create an LZ suffix tree
    lz_tree = LZSuffixTree()
    
    # Process text with automatic LZ76 parsing
    word = "0101010101"  # Should have LZ76 complexity of 2
    print(f"Processing '{word}' with optimized LZ76 parsing:")
    
    for i, char in enumerate(word):
        new_word_added = lz_tree.add_character(char)
        print(f"\nAfter adding '{char}':")
        
        if new_word_added:
            print(f"New word was added to dictionary. Dictionary size now: {lz_tree.dictionary_size}")
        else:
            print(f"Current word continues. Dictionary size remains: {lz_tree.dictionary_size}")
        
        print(f"Current word is now: '{lz_tree.current_word}'")
        print(f"Last match length: {lz_tree.last_match_length}")
    
    # Final check for the last word
    if lz_tree.current_word and not lz_tree.is_current_word_in_tree():
        lz_tree.dictionary_size += 1
        # Reset current_word to avoid double counting in complexity calculation
        lz_tree.current_word = ""
        print(f"\nAdded final word to dictionary. Dictionary size now: {lz_tree.dictionary_size}")
    
    # Display final LZ76 complexity
    lz_complexity = lz_tree.compute_lz76_complexity()
    print(f"\nFinal LZ76 complexity for '{word}': {lz_complexity}")
    
    # For binary alternating pattern "0101010101", the LZ76 complexity should be:
    # - If current_word is empty: 2
    # - If current_word is not empty: 3 (dictionary size 2 + active word)
    expected_complexity = 3 if lz_tree.current_word else 2
    
    # Compare with the expected answer
    if lz_complexity == expected_complexity:
        print(f"Correct! LZ76 complexity for '0101010101' should be {expected_complexity}.")
        if lz_tree.current_word:
            print(f"This includes dictionary size {lz_tree.dictionary_size} plus 1 for the active word '{lz_tree.current_word}'.")
    else:
        print(f"Something went wrong! LZ76 complexity for '0101010101' should be {expected_complexity}, but got {lz_complexity}.")
    
    # Create and display the graphviz visualization
    dot = lz_tree.display_graphviz()
    if dot:
        # Save the visualization to a file
        dot.render("lz_suffix_tree", format="png", cleanup=True)
        print("\nVisualization saved as 'lz_suffix_tree.png'")

