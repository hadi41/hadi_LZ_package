#include "lz_suffix.h"
#include "online_suffix.h" // For API helpers like api_find_child_edge_by_char

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define INITIAL_WORD_BUFFER_CAPACITY 16

// Forward declaration for internal helper
static bool is_match_in_base_tree_c(LZSuffixTreeCState* lz_tree, char char_to_find);
static void internal_reset_lz_state(LZSuffixTreeCState* lz_tree, bool reset_base_tree);

LZSuffixTreeCState* create_lz_suffix_tree_c(void) {
    LZSuffixTreeCState* lz_tree = (LZSuffixTreeCState*)malloc(sizeof(LZSuffixTreeCState));
    if (!lz_tree) {
        perror("Failed to allocate LZSuffixTreeCState");
        exit(EXIT_FAILURE);
    }

    lz_tree->base_tree = create_suffix_tree_c();
    if (!lz_tree->base_tree) {
        free(lz_tree);
        // create_suffix_tree_c would have printed error and exited, but defensive
        exit(EXIT_FAILURE); 
    }

    lz_tree->current_word_capacity = INITIAL_WORD_BUFFER_CAPACITY;
    lz_tree->current_word_buffer = (char*)malloc(lz_tree->current_word_capacity * sizeof(char));
    if (!lz_tree->current_word_buffer) {
        perror("Failed to allocate current_word_buffer");
        free_suffix_tree_c(lz_tree->base_tree);
        free(lz_tree);
        exit(EXIT_FAILURE);
    }
    lz_tree->current_word_len = 0;

    internal_reset_lz_state(lz_tree, false); // false = don't reset base_tree here, it's new
    
    return lz_tree;
}

void free_lz_suffix_tree_c(LZSuffixTreeCState* lz_tree) {
    if (!lz_tree) return;
    if (lz_tree->base_tree) {
        free_suffix_tree_c(lz_tree->base_tree);
    }
    if (lz_tree->current_word_buffer) {
        free(lz_tree->current_word_buffer);
    }
    free(lz_tree);
}

static void internal_reset_lz_state(LZSuffixTreeCState* lz_tree, bool reset_base_tree_also) {
    if (reset_base_tree_also && lz_tree->base_tree) {
        // Re-initialize base_tree (Python equivalent: super().__init__(""))
        free_suffix_tree_c(lz_tree->base_tree);
        lz_tree->base_tree = create_suffix_tree_c();
        if (!lz_tree->base_tree) {
            // This is a critical failure during reset, might need robust error handling
            // For now, mimic previous exit pattern
            perror("Failed to re-create base_tree during reset_lz_suffix_tree_c");
            exit(EXIT_FAILURE);
        }
    }
    // If current_word_buffer exists, just reset its length. Capacity remains.
    if(lz_tree->current_word_buffer) {
        lz_tree->current_word_len = 0;
    }
    
    lz_tree->has_last_char_processed_by_lz = false;
    lz_tree->last_char_processed_by_lz = 0; // Default value, not strictly necessary due to flag
    lz_tree->dictionary_size = 0;

    // Reset LZ-specific active point to root of base_tree
    if (lz_tree->base_tree) { // base_tree might not exist if create_lz_suffix_tree_c failed earlier
        lz_tree->lz_active_node = lz_tree->base_tree->root;
    } else {
        lz_tree->lz_active_node = NULL; // Should ideally not happen in normal flow
    }
    lz_tree->lz_active_edge_first_char = 0; // Indicates at a node, no specific edge char
    lz_tree->lz_active_length = 0;
    lz_tree->lz_active_edge_text_start_idx = -1; // Invalid index
}

void reset_lz_suffix_tree_c(LZSuffixTreeCState* lz_tree) {
    if (!lz_tree) return;
    internal_reset_lz_state(lz_tree, true); // true = reset base_tree also
}


// Tries to match char_to_find from the current lz_active_point in lz_tree->base_tree.
// Updates lz_active_point if match is found.
static bool is_match_in_base_tree_c(LZSuffixTreeCState* lz_tree, char char_to_find) {
    if (!lz_tree || !lz_tree->base_tree || !lz_tree->lz_active_node) {
        // Invalid state, should not happen.
        return false; 
    }

    SuffixTreeCState* base_tree = lz_tree->base_tree;

    if (lz_tree->lz_active_length == 0) { // At a node (lz_active_node)
        EdgeC* edge = api_find_child_edge_by_char(lz_tree->lz_active_node, char_to_find);
        if (edge) {
            // Found an edge starting with char_to_find
            // The char on edge is base_tree->text[edge->start]
            // Which must be char_to_find if api_find_child_edge_by_char worked as expected.
            lz_tree->lz_active_edge_first_char = base_tree->text[edge->start];
            lz_tree->lz_active_edge_text_start_idx = edge->start;
            lz_tree->lz_active_length = 1;
            return true;
        } else {
            return false; // No edge starts with char_to_find
        }
    } else { // In the middle of an edge (lz_active_node, lz_active_edge_first_char, lz_active_length)
        EdgeC* current_edge = api_find_child_edge_by_char(lz_tree->lz_active_node, lz_tree->lz_active_edge_first_char);
        if (!current_edge) {
            // This indicates an inconsistent state, as we shouldn't be on an edge that doesn't exist.
            // Resetting active point might be a recovery, but for now, signal failure.
            // This could happen if base_tree was modified externally or due to a bug.
            // For robustness, one might reset lz_active_point here.
            return false; 
        }

        int edge_len = api_edge_length_c(current_edge, base_tree->text_len - 1);

        if (lz_tree->lz_active_length < edge_len) { // Still on this edge, haven't reached its end node
            if (base_tree->text[current_edge->start + lz_tree->lz_active_length] == char_to_find) {
                lz_tree->lz_active_length++;
                return true;
            } else {
                return false; // Mismatch on the edge
            }
        } else { // lz_tree->lz_active_length == edge_len. Reached end of current_edge.
                 // Transition to the destination node of current_edge.
            lz_tree->lz_active_node = current_edge->dest;
            lz_tree->lz_active_length = 0;
            lz_tree->lz_active_edge_first_char = 0; // Indicate we are at a node now
            lz_tree->lz_active_edge_text_start_idx = -1;
            // Now try to match char_to_find from this new node (recursively or iteratively)
            return is_match_in_base_tree_c(lz_tree, char_to_find); // Tail recursion
        }
    }
}

