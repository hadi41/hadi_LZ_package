'''Pure Python implementation of an Online Suffix Tree using Ukkonen's Algorithm.

This module provides the `OnlineSuffixTree` class, along with helper classes `Node` 
and `Edge`, to construct a suffix tree for a given string character by character.
It implements Ukkonen's algorithm for O(n) online construction (amortized for
alphabets of constant size, or O(n log |Sigma|) for larger alphabets if edge lookups
are not O(1)).

Features:
- Online construction: Characters can be added one at a time.
- Pattern searching: Supports finding if a pattern exists in the text.
- Visualization: Includes a basic text-based display and hooks for Graphviz
  (if the `graphviz` library is installed).

Classes:
    Edge: Represents an edge in the suffix tree.
    Node: Represents a node (internal or leaf) in the suffix tree.
    OnlineSuffixTree: The main class implementing Ukkonen's algorithm.
'''

class Edge:
    """Represents an edge in the suffix tree.

    An edge connects two nodes and is labeled by a substring of the main text.
    The substring is defined by `start` and `end` indices into the text.
    `float('inf')` is used for `end` to signify edges that extend to the
    current end of the text (typically leaf edges in Ukkonen's construction).

    Attributes:
        start (int): The starting index (inclusive) of the edge label in the text.
        end (float | int): The ending index (inclusive) of the edge label in the text.
                         Can be `float('inf')`.
        dest (Node): The destination node of this edge.
    """
    __slots__ = ('start', 'end', 'dest') # Optimizes memory usage

    def __init__(self, start: int, end: float, dest: 'Node'): # Use float for end due to float('inf')
        """Initializes an Edge.
        
        Args:
            start: Start index of the edge label.
            end: End index of the edge label (can be float('inf')).
            dest: The destination Node of this edge.
        """
        self.start = start
        self.end = end
        self.dest = dest

    def length(self, current_global_end: int) -> int:
        """Calculates the length of the edge label.

        If `self.end` is `float('inf')`, the length is determined relative to
        the `current_global_end` of the text being processed.

        Args:
            current_global_end: The current last index of the text in the suffix tree.
                                (Typically `len(text) - 1`).

        Returns:
            The length of the string segment labeling this edge.
            Returns 0 if start > real_end (e.g., for an effectively empty edge).
        """
        real_end = self.end if self.end != float('inf') else current_global_end
        if self.start > real_end: # Can happen if edge is conceptually empty or after some tree ops
            return 0
        return int(real_end - self.start + 1)

    def __repr__(self) -> str:
        return f"Edge(start={self.start}, end={self.end}, dest_id={id(self.dest)})"

class Node:
    """Represents a node in the suffix tree.

    Nodes store outgoing edges in a dictionary, where keys are the first characters
    of the edge labels. Each node can also have a suffix link to another node,
    which is a crucial part of Ukkonen's algorithm.

    Attributes:
        children (dict[str, Edge]): A dictionary mapping the first character of an
                                   outgoing edge to the `Edge` object itself.
        suffix_link (Node | None): The suffix link for this node, or None if not set
                                   (or for the root, depending on convention).
    """
    __slots__ = ('children', 'suffix_link') # Optimizes memory usage

    def __init__(self):
        """Initializes a new Node with no children and no suffix link."""
        self.children: dict[str, Edge] = {} # Maps first char of edge to Edge object
        self.suffix_link: 'Node' | None = None

    def __repr__(self) -> str:
        return f"Node(id={id(self)}, children={list(self.children.keys())}, suffix_link_id={id(self.suffix_link) if self.suffix_link else None})"

