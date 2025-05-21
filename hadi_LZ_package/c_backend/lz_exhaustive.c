#include "lz_exhaustive.h"
#include <string.h>
#include <stdlib.h>
#include <stdio.h> // For perror, remove if not used directly beyond that
#include <stdbool.h>
#include <math.h> // For ceil, log2

#ifdef _OPENMP
#include <omp.h>
#endif

// Internal State for LZ76 parsing
typedef struct {
    char* parsed_text;      // Concatenated phrases found so far
    size_t parsed_text_len;
    char* current_word;     // Current word being built
    size_t current_word_len;
    size_t dictionary_size;  // Number of phrases in the dictionary
    size_t max_len;          // Max length L, for buffer allocations
} LZState;

// Initialize an LZState. Buffers are allocated.
static bool lz_state_init(LZState* state, size_t L_max_len) {
    state->max_len = L_max_len;
    state->parsed_text = (char*)malloc(L_max_len + 1); 
    state->current_word = (char*)malloc(L_max_len + 1);

    if (!state->parsed_text || !state->current_word) {
        perror("LZState init failed to allocate buffers");
        free(state->parsed_text); // free if one was allocated
        free(state->current_word); // free if one was allocated
        return false;
    }

    state->parsed_text[0] = '\0';
    state->parsed_text_len = 0;
    state->current_word[0] = '\0';
    state->current_word_len = 0;
    state->dictionary_size = 0;
    return true;
}

// Free dynamically allocated buffers in an LZState
static void lz_state_free_buffers(LZState* state) {
    free(state->parsed_text);
    state->parsed_text = NULL;
    free(state->current_word);
    state->current_word = NULL;
}

// Deep copy an LZState. Assumes dest is uninitialized or its buffers will be overwritten.
// Returns false on allocation failure.
static bool lz_state_copy(LZState* dest, const LZState* src) {
    dest->max_len = src->max_len;
    dest->parsed_text = (char*)malloc(dest->max_len + 1);
    dest->current_word = (char*)malloc(dest->max_len + 1);

    if (!dest->parsed_text || !dest->current_word) {
        perror("LZState copy failed to allocate buffers");
        free(dest->parsed_text);
        free(dest->current_word);
        return false;
    }

    memcpy(dest->parsed_text, src->parsed_text, src->parsed_text_len + 1); // +1 for null terminator
    dest->parsed_text_len = src->parsed_text_len;
    memcpy(dest->current_word, src->current_word, src->current_word_len + 1); // +1 for null terminator
    dest->current_word_len = src->current_word_len;
    dest->dictionary_size = src->dictionary_size;
    return true;
}

// Mimics one step of lz_core.c's lz76_complexity logic or get_inefficient_lz76_phrase_count
// Updates new_state based on prev_state and next_char.
// IMPORTANT: new_state must be an independent copy. This function MODIFIES new_state passed to it,
// assuming its buffers are either fresh from lz_state_init or copied from prev_state and ready for modification.
// For the recursive strategy, it's better if this function takes prev_state,
// and populates a completely separate new_state whose buffers are allocated by this function.
// Let's try: advance_lz_state creates and returns a new state struct, or fills a pre-init'd one.
// The recursive caller will create two LZState locals for its two children branches.

