import numpy as np
from hadi_LZ_package import LZProcessor
import time
from typing import List, Tuple
import pandas as pd
import matplotlib.pyplot as plt
import os
import seaborn as sns

def generate_random_strings(n: int, length: int) -> List[str]:
    """Generate n random binary strings of given length"""
    return [''.join(np.random.choice(['0', '1'], length)) for _ in range(n)]

def run_benchmark(n_strings: int, string_length: int, n_threads: int) -> Tuple[float, float]:
    """Run benchmark and return time taken for regular and symmetric processing"""
    strings = generate_random_strings(n_strings, string_length)
    processor = LZProcessor(n_threads=n_threads)
    
    # Regular LZ76
    start_time = time.time()
    results = processor.process_strings(strings, symmetric=False)
    regular_time = time.time() - start_time
    
    # Symmetric LZ76
    start_time = time.time()
    sym_results = processor.process_strings(strings, symmetric=True)
    symmetric_time = time.time() - start_time
    
    return regular_time, symmetric_time

def main():
    # Test parameters
    string_lengths = [10, 30, 100]  # Different string lengths
    n_strings_list = [10_000, 100_000]  # Different numbers of strings
    n_threads_list = [1, 2, 4, 8]  # Test different thread counts
    
    # Results storage
    results = []
    
    try:
        # Run benchmarks
        for n_strings in n_strings_list:
            for string_length in string_lengths:
                base_regular_time = None
                base_symmetric_time = None
                
                for n_threads in n_threads_list:
                    print(f"Testing: {n_strings} strings of length {string_length} with {n_threads} threads")
                    regular_time, symmetric_time = run_benchmark(n_strings, string_length, n_threads)
                    
                    # Calculate speedup relative to single thread
                    if n_threads == 1:
                        base_regular_time = regular_time
                        base_symmetric_time = symmetric_time
                    
                    results.append({
                        'n_strings': n_strings,
                        'string_length': string_length,
                        'n_threads': n_threads,
                        'regular_time': regular_time,
                        'symmetric_time': symmetric_time,
                        'strings_per_second': n_strings / regular_time,
                        'symmetric_strings_per_second': n_strings / symmetric_time,
                        'speedup_regular': base_regular_time / regular_time if n_threads > 1 else 1.0,
                        'speedup_symmetric': base_symmetric_time / symmetric_time if n_threads > 1 else 1.0
                    })
        
        # Convert to DataFrame and save results
        df = pd.DataFrame(results)
        df.to_csv('benchmark_results.csv', index=False)
        
        # Print summary statistics
        print("\nBenchmark Summary:")
        print("=================")
        for n_strings in n_strings_list:
            for string_length in string_lengths:
                data = df[(df['string_length'] == string_length) & 
                         (df['n_strings'] == n_strings)]
                max_speedup = data['speedup_regular'].max()
                max_threads = data.loc[data['speedup_regular'].idxmax(), 'n_threads']
                print(f"\nConfiguration: {n_strings} strings of length {string_length}")
                print(f"Best speedup: {max_speedup:.2f}x with {max_threads} threads")
                print(f"Max throughput: {data['strings_per_second'].max():.0f} strings/second")
                print(f"Symmetric throughput: {data['symmetric_strings_per_second'].max():.0f} strings/second")
        
        # Create visualization
        plt.figure(figsize=(12, 6))
        
        # Plot speedup vs thread count
        plt.subplot(1, 2, 1)
        for length in string_lengths:
            data = df[df['string_length'] == length]
            plt.plot(data['n_threads'], data['speedup_regular'], 
                    marker='o', label=f'Length {length}')
        
        plt.xlabel('Number of Threads')
        plt.ylabel('Speedup')
        plt.title('Speedup vs Thread Count')
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        # Plot throughput
        plt.subplot(1, 2, 2)
        for length in string_lengths:
            data = df[df['string_length'] == length]
            plt.plot(data['n_threads'], data['strings_per_second'], 
                    marker='o', label=f'Length {length}')
        
        plt.xlabel('Number of Threads')
        plt.ylabel('Strings per Second')
        plt.title('Throughput vs Thread Count')
        plt.grid(True, alpha=0.3)
        plt.legend()
        
        plt.tight_layout()
        plt.savefig('benchmark_results.png', dpi=300, bbox_inches='tight')
        plt.close()
        
    except KeyboardInterrupt:
        print("\nBenchmark interrupted by user.")

if __name__ == '__main__':
    main() 