#include "online_suffix.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// --- Static Helper Function Declarations ---

static NodeC* new_node_c(void);
static EdgeC* new_edge_c(int start, int end, NodeC* dest);
// static int edge_length_c(EdgeC* edge, int current_global_end); // Now public via api_edge_length_c
static EdgeC* find_child_edge_by_char_internal(NodeC* node, char ch_val); // Internal version
static void set_child_edge_c(NodeC* node, char ch_val, EdgeC* edge_to_set);
static void free_node_recursive_c(NodeC* node); // Renamed for clarity (C specific)

// --- Static Helper Function Implementations ---

/**
 * @brief Allocates and initializes a new suffix tree node (NodeC).
 * Sets children_list and suffix_link to NULL.
 * @return Pointer to the newly allocated NodeC.
 * @note Exits program on malloc failure.
 */
static NodeC* new_node_c(void) {
    NodeC* node = (NodeC*)malloc(sizeof(NodeC));
    if (!node) {
        perror("Failed to allocate NodeC in new_node_c");
        exit(EXIT_FAILURE);
    }
    node->children_list = NULL;
    node->suffix_link = NULL;
    return node;
}

/**
 * @brief Allocates and initializes a new suffix tree edge (EdgeC).
 * @param start Start index of the edge label in the global text.
 * @param end End index of the edge label. Use INF_END for edges extending to current text end.
 * @param dest Pointer to the destination node of this edge.
 * @return Pointer to the newly allocated EdgeC.
 * @note Exits program on malloc failure.
 */
static EdgeC* new_edge_c(int start, int end, NodeC* dest) {
    EdgeC* edge = (EdgeC*)malloc(sizeof(EdgeC));
    if (!edge) {
        perror("Failed to allocate EdgeC in new_edge_c");
        exit(EXIT_FAILURE);
    }
    edge->start = start;
    edge->end = end;
    edge->dest = dest;
    return edge;
}

/* // This is now public as api_edge_length_c
static int edge_length_c(EdgeC* edge, int current_global_end) {
    if (!edge) return 0;
    int real_end = (edge->end == INF_END) ? current_global_end : edge->end;
    return real_end - edge->start + 1;
}
*/

/**
 * @brief Internal helper to find a child edge of a node that starts with a specific character.
 * This version is static and used internally within this file.
 * @param node The parent NodeC.
 * @param ch_val The first character of the edge to find.
 * @return Pointer to the EdgeC if found, NULL otherwise.
 */
static EdgeC* find_child_edge_by_char_internal(NodeC* node, char ch_val) {
    if (!node) return NULL;
    ChildEntry* current_entry = node->children_list;
    while (current_entry != NULL) {
        if (current_entry->character == ch_val) {
            return current_entry->edge;
        }
        current_entry = current_entry->next;
    }
    return NULL;
}

/**
 * @brief Sets or updates a child edge for a given character in a node\'s children list.
 *
 * If an edge starting with `ch_val` already exists, its `EdgeC*` pointer is updated to `edge_to_set`.
 * The old `EdgeC` object pointed to by the `ChildEntry` is NOT freed by this function; 
 * in Ukkonen\'s algorithm, splits often mean the old edge object is effectively replaced or becomes part of a new structure,
 * and its components are reused or explicitly freed elsewhere (e.g. `found_edge` in `add_char_c` split case).
 * If no edge starts with `ch_val`, a new `ChildEntry` is allocated and added to the list.
 *
 * @param node The parent NodeC whose children list is to be modified.
 * @param ch_val The character representing the first char of the edge.
 * @param edge_to_set Pointer to the EdgeC to associate with `ch_val`.
 * @note Exits program on malloc failure for a new ChildEntry.
 */