// This function MODIFIES the state `s_to_update` based on `char_to_process`.
// `s_to_update` is assumed to be a valid state (e.g., copied from parent state).
static bool advance_lz_state_in_place(LZState* s_to_update, char char_to_process) {
    if (s_to_update->current_word_len >= s_to_update->max_len) {
        // Should not happen if L_max is string length L
        fprintf(stderr, "Error: current_word buffer overflow in advance_lz_state.\n");
        return false; 
    }
    s_to_update->current_word[s_to_update->current_word_len++] = char_to_process;
    s_to_update->current_word[s_to_update->current_word_len] = '\0';

    bool included = false;
    // Search domain: s_to_update->parsed_text + s_to_update->current_word (WITHOUT the latest char_to_process)
    size_t cw_prefix_len = s_to_update->current_word_len - 1;
    // Max length of search_domain_text = max_len (parsed) + max_len (cw_prefix) = 2 * max_len
    char* search_domain_text = (char*)malloc(s_to_update->parsed_text_len + cw_prefix_len + 1);
    if (!search_domain_text) {
        perror("Failed to alloc search_domain_text in advance_lz_state");
        // Backtrack current_word change before returning false
        s_to_update->current_word_len--;
        s_to_update->current_word[s_to_update->current_word_len] = '\0';
        return false; 
    }
    memcpy(search_domain_text, s_to_update->parsed_text, s_to_update->parsed_text_len);
    memcpy(search_domain_text + s_to_update->parsed_text_len, s_to_update->current_word, cw_prefix_len);
    search_domain_text[s_to_update->parsed_text_len + cw_prefix_len] = '\0';

    // Check if full s_to_update->current_word (with new char) is in search_domain_text
    // strstr is okay for this, or manual loop like lz_core
    if (s_to_update->parsed_text_len + cw_prefix_len >= s_to_update->current_word_len) { // only search if domain is long enough
        if (strstr(search_domain_text, s_to_update->current_word) != NULL) {
            included = true;
        }
    }
    free(search_domain_text);

    if (!included) {
        if (s_to_update->parsed_text_len + s_to_update->current_word_len > s_to_update->max_len) {
             fprintf(stderr, "Error: parsed_text buffer overflow in advance_lz_state.\n");
             // Backtrack current_word change
            s_to_update->current_word_len--;
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

static void generate_recursive(
    char* string_buffer, // Used to build the current L-length string, and derive index
    int k,               // Current depth/length of string_buffer
    int L,               // Target length
    LZState* parent_lz_state, // LZ state after processing string_buffer[0...k-1]
    int* phrase_counts_output
) {
    if (k == L) {
        size_t final_dict_size = parent_lz_state->dictionary_size;
        if (parent_lz_state->current_word_len > 0) {
            final_dict_size++;
        }

        // Convert binary string in string_buffer to an integer index
        size_t index = 0;
        for (int i = 0; i < L; ++i) {
            if (string_buffer[i] == '1') {
                index |= (1 << (L - 1 - i));
            }
        }
        phrase_counts_output[index] = final_dict_size;
        return;
    }

    // Branch for '0'
    string_buffer[k] = '0';
    LZState state_for_0;
    if (!lz_state_copy(&state_for_0, parent_lz_state)) { /* error handling */ return; }
    if (!advance_lz_state_in_place(&state_for_0, '0'))   { /* error handling */ lz_state_free_buffers(&state_for_0); return; }
    generate_recursive(string_buffer, k + 1, L, &state_for_0, phrase_counts_output);
    lz_state_free_buffers(&state_for_0);

    // Branch for '1'
    string_buffer[k] = '1';
    LZState state_for_1;
    if (!lz_state_copy(&state_for_1, parent_lz_state)) { /* error handling */ return; }
    if (!advance_lz_state_in_place(&state_for_1, '1'))   { /* error handling */ lz_state_free_buffers(&state_for_1); return; }
    generate_recursive(string_buffer, k + 1, L, &state_for_1, phrase_counts_output);
    lz_state_free_buffers(&state_for_1);
}

void lz76_exhaustive_generate(int L, int* phrase_counts_output) {
    if (L <= 0 || L > 30) { // 2^30 is too large for results array, L > 24-25 might be too slow
        fprintf(stderr, "L must be between 1 and 30 (approx). For L > 20, this will be very slow.\n");
        return;
    }

    LZState initial_state;
    if (!lz_state_init(&initial_state, L)) {
        return; // Init failed
    }

    char* string_buffer = (char*)malloc(L + 1);
    if (!string_buffer) {
        perror("Failed to allocate string_buffer");
        lz_state_free_buffers(&initial_state);
        return;
    }
    // string_buffer doesn't need to be null-terminated until k==L for index conversion, but good practice.

    generate_recursive(string_buffer, 0, L, &initial_state, phrase_counts_output);

    free(string_buffer);
    lz_state_free_buffers(&initial_state);
}

// --- Implementation for lz76_exhaustive_distribution ---

// Recursive helper for distribution calculation - this version is for a single task/thread
static void generate_recursive_for_distribution_task(
    int k,               // Current depth relative to the start of this task's sub-problem
    int target_depth,    // Target depth for this task (L - split_depth)
    LZState* current_task_lz_state, // LZ state for this task (copied from prefix state)
    long long* private_counts, // This task's private distribution array
    int max_complexity_to_track
) {
    if (k == target_depth) {
        size_t final_dict_size = current_task_lz_state->dictionary_size;
        if (current_task_lz_state->current_word_len > 0) {
            final_dict_size++;
        }
        if (final_dict_size < (size_t)(max_complexity_to_track - 1)) {
            private_counts[final_dict_size]++;
        } else {
            private_counts[max_complexity_to_track - 1]++;
        }
        return;
    }

    LZState state_for_0;
    if (!lz_state_copy(&state_for_0, current_task_lz_state)) { return; }
    if (!advance_lz_state_in_place(&state_for_0, '0')) { lz_state_free_buffers(&state_for_0); return; }
    generate_recursive_for_distribution_task(k + 1, target_depth, &state_for_0, private_counts, max_complexity_to_track);
    lz_state_free_buffers(&state_for_0);

    LZState state_for_1;
    if (!lz_state_copy(&state_for_1, current_task_lz_state)) { return; }
    if (!advance_lz_state_in_place(&state_for_1, '1')) { lz_state_free_buffers(&state_for_1); return; }
    generate_recursive_for_distribution_task(k + 1, target_depth, &state_for_1, private_counts, max_complexity_to_track);
    lz_state_free_buffers(&state_for_1);
}

// Helper to compute LZ state for a given prefix string, starting from an initial empty state.
static bool compute_state_for_prefix(const char* prefix, int prefix_len, LZState* out_state, size_t L_max) {
    if (!lz_state_init(out_state, L_max)) return false;
    for (int i = 0; i < prefix_len; ++i) {
        if (!advance_lz_state_in_place(out_state, prefix[i])) {
            lz_state_free_buffers(out_state);
            return false;
        }
    }
    return true;
}

void lz76_exhaustive_distribution(
    int L, 
    long long* counts_by_complexity, // Final shared output array
    int max_complexity_to_track,
    int num_threads_requested
) {
    if (L <= 0 || L > 60) { /* error */ fprintf(stderr, "L out of range.\n"); return; }
    if (!counts_by_complexity || max_complexity_to_track <= 0) { /* error */ fprintf(stderr, "Invalid output array.\n"); return; }

    int actual_num_threads = 1;
#ifdef _OPENMP
    if (num_threads_requested > 0) {
        actual_num_threads = num_threads_requested;
    } else { // Default to OMP_NUM_THREADS or system default
        actual_num_threads = omp_get_max_threads(); 
    }
    if (actual_num_threads <=0) actual_num_threads = 1;
#else
    // No OpenMP, run serially
    if (num_threads_requested > 1) {
        fprintf(stderr, "Warning: Compiled without OpenMP, running serially despite num_threads=%d requested.\n", num_threads_requested);
    }
#endif

    // Clear the output array (important as it might be uninitialized or reused)
    for(int i = 0; i < max_complexity_to_track; ++i) counts_by_complexity[i] = 0;

    if (L == 0) { // Handle L=0 explicitly if it means empty string, which has some defined complexity (e.g. 0 or 1)
        if (0 < max_complexity_to_track -1) counts_by_complexity[0]++; else counts_by_complexity[max_complexity_to_track-1]++;
        return;
    }

    // Determine split_depth: number of initial bits to pre-calculate sequentially
    // We want 2^split_depth tasks, roughly equal to actual_num_threads
    int split_depth = 0;
    if (actual_num_threads > 1) {
        split_depth = (int)floor(log2((double)actual_num_threads - 0.001)); // e.g. 4 threads -> log2(3.999) -> floor(1.99) -> 1. Needs to be ceil or adjusted.
                                                                    // Let's adjust: if num_threads=4, we want 2^2 prefixes. split_depth = ceil(log2(num_threads))
                                                                    // However, if num_threads is not power of 2, e.g., 3. We might do 2 prefixes and 1 thread gets 2, or 4 prefixes & 1 is idle.
                                                                    // Simpler: if threads > 1, at least split depth 1 (0...., 1....)
        int temp_threads = 1;
        while(temp_threads < actual_num_threads && split_depth < L) {
            temp_threads *= 2;
            split_depth++;
        }
        if (split_depth > L) split_depth = L; // Cannot exceed total length
    }
    if (actual_num_threads == 1) split_depth = 0; // Serial execution from root

    size_t num_tasks = 1 << split_depth;
    LZState* prefix_states = (LZState*)malloc(num_tasks * sizeof(LZState));
    char* prefix_string_buffer = (char*)malloc(split_depth + 1);

    if (!prefix_states || (split_depth > 0 && !prefix_string_buffer) ) {
        perror("Failed to allocate for prefix states/buffer");
        free(prefix_states);
        free(prefix_string_buffer);
        // Fallback to serial if this setup fails?
        // For now, assume this should work or it's a critical error.
        return;
    }

    // Generate initial prefix states sequentially
    if (split_depth == 0) { // Serial execution, single task from initial state
        if(!lz_state_init(&prefix_states[0], L)) { free(prefix_states); return;}
    } else {
        for (size_t i = 0; i < num_tasks; ++i) {
            // Convert i to split_depth binary string
            for (int bit_idx = 0; bit_idx < split_depth; ++bit_idx) {
                prefix_string_buffer[bit_idx] = ((i >> (split_depth - 1 - bit_idx)) & 1) ? '1' : '0';
            }
            prefix_string_buffer[split_depth] = '\0';
            if (!compute_state_for_prefix(prefix_string_buffer, split_depth, &prefix_states[i], L)) {
                fprintf(stderr, "Failed to compute state for prefix %s\n", prefix_string_buffer);
                for(size_t j=0; j<i; ++j) lz_state_free_buffers(&prefix_states[j]);
                free(prefix_states);
                free(prefix_string_buffer);
                return;
            }
        }
    }
    if (split_depth > 0) free(prefix_string_buffer);

    // Main parallel computation or serial execution
#ifdef _OPENMP
    if (actual_num_threads > 1 && L > split_depth) {
        omp_set_num_threads(actual_num_threads);
        long long** private_distribution_arrays = (long long**)malloc(actual_num_threads * sizeof(long long*));
        if (!private_distribution_arrays) { /* handle error */ goto cleanup_prefix_states; }

        for(int t=0; t < actual_num_threads; ++t) {
            private_distribution_arrays[t] = (long long*)calloc(max_complexity_to_track, sizeof(long long));
            if (!private_distribution_arrays[t]) { 
                /* handle error, free previously allocated */ 
                for(int k=0; k<t; ++k) free(private_distribution_arrays[k]);
                free(private_distribution_arrays);
                goto cleanup_prefix_states;
            }
        }

        #pragma omp parallel for schedule(dynamic) num_threads(actual_num_threads)
        for (size_t task_idx = 0; task_idx < num_tasks; ++task_idx) {
            int thread_id = omp_get_thread_num();
            // Each task (prefix) continues recursively
            generate_recursive_for_distribution_task(0, L - split_depth, &prefix_states[task_idx], 
                                                     private_distribution_arrays[thread_id], max_complexity_to_track);
        }

        // Aggregate results from private arrays
        for (int t = 0; t < actual_num_threads; ++t) {
            for (int c = 0; c < max_complexity_to_track; ++c) {
                counts_by_complexity[c] += private_distribution_arrays[t][c];
            }
            free(private_distribution_arrays[t]);
        }
        free(private_distribution_arrays);
    } else { // Run serially if actual_num_threads is 1 or L <= split_depth
        generate_recursive_for_distribution_task(0, L - split_depth, &prefix_states[0], 
                                                 counts_by_complexity, max_complexity_to_track);
    }
#else // No OpenMP, run serially from the single initial state (prefix_states[0])
    generate_recursive_for_distribution_task(0, L - split_depth, &prefix_states[0], 
                                             counts_by_complexity, max_complexity_to_track);
#endif

cleanup_prefix_states:
    for (size_t i = 0; i < num_tasks; ++i) {
        lz_state_free_buffers(&prefix_states[i]);
    }
    free(prefix_states);
} 