class OnlineSuffixTree:
    """An implicit suffix tree built online using Ukkonen's algorithm.

    This class allows for character-by-character construction of a suffix tree.
    It maintains the necessary state for Ukkonen's algorithm, including the
    active point (node, edge, length) and the number of remaining suffixes to add.

    The tree stores all suffixes of the text added so far. Leaf edges are typically
    represented with an end index of `float('inf')`, meaning they extend to the
    current end of the overall text (`global_end`).

    Attributes:
        text (str): The accumulated string for which the suffix tree is built.
        root (Node): The root node of the suffix tree.
        active_node (Node): (Ukkonen) The current node from which suffix extensions begin.
        active_edge (int): (Ukkonen) Index in `self.text` indicating the start of the current
                           active edge. If `active_length` is 0, this points to the character
                           about to be processed from `active_node`.
        active_length (int): (Ukkonen) The number of characters matched along the current
                             `active_edge` from `active_node`. If 0, we are at `active_node`.
        remainder (int): (Ukkonen) Number of suffixes yet to be explicitly processed in the
                         current phase (after adding a new character).
        global_end (int): The index of the last character currently in `self.text`.
                          Equivalent to `len(self.text) - 1`.
    """
    def __init__(self, initial_text: str = ""):
        """Initializes the OnlineSuffixTree.

        Args:
            initial_text (str, optional): An optional string to build the tree for initially.
                                        Defaults to "".
        """
        self.text: str = ""              
        self.root: Node = Node()          
        self.active_node: Node = self.root
        # active_edge: Start index in self.text of the edge we are currently on, if active_length > 0.
        # If active_length == 0, it's the index of the character we are trying to add from active_node.
        self.active_edge: int = 0        
        self.active_length: int = 0
        self.remainder: int = 0
        self.global_end: int = -1 # Index of the last character in self.text (-1 for empty text)

        if initial_text:
            for char_val in initial_text:
                self.add_char(char_val)

    def add_char(self, ch: str) -> None:
        """Adds a single character to the tree, extending all suffixes.

        This implements one phase of Ukkonen's algorithm.
        The `global_end` is incremented, `ch` is appended to `self.text`,
        and `remainder` is incremented. Then, a loop processes each remaining
        suffix that needs to be added or updated.

        Args:
            ch (str): The character to add. Must be a single character.
        """
        if not isinstance(ch, str) or len(ch) != 1:
            raise ValueError("Input must be a single character.")

        self.text += ch
        self.global_end += 1
        self.remainder += 1
        last_new_internal_node: Node | None = None # For setting suffix links after splits

        while self.remainder > 0:
            if self.active_length == 0:
                # If at a node, the active_edge is conceptually the current char being processed.
                self.active_edge = self.global_end 
            
            # char_on_active_edge is the first character of the edge from active_node that we need to check/traverse.
            char_on_active_edge_label = self.text[self.active_edge]

            if char_on_active_edge_label not in self.active_node.children:
                # Rule 2: No edge from active_node starts with char_on_active_edge_label.
                # Create a new leaf edge for the current suffix.
                new_leaf_node = Node()
                self.active_node.children[char_on_active_edge_label] = Edge(self.global_end, float('inf'), new_leaf_node)
                
                # If a previous split created an internal node, link it to active_node.
                if last_new_internal_node:
                    last_new_internal_node.suffix_link = self.active_node
                    last_new_internal_node = None
            else:
                # Edge exists. Need to check if we can traverse or need a split.
                current_edge = self.active_node.children[char_on_active_edge_label]
                current_edge_len = current_edge.length(self.global_end)

                if self.active_length >= current_edge_len:
                    # Active point is beyond this edge. Walk down.
                    self.active_node = current_edge.dest
                    self.active_length -= current_edge_len
                    self.active_edge += current_edge_len
                    continue # Re-evaluate from the new active_node.

                # We are on `current_edge`, and `active_length < current_edge_len`.
                # Check if `ch` (the char we are adding this phase) matches the char on the edge.
                if self.text[current_edge.start + self.active_length] == ch:
                    # Rule 3 (Show Stopper / Match): Suffix is already implicitly in the tree.
                    self.active_length += 1
                    if last_new_internal_node: # Set suffix link for any prior new internal node.
                        last_new_internal_node.suffix_link = self.active_node
                        last_new_internal_node = None
                    break # End this phase, all remaining suffixes also exist.

                # Rule 2 (Split): Mismatch. `ch` is different from the char on `current_edge`.
                new_internal_node = Node()
                
                # 1. Shorten the original edge to point to the new_internal_node.
                original_edge_first_char = self.text[current_edge.start]
                self.active_node.children[original_edge_first_char] = Edge(
                    current_edge.start,
                    current_edge.start + self.active_length - 1, # Ends just before the split point
                    new_internal_node
                )
                
                # 2. Create a new leaf edge from new_internal_node for `ch`.
                new_leaf_for_ch = Node()
                new_internal_node.children[ch] = Edge(self.global_end, float('inf'), new_leaf_for_ch)
                
                # 3. Create an edge from new_internal_node for the rest of the original edge.
                char_after_split_on_original = self.text[current_edge.start + self.active_length]
                new_internal_node.children[char_after_split_on_original] = Edge(
                    current_edge.start + self.active_length, # Starts at the split point
                    current_edge.end,                      # Original end (could be inf)
                    current_edge.dest                      # Original destination
                )

                if last_new_internal_node: # Set suffix link for previous new internal node.
                    last_new_internal_node.suffix_link = new_internal_node
                last_new_internal_node = new_internal_node # This new node will need a suffix link.

            # One suffix processed, move to the next one for this phase.
            self.remainder -= 1
            
            # Follow suffix link from active_node (or reset active_point if at root).
            if self.active_node == self.root and self.active_length > 0:
                self.active_length -= 1
                # Adjust active_edge: start of the (current_global_end - remainder)-th suffix.
                self.active_edge = self.global_end - self.remainder + 1 
            elif self.active_node != self.root:
                self.active_node = self.active_node.suffix_link or self.root # Follow link, or to root if None
            # If active_node is root and active_length is 0, active_edge gets set at loop start.

    def add_terminator(self, terminator_char: str = "$") -> None:
        """Adds a unique terminator character to the text and tree.

        This can be useful to ensure all suffixes are explicitly represented by paths
        ending at leaf nodes, which simplifies some suffix tree algorithms.
        The terminator should ideally be a character not present in the alphabet.

        Args:
            terminator_char (str, optional): The terminator character. Defaults to "$".
        """
        if not isinstance(terminator_char, str) or len(terminator_char) != 1:
            raise ValueError("Terminator must be a single character string.")
        self.add_char(terminator_char)

    def find(self, pattern: str) -> bool:
        """Checks if a given pattern string exists as a substring in the tree.

        Args:
            pattern: The string to search for.

        Returns:
            True if the pattern is found, False otherwise.
        """
        if not pattern: # Empty pattern is usually considered found.
            return True
            
        current_node = self.root
        pattern_idx = 0
        while pattern_idx < len(pattern):
            char_to_match = pattern[pattern_idx]
            if char_to_match not in current_node.children:
                return False # No edge starts with this character.
            
            edge = current_node.children[char_to_match]
            edge_label_in_text = self.text[edge.start : min(edge.end, self.global_end) + 1]
            
            len_matched_on_edge = 0
            for i in range(len(edge_label_in_text)):
                if pattern_idx + i >= len(pattern) or pattern[pattern_idx + i] != edge_label_in_text[i]:
                    # Pattern ends or mismatches on this edge.
                    break
                len_matched_on_edge += 1
            
            if len_matched_on_edge < len(edge_label_in_text) and pattern_idx + len_matched_on_edge < len(pattern):
                return False # Mismatch before edge or pattern ended.

            pattern_idx += len_matched_on_edge
            if pattern_idx == len(pattern):
                return True # Pattern fully matched.
            
            current_node = edge.dest # Move to next node
            
        return pattern_idx == len(pattern) # Should be true if loop completed.

    def display(self, node: Node | None = None, indent_level: int = 0, prefix: str = "") -> None:
        """Prints a text representation of the suffix tree structure for debugging.

        Args:
            node (Node, optional): The node to start displaying from. Defaults to root.
            indent_level (int, optional): Current indentation level for pretty printing.
            prefix (str, optional): Prefix string for child branches.
        """
        if node is None:
            node = self.root
            print("Suffix Tree (Root):")

        children_items = sorted(node.children.items()) # Sort for consistent display
        for i, (char, edge) in enumerate(children_items):
            is_last_child = (i == len(children_items) - 1)
            connector = "└── " if is_last_child else "├── "
            
            edge_label_segment = self.text[edge.start : min(edge.end, self.global_end) + 1]
            suffix_link_info = f" (SL->id:{id(edge.dest.suffix_link)})" if edge.dest.suffix_link else ""
            print(f"{prefix}{connector}'{edge_label_segment}' (to Node id:{id(edge.dest)}{suffix_link_info})")
            
            new_prefix = prefix + ("    " if is_last_child else "│   ")
            self.display(edge.dest, indent_level + 1, new_prefix)

    def display_graphviz(self, highlight_path: list | None = None, view_now: bool = False) -> object | None:
        """Generates a Graphviz Digraph object for visualizing the suffix tree.

        Requires the `graphviz` Python library to be installed.

        Args:
            highlight_path (list, optional): A list of (Node, edge_char or None) tuples 
                                           representing a path to highlight in the tree.
                                           If (Node, char), highlights edge char from Node.
                                           If (Node, None), highlights the Node itself.
            view_now (bool): If True and graphviz is available, attempts to render and
                             view the graph immediately. Defaults to False.

        Returns:
            graphviz.Digraph object if successful, None otherwise (e.g., if graphviz
            is not installed or an error occurs).
        """
        try:
            import graphviz # type: ignore
        except ImportError:
            print("Graphviz library not found. Please install it to use display_graphviz: pip install graphviz", file=sys.stderr)
            return None

        dot = graphviz.Digraph(comment='Suffix Tree')
        dot.attr(rankdir='TB') # Top-to-Bottom layout

        # Create a set of highlighted edges/nodes for quick lookup
        highlighted_elements = set()
        if highlight_path:
            for item in highlight_path:
                if isinstance(item, tuple) and len(item) == 2:
                    node_obj, edge_char = item
                    if edge_char:
                        highlighted_elements.add((id(node_obj), edge_char))
                    else:
                        highlighted_elements.add(id(node_obj)) # Highlight node
                elif isinstance(item, Node):
                     highlighted_elements.add(id(item)) # Allow highlighting just a node by object

        # Add nodes and edges recursively
        q: list[Node] = [self.root]
        visited_nodes = {id(self.root)}
        dot.node(str(id(self.root)), "R", 
                   color='red' if id(self.root) in highlighted_elements else 'black', 
                   style='filled' if id(self.root) in highlighted_elements else '',
                   fillcolor='lightcoral' if id(self.root) in highlighted_elements else 'white')

        while q:
            curr_node = q.pop(0)
            # Add suffix link if it exists and is not to self (for root)
            if curr_node.suffix_link and id(curr_node.suffix_link) != id(curr_node):
                dot.edge(str(id(curr_node)), str(id(curr_node.suffix_link)), style='dashed', arrowhead='empty', color='grey')

            for char, edge_obj in sorted(curr_node.children.items()):
                edge_label = self.text[edge_obj.start : min(edge_obj.end, self.global_end) + 1]
                dest_node_id_str = str(id(edge_obj.dest))

                edge_is_highlighted = (id(curr_node), char) in highlighted_elements
                dest_node_is_highlighted = id(edge_obj.dest) in highlighted_elements

                if id(edge_obj.dest) not in visited_nodes:
                    dot.node(dest_node_id_str, "", 
                               color='red' if dest_node_is_highlighted else 'black', 
                               style='filled' if dest_node_is_highlighted else '',
                               fillcolor='lightcoral' if dest_node_is_highlighted else 'white')
                    visited_nodes.add(id(edge_obj.dest))
                    q.append(edge_obj.dest)
                
                dot.edge(str(id(curr_node)), dest_node_id_str, label=f"{char}({edge_label})", 
                         color='red' if edge_is_highlighted else 'black',
                         penwidth='2.0' if edge_is_highlighted else '1.0')
        if view_now:
            try:
                dot.view()
            except Exception as e_gv_view:
                print(f"Could not automatically view graph: {e_gv_view}. You might need to install Graphviz executables or a viewer.", file=sys.stderr)
        return dot