bool add_char_lz_c(LZSuffixTreeCState* lz_tree, char current_ch) {
    if (!lz_tree) return false; // Or handle error

    // 1. Append current_ch to current_word_buffer for the current phrase
    if (lz_tree->current_word_len + 1 > lz_tree->current_word_capacity) {
        lz_tree->current_word_capacity = (lz_tree->current_word_capacity == 0) ? INITIAL_WORD_BUFFER_CAPACITY : lz_tree->current_word_capacity * 2;
        char* new_buffer = (char*)realloc(lz_tree->current_word_buffer, lz_tree->current_word_capacity * sizeof(char));
        if (!new_buffer) {
            perror("Failed to reallocate current_word_buffer in add_char_lz_c");
            // LZ Tree is in an inconsistent state. How to recover or signal fatal error?
            // For now, let's assume exit for simplicity, though not ideal for a library.
            exit(EXIT_FAILURE);
        }
        lz_tree->current_word_buffer = new_buffer;
    }
    lz_tree->current_word_buffer[lz_tree->current_word_len] = current_ch;
    lz_tree->current_word_len++;

    bool added_new_word_to_dict = false;
    
    // 2. Determine char_to_add_to_base_tree (which is the previous current_ch)
    //    and update last_char_processed_by_lz for the *next* call.
    char char_to_add_to_base_tree = 0;
    bool can_add_to_base_tree = lz_tree->has_last_char_processed_by_lz;
    if (can_add_to_base_tree) {
        char_to_add_to_base_tree = lz_tree->last_char_processed_by_lz;
    }
    lz_tree->last_char_processed_by_lz = current_ch;
    lz_tree->has_last_char_processed_by_lz = true;

    // 3. If a previous char exists, add it to the base_tree (which stores text[:-1])
    if (can_add_to_base_tree) {
        add_char_c(lz_tree->base_tree, char_to_add_to_base_tree);
    }

    // 4. Try to match current_ch from current lz_active_point in base_tree
    //    This is to see if current_word_buffer (which now includes current_ch) can be extended.
    //    The Python `is_current_word_in_tree` checks `self.last_char`, which is `current_ch`.
    if (is_match_in_base_tree_c(lz_tree, current_ch)) {
        // Match found: current_word_buffer (current phrase) continues.
        // is_match_in_base_tree_c updated lz_active_point.
        added_new_word_to_dict = false;
    } else {
        // No match: current_word_buffer (phrase ending *before* current_ch if we interpret strictly,
        // or current_word_buffer *including* current_ch if we follow python's dictionary.append(current_word) literally)
        // Python: self.dictionary.append(self.current_word) where current_word includes the failing char.
        // So, the phrase including current_ch is added.
        lz_tree->dictionary_size++;
        added_new_word_to_dict = true;

        // Reset LZ active point to root of base_tree, as a new phrase starts
        lz_tree->lz_active_node = lz_tree->base_tree->root;
        lz_tree->lz_active_edge_first_char = 0; 
        lz_tree->lz_active_length = 0;
        lz_tree->lz_active_edge_text_start_idx = -1;

        // Clear current_word_buffer; it will start fresh with the next char added to it.
        lz_tree->current_word_len = 0;
    }
    return added_new_word_to_dict;
}

int get_lz_complexity_c(LZSuffixTreeCState* lz_tree) {
    if (!lz_tree) return 0;
    int complexity = lz_tree->dictionary_size;
    if (lz_tree->current_word_len > 0) {
        complexity++;
    }
    return complexity;
}

void process_lz_batch_c(LZSuffixTreeCState* lz_tree_state, const char** strings_array, int num_strings, int* results_array) {
    if (!lz_tree_state || !strings_array || !results_array) {
        // Handle null pointers, perhaps by returning or logging an error.
        // For now, just return if essential components are missing.
        // Consider setting an error code if this were a library with more formal error handling.
        return;
    }

    for (int i = 0; i < num_strings; ++i) {
        // 1. Reset the LZ suffix tree state for the new string.
        //    internal_reset_lz_state is better as it allows not re-creating base_tree buffers if not needed.
        //    For batch, we absolutely want to reset the base_tree part too for each independent string.
        reset_lz_suffix_tree_c(lz_tree_state); // This will also reset the base SuffixTreeCState fully.

        const char* current_string = strings_array[i];
        if (!current_string) { // Handle null string in the array if necessary
            results_array[i] = 0; // Or some error indicator
            continue;
        }

        // 2. Process each character of the current string.
        for (int j = 0; current_string[j] != '\0'; ++j) {
            add_char_lz_c(lz_tree_state, current_string[j]);
        }

        // 3. Get the LZ complexity for the processed string.
        results_array[i] = get_lz_complexity_c(lz_tree_state);
    }
} 