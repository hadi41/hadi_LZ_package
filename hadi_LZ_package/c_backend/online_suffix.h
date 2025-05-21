#ifndef ONLINE_SUFFIX_H
#define ONLINE_SUFFIX_H

#include <stdbool.h> // For bool type

// Using -1 for infinity for edge.end, as global_end is always >= 0
#define INF_END -1

// Forward declarations
typedef struct NodeC NodeC;
typedef struct EdgeC EdgeC;
typedef struct SuffixTreeCState SuffixTreeCState;

struct EdgeC {
    int start;
    int end; // Use INF_END for infinity, resolved against SuffixTreeCState->global_end
    NodeC* dest;
};

// Child entry for the linked list in NodeC
typedef struct ChildEntry {
    char character;         // The first character of the edge
    EdgeC* edge;
    struct ChildEntry* next;
} ChildEntry;

struct NodeC {
    ChildEntry* children_list; // Linked list of outgoing edges
    NodeC* suffix_link;
};

struct SuffixTreeCState {
    char* text;
    int text_capacity;
    int text_len;       // Current length of the text, equivalent to python's global_end + 1

    NodeC* root;
    NodeC* active_node;
    int active_edge_char_index; // Start index in `text` of the edge implicitly traversed from active_node
    int active_length;  // How far along that implicit/explicit edge we are
    int remainder;      // Number of suffixes yet to be explicitly added

    // global_end is (text_len - 1)
};

// API Functions
SuffixTreeCState* create_suffix_tree_c(void);
void free_suffix_tree_c(SuffixTreeCState* tree);
void add_char_c(SuffixTreeCState* tree, char ch);
bool find_c(SuffixTreeCState* tree, const char* pattern);

// Helper functions (primarily for the wrapper or internal use if needed)
int get_text_len_c(SuffixTreeCState* tree);
char get_text_char_at_c(SuffixTreeCState* tree, int index);

// --- Exposed Helper Functions for other C modules ---
EdgeC* api_find_child_edge_by_char(NodeC* node, char ch_val);
int api_edge_length_c(EdgeC* edge, int current_global_end);

#endif // ONLINE_SUFFIX_H 