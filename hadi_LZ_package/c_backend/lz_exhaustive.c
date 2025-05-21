#include "lz_exhaustive.h"
#include <string.h>
#include <stdlib.h>
#include <stdio.h> // For perror, remove if not used directly beyond that
#include <stdbool.h>
#include <math.h> // For ceil, log2

#ifdef _OPENMP
#include <omp.h>
#endif

/**
 * @struct LZState
 * @brief Holds the state of LZ76 parsing for a single string.
 *
 * This structure is used to incrementally build and analyze strings, particularly
 * in the context of exhaustively generating all binary strings of a certain length.
 * It mirrors the core logic of the standard LZ76 algorithm but is adapted for
 * recursive construction and state duplication.
 */
typedef struct {
    char* parsed_text;      /**< Buffer storing the concatenated phrases already added to the dictionary. */
    size_t parsed_text_len; /**< Current length of `parsed_text`. */
    char* current_word;     /**< Buffer for the current word/phrase being built before it's added to the dictionary. */
    size_t current_word_len;/**< Current length of `current_word`. */
    size_t dictionary_size;  /**< Number of distinct phrases found so far (the LZ76 complexity count). */
    size_t max_len;          /**< The maximum expected length of any string being processed (e.g., L for strings of length L). Used for buffer allocation. */
} LZState;

/**
 * @brief Initializes an LZState structure.
 *
 * Allocates memory for `parsed_text` and `current_word` buffers based on `L_max_len`.
 * Initializes lengths to 0 and dictionary_size to 0.
 *
 * @param state Pointer to the LZState structure to initialize.
 * @param L_max_len The maximum length of strings this state will handle, used for buffer sizing.
 * @return `true` if initialization (including memory allocation) is successful, `false` otherwise.
 */
static bool lz_state_init(LZState* state, size_t L_max_len) {
    state->max_len = L_max_len;
    state->parsed_text = (char*)malloc(L_max_len + 1); 
    state->current_word = (char*)malloc(L_max_len + 1);

    if (!state->parsed_text || !state->current_word) {
        // perror("LZState init failed to allocate buffers"); // perror might be too verbose for a library
        fprintf(stderr, "Error: LZState init failed to allocate buffers for L_max_len = %zu\n", L_max_len);
        free(state->parsed_text); 
        free(state->current_word);
        return false;
    }

    state->parsed_text[0] = '\0';
    state->parsed_text_len = 0;
    state->current_word[0] = '\0';
    state->current_word_len = 0;
    state->dictionary_size = 0;
    return true;
}

/**
 * @brief Frees the dynamically allocated buffers within an LZState.
 * @param state Pointer to the LZState structure whose buffers are to be freed.
 */
static void lz_state_free_buffers(LZState* state) {
    free(state->parsed_text);
    state->parsed_text = NULL;
    free(state->current_word);
    state->current_word = NULL;
}

/**
 * @brief Creates a deep copy of an LZState structure.
 *
 * Allocates new buffers for `dest` and copies the content from `src`.
 * `dest` should be uninitialized or its existing buffers will be lost (and not freed here).
 *
 * @param dest Pointer to the LZState structure to be the destination of the copy.
 * @param src Pointer to the constant LZState structure to be the source of the copy.
 * @return `true` if copying is successful (including memory allocations), `false` otherwise.
 */
static bool lz_state_copy(LZState* dest, const LZState* src) {
    dest->max_len = src->max_len;
    // It's safer to initialize to NULL in case of early exit
    dest->parsed_text = NULL; 
    dest->current_word = NULL;

    dest->parsed_text = (char*)malloc(dest->max_len + 1);
    if (!dest->parsed_text) {
        fprintf(stderr, "Error: LZState copy failed to allocate parsed_text buffer (max_len=%zu)\n", dest->max_len);
        return false;
    }
    dest->current_word = (char*)malloc(dest->max_len + 1);
    if (!dest->current_word) {
        fprintf(stderr, "Error: LZState copy failed to allocate current_word buffer (max_len=%zu)\n", dest->max_len);
        free(dest->parsed_text); // Free the successfully allocated buffer
        dest->parsed_text = NULL;
        return false;
    }

    memcpy(dest->parsed_text, src->parsed_text, src->parsed_text_len + 1); // +1 for null terminator
    dest->parsed_text_len = src->parsed_text_len;
    memcpy(dest->current_word, src->current_word, src->current_word_len + 1); // +1 for null terminator
    dest->current_word_len = src->current_word_len;
    dest->dictionary_size = src->dictionary_size;
    return true;
}

