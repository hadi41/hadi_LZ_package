import sys
import os
import time
import numpy as np

# Adjust sys.path
_project_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _project_root_dir not in sys.path:
    sys.path.insert(0, _project_root_dir)

try:
    from hadi_LZ_package.lz_exhaustive_wrapper import LZExhaustiveCalculator
except ImportError as e:
    print(f"ERROR: Could not import necessary modules: {e}")
    print(f"Sys.path: {sys.path}")
    sys.exit(1)

def confirm_large_L(L_large: int) -> bool:
    """Ask for user confirmation when L is large."""
    if L_large > 30:
        print(f"\nWARNING: L={L_large} is very large. This will process 2^{L_large} strings.")
        print(f"This computation may take a very long time and use significant system resources.")
        while True:
            response = input("Do you want to proceed? (y/n): ").lower().strip()
            if response in ['y', 'yes']:
                return True
            elif response in ['n', 'no']:
                return False
            print("Please answer 'y' or 'n'.")
    return True

def run_large_L_distribution_only(L_large=24, num_threads: int | None = None):
    print(f"\n--- LZ76 Exhaustive Distribution Only for L={L_large} (Threads: {num_threads if num_threads is not None else 'default'}) ---")
    print(f"(Verification against lz_core.c is not feasible for this L value due to 2^{L_large} individual computations)")
    num_total_strings = 1 << L_large
    print(f"Total strings to process implicitly: {num_total_strings}")

    # Check for large L and get confirmation
    if not confirm_large_L(L_large):
        print("Operation cancelled by user.")
        return

    exhaustive_calculator = LZExhaustiveCalculator()
    
    # Max possible LZ76 phrase count for string of length L is L+1.
    # So, array needs to be at least size L+2 to store counts for complexities 0 to L+1.
    max_complexity_to_track = L_large + 5 # Python wrapper also defaults to L+5

    print(f"Running lz76_exhaustive_distribution(L={L_large}, max_complexity_track={max_complexity_to_track}, num_threads={num_threads if num_threads is not None else 'default'})...")
    start_time = time.perf_counter()
    try:
        # Pass suppress_warnings=True since we already have our own confirmation mechanism
        distribution = exhaustive_calculator.get_lz76_complexity_distribution(L_large, max_complexity_to_track, num_threads=num_threads, suppress_warnings=True)
        if distribution is None:
            print("  ERROR: Failed to get distribution for large L.")
            return
    except Exception as e:
        print(f"  ERROR calculating distribution for L={L_large}: {e}")
        return
    time_taken = time.perf_counter() - start_time
    print(f"  lz76_exhaustive_distribution for L={L_large} completed in {time_taken:.4f} seconds.")
    if num_total_strings > 0:
         print(f"  Effective avg time per string (amortized): {time_taken/num_total_strings:.12f}s")

    print(f"\n  LZ76 Phrase Count Distribution for L={L_large}:")
    for complexity_val, count in enumerate(distribution):
        if count > 0:
            print(f"    Complexity {complexity_val}: {count} strings")
    print("  (Note: Last bin is an overflow for complexities >= its index)")

if __name__ == "__main__":
    L_dist_large = 24  # Default value
    threads_for_dist = None  # Default to os.cpu_count() in wrapper
    
    if len(sys.argv) > 1:
        try:
            L_dist_large = int(sys.argv[1])
            if not (1 <= L_dist_large <= 40):  # Increased max L to 40
                print("Please choose L between 1 and 40.")
                sys.exit(1)
            if len(sys.argv) > 2:
                threads_for_dist = int(sys.argv[2])
                if threads_for_dist <= 0:
                    print("Number of threads must be positive.")
                    sys.exit(1)
        except ValueError:
            print("Usage: python run_large_lz_distribution.py [L_value (1-40)] [num_threads (optional)]")
            sys.exit(1)
    else:
        print("Usage: python run_large_lz_distribution.py [L_value (1-40)] [num_threads (optional)]")
        print("Running with default L=24...")
    
    run_large_L_distribution_only(L_large=L_dist_large, num_threads=threads_for_dist) 