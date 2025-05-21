#ifndef LZ_CORE_H
#define LZ_CORE_H

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

// Core function
double lz76_complexity(const char* input_string, size_t length);

// Parallel implementations
void lz76_complexity_parallel_original(const char** input_strings, size_t* lengths, 
                                     double* results, size_t n_strings, int n_threads);
void symmetric_lz76_parallel_original(const char** input_strings, size_t* lengths,
                                    double* results, size_t n_strings, int n_threads);

// LZ78 functions
double lz78_complexity(const char* input_string, size_t length);
double symmetric_lz78_complexity(const char* input_string, size_t length);
void lz78_complexity_parallel(const char** input_strings, size_t* lengths, 
                            double* results, size_t n_strings, int n_threads);
void symmetric_lz78_parallel(const char** input_strings, size_t* lengths,
                           double* results, size_t n_strings, int n_threads);

// Block entropy functions
double block_entropy(const char* input_string, size_t length, size_t dimension);
double symmetric_block_entropy(const char* input_string, size_t length, size_t dimension);
void block_entropy_parallel(const char** input_strings, size_t* lengths, 
                          size_t dimension, double* results, 
                          size_t n_strings, int n_threads);
void symmetric_block_entropy_parallel(const char** input_strings, size_t* lengths,
                                    size_t dimension, double* results,
                                    size_t n_strings, int n_threads);

// Conditional complexity functions
double conditional_lz76_complexity(const char* x_string, size_t x_length,
                                 const char* y_string, size_t y_length);
double conditional_lz78_complexity(const char* x_string, size_t x_length,
                                 const char* y_string, size_t y_length);

void conditional_lz76_parallel(const char** x_strings, const char** y_strings,
                             size_t* x_lengths, size_t* y_lengths,
                             double* results, size_t n_strings, int n_threads);
void conditional_lz78_parallel(const char** x_strings, const char** y_strings,
                             size_t* x_lengths, size_t* y_lengths,
                             double* results, size_t n_strings, int n_threads);

#ifdef __cplusplus
}
#endif

#endif // LZ_CORE_H