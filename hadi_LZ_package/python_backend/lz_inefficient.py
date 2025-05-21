'''Pure Python implementations of LZ76, LZ78, and related complexity measures.

This module provides reference implementations for:
- LZ78 complexity and its symmetric variant.
- LZ76 complexity and its symmetric variant.
- Block entropy.
- Conditional LZ76 and LZ78 complexities.

These functions are generally not optimized for performance and serve as a baseline
or for educational purposes. For performance-critical applications, the C-backed
wrappers in this package should be preferred.

Helper functions for generating random binary strings are also included.
'''
import numpy as np

def LZ78(input_string: str):
    """Calculates LZ78 complexity and the dictionary for a given string.

    The LZ78 algorithm parses the string, adding new phrases to a dictionary.
    A phrase is new if it's formed by a previously seen phrase plus one new character,
    or if it's a single new character not yet seen as a prefix.
    The implementation here checks if the `current_word` is a prefix of any existing
    dictionary word to decide if it should continue extending `current_word`.

    Args:
        input_string: The string to analyze.

    Returns:
        A tuple containing:
            - dictionary (list[str]): The list of phrases in the LZ78 dictionary.
            - complexity (int): The number of phrases in the dictionary (LZ78 complexity).
    """
    n = len(input_string)
    if n == 0:
        return [], 0
        
    dictionary = []
    current_word = ''
    remaining_string = input_string
    
    while remaining_string != '':
        current_word += remaining_string[0]
        remaining_string = remaining_string[1:]
        current_word_len = len(current_word)
        
        # Check if the current_word is a prefix of any word already in the dictionary.
        # If it is, we continue extending current_word with the next character.
        is_prefix_of_existing_word = False
        for existing_word_in_dict in dictionary: 
            if len(existing_word_in_dict) >= current_word_len:
                if existing_word_in_dict.startswith(current_word):
                    is_prefix_of_existing_word = True
                    break
        
        # If current_word is NOT a prefix of any existing dictionary word, 
        # it means this current_word is a new phrase.
        if not is_prefix_of_existing_word:
            dictionary.append(current_word)
            current_word = '' # Reset for the next phrase
            
    # If the loop finishes and current_word is not empty, 
    # it means the last part of the string formed a phrase that was being extended.
    if current_word != '':
        dictionary.append(current_word)
        
    return dictionary, len(dictionary)

def symmetric_LZ78(input_string: str) -> float:
    """Calculates the symmetric LZ78 complexity.

    This is the average of the LZ78 complexity of the input string
    and its reverse.

    Args:
        input_string: The string to analyze.

    Returns:
        The symmetric LZ78 complexity value.
    """
    if not input_string:
        return 0.0
    c1 = LZ78(input_string)[1]
    c2 = LZ78(input_string[::-1])[1]
    return (c1 + c2) / 2.0

def mutual_LZ78(input_string: str) -> float:
    """Calculates a form of mutual information using LZ78 complexity.
    
    This is defined as (C(S1) + C(S2) - C(S1S2)) / (2 * C(S1S2)) * log(N),
    where S1 is the first half of the string, S2 is the second half,
    S1S2 is the full string, C is LZ78 complexity, and N is string length.
    Note: The utility or standard interpretation of this specific formula should be verified.

    Args:
        input_string: The string to analyze.

    Returns:
        The calculated mutual LZ78 value. Returns 0.0 for empty or very short strings.
    """
    n = len(input_string)
    if n < 2: # Need at least two characters to split
        return 0.0

    l2 = n // 2
    s1 = input_string[:l2]
    s2 = input_string[l2:]

    c1 = LZ78(s1)[1]
    c2 = LZ78(s2)[1]
    c_total = LZ78(input_string)[1]

    if c_total == 0: # Avoid division by zero
        return 0.0
        
    # The formula seems to aim for a normalized difference, scaled by log(n).
    # (K(S1) + K(S2) - K(S1S2)) is related to information distance if K is Kolmogorov complexity.
    # The division by 2*c_total might be a normalization factor.
    mutual_info_val = (c1 + c2 - c_total) / (2 * c_total) * np.log(n) # Using natural log as often in info theory
    return mutual_info_val

