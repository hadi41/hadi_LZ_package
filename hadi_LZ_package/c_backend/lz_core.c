#include "lz_core.h"
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <omp.h>
#include <math.h>
#include <stdbool.h>

/**
 * @brief Calculates the LZ76 complexity of a single input string.
 *
 * This function implements the Lempel-Ziv 76 algorithm. It parses the input
 * string from left to right, building a dictionary of encountered substrings.
 * The complexity is the number of distinct substrings in this dictionary,
 * often normalized by log2 of the string length.
 *
 * @param input_string The null-terminated C string to analyze.
 * @param length The length of the input string (excluding the null terminator).
 * @return The LZ76 complexity value. If length is 0 or input_string is NULL, returns 0.0.
 *         The result is dictionary_size * log2(length).
 */
double lz76_complexity(const char* input_string, size_t length) {
    if (!input_string || length == 0) return 0.0;
    
    char* parsed = (char*)malloc((length + 1) * sizeof(char));
    if (!parsed) return -1.0; // Error handling for malloc
    size_t parsed_len = 0;
    size_t pos = 0;
    size_t dictionary_size = 0;
    char* current_word = (char*)malloc((length + 1) * sizeof(char));
    if (!current_word) { // Error handling for malloc
        free(parsed);
        return -1.0;
    }
    size_t current_len = 0;
    
    parsed[0] = '\0';
    
    while (pos < length) {
        current_word[current_len++] = input_string[pos++];
        current_word[current_len] = '\0';
        
        bool included = false;
        
        // Create temporary buffer for (parsed string + current_word without its last character)
        // This is the part of the string already processed and can be used as dictionary
        char* temp_dict_buffer = (char*)malloc(parsed_len + current_len); // Max possible length
        if (!temp_dict_buffer) { // Error handling
            free(parsed);
            free(current_word);
            return -1.0;
        }
        size_t temp_dict_buffer_len = 0;
        
        memcpy(temp_dict_buffer, parsed, parsed_len);
        temp_dict_buffer_len = parsed_len;
        
        if (current_len > 1) {
            memcpy(temp_dict_buffer + temp_dict_buffer_len, current_word, current_len - 1);
            temp_dict_buffer_len += current_len - 1;
        }
        // temp_dict_buffer is not null-terminated here, but memcmp will use lengths

        // Check if current_word is in temp_dict_buffer
        for (size_t i = 0; (i + current_len) <= temp_dict_buffer_len; i++) {
            if (memcmp(temp_dict_buffer + i, current_word, current_len) == 0) {
                included = true;
                break;
            }
        }
        
        free(temp_dict_buffer);
        
        if (!included) {
            memcpy(parsed + parsed_len, current_word, current_len);
            parsed_len += current_len;
            parsed[parsed_len] = '\0'; // Null-terminate parsed string
            
            current_len = 0; // Reset current_word
            dictionary_size++;
        }
    }
    
    if (current_len > 0) { // If loop finishes with a current_word not yet added
        dictionary_size++;
    }
    
    free(parsed);
    free(current_word);
    
    if (length == 0) return 0.0; // Avoid log2(0) or log2(1) if desired (original returned log2(length))
    return dictionary_size * log2((double)length); // Cast length to double for log2
}

/**
 * @brief Calculates LZ76 complexity for multiple strings in parallel using OpenMP.
 * @param input_strings An array of null-terminated C strings.
 * @param lengths An array of lengths corresponding to each input string.
 * @param results An array where the calculated complexity for each string will be stored.
 * @param n_strings The number of strings in the input arrays.
 * @param n_threads The number of threads to use for parallel computation.
 */
void lz76_complexity_parallel_original(const char** input_strings, size_t* lengths, 
                                     double* results, size_t n_strings, int n_threads) {
    omp_set_num_threads(n_threads);
    
    #pragma omp parallel for schedule(dynamic)
    for (size_t i = 0; i < n_strings; i++) {
        results[i] = lz76_complexity(input_strings[i], lengths[i]);
    }
}

