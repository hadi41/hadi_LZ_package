#ifndef LZ_CORE_H
#define LZ_CORE_H

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @file lz_core.h
 * @brief Core Lempel-Ziv complexity and related entropy measures.
 *
 * This header file declares functions for calculating LZ76 and LZ78 complexities,
 * block entropy, and their conditional and symmetric variants. It also includes
 * parallelized versions of these computations for improved performance on
 * multi-core processors.
 */

// Core function
/**
 * @brief Calculates the LZ76 complexity of a single input string.
 *
 * LZ76 complexity is a measure of the compressibility of a string, based on
 * the number of distinct substrings encountered when parsing the string from left to right.
 *
 * @param input_string The null-terminated C string to analyze.
 * @param length The length of the input string (excluding the null terminator).
 * @return The LZ76 complexity value (typically normalized by string length or log(length)).
 */
double lz76_complexity(const char* input_string, size_t length);

// Parallel implementations
/**
 * @brief Calculates LZ76 complexity for multiple strings in parallel.
 *
 * This function processes an array of strings concurrently, distributing the
 * workload across the specified number of threads.
 *
 * @param input_strings An array of null-terminated C strings.
 * @param lengths An array of lengths corresponding to each input string.
 * @param results An array where the calculated complexity for each string will be stored.
 * @param n_strings The number of strings in the input arrays.
 * @param n_threads The number of threads to use for parallel computation.
 */
void lz76_complexity_parallel_original(const char** input_strings, size_t* lengths, 
                                     double* results, size_t n_strings, int n_threads);
/**
 * @brief Calculates symmetric LZ76 complexity for multiple strings in parallel.
 *
 * Symmetric LZ76 complexity considers the complexity of the string and its reverse.
 * This function processes an array of strings concurrently.
 *
 * @param input_strings An array of null-terminated C strings.
 * @param lengths An array of lengths corresponding to each input string.
 * @param results An array where the calculated symmetric complexity for each string will be stored.
 * @param n_strings The number of strings in the input arrays.
 * @param n_threads The number of threads to use for parallel computation.
 */
void symmetric_lz76_parallel_original(const char** input_strings, size_t* lengths,
                                    double* results, size_t n_strings, int n_threads);

// LZ78 functions
/**
 * @brief Calculates the LZ78 complexity of a single input string.
 *
 * LZ78 complexity is another measure of string complexity, based on building a
 * dictionary of phrases encountered during parsing.
 *
 * @param input_string The null-terminated C string to analyze.
 * @param length The length of the input string.
 * @return The LZ78 complexity value.
 */
double lz78_complexity(const char* input_string, size_t length);

/**
 * @brief Calculates the symmetric LZ78 complexity of a single input string.
 *
 * Symmetric LZ78 considers the complexity of the string and its reverse, using the LZ78 algorithm.
 *
 * @param input_string The null-terminated C string to analyze.
 * @param length The length of the input string.
 * @return The symmetric LZ78 complexity value.
 */
double symmetric_lz78_complexity(const char* input_string, size_t length);

/**
 * @brief Calculates LZ78 complexity for multiple strings in parallel.
 *
 * @param input_strings An array of null-terminated C strings.
 * @param lengths An array of lengths corresponding to each input string.
 * @param results An array where the calculated LZ78 complexity for each string will be stored.
 * @param n_strings The number of strings in the input arrays.
 * @param n_threads The number of threads to use for parallel computation.
 */
void lz78_complexity_parallel(const char** input_strings, size_t* lengths, 
                            double* results, size_t n_strings, int n_threads);
/**
 * @brief Calculates symmetric LZ78 complexity for multiple strings in parallel.
 *
 * @param input_strings An array of null-terminated C strings.
 * @param lengths An array of lengths corresponding to each input string.
 * @param results An array where the calculated symmetric LZ78 complexity for each string will be stored.
 * @param n_strings The number of strings in the input arrays.
 * @param n_threads The number of threads to use for parallel computation.
 */
void symmetric_lz78_parallel(const char** input_strings, size_t* lengths,
                           double* results, size_t n_strings, int n_threads);

// Block entropy functions
/**
 * @brief Calculates the block entropy of a string for a given block dimension.
 *
 * Block entropy measures the average information content per symbol in blocks of a fixed size.
 *
 * @param input_string The null-terminated C string to analyze.
 * @param length The length of the input string.
 * @param dimension The size of the blocks (substrings) to consider.
 * @return The block entropy value.
 */
