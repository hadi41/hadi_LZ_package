#include "lz_core.h"
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <omp.h>
#include <math.h>
#include <stdbool.h>

// Original LZ76 complexity calculation
double lz76_complexity(const char* input_string, size_t length) {
    if (!input_string || length == 0) return 0.0;
    
    char* parsed = (char*)malloc((length + 1) * sizeof(char));
    size_t parsed_len = 0;
    size_t pos = 0;
    size_t dictionary_size = 0;
    char* current_word = (char*)malloc((length + 1) * sizeof(char));
    size_t current_len = 0;
    
    parsed[0] = '\0';
    
    while (pos < length) {
        // Add new character to current_word
        current_word[current_len++] = input_string[pos++];
        current_word[current_len] = '\0';
        
        bool included = false;
        
        // Create temporary buffer for parsed + current_word[:-1]
        char* temp = (char*)malloc(length + 1);
        size_t temp_len = 0;
        
        // Copy parsed
        memcpy(temp, parsed, parsed_len);
        temp_len = parsed_len;
        
        // Add current_word[:-1] if it exists
        if (current_len > 1) {
            memcpy(temp + temp_len, current_word, current_len - 1);
            temp_len += current_len - 1;
        }
        temp[temp_len] = '\0';
        
        // Check for current_word in temp string
        for (size_t i = 0; i < temp_len; i++) {
            if (i + current_len <= temp_len) {
                if (memcmp(temp + i, current_word, current_len) == 0) {
                    included = true;
                    break;
                }
            }
        }
        
        free(temp);
        
        if (!included) {
            // Add current_word to parsed
            memcpy(parsed + parsed_len, current_word, current_len);
            parsed_len += current_len;
            parsed[parsed_len] = '\0';
            
            // Reset current_word
            current_len = 0;
            dictionary_size++;
        }
    }
    
    // Handle any remaining current_word
    if (current_len > 0) {
        dictionary_size++;
    }
    
    free(parsed);
    free(current_word);
    
    return dictionary_size * log2(length);
}

// Original parallel implementation
void lz76_complexity_parallel_original(const char** input_strings, size_t* lengths, 
                                     double* results, size_t n_strings, int n_threads) {
    omp_set_num_threads(n_threads);
    
    #pragma omp parallel for schedule(dynamic)
    for (size_t i = 0; i < n_strings; i++) {
        results[i] = lz76_complexity(input_strings[i], lengths[i]);
    }
}

// Original symmetric parallel implementation
void symmetric_lz76_parallel_original(const char** input_strings, size_t* lengths,
                                    double* results, size_t n_strings, int n_threads) {
    omp_set_num_threads(n_threads);
    
    #pragma omp parallel
    {
        char* reversed = NULL;
        size_t max_length = 0;
        
        #pragma omp for schedule(dynamic)
        for (size_t i = 0; i < n_strings; i++) {
            if (lengths[i] > max_length) {
                reversed = (char*)realloc(reversed, lengths[i] + 1);
                max_length = lengths[i];
            }
            
            for (size_t j = 0; j < lengths[i]; j++) {
                reversed[j] = input_strings[i][lengths[i] - 1 - j];
            }
            reversed[lengths[i]] = '\0';
            
            double c1 = lz76_complexity(input_strings[i], lengths[i]);
            double c2 = lz76_complexity(reversed, lengths[i]);
            results[i] = (c1 + c2) / 2.0;
        }
        
        free(reversed);
    }
}

// LZ78 complexity calculation
double lz78_complexity(const char* input_string, size_t length) {
    if (!input_string || length == 0) return 0.0;
    
    // Dictionary implemented as array of strings
    char** dictionary = (char**)malloc(length * sizeof(char*));
    size_t dict_size = 0;
    
    // Allocate memory for current word
    char* current_word = (char*)malloc((length + 1) * sizeof(char));
    size_t current_len = 0;
    size_t pos = 0;
    
    while (pos < length) {
        // Add new character to current_word
        current_word[current_len++] = input_string[pos++];
        current_word[current_len] = '\0';
        
        bool found = false;
        
        // Check if current_word is prefix of any dictionary word
        for (size_t i = 0; i < dict_size; i++) {
            size_t dict_word_len = strlen(dictionary[i]);
            if (dict_word_len >= current_len) {
                if (memcmp(dictionary[i], current_word, current_len) == 0) {
                    found = true;
                    break;
                }
            }
        }
        
        if (!found) {
            // Add to dictionary
            dictionary[dict_size] = (char*)malloc((current_len + 1) * sizeof(char));
            strcpy(dictionary[dict_size], current_word);
            dict_size++;
            current_len = 0;
        }
    }
    
    // Handle remaining current_word
    if (current_len > 0) {
        dict_size++;
    }
    
    // Clean up
    for (size_t i = 0; i < dict_size; i++) {
        free(dictionary[i]);
    }
    free(dictionary);
    free(current_word);
    
    return (double)dict_size;
}