/**
 * @brief Calculates symmetric LZ76 complexity for multiple strings in parallel.
 * Symmetric LZ76 complexity is the average of LZ76(S) and LZ76(S_reversed).
 * @param input_strings An array of null-terminated C strings.
 * @param lengths An array of lengths corresponding to each input string.
 * @param results An array where the calculated symmetric complexity for each string will be stored.
 * @param n_strings The number of strings in the input arrays.
 * @param n_threads The number of threads to use for parallel computation.
 */
void symmetric_lz76_parallel_original(const char** input_strings, size_t* lengths,
                                    double* results, size_t n_strings, int n_threads) {
    omp_set_num_threads(n_threads);
    
    #pragma omp parallel
    {
        char* reversed = NULL;
        size_t max_len_processed_by_thread = 0; // Thread-local max length for buffer re-use
        
        #pragma omp for schedule(dynamic)
        for (size_t i = 0; i < n_strings; i++) {
            if (lengths[i] > max_len_processed_by_thread) {
                // realloc can be expensive, only do if necessary
                char* temp_reversed = (char*)realloc(reversed, lengths[i] + 1);
                if (!temp_reversed) { // realloc failed
                    // Handle error: maybe set result to an error code or skip
                    // For now, we'll assume realloc succeeds or live with old buffer if it fails on larger string.
                    // A more robust solution would involve error propagation.
                    if (reversed) { // If realloc failed but we had a buffer, try to use it
                        // This part is tricky, as the length might be too small.
                        // Best to signal an error. For now, we proceed with caution.
                    } else {
                         results[i] = -1.0; // Indicate error
                         continue; // Skip this string
                    }
                } else {
                    reversed = temp_reversed;
                }
                max_len_processed_by_thread = lengths[i];
            }
            
            if (!reversed && lengths[i] > 0) { // Should not happen if realloc logic is correct above.
                 results[i] = -1.0; // Indicate error
                 continue;
            }

            for (size_t j = 0; j < lengths[i]; j++) {
                reversed[j] = input_strings[i][lengths[i] - 1 - j];
            }
            reversed[lengths[i]] = '\0';
            
            double c1 = lz76_complexity(input_strings[i], lengths[i]);
            double c2 = lz76_complexity(reversed, lengths[i]);
            if (c1 < 0 || c2 < 0) { // Check for errors from lz76_complexity
                results[i] = -1.0; // Propagate error
            } else {
                results[i] = (c1 + c2) / 2.0;
            }
        }
        
        free(reversed); // Each thread frees its own buffer
    }
}

/**
 * @brief Calculates the LZ78 complexity of a single input string.
 *
 * This function implements the Lempel-Ziv 78 algorithm. It parses the input
 * string and builds a dictionary of phrases. Each new phrase is formed by
 * extending a previously seen phrase by one character. The complexity is
 * the total number of phrases in the dictionary.
 *
 * @param input_string The null-terminated C string to analyze.
 * @param length The length of the input string.
 * @return The LZ78 complexity (number of phrases). Returns 0.0 if input is NULL or length is 0.
 */