static void set_child_edge_c(NodeC* node, char ch_val, EdgeC* edge_to_set) {
    if (!node) return;

    ChildEntry* current_entry = node->children_list;
    ChildEntry* prev_entry = NULL;

    // Try to find an existing ChildEntry for ch_val
    while (current_entry != NULL) {
        if (current_entry->character == ch_val) {
            // Found existing entry, update its edge pointer.
            // The caller is responsible for managing the lifecycle of the EdgeC object that was previously here.
            // For example, in a split, the original found_edge that is being replaced by shortened_original_edge
            // is freed after its components are used for the new split structure.
            current_entry->edge = edge_to_set;
            return;
        }
        prev_entry = current_entry;
        current_entry = current_entry->next;
    }

    // No existing entry for ch_val, create and add a new ChildEntry.
    ChildEntry* new_child_entry = (ChildEntry*)malloc(sizeof(ChildEntry));
    if (!new_child_entry) {
        perror("Failed to allocate ChildEntry in set_child_edge_c");
        exit(EXIT_FAILURE);
    }
    new_child_entry->character = ch_val;
    new_child_entry->edge = edge_to_set;
    new_child_entry->next = NULL;

    if (prev_entry == NULL) { // List was empty, or new entry is the first one.
        node->children_list = new_child_entry;
    } else { // Append to the end of the list.
        prev_entry->next = new_child_entry;
    }
}


// --- Core API Function Implementations ---

// Documented in online_suffix.h
SuffixTreeCState* create_suffix_tree_c(void) {
    SuffixTreeCState* tree = (SuffixTreeCState*)malloc(sizeof(SuffixTreeCState));
    if (!tree) {
        perror("Failed to allocate SuffixTreeCState");
        exit(EXIT_FAILURE);
    }

    tree->text_capacity = 16; // Initial capacity, can be tuned.
    tree->text = (char*)malloc(tree->text_capacity * sizeof(char));
    if (!tree->text) {
        perror("Failed to allocate text buffer in SuffixTreeCState");
        free(tree);
        exit(EXIT_FAILURE);
    }
    tree->text[0] = '\0'; // Initialize with empty string representation if needed, though text_len=0 is key.
    tree->text_len = 0;

    tree->root = new_node_c();
    tree->active_node = tree->root; 
    tree->active_edge_char_index = -1; // Or some indicator of not being on an edge char; text[0] may be valid.
                                     // This is the start index in `text` of the edge implicitly traversed from active_node.
                                     // If active_length = 0, this is not strictly defined / used until an edge is chosen.
    tree->active_length = 0;
    tree->remainder = 0; // Start with 0 suffixes to add. Increases with each char.
    
    // Per Ukkonen\'s, root suffix link can point to a conceptual auxiliary node or handled by checks.
    // Often, it points to itself or NULL. Pointing to root is common.
    tree->root->suffix_link = tree->root; 

    return tree;
}

/**
 * @brief Recursively frees a node and its descendants (edges and child nodes).
 * This function performs a post-order traversal to free tree resources.
 * @param node The node to start freeing from.
 */
static void free_node_recursive_c(NodeC* node) {
    if (!node) return;

    ChildEntry* current_child_entry = node->children_list;
    while (current_child_entry != NULL) {
        ChildEntry* next_child_entry = current_child_entry->next;
        
        if (current_child_entry->edge) {
            // Recursively free the destination node of the edge.
            // Suffix tree edges form a tree structure (ignoring suffix links for this traversal),
            // so each node (except root) is a destination of exactly one edge from its parent.
            free_node_recursive_c(current_child_entry->edge->dest);
            free(current_child_entry->edge); // Free the edge structure itself.
        }
        free(current_child_entry); // Free the ChildEntry list node.
        current_child_entry = next_child_entry;
    }
    free(node); // Finally, free the node itself.
}

// Documented in online_suffix.h
void free_suffix_tree_c(SuffixTreeCState* tree) {
    if (!tree) return;
    if (tree->text) {
        free(tree->text);
        tree->text = NULL;
    }
    // The primary structure of nodes and edges forms a tree rooted at `tree->root`.
    // Suffix links are extra pointers but do not define ownership for freeing purposes.
    // A recursive free starting from the root should correctly deallocate all nodes and edges.
    if (tree->root) {
        free_node_recursive_c(tree->root);
        tree->root = NULL; // Mark as freed
    }
    
    free(tree); // Free the main state structure.
}