/**
 * @brief Advances an LZState by processing one additional character.
 *
 * This function appends `char_to_process` to the `current_word` of `s_to_update`.
 * It then checks if this new `current_word` is present in the history 
 * (defined as `parsed_text` + `current_word` (before appending the new character)).
 * If not found, the `current_word` is added to `parsed_text`, `dictionary_size` is incremented,
 * and `current_word` is reset.
 *
 * @param s_to_update Pointer to the LZState to be modified.
 * @param char_to_process The character (e.g., '0' or '1') to append and process.
 * @return `true` if the state was advanced successfully, `false` on error (e.g., buffer allocation failure).
 */
static bool advance_lz_state_in_place(LZState* s_to_update, char char_to_process) {
    if (s_to_update->current_word_len >= s_to_update->max_len) {
        fprintf(stderr, "Error: current_word buffer overflow in advance_lz_state. Max len %zu, current_word_len %zu\n", s_to_update->max_len, s_to_update->current_word_len);
        return false; 
    }
    s_to_update->current_word[s_to_update->current_word_len++] = char_to_process;
    s_to_update->current_word[s_to_update->current_word_len] = '\0';

    bool included = false;
    size_t cw_prefix_len = s_to_update->current_word_len - 1;
    
    // The search domain for the LZ76 rule is: parsed_text + current_word (excluding the char just added).
    // This temporary buffer holds this search domain.
    char* search_domain_text = (char*)malloc(s_to_update->parsed_text_len + cw_prefix_len + 1);
    if (!search_domain_text) {
        fprintf(stderr, "Error: Failed to alloc search_domain_text in advance_lz_state (len=%zu)\n", s_to_update->parsed_text_len + cw_prefix_len + 1);
        s_to_update->current_word_len--; // Backtrack current_word change
        s_to_update->current_word[s_to_update->current_word_len] = '\0';
        return false; 
    }
    memcpy(search_domain_text, s_to_update->parsed_text, s_to_update->parsed_text_len);
    memcpy(search_domain_text + s_to_update->parsed_text_len, s_to_update->current_word, cw_prefix_len);
    search_domain_text[s_to_update->parsed_text_len + cw_prefix_len] = '\0'; // Null-terminate search domain

    // Check if the full s_to_update->current_word (now including char_to_process) is in search_domain_text.
    // strstr is fine for this, or a manual loop like in lz_core.c for potentially better performance
    // if current_word_len is very small often (though strstr is highly optimized).
    if (s_to_update->parsed_text_len + cw_prefix_len >= s_to_update->current_word_len) { 
        if (strstr(search_domain_text, s_to_update->current_word) != NULL) {
            included = true;
        }
    }
    free(search_domain_text);

    if (!included) {
        if (s_to_update->parsed_text_len + s_to_update->current_word_len > s_to_update->max_len) {
             fprintf(stderr, "Error: parsed_text buffer overflow in advance_lz_state. Max len %zu, trying to write %zu\n", s_to_update->max_len, s_to_update->parsed_text_len + s_to_update->current_word_len);
            s_to_update->current_word_len--; // Backtrack current_word change
            s_to_update->current_word[s_to_update->current_word_len] = '\0';
            return false; 
        }
        memcpy(s_to_update->parsed_text + s_to_update->parsed_text_len, s_to_update->current_word, s_to_update->current_word_len);
        s_to_update->parsed_text_len += s_to_update->current_word_len;
        s_to_update->parsed_text[s_to_update->parsed_text_len] = '\0';
        
        s_to_update->current_word_len = 0;
        s_to_update->current_word[0] = '\0';
        s_to_update->dictionary_size++;
    }
    return true;
}

/**
 * @brief Recursive helper function for `lz76_exhaustive_generate`.
 *
 * Generates all binary strings of length `L` by exploring a binary tree.
 * For each fully generated string, it calculates its LZ76 phrase count and stores it.
 *
 * @param string_buffer Buffer to construct the current binary string. Also used to derive index.
 * @param k Current length of the string being built in `string_buffer` (recursion depth).
 * @param L Target length for the binary strings.
 * @param parent_lz_state Pointer to the LZState after processing the prefix `string_buffer[0...k-1]`
 *                        This state is copied and advanced for recursive calls.
 * @param phrase_counts_output Array to store the final phrase count for each generated string.
 *                             The index corresponds to the integer value of the binary string.
 */