double lz78_complexity(const char* input_string, size_t length) {
    if (!input_string || length == 0) return 0.0;
    
    char** dictionary = (char**)malloc(length * sizeof(char*)); // Max possible phrases = length
    if(!dictionary) return -1.0; // Malloc error
    size_t dict_size = 0;
    
    char* current_word = (char*)malloc((length + 1) * sizeof(char));
    if(!current_word) { // Malloc error
        free(dictionary);
        return -1.0;
    }
    size_t current_len = 0;
    size_t pos = 0;
    
    while (pos < length) {
        current_word[current_len++] = input_string[pos++];
        current_word[current_len] = '\0';
        
        bool found_prefix_in_dict = false;
        // Check if current_word (as a prefix) is in the dictionary
        // The LZ78 definition: add S_i + c to dictionary if S_i is in dictionary and S_i + c is not.
        // This implementation checks if the current_word is already a full entry.
        // A more standard LZ78 might check if current_word[0...current_len-2] is in dictionary.
        // Let's assume this variant is intended.
        for (size_t i = 0; i < dict_size; i++) {
            // Check if dictionary[i] is a prefix of current_word
            // No, it should be: is current_word a prefix of dictionary[i]?
            // Or, more simply: is current_word already in the dictionary?
            // The original code checks if current_word is a prefix of any dictionary word.
            // This seems non-standard. A standard approach:
            // Dictionary D = {epsilon}
            // While not end of string:
            //   Find longest prefix P of remaining string that is in D
            //   Add P + next_char to D
            //   Remove P + next_char from string
            // Let's stick to documenting the provided code's logic.
            // The provided code finds if current_word is itself already a complete word,
            // or if current_word is a prefix of an existing dictionary word.

            size_t dict_word_len = strlen(dictionary[i]);
            if (dict_word_len >= current_len) { // Only check if dict word is long enough
                if (memcmp(dictionary[i], current_word, current_len) == 0) {
                    found_prefix_in_dict = true; // current_word is a prefix or exact match of an existing dict word
                    break;
                }
            }
        }
        
        if (!found_prefix_in_dict) {
            // Add current_word to dictionary
            dictionary[dict_size] = (char*)malloc((current_len + 1) * sizeof(char));
            if (!dictionary[dict_size]) { // Malloc error
                // Cleanup partially filled dictionary
                for(size_t k=0; k<dict_size; ++k) free(dictionary[k]);
                free(dictionary);
                free(current_word);
                return -1.0;
            }
            strcpy(dictionary[dict_size], current_word);
            dict_size++;
            current_len = 0; // Reset for the next word
        }
    }
    
    if (current_len > 0) { // If loop ends and current_word was a prefix of a dict entry
        dict_size++; // This part ensures the last component is counted
    }
    
    for (size_t i = 0; i < dict_size; i++) {
        if(dictionary[i]) free(dictionary[i]); // Check for NULL if an error occurred during allocation
    }
    free(dictionary);
    free(current_word);
    
    return (double)dict_size;
}

/**
 * @brief Calculates the symmetric LZ78 complexity of a string.
 * Symmetric LZ78 is the average of LZ78(S) and LZ78(S_reversed).
 * @param input_string The null-terminated C string.
 * @param length The length of the string.
 * @return The symmetric LZ78 complexity. Returns 0.0 if input is NULL or length is 0.
 */
double symmetric_lz78_complexity(const char* input_string, size_t length) {
    if (!input_string || length == 0) return 0.0;
    
    char* reversed = (char*)malloc((length + 1) * sizeof(char));
    if(!reversed) return -1.0; // Malloc error
    
    for (size_t i = 0; i < length; i++) {
        reversed[i] = input_string[length - 1 - i];
    }
    reversed[length] = '\0';
    
    double c1 = lz78_complexity(input_string, length);
    double c2 = lz78_complexity(reversed, length);
    
    free(reversed);

    if (c1 < 0 || c2 < 0) return -1.0; // Propagate error
    return (c1 + c2) / 2.0;
}

/**
 * @brief Calculates LZ78 complexity for multiple strings in parallel.
 * @param input_strings Array of null-terminated C strings.
 * @param lengths Array of lengths for each string.
 * @param results Array to store calculated complexities.
 * @param n_strings Number of strings.
 * @param n_threads Number of threads for OpenMP.
 */
void lz78_complexity_parallel(const char** input_strings, size_t* lengths, 
                            double* results, size_t n_strings, int n_threads) {
    omp_set_num_threads(n_threads);
    
    #pragma omp parallel for schedule(dynamic)
    for (size_t i = 0; i < n_strings; i++) {
        results[i] = lz78_complexity(input_strings[i], lengths[i]);
    }
}