// Symmetric LZ78 complexity
double symmetric_lz78_complexity(const char* input_string, size_t length) {
    if (!input_string || length == 0) return 0.0;
    
    // Allocate memory for reversed string
    char* reversed = (char*)malloc((length + 1) * sizeof(char));
    
    // Create reversed string
    for (size_t i = 0; i < length; i++) {
        reversed[i] = input_string[length - 1 - i];
    }
    reversed[length] = '\0';
    
    // Calculate both complexities
    double c1 = lz78_complexity(input_string, length);
    double c2 = lz78_complexity(reversed, length);
    
    free(reversed);
    
    return (c1 + c2) / 2.0;
}

// Parallel LZ78 complexity calculation
void lz78_complexity_parallel(const char** input_strings, size_t* lengths, 
                            double* results, size_t n_strings, int n_threads) {
    omp_set_num_threads(n_threads);
    
    #pragma omp parallel for schedule(dynamic)
    for (size_t i = 0; i < n_strings; i++) {
        results[i] = lz78_complexity(input_strings[i], lengths[i]);
    }
}

// Parallel symmetric LZ78 complexity calculation
void symmetric_lz78_parallel(const char** input_strings, size_t* lengths,
                           double* results, size_t n_strings, int n_threads) {
    omp_set_num_threads(n_threads);
    
    #pragma omp parallel
    {
        char* reversed = NULL;
        size_t max_length = 0;
        
        #pragma omp for schedule(dynamic)
        for (size_t i = 0; i < n_strings; i++) {
            if (lengths[i] > max_length) {
                reversed = (char*)realloc(reversed, lengths[i] + 1);
                max_length = lengths[i];
            }
            
            // Create reversed string
            for (size_t j = 0; j < lengths[i]; j++) {
                reversed[j] = input_strings[i][lengths[i] - 1 - j];
            }
            reversed[lengths[i]] = '\0';
            
            double c1 = lz78_complexity(input_strings[i], lengths[i]);
            double c2 = lz78_complexity(reversed, lengths[i]);
            results[i] = (c1 + c2) / 2.0;
        }
        
        free(reversed);
    }
}

// Structure to store subsequence counts
typedef struct {
    char* subsequence;
    size_t count;
} SubseqCount;

// Helper function to find or add subsequence
static size_t find_or_add_subsequence(SubseqCount* counts, size_t* count_size, 
                                    const char* subsequence, size_t subseq_len) {
    // Search for existing subsequence
    for (size_t i = 0; i < *count_size; i++) {
        if (strlen(counts[i].subsequence) == subseq_len && 
            memcmp(counts[i].subsequence, subsequence, subseq_len) == 0) {
            counts[i].count++;
            return counts[i].count;
        }
    }
    
    // Add new subsequence
    counts[*count_size].subsequence = (char*)malloc((subseq_len + 1) * sizeof(char));
    memcpy(counts[*count_size].subsequence, subsequence, subseq_len);
    counts[*count_size].subsequence[subseq_len] = '\0';
    counts[*count_size].count = 1;
    (*count_size)++;
    return 1;
}