// Documented in online_suffix.h
void add_char_c(SuffixTreeCState* tree, char ch) {
    if (!tree) return; // Should not happen if API used correctly

    // Phase: Extend text
    if (tree->text_len + 1 >= tree->text_capacity) { // +1 for new char. Null terminator not explicitly managed here for text array for tree logic.
        tree->text_capacity = (tree->text_capacity == 0) ? 16 : tree->text_capacity * 2;
        char* new_text = (char*)realloc(tree->text, tree->text_capacity * sizeof(char));
        if (!new_text) {
            perror("Failed to reallocate text in add_char_c");
            // This is a critical error. Tree state becomes invalid.
            // For a library, an error code or flag should be set.
            exit(EXIT_FAILURE); 
        }
        tree->text = new_text;
    }
    tree->text[tree->text_len] = ch;
    tree->text_len++;
    int current_global_end = tree->text_len - 1; // Current char is at this index

    tree->remainder++; // One more suffix to add (the one ending with `ch`)
    NodeC* last_new_internal_node = NULL; // Used for setting suffix links after a split

    // Loop for each suffix that needs to be added in this phase (Ukkonen\'s trick)
    while (tree->remainder > 0) {
        // Determine current position before attempting to walk down or split.
        if (tree->active_length == 0) {
            // If at a node, the edge to consider is the one starting with `ch` (the current char of the suffix we are adding)
            // In Python, this was self.active_edge = self.text[self.global_end] (current char index)
            // Here, active_edge_char_index tracks the START of the edge we are ON.
            // If active_length is 0, we are AT active_node. The edge we *would* take is for `ch`.
            // The char to find on an edge from active_node is `ch` itself (the char of the current suffix end).
            // For find_child_edge_by_char_internal, we need tree->text[tree->active_edge_char_index] if active_length > 0
            // or `ch` if active_length == 0.
            // Let char_to_find_from_active_node be the character that labels the edge we need to check/traverse.
            // This is the (current_global_end - tree->active_length)-th character of the current suffix.
        }

        char char_to_test_on_edge_from_active_node;
        if (tree->active_length == 0) {
            // We are at active_node. The edge we are interested in starts with the current character `ch`.
            char_to_test_on_edge_from_active_node = ch; 
        } else {
            // We are on an edge. The edge is tree->text[tree->active_edge_char_index ...].
            // The next char to check on THIS active edge is tree->text[tree->active_edge_char_index + tree->active_length].
            // But for finding the edge itself, we use its first char: tree->text[tree->active_edge_char_index].
            // For Ukkonen's rule 3 (match/mismatch), we compare `ch` with the char at `active_length` on the edge.
            char_to_test_on_edge_from_active_node = tree->text[tree->active_edge_char_index];
        }

        EdgeC* active_edge_object = find_child_edge_by_char_internal(tree->active_node, char_to_test_on_edge_from_active_node);

        if (active_edge_object == NULL) { // Rule 2: No edge from active_node starts with char_to_test_on_edge_from_active_node.
                                          // This means we must insert a new leaf edge from active_node for `ch`.
            NodeC* new_leaf = new_node_c();
            EdgeC* new_e = new_edge_c(current_global_end, INF_END, new_leaf);
            set_child_edge_c(tree->active_node, ch, new_e); // The edge starts with `ch`.

            if (last_new_internal_node != NULL) { // If a previous split created an internal node.
                last_new_internal_node->suffix_link = tree->active_node;
                last_new_internal_node = NULL; 
            }
            // No need to set last_new_internal_node to active_node here, as active_node is not new.
        } else { // Edge found. Now, check if we can traverse or need to split (Rule 3 logic).
            int elen = api_edge_length_c(active_edge_object, current_global_end);

            // Walk-down optimization: If active_length is GTE edge length, traverse to edge\'s dest.
            if (tree->active_length >= elen) {
                tree->active_node = active_edge_object->dest;
                tree->active_length -= elen;
                // active_edge_char_index needs to be updated for the new active_node and remaining active_length.
                // It should be the start of the edge corresponding to the char (current_global_end - active_length).
                tree->active_edge_char_index += elen; // This might be incorrect. It should be re-derived for the new active_node.
                                                      // Or, if active_length becomes 0, it's set at start of loop.
                continue; // Re-evaluate from the new active_node with adjusted active_length.
            }

            // We are on active_edge_object, and active_length < elen.
            // Check if current char `ch` matches the char on the edge at this active_length.
            if (tree->text[active_edge_object->start + tree->active_length] == ch) { // Rule 3: Match. Suffix already implicitly exists.
                tree->active_length++; // Extend implicit match.
                if (last_new_internal_node != NULL) { // Suffix link from previous new internal node if any.
                    last_new_internal_node->suffix_link = tree->active_node;
                    last_new_internal_node = NULL;
                }
                break; // End current phase (remainder loop) as this suffix and all smaller ones are present.
            }

            // Rule 2 (Mismatch): Split is required. Current char `ch` differs from char on edge.
            NodeC* new_internal_split_node = new_node_c();
            
            // 1. Create new edge from active_node to new_internal_split_node.
            //    This edge label is the part of original active_edge_object before the split point.
            EdgeC* edge_to_split = new_edge_c(
                active_edge_object->start, // Starts same as original edge
                active_edge_object->start + tree->active_length - 1, // Ends just before the mismatch
                new_internal_split_node
            );
            set_child_edge_c(tree->active_node, tree->text[active_edge_object->start], edge_to_split);

            // 2. Create new leaf edge from new_internal_split_node for the current char `ch`.
            //    This represents the new suffix ending at `ch`.
            NodeC* new_leaf_for_ch = new_node_c();
            EdgeC* new_leaf_edge_from_split = new_edge_c(current_global_end, INF_END, new_leaf_for_ch);
            set_child_edge_c(new_internal_split_node, ch, new_leaf_edge_from_split);

            // 3. Create edge from new_internal_split_node for the remainder of the original active_edge_object.
            //    This edge starts with the character that caused the mismatch on the original edge.
            char char_after_split_on_original_edge = tree->text[active_edge_object->start + tree->active_length];
            EdgeC* continuation_of_original_edge = new_edge_c(
                active_edge_object->start + tree->active_length, // Starts at mismatch point
                active_edge_object->end,           // Original end (could be INF_END)
                active_edge_object->dest           // Original destination node
            );
            set_child_edge_c(new_internal_split_node, char_after_split_on_original_edge, continuation_of_original_edge);
            
            // The original active_edge_object is now replaced by edge_to_split and its components are reused or form new structures.
            // The EdgeC structure pointed to by active_edge_object itself should be freed.
            free(active_edge_object);

            // Set suffix link for previously created internal node (if any).
            if (last_new_internal_node != NULL) {
                last_new_internal_node->suffix_link = new_internal_split_node;
            }
            last_new_internal_node = new_internal_split_node; // This new split node might need a suffix link later.
        }

        tree->remainder--; // One suffix processed.

        // Follow suffix link for next iteration of remainder loop.
        if (tree->active_node == tree->root && tree->active_length > 0) {
            // If at root and still have active_length, shorten it from the left.
            // The new active_edge starts one char later in the text.
            tree->active_length--;
            // The char for the new active_edge (if active_length > 0) is text[current_global_end - remainder - active_length +1]?
            // Python: self.active_edge = self.global_end - self.remainder + 1 
            // This should be the start index of the suffix string we are currently trying to insert.
            // (text_len -1) - remainder + 1 = text_len - remainder
            // No, if text is S_1 S_2 ... S_k, active_edge was S_j ... S_k (char ch)
            // after SL, active_edge is S_{j+1} ... S_k
            // So active_edge_char_index should effectively point to S_{j+1}
            // If original active_edge_char_index was text[idx_start_of_edge]
            // The new one will be for the edge starting with text[idx_start_of_edge + 1] if we shift text window.
            // Ukkonen: active_edge = T[global_end - remainder + 1]
            tree->active_edge_char_index = current_global_end - tree->remainder - tree->active_length +1; // This is tricky. The first char of the *new* active edge path. If active_length is 0, this is not used immediately.

        } else if (tree->active_node != tree->root) { // If not root, follow defined suffix link.
            tree->active_node = tree->active_node->suffix_link; 
            // active_edge_char_index and active_length remain, to be re-evaluated against new active_node.
        }
        // If active_node is root and active_length became 0, the loop continues and active_edge logic at top will handle it.
    }
}