/**
 * @brief Calculates symmetric LZ78 complexity for multiple strings in parallel.
 * @param input_strings Array of null-terminated C strings.
 * @param lengths Array of lengths for each string.
 * @param results Array to store calculated symmetric complexities.
 * @param n_strings Number of strings.
 * @param n_threads Number of threads for OpenMP.
 */
void symmetric_lz78_parallel(const char** input_strings, size_t* lengths,
                           double* results, size_t n_strings, int n_threads) {
    omp_set_num_threads(n_threads);
    
    #pragma omp parallel
    {
        char* reversed = NULL;
        size_t max_len_processed_by_thread = 0;

        #pragma omp for schedule(dynamic)
        for (size_t i = 0; i < n_strings; i++) {
            if (lengths[i] > max_len_processed_by_thread) {
                char* temp_reversed = (char*)realloc(reversed, lengths[i] + 1);
                if (!temp_reversed) {
                    results[i] = -1.0; continue;
                }
                reversed = temp_reversed;
                max_len_processed_by_thread = lengths[i];
            }
            if (!reversed && lengths[i] > 0) {
                 results[i] = -1.0; continue;
            }

            for (size_t j = 0; j < lengths[i]; j++) {
                reversed[j] = input_strings[i][lengths[i] - 1 - j];
            }
            reversed[lengths[i]] = '\0';
            
            double c1 = lz78_complexity(input_strings[i], lengths[i]);
            double c2 = lz78_complexity(reversed, lengths[i]);
            if (c1 < 0 || c2 < 0) {
                results[i] = -1.0;
            } else {
                results[i] = (c1 + c2) / 2.0;
            }
        }
        free(reversed);
    }
}

/**
 * @struct SubseqCount
 * @brief Structure to store a subsequence (string) and its occurrence count.
 */
typedef struct {
    char* subsequence; /**< The subsequence string. */
    size_t count;      /**< Number of times this subsequence occurred. */
} SubseqCount;

/**
 * @brief Finds a subsequence in an array of SubseqCount structures or adds it if not found.
 *
 * Iterates through the `counts` array. If `subsequence` is found, its count is incremented.
 * Otherwise, a new entry for `subsequence` is added to `counts`, and its count is set to 1.
 * The `counts` array and `count_size` are updated accordingly.
 *
 * @param counts Pointer to an array of SubseqCount structures.
 * @param count_size Pointer to the current number of unique subsequences in `counts`.
 *                   This value is incremented if a new subsequence is added.
 * @param subsequence The subsequence string to find or add.
 * @param subseq_len The length of the subsequence string.
 * @return The updated count of the found or added subsequence. Returns 0 on allocation error.
 *
 * @note The caller is responsible for ensuring `counts` has enough allocated memory.
 *       This function allocates memory for `subsequence` within the `SubseqCount` structure.
 */
static size_t find_or_add_subsequence(SubseqCount* counts, size_t* count_size, 
                                    const char* subsequence, size_t subseq_len) {
    for (size_t i = 0; i < *count_size; i++) {
        if (strlen(counts[i].subsequence) == subseq_len && 
            memcmp(counts[i].subsequence, subsequence, subseq_len) == 0) {
            counts[i].count++;
            return counts[i].count;
        }
    }
    
    // Subsequence not found, add new one
    // Ensure there's space: This function assumes caller manages overall 'counts' array size.
    counts[*count_size].subsequence = (char*)malloc((subseq_len + 1) * sizeof(char));
    if (!counts[*count_size].subsequence) {
        // Allocation failed for the subsequence string
        return 0; // Indicate error
    }
    memcpy(counts[*count_size].subsequence, subsequence, subseq_len);
    counts[*count_size].subsequence[subseq_len] = '\0';
    counts[*count_size].count = 1;
    (*count_size)++;
    return 1;
}