static void generate_recursive(
    char* string_buffer, 
    int k,              
    int L,              
    LZState* parent_lz_state, 
    int* phrase_counts_output
) {
    if (k == L) { // Base case: string of length L is fully generated
        size_t final_dict_size = parent_lz_state->dictionary_size;
        // If there's a non-empty current_word when the string ends, it counts as one more phrase.
        if (parent_lz_state->current_word_len > 0) {
            final_dict_size++;
        }

        // Convert the binary string in string_buffer to an integer index.
        // E.g., for L=3, "101" -> 1*(2^2) + 0*(2^1) + 1*(2^0) = 5.
        size_t index = 0;
        for (int i = 0; i < L; ++i) {
            if (string_buffer[i] == '1') {
                index |= (1 << (L - 1 - i)); // Bitwise OR to set the bit
            }
        }
        if (index >= (size_t)(1 << L)) {
            fprintf(stderr, "Error: Index out of bounds in generate_recursive. L=%d, index=%zu\n", L, index);
            return; // Avoid writing out of bounds
        }
        phrase_counts_output[index] = final_dict_size;
        return;
    }

    // Recursive step: branch for appending '0'
    string_buffer[k] = '0';
    LZState state_for_0;
    // It is crucial to work on a copy of the parent state.
    if (!lz_state_copy(&state_for_0, parent_lz_state)) { 
        fprintf(stderr, "Error: Failed to copy LZState for '0' branch at depth %d\n", k);
        return; // Critical error, cannot proceed with this branch
    }
    if (!advance_lz_state_in_place(&state_for_0, '0'))   { 
        fprintf(stderr, "Error: Failed to advance LZState for '0' branch at depth %d\n", k);
        lz_state_free_buffers(&state_for_0); 
        return; // Critical error
    }
    generate_recursive(string_buffer, k + 1, L, &state_for_0, phrase_counts_output);
    lz_state_free_buffers(&state_for_0); // Clean up the state for this branch

    // Recursive step: branch for appending '1'
    string_buffer[k] = '1';
    LZState state_for_1;
    if (!lz_state_copy(&state_for_1, parent_lz_state)) { 
        fprintf(stderr, "Error: Failed to copy LZState for '1' branch at depth %d\n", k);
        return; 
    }
    if (!advance_lz_state_in_place(&state_for_1, '1'))   { 
        fprintf(stderr, "Error: Failed to advance LZState for '1' branch at depth %d\n", k);
        lz_state_free_buffers(&state_for_1); 
        return; 
    }
    generate_recursive(string_buffer, k + 1, L, &state_for_1, phrase_counts_output);
    lz_state_free_buffers(&state_for_1); // Clean up the state for this branch
}

// See lz_exhaustive.h for documentation
void lz76_exhaustive_generate(int L, int* phrase_counts_output) {
    if (L <= 0 || L > 24) { // 2^24 is 16 million. Max L around 20-22 for reasonable single-core speed.
                           // L > 24 might cause excessive memory for output or extreme slowness.
                           // Original code had L > 30 check, but 2^30 is too large for practical int array index.
        fprintf(stderr, "L must be between 1 and 24 (approx) for lz76_exhaustive_generate. L=%d provided.\n", L);
        return;
    }
    if (!phrase_counts_output) {
        fprintf(stderr, "Error: phrase_counts_output cannot be NULL.\n");
        return;
    }

    LZState initial_state;
    if (!lz_state_init(&initial_state, L)) {
        fprintf(stderr, "Error: Failed to initialize root LZState for lz76_exhaustive_generate(L=%d)\n", L);
        return; 
    }

    char* string_buffer = (char*)malloc(L + 1); // +1 for potential null terminator (though not strictly needed by logic)
    if (!string_buffer) {
        fprintf(stderr, "Error: Failed to allocate string_buffer for lz76_exhaustive_generate(L=%d)\n", L);
        lz_state_free_buffers(&initial_state);
        return;
    }
    // string_buffer content doesn't matter initially, it gets filled by generate_recursive.

    generate_recursive(string_buffer, 0, L, &initial_state, phrase_counts_output);

    free(string_buffer);
    lz_state_free_buffers(&initial_state);
}

