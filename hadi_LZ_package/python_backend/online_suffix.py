class Edge:
    """
    Represents an edge in the suffix tree, with a start index, an end index,
    and a destination node.
    """
    __slots__ = ('start', 'end', 'dest')

    def __init__(self, start: int, end: float, dest: 'Node'):
        self.start = start
        self.end = end
        self.dest = dest

    def length(self, current_end: int) -> int:
        """
        Compute the length of this edge, using the global current_end
        if self.end is infinity.
        """
        real_end = self.end if self.end != float('inf') else current_end
        return real_end - self.start + 1

class Node:
    """
    A node in the suffix tree, storing outgoing edges and a suffix link.
    Each edge is stored in a dictionary mapping a character to an Edge.
    """
    __slots__ = ('children', 'suffix_link')

    def __init__(self):
        self.children: dict[str, Edge] = {}
        self.suffix_link: 'Node' | None = None

class OnlineSuffixTree:
    """
    Implicit suffix tree built online via Ukkonen's algorithm.
    Supports character-by-character addition and pattern search.
    Note: no terminator is added automatically; call add_terminator() when you
    wish to finalize the explicit tree with a unique end marker.
    """
    def __init__(self, initial_text: str = ""):
        self.text = ""              # accumulated text
        self.root = Node()           # root of the tree
        self.active_node = self.root
        self.active_edge = 0         # index in self.text
        self.active_length = 0
        self.remainder = 0
        self.global_end = -1                # global end index for leaves

        # build initial_text only
        if initial_text:
            for ch in initial_text:
                self.add_char(ch)

    def add_char(self, ch: str) -> None:
        """Add one character at position end+1 and update the tree."""
        self.text += ch
        self.global_end += 1
        self.remainder += 1
        last_new: Node | None = None

        while self.remainder > 0:
            if self.active_length == 0:
                self.active_edge = self.global_end
            edge_char = self.text[self.active_edge]

            if edge_char not in self.active_node.children:
                leaf = Node()
                self.active_node.children[edge_char] = Edge(self.global_end, float('inf'), leaf)
                if last_new:
                    last_new.suffix_link = self.active_node
                    last_new = None
            else:
                edge = self.active_node.children[edge_char]
                edge_len = edge.length(self.global_end)

                if self.active_length >= edge_len:
                    # walk down
                    self.active_edge += edge_len
                    self.active_length -= edge_len
                    self.active_node = edge.dest
                    continue

                if self.text[edge.start + self.active_length] == ch:
                    # extension rule 3: current suffix is already in tree
                    self.active_length += 1
                    if last_new:
                        last_new.suffix_link = self.active_node
                        last_new = None
                    break

                # split edge
                split = Node()
                # original edge shortened
                self.active_node.children[edge_char] = Edge(
                    edge.start,
                    edge.start + self.active_length - 1,
                    split
                )
                # new leaf from split
                leaf = Node()
                split.children[self.text[self.global_end]] = Edge(self.global_end, float('inf'), leaf)
                # leftover of original edge
                next_char = self.text[edge.start + self.active_length]
                split.children[next_char] = Edge(
                    edge.start + self.active_length,
                    edge.end,
                    edge.dest
                )

                if last_new:
                    last_new.suffix_link = split
                last_new = split

            # move to next suffix
            self.remainder -= 1
            if self.active_node is self.root and self.active_length > 0:
                self.active_length -= 1
                self.active_edge = self.global_end - self.remainder + 1
            elif self.active_node is not self.root:
                self.active_node = self.active_node.suffix_link or self.root

    def add_terminator(self) -> None:
        """Explicitly add a unique terminator character to finalize the tree."""
        self.add_char("$")

    def find(self, pattern: str) -> bool:
        """Return True if pattern exists in the accumulated text."""
        node = self.root
        i = 0
        while i < len(pattern):
            ch = pattern[i]
            if ch not in node.children:
                return False
            edge = node.children[ch]
            real_end = edge.end if edge.end != float('inf') else self.global_end
            real_end = min(real_end, self.global_end)
            segment = self.text[edge.start:real_end + 1]

            # compare segment to pattern slice
            j = 0
            while j < len(segment) and i + j < len(pattern):
                if segment[j] != pattern[i + j]:
                    return False
                j += 1
            if i + j == len(pattern):
                return True
            node = edge.dest
            i += j
        return True

    def display(self, node: Node | None = None, indent: int = 0) -> None:
        """Print the tree edges for inspection."""
        if node is None:
            node = self.root
            print("Suffix Tree:")
        for ch, edge in sorted(node.children.items()):
            real_end = edge.end if edge.end != float('inf') else self.global_end
            real_end = min(real_end, self.global_end)
            segment = self.text[edge.start:real_end + 1]
            print("  " * indent + repr(segment))
            self.display(edge.dest, indent + 1)