double block_entropy(const char* input_string, size_t length, size_t dimension);

/**
 * @brief Calculates the symmetric block entropy of a string.
 *
 * Symmetric block entropy considers the block entropy of the string and its reverse.
 *
 * @param input_string The null-terminated C string to analyze.
 * @param length The length of the input string.
 * @param dimension The size of the blocks.
 * @return The symmetric block entropy value.
 */
double symmetric_block_entropy(const char* input_string, size_t length, size_t dimension);

/**
 * @brief Calculates block entropy for multiple strings in parallel.
 *
 * @param input_strings An array of null-terminated C strings.
 * @param lengths An array of lengths corresponding to each input string.
 * @param dimension The size of the blocks.
 * @param results An array where the calculated block entropy for each string will be stored.
 * @param n_strings The number of strings in the input arrays.
 * @param n_threads The number of threads to use for parallel computation.
 */
void block_entropy_parallel(const char** input_strings, size_t* lengths, 
                          size_t dimension, double* results, 
                          size_t n_strings, int n_threads);
/**
 * @brief Calculates symmetric block entropy for multiple strings in parallel.
 *
 * @param input_strings An array of null-terminated C strings.
 * @param lengths An array of lengths corresponding to each input string.
 * @param dimension The size of the blocks.
 * @param results An array where the calculated symmetric block entropy for each string will be stored.
 * @param n_strings The number of strings in the input arrays.
 * @param n_threads The number of threads to use for parallel computation.
 */
void symmetric_block_entropy_parallel(const char** input_strings, size_t* lengths,
                                    size_t dimension, double* results,
                                    size_t n_strings, int n_threads);

// Conditional complexity functions
/**
 * @brief Calculates the conditional LZ76 complexity of string X given string Y.
 *
 * This measures the complexity of X after the information in Y has been accounted for.
 * It's approximated by C(XY) - C(Y), where C is the LZ76 complexity.
 *
 * @param x_string The primary null-terminated C string (X).
 * @param x_length The length of x_string.
 * @param y_string The conditional null-terminated C string (Y).
 * @param y_length The length of y_string.
 * @return The conditional LZ76 complexity value.
 */
double conditional_lz76_complexity(const char* x_string, size_t x_length,
                                 const char* y_string, size_t y_length);
/**
 * @brief Calculates the conditional LZ78 complexity of string X given string Y.
 *
 * This measures the complexity of X using LZ78, after accounting for Y.
 * It's approximated by C(XY) - C(Y), where C is the LZ78 complexity.
 *
 * @param x_string The primary null-terminated C string (X).
 * @param x_length The length of x_string.
 * @param y_string The conditional null-terminated C string (Y).
 * @param y_length The length of y_string.
 * @return The conditional LZ78 complexity value.
 */
double conditional_lz78_complexity(const char* x_string, size_t x_length,
                                 const char* y_string, size_t y_length);

/**
 * @brief Calculates conditional LZ76 complexity for multiple pairs of strings in parallel.
 *
 * @param x_strings An array of primary null-terminated C strings.
 * @param y_strings An array of conditional null-terminated C strings.
 * @param x_lengths An array of lengths for x_strings.
 * @param y_lengths An array of lengths for y_strings.
 * @param results An array where the calculated conditional complexities will be stored.
 * @param n_strings The number of string pairs.
 * @param n_threads The number of threads to use for parallel computation.
 */
void conditional_lz76_parallel(const char** x_strings, const char** y_strings,
                             size_t* x_lengths, size_t* y_lengths,
                             double* results, size_t n_strings, int n_threads);
/**
 * @brief Calculates conditional LZ78 complexity for multiple pairs of strings in parallel.
 *
 * @param x_strings An array of primary null-terminated C strings.
 * @param y_strings An array of conditional null-terminated C strings.
 * @param x_lengths An array of lengths for x_strings.
 * @param y_lengths An array of lengths for y_strings.
 * @param results An array where the calculated conditional complexities will be stored.
 * @param n_strings The number of string pairs.
 * @param n_threads The number of threads to use for parallel computation.
 */
void conditional_lz78_parallel(const char** x_strings, const char** y_strings,
                             size_t* x_lengths, size_t* y_lengths,
                             double* results, size_t n_strings, int n_threads);

#ifdef __cplusplus
}
#endif

#endif // LZ_CORE_H