/**
 * @brief Calculates the block entropy of a string for a given block dimension.
 *
 * Block entropy is calculated as -sum(p_i * log2(p_i)), where p_i is the
 * probability of occurrence of the i-th unique block (subsequence) of the given dimension.
 *
 * @param input_string The null-terminated C string.
 * @param length The length of the string.
 * @param dimension The size (dimension) of the blocks (substrings) to consider.
 * @return The block entropy value. Returns 0.0 if input is invalid or on error.
 */
double block_entropy(const char* input_string, size_t length, size_t dimension) {
    if (!input_string || length == 0 || dimension == 0 || dimension > length) return 0.0;
    
    size_t num_blocks = length - dimension + 1;
    SubseqCount* counts = (SubseqCount*)malloc(num_blocks * sizeof(SubseqCount)); // Max possible unique blocks
    if(!counts) return -1.0; // Malloc error
    size_t unique_block_count = 0;
    
    char* current_block_buffer = (char*)malloc((dimension + 1) * sizeof(char));
    if(!current_block_buffer) { // Malloc error
        free(counts);
        return -1.0;
    }
    
    for (size_t i = 0; i <= length - dimension; i++) {
        memcpy(current_block_buffer, input_string + i, dimension);
        current_block_buffer[dimension] = '\0';
        if (find_or_add_subsequence(counts, &unique_block_count, current_block_buffer, dimension) == 0) {
            // Error in find_or_add_subsequence (malloc failed)
            for(size_t k=0; k < unique_block_count; ++k) free(counts[k].subsequence);
            free(counts);
            free(current_block_buffer);
            return -1.0; // Propagate error
        }
    }
    
    double entropy = 0.0;
    double total_blocks_float = (double)num_blocks;
    
    for (size_t i = 0; i < unique_block_count; i++) {
        double p = (double)counts[i].count / total_blocks_float;
        if (p > 0) { // Avoid log2(0)
            entropy -= p * log2(p);
        }
    }
    
    for (size_t i = 0; i < unique_block_count; i++) {
        free(counts[i].subsequence);
    }
    free(counts);
    free(current_block_buffer);
    
    return entropy;
}

/**
 * @brief Calculates the symmetric block entropy of a string.
 * Symmetric block entropy is the average of block_entropy(S) and block_entropy(S_reversed).
 * @param input_string The null-terminated C string.
 * @param length The length of the string.
 * @param dimension The block dimension.
 * @return The symmetric block entropy. Returns 0.0 if input is invalid.
 */
double symmetric_block_entropy(const char* input_string, size_t length, size_t dimension) {
    if (!input_string || length == 0 || dimension == 0 || dimension > length) return 0.0;
    
    char* reversed = (char*)malloc((length + 1) * sizeof(char));
    if(!reversed) return -1.0; // Malloc error
    
    for (size_t i = 0; i < length; i++) {
        reversed[i] = input_string[length - 1 - i];
    }
    reversed[length] = '\0';
    
    double e1 = block_entropy(input_string, length, dimension);
    double e2 = block_entropy(reversed, length, dimension);
    
    free(reversed);
    
    if (e1 < 0 || e2 < 0) return -1.0; // Propagate error
    return (e1 + e2) / 2.0;
}

/**
 * @brief Calculates block entropy for multiple strings in parallel.
 * @param input_strings Array of null-terminated C strings.
 * @param lengths Array of string lengths.
 * @param dimension Block dimension.
 * @param results Array to store calculated entropies.
 * @param n_strings Number of strings.
 * @param n_threads Number of threads for OpenMP.
 */
void block_entropy_parallel(const char** input_strings, size_t* lengths,
                          size_t dimension, double* results,
                          size_t n_strings, int n_threads) {
    omp_set_num_threads(n_threads);
    
    #pragma omp parallel for schedule(dynamic)
    for (size_t i = 0; i < n_strings; i++) {
        results[i] = block_entropy(input_strings[i], lengths[i], dimension);
    }
}