// Documented in online_suffix.h
bool find_c(SuffixTreeCState* tree, const char* pattern) {
    if (!tree || !pattern || !tree->root) return false;

    NodeC* current_node = tree->root;
    int pattern_len = strlen(pattern);
    if (pattern_len == 0) return true; // Empty pattern is found by convention.

    int current_char_in_pattern_idx = 0;
    int current_global_end = tree->text_len - 1;

    while (current_char_in_pattern_idx < pattern_len) {
        char pattern_char_to_match_on_edge = pattern[current_char_in_pattern_idx];
        EdgeC* found_edge = find_child_edge_by_char_internal(current_node, pattern_char_to_match_on_edge);

        if (found_edge == NULL) {
            return false; // No edge from current_node starts with this pattern character.
        }

        // An edge is found. Compare the pattern segment with the edge label.
        int edge_start_idx_in_text = found_edge->start;
        int edge_actual_end_idx_in_text = (found_edge->end == INF_END) ? current_global_end : found_edge->end;
        int current_edge_len = edge_actual_end_idx_in_text - edge_start_idx_in_text + 1;

        for (int i = 0; i < current_edge_len; ++i) {
            // Check if pattern is exhausted while on this edge.
            if (current_char_in_pattern_idx >= pattern_len) {
                return true; // Pattern is a prefix of path, so it is found.
            }
            // Compare char from pattern with char from edge label (text).
            if (tree->text[edge_start_idx_in_text + i] != pattern[current_char_in_pattern_idx]) {
                return false; // Mismatch on the edge.
            }
            current_char_in_pattern_idx++; // Matched one more character.
        }
        
        // If we successfully traversed the entire edge label and pattern is not exhausted,
        // move to the destination node of this edge.
        current_node = found_edge->dest;
        // Loop continues to match remaining part of the pattern from current_node.
    }
    // If loop finishes, means current_char_in_pattern_idx == pattern_len, so pattern is fully matched.
    return true; 
}

