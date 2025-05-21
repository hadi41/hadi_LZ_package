#include "lz_suffix.h"
#include "online_suffix.h" // For API helpers like api_find_child_edge_by_char, create_suffix_tree_c, etc.

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define INITIAL_WORD_BUFFER_CAPACITY 16 /**< Initial capacity for the current_word_buffer. */

// Forward declarations for internal static helper functions
static bool is_match_in_base_tree_c(LZSuffixTreeCState* lz_tree, char char_to_find);
static void internal_reset_lz_state(LZSuffixTreeCState* lz_tree, bool reset_base_tree_also);

/**
 * @brief Creates and initializes a new LZSuffixTreeCState object.
 *
 * Allocates memory for the LZSuffixTreeCState itself and its internal components:
 *  - The `base_tree` (an online suffix tree from `online_suffix.c`).
 *  - The `current_word_buffer` for storing the current LZ phrase.
 * Initializes all state variables to their default (empty/reset) values.
 * If any allocation fails, it attempts to clean up previously allocated memory and prints an error,
 * then exits the program. This exit behavior might be changed for a library setting.
 *
 * @return Pointer to the newly created and initialized LZSuffixTreeCState.
 * @note Exits on allocation failure.
 */
LZSuffixTreeCState* create_lz_suffix_tree_c(void) {
    LZSuffixTreeCState* lz_tree = (LZSuffixTreeCState*)malloc(sizeof(LZSuffixTreeCState));
    if (!lz_tree) {
        perror("Failed to allocate LZSuffixTreeCState");
        exit(EXIT_FAILURE); // Critical error
    }

    lz_tree->base_tree = create_suffix_tree_c(); // From online_suffix.c
    if (!lz_tree->base_tree) {
        free(lz_tree); // Base tree creation failed (it would have printed error & exited)
        // Defensive exit, create_suffix_tree_c might have already exited.
        exit(EXIT_FAILURE); 
    }

    lz_tree->current_word_capacity = INITIAL_WORD_BUFFER_CAPACITY;
    lz_tree->current_word_buffer = (char*)malloc(lz_tree->current_word_capacity * sizeof(char));
    if (!lz_tree->current_word_buffer) {
        perror("Failed to allocate current_word_buffer");
        free_suffix_tree_c(lz_tree->base_tree);
        free(lz_tree);
        exit(EXIT_FAILURE); // Critical error
    }
    // Initialize current_word_len, dictionary_size, and LZ active point via internal_reset_lz_state.
    // Buffers are allocated, so current_word_len is set to 0 by internal_reset_lz_state.
    internal_reset_lz_state(lz_tree, false); // false = don't reset base_tree here, it's newly created.
    
    return lz_tree;
}

/**
 * @brief Frees an LZSuffixTreeCState and all its associated dynamically allocated memory.
 *
 * This includes:
 *  - The `base_tree` (by calling `free_suffix_tree_c`).
 *  - The `current_word_buffer`.
 *  - The `LZSuffixTreeCState` structure itself.
 * Handles NULL pointers gracefully for each component.
 *
 * @param lz_tree Pointer to the LZSuffixTreeCState to be freed. If NULL, the function does nothing.
 */
void free_lz_suffix_tree_c(LZSuffixTreeCState* lz_tree) {
    if (!lz_tree) return;
    if (lz_tree->base_tree) {
        free_suffix_tree_c(lz_tree->base_tree);
        lz_tree->base_tree = NULL; // Good practice after free
    }
    if (lz_tree->current_word_buffer) {
        free(lz_tree->current_word_buffer);
        lz_tree->current_word_buffer = NULL; // Good practice
    }
    free(lz_tree);
}

