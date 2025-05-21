import numpy as np

def LZ78(input_string):
    n = len(input_string)
    dictionary = []
    current_word = ''
    remaining = input_string
    while remaining != '':
        current_word += remaining[0]
        remaining = remaining[1:]
        l = len(current_word)
        check = False
        for word in dictionary: 
            if len(word) >= l:
                if word[:l] == current_word:
                    check = True
                    break
        if check == False:
            dictionary.append(current_word)
            current_word = ''
    if current_word != '':
        dictionary.append(current_word)
    return dictionary, len(dictionary)

def symmetric_LZ78(input_string):
    c1 = np.array(LZ78(input_string)[1])
    c2 = np.array(LZ78(input_string[::-1])[1])
    return (c1 + c2) / 2

def mutual_LZ78(input_string):
    l2 = len(input_string) // 2
    # print(type(input_string[:l2]), input_string[:l2])
    c1 = np.array(LZ78(input_string[:l2])[1])
    c2 = np.array(LZ78(input_string[l2:])[1])
    c_total = np.array(LZ78(input_string)[1])
    return (c1 + c2 - c_total) / (2 * c_total) * np.log(len(input_string))

def generate_random_string(n):
    return ''.join(np.random.choice(['0','1'], n))

def generate_random_string_ensemble(n, l):
    return [generate_random_string(l) for _ in range(n)]

def LZ76(input_string):
    n= len(input_string)
    current_word = ''
    parsed = ''
    remaining = input_string
    dictionary_size = 0
    while remaining != '':
        new_character = remaining[0]
        current_word += new_character
        remaining = remaining[1:]
        l = len(current_word)
        included = False
        # print(parsed, current_word)
        for i in range(0, len(parsed)):
            if (parsed + current_word[:-1])[i:i+l] == current_word:
                # print(parsed + current_word[:-1], current_word, i)
                included = True
                break
        if included == False:
            dictionary_size += 1
            # print('added')
            parsed += current_word
            current_word = ''
    if current_word != '':
        dictionary_size += 1
    complexity = np.log2(n) * dictionary_size
    return complexity

def symmetric_LZ76(input_string):
    c1 = LZ76(input_string)
    c2 = LZ76(input_string[::-1])
    return (c1 + c2) / 2

def block_entropy(dimension, sequence):
    encountered = {}
    for i in range(0, len(sequence) - dimension + 1):
        subseq = sequence[i:i+dimension]
        if subseq in encountered.keys():
            encountered[subseq] += 1
        else:
            encountered[subseq] = 1
    norm = len(sequence) - dimension + 1
    return -np.sum([p/norm * np.log2(p/norm) for p in encountered.values()])

import numpy as np

# ... existing functions ...

def conditional_LZ76(x_string, y_string):
    """Calculate conditional complexity K(y|x) using LZ76."""
    if not x_string or not y_string:
        return 0.0
    
    # Calculate K(xy)
    xy_string = x_string + y_string
    kxy = LZ76(xy_string)
    
    # Calculate K(x)
    kx = LZ76(x_string)
    
    return kxy - kx

def conditional_LZ78(x_string, y_string):
    """Calculate conditional complexity K(y|x) using LZ78."""
    if not x_string or not y_string:
        return 0.0
    
    # Calculate K(xy)
    xy_string = x_string + y_string
    kxy = LZ78(xy_string)[1]  # LZ78 returns (dictionary, size)
    
    # Calculate K(x)
    kx = LZ78(x_string)[1]
    
    return kxy - kx
    


if __name__ == '__main__':
    print(symmetric_LZ78('0100101011'))
    print(LZ78('01000110110000010100111001011101'))
    print(mutual_LZ78('0100101011011001'))