double block_entropy(const char* input_string, size_t length, size_t dimension) {
    if (!input_string || length == 0 || dimension == 0 || dimension > length) return 0.0;
    
    // Allocate array for subsequence counts
    size_t max_subseqs = length - dimension + 1;
    SubseqCount* counts = (SubseqCount*)malloc(max_subseqs * sizeof(SubseqCount));
    size_t count_size = 0;
    
    // Temporary buffer for subsequences
    char* subseq = (char*)malloc((dimension + 1) * sizeof(char));
    
    // Count subsequences
    for (size_t i = 0; i <= length - dimension; i++) {
        memcpy(subseq, input_string + i, dimension);
        subseq[dimension] = '\0';
        find_or_add_subsequence(counts, &count_size, subseq, dimension);
    }
    
    // Calculate entropy
    double entropy = 0.0;
    double norm = (double)(length - dimension + 1);
    
    for (size_t i = 0; i < count_size; i++) {
        double p = counts[i].count / norm;
        entropy -= p * log2(p);
    }
    
    // Cleanup
    for (size_t i = 0; i < count_size; i++) {
        free(counts[i].subsequence);
    }
    free(counts);
    free(subseq);
    
    return entropy;
}

double symmetric_block_entropy(const char* input_string, size_t length, size_t dimension) {
    if (!input_string || length == 0) return 0.0;
    
    // Allocate memory for reversed string
    char* reversed = (char*)malloc((length + 1) * sizeof(char));
    
    // Create reversed string
    for (size_t i = 0; i < length; i++) {
        reversed[i] = input_string[length - 1 - i];
    }
    reversed[length] = '\0';
    
    // Calculate both entropies
    double e1 = block_entropy(input_string, length, dimension);
    double e2 = block_entropy(reversed, length, dimension);
    
    free(reversed);
    
    return (e1 + e2) / 2.0;
}

void block_entropy_parallel(const char** input_strings, size_t* lengths,
                          size_t dimension, double* results,
                          size_t n_strings, int n_threads) {
    omp_set_num_threads(n_threads);
    
    #pragma omp parallel for schedule(dynamic)
    for (size_t i = 0; i < n_strings; i++) {
        results[i] = block_entropy(input_strings[i], lengths[i], dimension);
    }
}

void symmetric_block_entropy_parallel(const char** input_strings, size_t* lengths,
                                    size_t dimension, double* results,
                                    size_t n_strings, int n_threads) {
    omp_set_num_threads(n_threads);
    
    #pragma omp parallel
    {
        char* reversed = NULL;
        size_t max_length = 0;
        
        #pragma omp for schedule(dynamic)
        for (size_t i = 0; i < n_strings; i++) {
            if (lengths[i] > max_length) {
                reversed = (char*)realloc(reversed, lengths[i] + 1);
                max_length = lengths[i];
            }
            
            // Create reversed string
            for (size_t j = 0; j < lengths[i]; j++) {
                reversed[j] = input_strings[i][lengths[i] - 1 - j];
            }
            reversed[lengths[i]] = '\0';
            
            double e1 = block_entropy(input_strings[i], lengths[i], dimension);
            double e2 = block_entropy(reversed, lengths[i], dimension);
            results[i] = (e1 + e2) / 2.0;
        }
        
        free(reversed);
    }
}

// Helper function to concatenate strings
static char* concat_strings(const char* str1, size_t len1, const char* str2, size_t len2) {
    char* result = (char*)malloc(len1 + len2 + 1);
    memcpy(result, str1, len1);
    memcpy(result + len1, str2, len2);
    result[len1 + len2] = '\0';
    return result;
}

double conditional_lz76_complexity(const char* x_string, size_t x_length,
                                 const char* y_string, size_t y_length) {
    if (!x_string || !y_string || x_length == 0 || y_length == 0) return 0.0;
    
    // Calculate K(xy)
    char* xy = concat_strings(x_string, x_length, y_string, y_length);
    double kxy = lz76_complexity(xy, x_length + y_length);
    
    // Calculate K(x)
    double kx = lz76_complexity(x_string, x_length);
    
    free(xy);
    return kxy - kx;
}

double conditional_lz78_complexity(const char* x_string, size_t x_length,
                                 const char* y_string, size_t y_length) {
    if (!x_string || !y_string || x_length == 0 || y_length == 0) return 0.0;
    
    // Calculate K(xy)
    char* xy = concat_strings(x_string, x_length, y_string, y_length);
    double kxy = lz78_complexity(xy, x_length + y_length);
    
    // Calculate K(x)
    double kx = lz78_complexity(x_string, x_length);
    
    free(xy);
    return kxy - kx;
}

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