// Documented in online_suffix.h
int get_text_len_c(SuffixTreeCState* tree) {
    if (!tree) return 0;
    return tree->text_len;
}

// Documented in online_suffix.h
char get_text_char_at_c(SuffixTreeCState* tree, int index) {
    if (!tree || index < 0 || index >= tree->text_len) {
        if (tree && tree->text_len == 0 && index == 0) { /* common case for empty string? */ }
        else if (tree) fprintf(stderr, "Warning: get_text_char_at_c index %d out of bounds for text_len %d.\n", index, tree->text_len);
        else fprintf(stderr, "Warning: get_text_char_at_c called with NULL tree.\n");
        return '\0'; // Error: return null char for out of bounds or NULL tree.
    }
    return tree->text[index];
}

// --- Exposed Helper Function Implementations ---

// Documented in online_suffix.h
// This is the public API version, the internal one is find_child_edge_by_char_internal
EdgeC* api_find_child_edge_by_char(NodeC* node, char ch_val, const char* text __attribute__((unused))) {
    // `text` parameter is not used by this implementation as ChildEntry stores the first char.
    // Kept for API compatibility if some versions/callers expect it, but marked unused.
    return find_child_edge_by_char_internal(node, ch_val);
}

// Documented in online_suffix.h
int api_edge_length_c(EdgeC* edge, int current_global_end) {
    if (!edge) return 0;
    int real_end = (edge->end == INF_END) ? current_global_end : edge->end;
    // Ensure start is not past real_end, can happen if INF_END and global_end is small or edge is empty.
    if (edge->start > real_end) return 0; 
    return real_end - edge->start + 1;
}
