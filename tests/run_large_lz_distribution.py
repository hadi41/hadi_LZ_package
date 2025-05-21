'''Runs LZ76 exhaustive complexity distribution for large binary string lengths (L).

This script utilizes the `LZExhaustiveCalculator` to compute and display the
distribution of LZ76 phrase counts for all 2^L binary strings of a specified
length `L`. It is designed for testing and benchmarking the performance of the
C backend for large `L` values, which can be computationally intensive.

The script includes:
- Command-line argument parsing for `L` and the number of threads.
- A confirmation prompt for very large `L` values due to long computation times.
- Timing of the distribution calculation.
- Output of the resulting complexity distribution.

Usage:
    python run_large_lz_distribution.py [L_value] [num_threads (optional)]

Example:
    python run_large_lz_distribution.py 24 8
    python run_large_lz_distribution.py 20
'''
import sys
import os
import time
import numpy as np

# --- Path Setup --- 
# Add the project root to sys.path to allow importing from hadi_LZ_package
_project_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _project_root_dir not in sys.path:
    sys.path.insert(0, _project_root_dir)

try:
    from hadi_LZ_package.lz_exhaustive_wrapper import LZExhaustiveCalculator
except ImportError as e:
    print(f"ERROR: Could not import LZExhaustiveCalculator. {e}")
    print("Ensure that hadi_LZ_package is installed or properly added to your PYTHONPATH.")
    print(f"Current sys.path: {sys.path}")
    sys.exit(1)

def confirm_large_L(L_value: int) -> bool:
    """Asks for user confirmation if the provided L is very large.

    Args:
        L_value: The length L of binary strings.

    Returns:
        True if the user confirms to proceed or if L is not considered very large,
        False if the user cancels.
    """
    # Define a threshold for when to ask for confirmation.
    # L > 28 implies >268 million strings, L > 30 is over a billion.
    confirmation_threshold = 28 
    if L_value > confirmation_threshold:
        print(f"\nWARNING: L={L_value} is very large. This will process 2^{L_value} strings.")
        print(f"This computation may take a very long time and consume significant system resources.")
        while True:
            try:
                response = input("Do you want to proceed? (yes/no): ").lower().strip()
                if response in ['y', 'yes']:
                    return True
                elif response in ['n', 'no']:
                    return False
                print("Please answer 'yes' or 'no'.")
            except EOFError: # Handle cases where input stream is closed (e.g., in automated tests)
                print("No input received, cancelling operation for large L.")
                return False
    return True # Proceed if L is not above the threshold

def run_large_L_distribution_only(L_target: int, num_threads: int | None = None):
    """Runs the LZ76 exhaustive distribution calculation for a given L and number of threads.

    Args:
        L_target: The length L of binary strings for which to calculate the distribution.
        num_threads (int | None, optional): The number of threads to request for the C backend.
                                          If None, the C backend or wrapper's default (e.g., os.cpu_count()) will be used.
    """
    print(f"\n--- LZ76 Exhaustive Distribution for L={L_target} (Threads: {num_threads if num_threads is not None else 'default'}) ---")
    
    num_total_strings = 1 << L_target
    print(f"Calculating distribution for 2^{L_target} = {num_total_strings:,} strings.")

    # Check for large L and get confirmation from the user.
    if not confirm_large_L(L_target):
        print("Operation cancelled by user due to large L.")
        return

    try:
        exhaustive_calculator = LZExhaustiveCalculator()
    except Exception as e_init:
        print(f"ERROR: Could not initialize LZExhaustiveCalculator: {e_init}")
        return
    
    # Determine max_complexity_to_track. LZ76 phrases for length L can go up to L or L+1.
    # The calculator's default is L+5, which is usually sufficient.
    # We can pass None to use the wrapper's default or specify one.
    # For very large L, this array itself is small, so default is fine.
    max_complexity_to_track = L_target + 5 

    print(f"Running lz76_exhaustive_distribution(L={L_target}, max_complexity_track={max_complexity_to_track}, num_threads={num_threads if num_threads is not None else 'wrapper default'})...")
    start_time = time.perf_counter()
    distribution = None # Initialize to ensure it's defined
    try:
        # suppress_warnings=True in the call to the wrapper because this script has its own confirmation.
        distribution = exhaustive_calculator.get_lz76_complexity_distribution(
            L_target, 
            max_complexity_to_track=max_complexity_to_track, 
            num_threads=num_threads, 
            suppress_warnings=True
        )
        if distribution is None:
            print("  ERROR: Failed to get distribution. The calculator returned None.")
            return
    except ValueError as ve:
        print(f"  ERROR: Invalid parameter for L={L_target}: {ve}")
        return
    except MemoryError as me:
        print(f"  ERROR: Memory allocation failed during calculation for L={L_target}: {me}")
        return
    except Exception as e_calc:
        print(f"  ERROR during distribution calculation for L={L_target}: {e_calc}")
        return
    
    time_taken = time.perf_counter() - start_time
    print(f"  lz76_exhaustive_distribution for L={L_target} completed in {time_taken:.4f} seconds.")
    
    if num_total_strings > 0 and time_taken > 0:
         # This is an effective amortized time, as the C code iterates 2^L times internally.
         print(f"  Effective average time per implicitly processed string: {time_taken/num_total_strings:.12e}s") 

    print(f"\n  LZ76 Phrase Count Distribution for L={L_target}:")
    non_zero_counts = 0
    for complexity_val, count in enumerate(distribution):
        if count > 0:
            print(f"    Complexity {complexity_val}: {count:,} strings")
            non_zero_counts +=1
    if non_zero_counts == 0:
        print("    No strings found for any complexity (distribution array is all zeros).")
    print(f"  (Note: Last bin [index {max_complexity_to_track-1}] is an overflow for complexities >= its index)")

if __name__ == "__main__":
    L_default = 20 # Default L if not provided, smaller for quicker default run.
    L_val_arg = L_default
    threads_arg = None 
    
    if len(sys.argv) > 1:
        try:
            L_val_arg = int(sys.argv[1])
            # Set a practical upper limit for L that can be run via script.
            # User will be warned by confirm_large_L for L > 28.
            if not (1 <= L_val_arg <= 35): 
                print(f"ERROR: Please choose L between 1 and 35. Provided: {L_val_arg}")
                sys.exit(1)
            if len(sys.argv) > 2:
                threads_arg = int(sys.argv[2])
                if threads_arg <= 0:
                    print("ERROR: Number of threads must be a positive integer.")
                    sys.exit(1)
        except ValueError:
            print("Usage: python run_large_lz_distribution.py [L_value (1-35)] [num_threads (optional)]")
            sys.exit(1)
    else:
        print(f"Usage: python run_large_lz_distribution.py [L_value (1-35)] [num_threads (optional)]")
        print(f"No L_value provided, running with default L={L_default}...")
    
    run_large_L_distribution_only(L_target=L_val_arg, num_threads=threads_arg) 