/**
 * @brief Recursive helper for `lz76_exhaustive_distribution` (parallel tasks).
 *
 * This function is called by each OpenMP task (or serially if num_threads=1).
 * It starts from a pre-calculated `current_task_lz_state` (which corresponds to a specific prefix)
 * and recursively explores the sub-tree of binary strings of length `target_depth`.
 * It aggregates phrase counts into a `private_counts` array for the current task/thread.
 *
 * @param k Current depth of recursion relative to the start of this task's sub-problem.
 * @param target_depth The remaining length of strings to generate for this task (L - split_depth).
 * @param current_task_lz_state The initial LZState for this task, corresponding to a binary prefix.
 * @param private_counts Thread-local array to store phrase count distribution for this task.
 * @param max_complexity_to_track Size of `private_counts` array. Counts for complexities >= this value
 *                                are binned in the last entry.
 */
static void generate_recursive_for_distribution_task(
    int k,              
    int target_depth,   
    LZState* current_task_lz_state, 
    long long* private_counts, 
    int max_complexity_to_track
) {
    if (k == target_depth) { // Base case: sub-string for this task is fully generated
        size_t final_dict_size = current_task_lz_state->dictionary_size;
        if (current_task_lz_state->current_word_len > 0) {
            final_dict_size++;
        }

        if (final_dict_size < (size_t)(max_complexity_to_track - 1)) {
            private_counts[final_dict_size]++;
        } else { // Bin into the last counter if complexity is too high or equals max_complexity_to_track-1
            private_counts[max_complexity_to_track - 1]++;
        }
        return;
    }

    LZState state_for_0;
    if (!lz_state_copy(&state_for_0, current_task_lz_state)) { /* Error logged in lz_state_copy */ return; }
    if (!advance_lz_state_in_place(&state_for_0, '0')) { /* Error logged */ lz_state_free_buffers(&state_for_0); return; }
    generate_recursive_for_distribution_task(k + 1, target_depth, &state_for_0, private_counts, max_complexity_to_track);
    lz_state_free_buffers(&state_for_0);

    LZState state_for_1;
    if (!lz_state_copy(&state_for_1, current_task_lz_state)) { /* Error logged */ return; }
    if (!advance_lz_state_in_place(&state_for_1, '1')) { /* Error logged */ lz_state_free_buffers(&state_for_1); return; }
    generate_recursive_for_distribution_task(k + 1, target_depth, &state_for_1, private_counts, max_complexity_to_track);
    lz_state_free_buffers(&state_for_1);
}

/**
 * @brief Computes the LZ76 state for a given binary prefix string.
 *
 * Initializes an LZState and processes each character of the `prefix` string
 * using `advance_lz_state_in_place`.
 *
 * @param prefix The binary prefix string (e.g., "010").
 * @param prefix_len The length of the `prefix` string.
 * @param out_state Pointer to an LZState structure that will be initialized and populated.
 * @param L_max The maximum length of strings this state will eventually handle (total length L).
 *              This is used for buffer allocation in `lz_state_init`.
 * @return `true` if the state is computed successfully, `false` on error.
 */
static bool compute_state_for_prefix(const char* prefix, int prefix_len, LZState* out_state, size_t L_max) {
    if (!lz_state_init(out_state, L_max)) { 
        fprintf(stderr, "Error: Failed to init state for prefix (%s) computation.\n", prefix);
        return false; 
    }
    for (int i = 0; i < prefix_len; ++i) {
        if (!advance_lz_state_in_place(out_state, prefix[i])) {
            fprintf(stderr, "Error: Failed to advance state for prefix %s at char %c (index %d).\n", prefix, prefix[i], i);
            lz_state_free_buffers(out_state);
            return false;
        }
    }
    return true;
}