/**
 * @brief Internal helper to reset the LZ-specific parts of an LZSuffixTreeCState.
 *
 * Resets `current_word_len`, `dictionary_size`, `last_char_processed_by_lz`, 
 * `has_last_char_processed_by_lz`, and the LZ-specific active point (`lz_active_node`, etc.)
 * to their initial states for processing a new string.
 * If `reset_base_tree_also` is true, it also fully frees and re-creates the `base_tree`.
 *
 * @param lz_tree Pointer to the LZSuffixTreeCState to reset.
 * @param reset_base_tree_also If true, the `base_tree` is also reset (freed and re-created).
 *                             If false, the `base_tree` is assumed to be in a valid state (e.g., newly created).
 * @note Exits on failure if `reset_base_tree_also` is true and re-creation of `base_tree` fails.
 */
static void internal_reset_lz_state(LZSuffixTreeCState* lz_tree, bool reset_base_tree_also) {
    if (!lz_tree) return;

    if (reset_base_tree_also) {
        if (lz_tree->base_tree) { // If it exists, free and recreate
            free_suffix_tree_c(lz_tree->base_tree);
            lz_tree->base_tree = NULL; // Nullify before attempting re-creation
        }
        lz_tree->base_tree = create_suffix_tree_c();
        if (!lz_tree->base_tree) {
            // This is a critical failure during a reset operation.
            perror("Failed to re-create base_tree during internal_reset_lz_state");
            // Depending on context, might throw exception or return error code in a library.
            exit(EXIT_FAILURE); // Exiting for consistency with create functions.
        }
    }

    // Reset current_word_buffer's content by setting its length to 0.
    // The buffer itself and its capacity are preserved for reuse.
    if (lz_tree->current_word_buffer) { // Should always exist if lz_tree is valid
        lz_tree->current_word_len = 0;
        // current_word_buffer[0] = '\0'; // Not strictly necessary if len is 0
    }
    
    lz_tree->has_last_char_processed_by_lz = false;
    lz_tree->last_char_processed_by_lz = 0; // Default, actual value ignored if flag is false
    lz_tree->dictionary_size = 0;

    // Reset LZ-specific active point to the root of the base_tree.
    if (lz_tree->base_tree) { // Should be valid unless create_suffix_tree_c failed
        lz_tree->lz_active_node = lz_tree->base_tree->root;
    } else {
        // This case implies base_tree is NULL, which is problematic for subsequent operations.
        // It should ideally have been caught by the base_tree creation check above.
        lz_tree->lz_active_node = NULL; 
    }
    lz_tree->lz_active_edge_first_char = 0; // Represents being at a node, not on a specific edge character.
    lz_tree->lz_active_length = 0;          // No match length along an edge yet.
    lz_tree->lz_active_edge_text_start_idx = -1; // Invalid text index, as not on an edge.
}

/**
 * @brief Resets an LZSuffixTreeCState to its initial empty state, ready for a new string.
 *
 * This is a public API function that calls `internal_reset_lz_state` ensuring that the
 * `base_tree` is also fully reset.
 *
 * @param lz_tree Pointer to the LZSuffixTreeCState to reset. If NULL, the function does nothing.
 */
void reset_lz_suffix_tree_c(LZSuffixTreeCState* lz_tree) {
    if (!lz_tree) return;
    internal_reset_lz_state(lz_tree, true); // true = reset base_tree also for a full public reset.
}


/**
 * @brief Internal helper: Tries to match `char_to_find` from the current LZ active point in `lz_tree->base_tree`.
 *
 * This function simulates traversing the `base_tree` (which represents the LZ dictionary) 
 * to see if the current LZ phrase can be extended by `char_to_find`.
 * It updates the LZ active point (`lz_active_node`, `lz_active_edge_first_char`, `lz_active_length`, `lz_active_edge_text_start_idx`)
 * if a match is found.
 *
 * @param lz_tree Pointer to the `LZSuffixTreeCState` containing the LZ active point and the `base_tree`.
 * @param char_to_find The character to attempt to match from the current LZ active point.
 * @return `true` if `char_to_find` extends the match in `base_tree`, `false` otherwise.
 */
