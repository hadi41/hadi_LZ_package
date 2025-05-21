#ifndef LZ_EXHAUSTIVE_H
#define LZ_EXHAUSTIVE_H

#include <stddef.h> // For size_t

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Calculates the LZ76 phrase count for all 2^L binary strings of length L.
 * Results are stored in the provided output array.
 *
 * @param L The length of the binary strings.
 * @param phrase_counts_output A pre-allocated array of size (1 << L) (i.e., 2^L).
 *                             The phrase count for the string represented by the integer index `i`
 *                             (when `i` is written in `L` binary digits) will be stored at `phrase_counts_output[i]`.
 */
void lz76_exhaustive_generate(int L, int* phrase_counts_output);

/**
 * Calculates the distribution of LZ76 phrase counts for all 2^L binary strings of length L.
 *
 * @param L The length of the binary strings.
 * @param counts_by_complexity A pre-allocated array where counts_by_complexity[c] will store
 *                             the number of strings having phrase count c.
 * @param max_complexity_to_track The size of the counts_by_complexity array.
 *                                Complexities >= (max_complexity_to_track - 1) will be grouped in the last bin.
 * @param num_threads The number of OpenMP threads to use for parallelization. If 0 or 1, runs serially.
 */
void lz76_exhaustive_distribution(int L, long long* counts_by_complexity, int max_complexity_to_track, int num_threads);

#ifdef __cplusplus
}
#endif

#endif // LZ_EXHAUSTIVE_H 