def generate_random_string(length: int, alphabet: list = ['0','1']) -> str:
    """Generates a random string of a given length from a specified alphabet.

    Args:
        length: The desired length of the string.
        alphabet: A list of characters to choose from. Defaults to ['0', '1'].

    Returns:
        A randomly generated string.
    """
    if length <= 0:
        return ""
    if not alphabet:
        raise ValueError("Alphabet cannot be empty for generating random string.")
    return ''.join(np.random.choice(alphabet, length))

def generate_random_string_ensemble(num_strings: int, string_length: int, alphabet: list = ['0','1']) -> list[str]:
    """Generates an ensemble (list) of random strings.

    Args:
        num_strings: The number of random strings to generate.
        string_length: The length of each random string.
        alphabet: The alphabet to use for generating strings. Defaults to ['0', '1'].

    Returns:
        A list of randomly generated strings.
    """
    return [generate_random_string(string_length, alphabet) for _ in range(num_strings)]

def LZ76(input_string: str) -> float:
    """Calculates LZ76 complexity for a given string.

    The LZ76 algorithm parses the string, adding a new phrase to its dictionary
    whenever the current `current_word` (formed by appending the next character)
    is not found as a substring in `parsed_text + current_word[:-1]` (i.e., previously parsed text plus
    the current word without its newest character).
    The complexity is often reported as `dictionary_size * log2(n)`.

    Args:
        input_string: The string to analyze.

    Returns:
        The LZ76 complexity value. Returns 0.0 for an empty string.
    """
    n = len(input_string)
    if n == 0:
        return 0.0
        
    current_word = ''
    parsed_text_history = '' # Stores concatenated phrases already added to the dictionary
    remaining_string = input_string
    dictionary_size = 0
    
    while remaining_string != '':
        next_character = remaining_string[0]
        current_word += next_character
        remaining_string = remaining_string[1:]
        
        current_word_len = len(current_word)
        
        # The search space for LZ76 is the history of parsed phrases plus the current word without its last character.
        search_space = parsed_text_history + current_word[:-1]
        
        # Check if current_word is a substring of the search_space.
        # The original code had a loop: for i in range(0, len(parsed)): if (parsed + current_word[:-1])[i:i+l] == current_word:
        # This is equivalent to checking if current_word is in (parsed + current_word[:-1]).
        is_substring_in_history = False
        if current_word in search_space:
            is_substring_in_history = True
            
        if not is_substring_in_history:
            dictionary_size += 1
            parsed_text_history += current_word # Add the new phrase to history
            current_word = '' # Reset for the next phrase
            
    # If the loop finishes and current_word is not empty, it forms the last phrase.
    if current_word != '':
        dictionary_size += 1
        
    # Common normalization for LZ76 complexity.
    # If n=1, log2(1)=0. If n=0, already returned 0.0. For n>1, log2(n)>0.
    if n <= 1: # Avoid log2(1) or log2(0) issues, though n=0 is caught.
        return float(dictionary_size) # For very short strings, raw count might be more informative.
    
    complexity = np.log2(n) * dictionary_size
    return complexity

def symmetric_LZ76(input_string: str) -> float:
    """Calculates the symmetric LZ76 complexity.

    Average of LZ76(string) and LZ76(reversed_string).

    Args:
        input_string: The string to analyze.

    Returns:
        The symmetric LZ76 complexity.
    """
    if not input_string:
        return 0.0
    c1 = LZ76(input_string)
    c2 = LZ76(input_string[::-1])
    return (c1 + c2) / 2.0

def block_entropy(input_string: str, dimension: int) -> float:
    """Calculates the block entropy of a sequence for a given block dimension.

    Block entropy is H_d = - sum(p_i * log2(p_i)), where p_i is the probability
    of the i-th unique block of `dimension` characters.

    Args:
        input_string: The sequence (string) to analyze.
        dimension: The size of the blocks (substrings).

    Returns:
        The block entropy value. Returns 0.0 if dimension is invalid or too large.
    """
    n = len(input_string)
    if dimension <= 0 or dimension > n:
        return 0.0

    encountered_blocks = {}
    num_blocks_total = n - dimension + 1
    
    for i in range(num_blocks_total):
        sub_sequence = input_string[i : i + dimension]
        encountered_blocks[sub_sequence] = encountered_blocks.get(sub_sequence, 0) + 1
            
    if num_blocks_total == 0: # Should not happen if dimension <= n
        return 0.0

    entropy = 0.0
    for count in encountered_blocks.values():
        probability = count / num_blocks_total
        if probability > 0: # Avoid log2(0)
            entropy -= probability * np.log2(probability)
            
    return entropy