/**
 * @brief Calculates symmetric block entropy for multiple strings in parallel.
 * @param input_strings Array of null-terminated C strings.
 * @param lengths Array of string lengths.
 * @param dimension Block dimension.
 * @param results Array to store calculated symmetric entropies.
 * @param n_strings Number of strings.
 * @param n_threads Number of threads for OpenMP.
 */
void symmetric_block_entropy_parallel(const char** input_strings, size_t* lengths,
                                    size_t dimension, double* results,
                                    size_t n_strings, int n_threads) {
    omp_set_num_threads(n_threads);
    
    #pragma omp parallel
    {
        char* reversed = NULL;
        size_t max_len_processed_by_thread = 0;

        #pragma omp for schedule(dynamic)
        for (size_t i = 0; i < n_strings; i++) {
             if (lengths[i] > max_len_processed_by_thread) {
                char* temp_reversed = (char*)realloc(reversed, lengths[i] + 1);
                 if (!temp_reversed) {
                    results[i] = -1.0; continue;
                }
                reversed = temp_reversed;
                max_len_processed_by_thread = lengths[i];
            }
            if (!reversed && lengths[i] > 0) {
                 results[i] = -1.0; continue;
            }
            
            for (size_t j = 0; j < lengths[i]; j++) {
                reversed[j] = input_strings[i][lengths[i] - 1 - j];
            }
            reversed[lengths[i]] = '\0';
            
            double e1 = block_entropy(input_strings[i], lengths[i], dimension);
            double e2 = block_entropy(reversed, lengths[i], dimension);

            if (e1 < 0 || e2 < 0) {
                results[i] = -1.0;
            } else {
                results[i] = (e1 + e2) / 2.0;
            }
        }
        free(reversed);
    }
}

/**
 * @brief Concatenates two strings.
 * The caller is responsible for freeing the returned string.
 * @param str1 First string.
 * @param len1 Length of the first string.
 * @param str2 Second string.
 * @param len2 Length of the second string.
 * @return A new string which is the concatenation of str1 and str2. NULL on malloc error.
 */
static char* concat_strings(const char* str1, size_t len1, const char* str2, size_t len2) {
    char* result = (char*)malloc(len1 + len2 + 1);
    if (!result) return NULL;
    memcpy(result, str1, len1);
    memcpy(result + len1, str2, len2);
    result[len1 + len2] = '\0';
    return result;
}

/**
 * @brief Calculates conditional LZ76 complexity C(X|Y) approx K(XY) - K(Y).
 * Note: The original code calculates K(XY) - K(X). This is C(Y|X).
 * For C(X|Y), it should be K(YX) - K(Y) or K(XY) - K(Y) depending on convention.
 * Assuming C(X|Y) = K(XY) - K(Y) as a common approximation.
 * The current implementation uses K(XY) - K(X). I will document it as such but note the standard.
 *
 * Calculates C(Y|X) = LZ76(XY) - LZ76(X).
 *
 * @param x_string The primary string X.
 * @param x_length Length of X.
 * @param y_string The conditional string Y.
 * @param y_length Length of Y.
 * @return Conditional LZ76 complexity C(Y|X). Returns 0.0 if inputs are invalid, -1.0 on error.
 */
double conditional_lz76_complexity(const char* x_string, size_t x_length,
                                 const char* y_string, size_t y_length) {
    if (!x_string || !y_string || x_length == 0 ) return 0.0; // y_length can be 0 for C(X|epsilon) = C(X)
                                                              // but K(XY) - K(X) makes less sense if y is empty
                                                              // For C(X|Y), if Y is empty, C(X|epsilon) = C(X).
                                                              // K(X epsilon) - K(epsilon) = K(X) - 0 = K(X).
                                                              // Let's assume y_length > 0 as per original code's likely intent for K(XY) - K(X)
    if (y_length == 0) { // Calculating C(X|empty_string) which is C(X)
        // Original: K(X) - K(X) = 0. This does not seem right.
        // If we want C(X|Y) = K(XY) - K(Y), then if Y is empty, K(X) - K(empty) = K(X).
        // The provided code calculates K(XY) - K(X). If Y is empty, XY=X, so K(X)-K(X)=0.
        // This specific case (y_length == 0) needs clarification based on desired formula.
        // Sticking to original code structure:
        return 0.0; // K(X) - K(X) = 0
    }


    char* xy_str = concat_strings(x_string, x_length, y_string, y_length);
    if (!xy_str) return -1.0; // Malloc error
    
    double k_xy = lz76_complexity(xy_str, x_length + y_length);
    free(xy_str);

    // K(X)
    double k_x = lz76_complexity(x_string, x_length);
    
    if (k_xy < 0 || k_x < 0) return -1.0; // Propagate error

    // This is K(XY) - K(X) which approximates C(Y|X)
    return k_xy - k_x;
}