static bool is_match_in_base_tree_c(LZSuffixTreeCState* lz_tree, char char_to_find) {
    if (!lz_tree || !lz_tree->base_tree || !lz_tree->lz_active_node) {
        fprintf(stderr, "Error: is_match_in_base_tree_c called with invalid LZ/BaseTree/ActiveNode state.\n");
        return false; 
    }

    SuffixTreeCState* base_tree = lz_tree->base_tree;

    if (lz_tree->lz_active_length == 0) { // Currently at a node (lz_active_node).
        // Try to find an outgoing edge from lz_active_node that starts with char_to_find.
        EdgeC* edge = api_find_child_edge_by_char(lz_tree->lz_active_node, char_to_find, base_tree->text);
        if (edge) {
            // Found such an edge. Start matching along this edge.
            lz_tree->lz_active_edge_first_char = base_tree->text[edge->start]; // This must be char_to_find.
            lz_tree->lz_active_edge_text_start_idx = edge->start;
            lz_tree->lz_active_length = 1; // Matched one character along this edge.
            // If edge length is 1, we might immediately transition to its dest node in next call if it matches again
            // No, if edge length is 1, we are now at lz_active_length=1. If next char matches, we either extend or move to node.
            return true;
        } else {
            return false; // No edge from lz_active_node starts with char_to_find.
        }
    } else { // Currently in the middle of an edge (implicit node).
             // lz_active_node is the source node of this edge.
             // lz_active_edge_first_char is the first char of this edge.
             // lz_active_length is the number of chars matched along this edge so far.
        EdgeC* current_edge = api_find_child_edge_by_char(lz_tree->lz_active_node, lz_tree->lz_active_edge_first_char, base_tree->text);
        if (!current_edge) {
            fprintf(stderr, "Error: Inconsistent LZ active point: on an edge that doesn't exist from lz_active_node.\n");
            // This implies a bug or corrupted state. Resetting LZ active point might be a partial recovery.
            lz_tree->lz_active_node = base_tree->root; // Attempt to recover by resetting to root
            lz_tree->lz_active_length = 0;
            lz_tree->lz_active_edge_first_char = 0;
            lz_tree->lz_active_edge_text_start_idx = -1;
            return false; 
        }

        int edge_len = api_edge_length_c(current_edge, base_tree->text_len -1 ); // Use current text_len for edge length

        if (lz_tree->lz_active_length < edge_len) { // Still on the current_edge, not yet at its destination node.
            // Check if the next character on the edge matches char_to_find.
            if (base_tree->text[current_edge->start + lz_tree->lz_active_length] == char_to_find) {
                lz_tree->lz_active_length++; // Extend match along this edge.
                return true;
            } else {
                return false; // Mismatch on the edge.
            }
        } else { // lz_tree->lz_active_length == edge_len. We have reached the end of current_edge.
                 // Transition to the destination node of current_edge.
            lz_tree->lz_active_node = current_edge->dest;
            lz_tree->lz_active_length = 0; // Reset, as we are now at a node.
            lz_tree->lz_active_edge_first_char = 0;
            lz_tree->lz_active_edge_text_start_idx = -1;
            // Now, from this new lz_active_node, try to match char_to_find again.
            return is_match_in_base_tree_c(lz_tree, char_to_find); // Tail recursive call.
        }
    }
}

