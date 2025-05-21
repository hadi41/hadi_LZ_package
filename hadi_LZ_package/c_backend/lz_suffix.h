#ifndef LZ_SUFFIX_H
#define LZ_SUFFIX_H

#include "online_suffix.h" // For SuffixTreeCState, NodeC, etc.
#include <stdbool.h>
#include <stddef.h> // For size_t

// Forward declaration of the main struct to handle circular dependency or for clarity
typedef struct LZSuffixTreeCState LZSuffixTreeCState;

/**
 * @struct LZSuffixTreeCState
 * @brief Manages the state for LZ76 complexity calculation using an online suffix tree.
 *
 * This structure integrates an online suffix tree (`base_tree`) to efficiently find
 * previous occurrences of substrings, which is key to the LZ76 algorithm.
 * The `base_tree` stores the text processed so far, *excluding* the current character being added
 * to the LZ phrase (`current_word_buffer`).
 */
struct LZSuffixTreeCState {
    SuffixTreeCState* base_tree;      /**< Pointer to the online suffix tree state. This tree represents S_1S_2...S_{i-1} (the dictionary so far). */

    char* current_word_buffer;        /**< Buffer for the current LZ phrase (S_i) being built. */
    int current_word_capacity;      /**< Allocated capacity of `current_word_buffer`. */
    int current_word_len;           /**< Current length of the phrase in `current_word_buffer`. */

    // The overall text processed is conceptually (text in base_tree) + (text in current_word_buffer).
    // base_tree->text usually holds text_so_far[:-1]
    // current_word_buffer holds the current phrase being matched against base_tree.

    char last_char_processed_by_lz; /**< The most recent character appended by `add_char_lz_c`. 
                                     *   This is the character that extended `current_word_buffer`.*/
    bool has_last_char_processed_by_lz; /**< Flag: true if `last_char_processed_by_lz` contains a valid character. */
    int dictionary_size;            /**< The LZ76 complexity: number of phrases (S_1, S_2, ...) found so far. */

    // LZ-specific active point for matching current_word_buffer in base_tree.
    // This is distinct from base_tree->active_node etc., which are for suffix tree construction.
    // This active point tracks how much of current_word_buffer has been found in base_tree (the dictionary).
    NodeC* lz_active_node;          /**< Current node in `base_tree` reached while matching `current_word_buffer`. */
    char lz_active_edge_first_char; /**< If `lz_active_length` > 0, this is the first character of the edge in `base_tree` 
                                     *   along which the current match is being made. Valid if lz_active_length > 0. */ 
    int lz_active_length;           /**< Length of the current match along an edge descending from `lz_active_node`. */
    int lz_active_edge_text_start_idx; /**< Start index in `base_tree->text` of the edge identified by `lz_active_edge_first_char`. 
                                          *  Valid if `lz_active_length` > 0 and `lz_active_node` is not root or is not an implicit suffix link jump. */
};

// API Functions

/**
 * @brief Creates and initializes a new LZSuffixTreeCState.
 * Allocates memory for the state and its internal structures, including the base suffix tree.
 * @return Pointer to the newly created LZSuffixTreeCState, or NULL on failure.
 */
LZSuffixTreeCState* create_lz_suffix_tree_c(void);

/**
 * @brief Frees an LZSuffixTreeCState and all its associated resources.
 * This includes freeing the internal `base_tree`.
 * @param lz_tree Pointer to the LZSuffixTreeCState to be freed. If NULL, the function does nothing.
 */
void free_lz_suffix_tree_c(LZSuffixTreeCState* lz_tree);

/**
 * @brief Processes a single character for LZ76 complexity calculation.
 *
 * Appends `ch` to the `current_word_buffer`. 
 * Then, it attempts to match the updated `current_word_buffer` against the dictionary 
 * (represented by `base_tree`).
 * If `current_word_buffer` is NOT found in `base_tree`:
 *  1. The `current_word_buffer` (before adding `ch`) is considered a complete phrase.
 *  2. Characters from this completed phrase are added to `base_tree` to update the dictionary.
 *  3. `dictionary_size` is incremented.
 *  4. `current_word_buffer` is reset to contain only `ch`.
 *  5. The LZ active point is reset.
 * If `current_word_buffer` IS found in `base_tree`, it means the current phrase is not yet complete.
 * The function updates the LZ active point to reflect the match.
 *
 * @param lz_tree Pointer to the LZSuffixTreeCState.
 * @param ch The character to add.
 * @return `true` if adding this character `ch` resulted in the completion of a new LZ phrase 
 *         (i.e., the previous `current_word_buffer` + `ch` was not in the dictionary, so the old `current_word_buffer` became a phrase).
 *         Returns `false` if `ch` simply extended the current matching word or on error.
 */
bool add_char_lz_c(LZSuffixTreeCState* lz_tree, char ch);

/**
 * @brief Retrieves the current LZ76 complexity (phrase count).
 *
 * This is the number of phrases in the dictionary built so far.
 * If `current_word_buffer` is not empty at the time of calling, it means the last phrase
 * is still being formed and is not yet counted in `dictionary_size` from `add_char_lz_c`.
 * This function adds 1 to `dictionary_size` if `current_word_len > 0` to account for it.
 *
 * @param lz_tree Pointer to the LZSuffixTreeCState.
 * @return The current LZ76 complexity. Returns 0 if lz_tree is NULL.
 */
int get_lz_complexity_c(LZSuffixTreeCState* lz_tree);

/**
 * @brief Resets an LZSuffixTreeCState to its initial empty state.
 *
 * Clears the internal suffix tree (`base_tree`), resets `current_word_buffer`,
 * `dictionary_size`, and LZ active point variables.
 * The state can then be reused for processing a new string.
 *
 * @param lz_tree Pointer to the LZSuffixTreeCState to reset.
 */
void reset_lz_suffix_tree_c(LZSuffixTreeCState* lz_tree);


/**
 * @brief Processes a batch of strings to calculate their LZ76 complexities using a suffix tree approach.
 *
 * For each string in `strings_array`:
 *  1. Resets the provided `lz_tree_state`.
 *  2. Calls `add_char_lz_c` for each character in the string.
 *  3. Calls `get_lz_complexity_c` to get the final phrase count.
 *  4. Stores the result in `results_array`.
 *
 * This function is designed for efficiency when processing multiple strings by reusing the
 * `LZSuffixTreeCState` memory allocations (though states are reset).
 *
 * @param lz_tree_state A pointer to an existing `LZSuffixTreeCState`. This state will be modified (reset for each string).
 *                      The caller is responsible for its creation via `create_lz_suffix_tree_c` and 
 *                      eventual destruction via `free_lz_suffix_tree_c`.
 * @param strings_array An array of null-terminated C strings to process.
 * @param num_strings The number of strings in `strings_array`.
 * @param results_array A pre-allocated array of integers where the LZ76 complexity for each corresponding
 *                      input string will be stored. Must be large enough to hold `num_strings` integers.
 */
void process_lz_batch_c(LZSuffixTreeCState* lz_tree_state, const char** strings_array, int num_strings, int* results_array);


#endif // LZ_SUFFIX_H 