def conditional_LZ76(x_string: str, y_string: str) -> float:
    """Calculates conditional complexity K(Y|X) ~ LZ76(XY) - LZ76(X).

    Args:
        x_string: The conditioning string (X).
        y_string: The primary string (Y) whose complexity given X is sought.

    Returns:
        The conditional LZ76 complexity K(Y|X).
        Returns 0.0 if either string is empty, as K(empty) is often taken as 0,
        leading to K(Y|empty) = K(Y) or K(empty|X) = 0.
        The formula K(XY)-K(X) gives K(Y) if X is empty (assuming K(empty)=0).
        If Y is empty, it gives K(X)-K(X)=0.
    """
    if not x_string: # K(Y|empty) = K(Y)
        return LZ76(y_string)
    if not y_string: # K(empty|X) = 0 by this formula
        return 0.0
    
    xy_string = x_string + y_string
    k_xy = LZ76(xy_string)
    k_x = LZ76(x_string)
    
    return k_xy - k_x

def conditional_LZ78(x_string: str, y_string: str) -> float:
    """Calculates conditional complexity K(Y|X) ~ LZ78(XY) - LZ78(X).

    Args:
        x_string: The conditioning string (X).
        y_string: The primary string (Y).

    Returns:
        The conditional LZ78 complexity K(Y|X).
        Similar logic for empty strings as in `conditional_LZ76`.
    """
    if not x_string: # K(Y|empty) = K(Y)
        return float(LZ78(y_string)[1]) # LZ78 returns (dict, size)
    if not y_string: # K(empty|X) = 0
        return 0.0
    
    xy_string = x_string + y_string
    k_xy = LZ78(xy_string)[1]
    k_x = LZ78(x_string)[1]
    
    return float(k_xy - k_x)
    

if __name__ == '__main__':
    print("--- Pure Python LZ Implementations Example ---")
    s1 = '0100101011'
    s2 = 'ababababab'
    s3 = 'randomstring'

    print(f"\nLZ78('{s1}'): phrases={LZ78(s1)[0]}, complexity={LZ78(s1)[1]}")
    print(f"Symmetric LZ78('{s1}'): {symmetric_LZ78(s1):.3f}")
    
    print(f"\nLZ76('{s2}'): {LZ76(s2):.3f}")
    print(f"Symmetric LZ76('{s2}'): {symmetric_LZ76(s2):.3f}")

    print(f"\nBlock Entropy of '{s1}' (dim=2): {block_entropy(s1, 2):.3f}")
    print(f"Block Entropy of '{s2}' (dim=3): {block_entropy(s2, 3):.3f}")

    x = "00000"
    y = "11111"
    print(f"\nConditional LZ76 K('{y}'|'{x}'): {conditional_LZ76(x,y):.3f}")
    print(f"Conditional LZ78 K('{y}'|'{x}'): {conditional_LZ78(x,y):.3f}")

    print(f"\nMutual LZ78 for '{s1+s2}': {mutual_LZ78(s1+s2):.3f}")

    rand_str = generate_random_string(20)
    print(f"\nRandom string (len 20): {rand_str}")
    print(f"LZ76 for random string: {LZ76(rand_str):.3f}")

    # Test empty string cases
    print("\n--- Empty String Tests ---")
    print(f"LZ78(''): {LZ78('')}")
    print(f"LZ76(''): {LZ76('')}")
    print(f"Symmetric LZ78(''): {symmetric_LZ78('')}")
    print(f"Symmetric LZ76(''): {symmetric_LZ76('')}")
    print(f"Block Entropy('', dim=1): {block_entropy(' ', 1)}") # block_entropy needs non-empty
    print(f"Conditional LZ76('abc', ''): {conditional_LZ76('abc', '')}")
    print(f"Conditional LZ76('', 'abc'): {conditional_LZ76('', 'abc')}")
    print(f"Conditional LZ78('abc', ''): {conditional_LZ78('abc', '')}")
    print(f"Conditional LZ78('', 'abc'): {conditional_LZ78('', 'abc')}")