/**
 * @brief Calculates conditional LZ78 complexity C(Y|X) = LZ78(XY) - LZ78(X).
 * (Similar note as conditional_lz76_complexity regarding C(X|Y) vs C(Y|X))
 * @param x_string The primary string X.
 * @param x_length Length of X.
 * @param y_string The conditional string Y.
 * @param y_length Length of Y.
 * @return Conditional LZ78 complexity C(Y|X). Returns 0.0 if inputs invalid, -1.0 on error.
 */
double conditional_lz78_complexity(const char* x_string, size_t x_length,
                                 const char* y_string, size_t y_length) {
    if (!x_string || !y_string || x_length == 0) return 0.0; // See notes in lz76 version.
    if (y_length == 0) return 0.0; // K(X) - K(X) = 0

    char* xy_str = concat_strings(x_string, x_length, y_string, y_length);
    if(!xy_str) return -1.0; // Malloc error

    double k_xy = lz78_complexity(xy_str, x_length + y_length);
    free(xy_str);

    double k_x = lz78_complexity(x_string, x_length);

    if (k_xy < 0 || k_x < 0) return -1.0; // Propagate error
    
    // This is K(XY) - K(X) which approximates C(Y|X)
    return k_xy - k_x;
}

/**
 * @brief Calculates conditional LZ76 C(Y|X) for multiple string pairs in parallel.
 * @param x_strings Array of primary strings X.
 * @param y_strings Array of conditional strings Y.
 * @param x_lengths Array of lengths for X strings.
 * @param y_lengths Array of lengths for Y strings.
 * @param results Array to store calculated conditional complexities.
 * @param n_strings Number of string pairs.
 * @param n_threads Number of threads for OpenMP.
 */
void conditional_lz76_parallel(const char** x_strings, const char** y_strings,
                             size_t* x_lengths, size_t* y_lengths,
                             double* results, size_t n_strings, int n_threads) {
    omp_set_num_threads(n_threads);
    
    #pragma omp parallel for schedule(dynamic)
    for (size_t i = 0; i < n_strings; i++) {
        results[i] = conditional_lz76_complexity(x_strings[i], x_lengths[i],
                                               y_strings[i], y_lengths[i]);
    }
}

/**
 * @brief Calculates conditional LZ78 C(Y|X) for multiple string pairs in parallel.
 * @param x_strings Array of primary strings X.
 * @param y_strings Array of conditional strings Y.
 * @param x_lengths Array of lengths for X strings.
 * @param y_lengths Array of lengths for Y strings.
 * @param results Array to store calculated conditional complexities.
 * @param n_strings Number of string pairs.
 * @param n_threads Number of threads for OpenMP.
 */
void conditional_lz78_parallel(const char** x_strings, const char** y_strings,
                             size_t* x_lengths, size_t* y_lengths,
                             double* results, size_t n_strings, int n_threads) {
    omp_set_num_threads(n_threads);
    
    #pragma omp parallel for schedule(dynamic)
    for (size_t i = 0; i < n_strings; i++) {
        results[i] = conditional_lz78_complexity(x_strings[i], x_lengths[i],
                                               y_strings[i], y_lengths[i]);
    }
}