// See lz_exhaustive.h for documentation
void lz76_exhaustive_distribution(
    int L, 
    long long* counts_by_complexity, 
    int max_complexity_to_track,
    int num_threads_requested
) {
    if (L <= 0 || L > 30) { // L > 30 (2^30 strings) is generally too much. Practical limit might be ~25-28 depending on resources.
        fprintf(stderr, "Error: L must be > 0 and typically <= 30. L=%d provided.\n", L);
        return;
    }
    if (!counts_by_complexity || max_complexity_to_track <= 0) {
        fprintf(stderr, "Error: counts_by_complexity is NULL or max_complexity_to_track is invalid.\n");
        return;
    }

    int actual_num_threads = 1;
#ifdef _OPENMP
    if (num_threads_requested <= 0) { // Default: use all available threads as detected by OpenMP
        actual_num_threads = omp_get_max_threads();
    } else {
        actual_num_threads = num_threads_requested;
    }
    if (actual_num_threads <= 0) actual_num_threads = 1; // Safety check
#else
    if (num_threads_requested > 1) {
        fprintf(stderr, "Warning: Compiled without OpenMP. Running serially despite num_threads=%d requested.\n", num_threads_requested);
    }
    // actual_num_threads remains 1
#endif

    // Clear the output array as it might contain old data or be uninitialized.
    for(int i = 0; i < max_complexity_to_track; ++i) counts_by_complexity[i] = 0;

    if (L == 0) { // Edge case: empty string
        // Assuming complexity of empty string is 0. Adjust if different definition.
        if (0 < max_complexity_to_track -1 ) counts_by_complexity[0]++; 
        else counts_by_complexity[max_complexity_to_track-1]++;
        return;
    }

    // Determine split_depth: number of initial prefix bits to generate states for sequentially.
    // The goal is to create 2^split_depth tasks, which can then be run in parallel.
    int split_depth = 0;
    if (actual_num_threads > 1) {
        // Calculate a split_depth such that 2^split_depth is close to actual_num_threads.
        // This aims to balance work among threads.
        // Example: if actual_num_threads = 7, log2(7) approx 2.8. floor(2.8)=2. split_depth=2 creates 4 tasks.
        // A slightly more aggressive split: ceil(log2(actual_num_threads))
        if (actual_num_threads > 0) { // log2 is undefined for <=0
             split_depth = (int)floor(log2((double)actual_num_threads));
        }
        // Ensure enough tasks, or at least some split if multiple threads
        if ((1 << split_depth) < actual_num_threads && split_depth < L) {
             split_depth++; // Try one more level of splitting if it doesn't exceed L
        }
         // Max split_depth is L itself. No point splitting beyond string length.
        if (split_depth > L) split_depth = L;
        // Minimum split_depth if threads > 1 and L is large enough
        if (split_depth == 0 && actual_num_threads > 1 && L > 0) split_depth = 1; 
    }
    // If only one thread, or if split_depth calculations result in 0 (e.g. L is small), run serially from root.
    // No, if actual_num_threads is 1, split_depth should definitely be 0.
    if (actual_num_threads == 1) split_depth = 0;

    size_t num_tasks = 1 << split_depth; // Number of distinct prefixes to compute states for.
    LZState* prefix_states = (LZState*)malloc(num_tasks * sizeof(LZState));
    if (!prefix_states) {
        fprintf(stderr, "Error: Failed to allocate memory for prefix_states array (num_tasks=%zu).\n", num_tasks);
        return;
    }
    for(size_t i=0; i<num_tasks; ++i) { // Initialize to known bad state for easier error checking on cleanup
        prefix_states[i].parsed_text = NULL; 
        prefix_states[i].current_word = NULL; 
    }

    char* prefix_string_buffer = NULL;
    if (split_depth > 0) {
        prefix_string_buffer = (char*)malloc(split_depth + 1); // For constructing prefix strings
        if (!prefix_string_buffer) {
            fprintf(stderr, "Error: Failed to allocate prefix_string_buffer (split_depth=%d).\n", split_depth);
            free(prefix_states);
            return;
        }
    }

    // Generate initial LZStates for each prefix sequentially.
    if (split_depth == 0) { // Single task: initial empty state for the whole string L.
        if (!compute_state_for_prefix("", 0, &prefix_states[0], L)) {
             fprintf(stderr, "Error: Failed to compute initial empty state for serial run.\n");
            // prefix_states[0] might have had buffers allocated by compute_state_for_prefix before failing
            lz_state_free_buffers(&prefix_states[0]);
            free(prefix_states);
            // prefix_string_buffer is NULL here, no need to free
            return;
        }
    } else {
        for (size_t i = 0; i < num_tasks; ++i) {
            // Convert task index `i` to its `split_depth`-bit binary string representation.
            for (int bit_idx = 0; bit_idx < split_depth; ++bit_idx) {
                prefix_string_buffer[bit_idx] = ((i >> (split_depth - 1 - bit_idx)) & 1) ? '1' : '0';
            }
            prefix_string_buffer[split_depth] = '\0';
            
            if (!compute_state_for_prefix(prefix_string_buffer, split_depth, &prefix_states[i], L)) {
                fprintf(stderr, "Error: Failed to compute state for prefix \"%s\".\n", prefix_string_buffer);
                // Cleanup already initialized prefix states before exiting
                for (size_t j = 0; j <= i; ++j) { // up to and including the one that may have partially allocated
                    lz_state_free_buffers(&prefix_states[j]);
                }
                free(prefix_states);
                free(prefix_string_buffer);
                return;
            }
        }
    }
    if (prefix_string_buffer) free(prefix_string_buffer);

    // Parallel computation of sub-problems or serial execution.
#ifdef _OPENMP
    if (actual_num_threads > 1 && L > split_depth) { // Only parallelize if threads > 1 and there's work to split (L > split_depth)
        omp_set_num_threads(actual_num_threads);
        
        // Each thread gets its own array to store distribution counts locally.
        long long** private_distribution_arrays = (long long**)malloc(actual_num_threads * sizeof(long long*));
        if (!private_distribution_arrays) {
            fprintf(stderr, "Error: Failed to allocate array for private_distribution_arrays.\n");
            goto cleanup_prefix_states_label; // Use goto for centralized cleanup
        }
        for(int t=0; t < actual_num_threads; ++t) private_distribution_arrays[t] = NULL; // Initialize to NULL

        bool alloc_ok = true;
        for(int t=0; t < actual_num_threads; ++t) {
            private_distribution_arrays[t] = (long long*)calloc(max_complexity_to_track, sizeof(long long));
            if (!private_distribution_arrays[t]) { 
                fprintf(stderr, "Error: Failed to calloc private_distribution_array for thread %d.\n", t);
                alloc_ok = false; break;
            }
        }

        if (!alloc_ok) {
            for(int t=0; t < actual_num_threads; ++t) free(private_distribution_arrays[t]); // Free any that were allocated
            free(private_distribution_arrays);
            goto cleanup_prefix_states_label;
        }

        #pragma omp parallel for schedule(dynamic) num_threads(actual_num_threads)
        for (size_t task_idx = 0; task_idx < num_tasks; ++task_idx) {
            int thread_id = omp_get_thread_num();
            if (thread_id < 0 || thread_id >= actual_num_threads) {
                 fprintf(stderr, "Error: Invalid thread_id %d from omp_get_thread_num()\n", thread_id);
                 // This task might not complete correctly. How to handle?
                 // For now, continue, but this indicates an OpenMP setup issue.
                 continue; 
            }
            // Each task (prefix) starts a recursive generation for the remaining L - split_depth characters.
            generate_recursive_for_distribution_task(0, L - split_depth, &prefix_states[task_idx], 
                                                     private_distribution_arrays[thread_id], max_complexity_to_track);
        }

        // Aggregate results from each thread's private array into the final shared array.
        for (int t = 0; t < actual_num_threads; ++t) {
            if (private_distribution_arrays[t]) { // Check if it was allocated
                for (int c = 0; c < max_complexity_to_track; ++c) {
                    counts_by_complexity[c] += private_distribution_arrays[t][c];
                }
                free(private_distribution_arrays[t]);
            }
        }
        free(private_distribution_arrays);

    } else { // Run serially if actual_num_threads is 1, or L <= split_depth (no further recursion needed for tasks)
        // If L == split_depth, target_depth for recursion is 0. The base case of generate_recursive_for_distribution_task handles this.
        // It will use prefix_states[task_idx] and directly update counts.
        // This loop is for L > split_depth but actual_num_threads = 1.
        // Or if L == split_depth, the recursive call will immediately hit base case.
        for (size_t task_idx = 0; task_idx < num_tasks; ++task_idx) { // num_tasks will be 1 if split_depth is 0
             generate_recursive_for_distribution_task(0, L - split_depth, &prefix_states[task_idx], 
                                                 counts_by_complexity, max_complexity_to_track);
        }
    }
#else // No OpenMP defined: run serially.
    // num_tasks will be 1 (split_depth is 0), prefix_states[0] is the initial empty state.
    generate_recursive_for_distribution_task(0, L, &prefix_states[0], // L - 0 = L
                                             counts_by_complexity, max_complexity_to_track);
#endif

cleanup_prefix_states_label: // Label for goto cleanup
    for (size_t i = 0; i < num_tasks; ++i) {
        // Buffers inside prefix_states[i] should be freed if they were successfully allocated by compute_state_for_prefix
        // If compute_state_for_prefix failed for a state, it should have freed its own buffers.
        // If it succeeded, they are freed here.
        lz_state_free_buffers(&prefix_states[i]); 
    }
    free(prefix_states);
} 