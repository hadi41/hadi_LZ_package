#ifndef ONLINE_SUFFIX_H
#define ONLINE_SUFFIX_H

#include <stdbool.h> // For bool type
#include <stddef.h>  // For size_t (though not directly used here, good for consistency with C files)

/** @brief Represents an infinite end for an edge, resolved against `SuffixTreeCState->text_len - 1`. */
#define INF_END -1

// Forward declarations for core suffix tree structures
typedef struct NodeC NodeC;
typedef struct EdgeC EdgeC;
typedef struct SuffixTreeCState SuffixTreeCState;

/**
 * @struct EdgeC
 * @brief Represents an edge in the suffix tree.
 * An edge connects two nodes and is labeled by a substring of the input text.
 */
struct EdgeC {
    int start;      /**< Start index (inclusive) in `SuffixTreeCState->text` for the edge label. */
    int end;        /**< End index (inclusive) in `SuffixTreeCState->text` for the edge label. 
                     *   Uses `INF_END` if the edge extends to the current end of the text (a leaf edge). */
    NodeC* dest;    /**< Pointer to the destination node of this edge. */
};

/**
 * @struct ChildEntry
 * @brief A node in a linked list representing the children of a `NodeC`.
 * Each `ChildEntry` points to an `EdgeC` that starts with a specific character.
 */
typedef struct ChildEntry {
    char character;         /**< The first character of the `EdgeC` this entry represents. Used for quick lookup. */
    EdgeC* edge;            /**< Pointer to the actual `EdgeC` (child). */
    struct ChildEntry* next;/**< Pointer to the next `ChildEntry` in the linked list for this parent node. */
} ChildEntry;

/**
 * @struct NodeC
 * @brief Represents a node in the suffix tree.
 * Nodes can be internal or leaf nodes. They have outgoing edges (children) and may have a suffix link.
 */
struct NodeC {
    ChildEntry* children_list; /**< Pointer to the head of a linked list of `ChildEntry`s, representing outgoing edges. */
    NodeC* suffix_link;      /**< Pointer to another `NodeC` which is the suffix link for this node. NULL for root initially. */
};

/**
 * @struct SuffixTreeCState
 * @brief Manages the overall state of an online suffix tree constructed using Ukkonen\'s algorithm.
 *
 * This structure holds the input text, the tree (root node), and the \"active point\"
 * variables required by Ukkonen\'s algorithm for efficient online construction.
 */
struct SuffixTreeCState {
    char* text;                 /**< Buffer storing the input text for which the suffix tree is built. Dynamically resized. */
    int text_capacity;          /**< Current allocated capacity of the `text` buffer. */
    int text_len;               /**< Current length of the string stored in `text`. This is equivalent to global_end + 1 from Ukkonen\'s. */

    NodeC* root;                /**< Pointer to the root node of the suffix tree. */
    NodeC* active_node;         /**< (Ukkonen) The current node from which the next suffix extension begins. */
    int active_edge_char_index; /**< (Ukkonen) If `active_length` > 0, this is the start index in `text` of the character 
                                 *   labeling the edge from `active_node` that we are currently on. 
                                 *   More precisely, it is the index of the first char of that edge. 
                                 *   Set to a sentinel (e.g., -1 or 0 if not used for char itself) when active_length is 0. */
    int active_length;          /**< (Ukkonen) The number of characters matched along the current `active_edge` from `active_node`. 
                                 *   If 0, we are exactly at `active_node`. */
    int remainder;              /**< (Ukkonen) The number of suffixes that still need to be explicitly added to the tree in the current phase. */

    // Note: global_end in Ukkonen\'s algorithm corresponds to (text_len - 1) here.
};

// --- Core API Functions ---

/**
 * @brief Creates and initializes a new, empty SuffixTreeCState.
 * Allocates memory for the state and its root node. Initializes text buffer.
 * @return Pointer to the newly created SuffixTreeCState, or NULL on allocation failure (exits program).
 * @note Exits program on critical allocation failure.
 */
SuffixTreeCState* create_suffix_tree_c(void);

/**
 * @brief Frees a SuffixTreeCState and all its associated resources.
 * This includes freeing all nodes, edges, child entries, and the text buffer.
 * @param tree Pointer to the SuffixTreeCState to be freed. If NULL, the function does nothing.
 */
void free_suffix_tree_c(SuffixTreeCState* tree);

/**
 * @brief Adds a character to the suffix tree, updating it online using Ukkonen\'s algorithm.
 * @param tree Pointer to the SuffixTreeCState to be updated.
 * @param ch The character to add to the end of the current text.
 * @note Exits program on critical allocation failure during tree extension.
 */
void add_char_c(SuffixTreeCState* tree, char ch);

/**
 * @brief Checks if a given pattern string exists as a substring in the text represented by the suffix tree.
 * @param tree Pointer to the SuffixTreeCState.
 * @param pattern The null-terminated C string to search for.
 * @return `true` if the pattern is found, `false` otherwise or if tree/pattern is NULL.
 */
bool find_c(SuffixTreeCState* tree, const char* pattern);

// --- Helper/Utility Functions (primarily for wrapper or internal use) ---

/**
 * @brief Gets the current length of the text stored in the suffix tree.
 * @param tree Pointer to the SuffixTreeCState.
 * @return The length of the text. Returns 0 if tree is NULL.
 */
int get_text_len_c(SuffixTreeCState* tree);

/**
 * @brief Gets the character at a specific index from the text stored in the suffix tree.
 * @param tree Pointer to the SuffixTreeCState.
 * @param index The index of the character to retrieve.
 * @return The character at the given index. Returns \'\\0\' or handles error if index is out of bounds or tree is NULL.
 */
char get_text_char_at_c(SuffixTreeCState* tree, int index);

// --- Helper Functions Exposed for Use by Other C Modules (e.g., lz_suffix.c) ---

/**
 * @brief Finds a child edge of a given node that starts with a specific character.
 * Iterates through the node\'s children list.
 * @param node Pointer to the parent `NodeC`.
 * @param ch_val The character to match the first character of an outgoing edge.
 * @param text Pointer to the global text array (from SuffixTreeCState->text), needed to read edge labels.
 * @return Pointer to the `EdgeC` if found, otherwise NULL.
 */
EdgeC* api_find_child_edge_by_char(NodeC* node, char ch_val, const char* text);

/**
 * @brief Calculates the length of an edge.
 * If edge->end is INF_END, its length is calculated relative to `current_global_end` (which is typically `text_len - 1`).
 * @param edge Pointer to the `EdgeC`.
 * @param current_global_end The current effective end index of the text (usually `SuffixTreeCState->text_len - 1`).
 * @return The length of the edge label (number of characters).
 */
int api_edge_length_c(EdgeC* edge, int current_global_end);

#endif // ONLINE_SUFFIX_H 