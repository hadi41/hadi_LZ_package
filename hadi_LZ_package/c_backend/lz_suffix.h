#ifndef LZ_SUFFIX_H
#define LZ_SUFFIX_H

#include "online_suffix.h" // For SuffixTreeCState, NodeC, etc.
#include <stdbool.h>

// Forward declaration
typedef struct LZSuffixTreeCState LZSuffixTreeCState;

struct LZSuffixTreeCState {
    SuffixTreeCState* base_tree;      // Suffix tree for text[:-1]

    char* current_word_buffer;        // Buffer for the current LZ phrase being built
    int current_word_capacity;
    int current_word_len;

    // current_text (full text including last char) is implicitly managed by adding to current_word_buffer
    // and occasionally flushing parts to base_tree->text. We might not need a separate current_text buffer in C
    // if we can reconstruct it or if its only role was for display/debug in Python.
    // The base_tree->text stores text[:-1]. The current_word_buffer stores the current phrase.

    char last_char_processed_by_lz; // Last character fed to add_char_lz_c, used for matching
    bool has_last_char_processed_by_lz; // Flag to indicate if last_char_processed_by_lz is valid
    int dictionary_size;            // Number of phrases in LZ76 dictionary

    // LZ-specific active point for matching current_word in base_tree
    NodeC* lz_active_node;          // Current node in base_tree for matching
    // If lz_active_length > 0, this is the char in base_tree->text that starts the active edge
    char lz_active_edge_first_char; 
    int lz_active_length;           // Length of match along the current edge from lz_active_node
    int lz_active_edge_text_start_idx; // Start index in base_tree->text of the current active edge
};

// API Functions
LZSuffixTreeCState* create_lz_suffix_tree_c(void);
void free_lz_suffix_tree_c(LZSuffixTreeCState* lz_tree);

/**
 * Adds a character to the LZ suffix tree processor.
 * Updates the internal LZ76 state (current word, dictionary size).
 * Adds the *previous* character to the underlying suffix tree (base_tree).
 * Returns true if adding this character completed a new phrase for the LZ dictionary.
 */
bool add_char_lz_c(LZSuffixTreeCState* lz_tree, char ch);

int get_lz_complexity_c(LZSuffixTreeCState* lz_tree);
void reset_lz_suffix_tree_c(LZSuffixTreeCState* lz_tree);

// Batch processing function
/**
 * Processes a batch of strings to calculate their LZ76 complexities.
 * Uses a single LZSuffixTreeCState which is reset for each string.
 * 
 * @param lz_tree_state A pointer to an existing LZSuffixTreeCState to be reused.
 *                      The caller is responsible for creating and freeing this state.
 * @param strings_array An array of null-terminated C strings.
 * @param num_strings The number of strings in strings_array.
 * @param results_array An array where the LZ76 complexities (int) will be stored.
 *                      This array must be pre-allocated by the caller to hold num_strings integers.
 */
void process_lz_batch_c(LZSuffixTreeCState* lz_tree_state, const char** strings_array, int num_strings, int* results_array);

//Potentially a helper to get the current dictionary items if needed for Python wrapper status
//char** get_lz_dictionary_c(LZSuffixTreeCState* lz_tree, int* count);
//void free_lz_dictionary_c(char** dict_array, int count);


#endif // LZ_SUFFIX_H 