/**
 * @brief Processes a single character `current_ch` for LZ76 complexity calculation.
 *
 * The core logic involves several steps:
 * 1. Append `current_ch` to the `current_word_buffer`.
 * 2. If a character was processed in the *previous* call (`last_char_processed_by_lz`),
 *    add that *previous* character to the `base_tree` (which represents the dictionary of past phrases).
 * 3. Attempt to match `current_ch` from the current LZ active point within the `base_tree`
 *    using `is_match_in_base_tree_c`. This checks if the `current_word_buffer` (now including `current_ch`)
 *    exists as a prefix in the dictionary.
 * 4. If a match IS found: The `current_word_buffer` continues to be a prefix of some dictionary entry.
 *    The LZ active point is updated by `is_match_in_base_tree_c`.
 * 5. If a match IS NOT found: The `current_word_buffer` (including `current_ch`) forms a new, complete LZ phrase.
 *    - Increment `dictionary_size`.
 *    - Reset `current_word_buffer` (it will start fresh with the next character).
 *    - Reset the LZ active point to the root of `base_tree`.
 *
 * @param lz_tree Pointer to the LZSuffixTreeCState to be updated.
 * @param current_ch The character to process.
 * @return `true` if this call resulted in completing a new LZ phrase (i.e., `dictionary_size` was incremented).
 *         `false` if `current_ch` merely extended the current matching phrase or on critical error.
 * @note Exits on `realloc` failure for `current_word_buffer`.
 */
bool add_char_lz_c(LZSuffixTreeCState* lz_tree, char current_ch) {
    if (!lz_tree || !lz_tree->base_tree) { // Basic sanity checks
        fprintf(stderr, "Error: add_char_lz_c called with NULL lz_tree or base_tree.\n");
        return false; 
    }

    // 1. Append current_ch to current_word_buffer.
    if (lz_tree->current_word_len + 1 > lz_tree->current_word_capacity) { // +1 for new char, not for null term here
        int new_capacity = (lz_tree->current_word_capacity == 0) ? INITIAL_WORD_BUFFER_CAPACITY : lz_tree->current_word_capacity * 2;
        char* new_buffer = (char*)realloc(lz_tree->current_word_buffer, new_capacity * sizeof(char));
        if (!new_buffer) {
            perror("Failed to reallocate current_word_buffer in add_char_lz_c");
            // This is a critical error. The LZ tree state is now potentially corrupt.
            // A robust library might return an error code or have a mechanism to signal this.
            exit(EXIT_FAILURE); // For now, exit to prevent further issues.
        }
        lz_tree->current_word_buffer = new_buffer;
        lz_tree->current_word_capacity = new_capacity;
    }
    lz_tree->current_word_buffer[lz_tree->current_word_len] = current_ch;
    lz_tree->current_word_len++;
    // current_word_buffer is not kept null-terminated during this phase, only by its length.

    bool added_new_phrase_to_dictionary = false;
    
    // 2. Determine char_to_add_to_base_tree. This is the character that was current_ch in the *previous* call.
    //    The base_tree (dictionary) always represents text_so_far[:-1].
    char char_to_add_to_base_tree = 0; // Value if not can_add_to_base_tree
    bool can_add_to_base_tree = lz_tree->has_last_char_processed_by_lz;
    if (can_add_to_base_tree) {
        char_to_add_to_base_tree = lz_tree->last_char_processed_by_lz;
    }
    // Update for the *next* call: current_ch becomes the new last_char_processed.
    lz_tree->last_char_processed_by_lz = current_ch;
    lz_tree->has_last_char_processed_by_lz = true;

    // 3. If a previous character exists (i.e., this isn't the very first char of the string),
    //    add that *previous* character to the base_tree to update the dictionary.
    if (can_add_to_base_tree) {
        add_char_c(lz_tree->base_tree, char_to_add_to_base_tree); // From online_suffix.c
    }

    // 4. Try to match current_ch from the current LZ active point in base_tree.
    //    This determines if the current_word_buffer (which now includes current_ch)
    //    is still a prefix of something already seen in the dictionary (base_tree).
    if (is_match_in_base_tree_c(lz_tree, current_ch)) {
        // Match found: current_word_buffer (as extended by current_ch) is still part of an existing phrase or prefix.
        // The LZ active point was updated by is_match_in_base_tree_c.
        added_new_phrase_to_dictionary = false;
    } else {
        // No match: The current_word_buffer (including current_ch) forms a new, distinct LZ phrase.
        // (This interpretation follows the Python version where `self.dictionary.append(self.current_word)`
        //  is done after `current_word` fails to extend, meaning the failing char is part of the new phrase).
        lz_tree->dictionary_size++;
        added_new_phrase_to_dictionary = true;

        // Reset the LZ active point to the root of base_tree because a new phrase has started.
        lz_tree->lz_active_node = lz_tree->base_tree->root;
        lz_tree->lz_active_edge_first_char = 0; 
        lz_tree->lz_active_length = 0;
        lz_tree->lz_active_edge_text_start_idx = -1;

        // The current_word_buffer is now considered complete. For the *next* cycle of LZ, 
        // it needs to be reset. However, the characters of this just-completed phrase
        // are NOT YET in base_tree. They will be added one-by-one in subsequent calls to add_char_lz_c
        // via the `char_to_add_to_base_tree` logic.
        // The current_word_buffer itself is effectively reset for LZ purposes by setting its length to 0 here.
        // The content of current_word_buffer (the phrase just added) will be overwritten as new chars come in.
        lz_tree->current_word_len = 0;
        // It is important that the *next* call to is_match_in_base_tree_c starts fresh for the new word.
        // This is ensured by resetting lz_active_node above and then the next char will be the first char of the new word.
    }
    return added_new_phrase_to_dictionary;
}

/**
 * @brief Retrieves the current LZ76 complexity (phrase count).
 *
 * The complexity is `dictionary_size` plus one if there is an unfinished phrase
 * in `current_word_buffer`.
 *
 * @param lz_tree Pointer to the LZSuffixTreeCState. Must not be NULL.
 * @return The LZ76 complexity. Returns 0 if lz_tree is NULL (though ideally, this should be an error).
 */
int get_lz_complexity_c(LZSuffixTreeCState* lz_tree) {
    if (!lz_tree) {
        fprintf(stderr, "Error: get_lz_complexity_c called with NULL lz_tree.\n");
        return 0; // Or a defined error code
    }
    int complexity = lz_tree->dictionary_size;
    // If there are characters in current_word_buffer, they form the final, incomplete phrase.
    if (lz_tree->current_word_len > 0) {
        complexity++;
    }
    return complexity;
}

/**
 * @brief Processes a batch of strings to calculate their LZ76 complexities.
 *
 * Uses a single `LZSuffixTreeCState` which is reset for each string in the batch.
 * This is efficient as it reuses memory allocations for the state and suffix tree structures.
 *
 * @param lz_tree_state Pointer to an existing `LZSuffixTreeCState` to be reused. 
 *                      It will be reset before processing each string. Must not be NULL.
 * @param strings_array An array of null-terminated C strings. Must not be NULL.
 * @param num_strings The number of strings in `strings_array`.
 * @param results_array A pre-allocated array where the LZ76 complexities (int) will be stored.
 *                      Must be large enough to hold `num_strings` integers. Must not be NULL.
 * @note If any of the pointer arguments are NULL, the function returns without processing.
 *       Individual NULL strings within `strings_array` are processed as having complexity 0.
 */
void process_lz_batch_c(LZSuffixTreeCState* lz_tree_state, const char** strings_array, int num_strings, int* results_array) {
    if (!lz_tree_state || !strings_array || !results_array) {
        fprintf(stderr, "Error: process_lz_batch_c called with NULL arguments.\n");
        // Optionally, set an error state or return an error code if designing a robust library.
        return;
    }

    for (int i = 0; i < num_strings; ++i) {
        reset_lz_suffix_tree_c(lz_tree_state); // Full reset for each new string, including base_tree.

        const char* current_string = strings_array[i];
        if (!current_string) { 
            results_array[i] = 0; // Define complexity of NULL string as 0.
            // Reset last_char_processed states in case the previous string ended, then a NULL string, then another valid string.
            // reset_lz_suffix_tree_c already handles this robustly.
            continue;
        }

        for (int j = 0; current_string[j] != '\0'; ++j) {
            add_char_lz_c(lz_tree_state, current_string[j]);
        }
        results_array[i] = get_lz_complexity_c(lz_tree_state);
    }
} 