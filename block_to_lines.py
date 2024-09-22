from config import box_width, num_lines, char_widths, approximate_word_length, font_width, valid_char_set, max_char_per_line

# Define ANSI escape codes for colors
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"

def replace_invalid_chars(word, valid_char_set, line_number=None):
    new_word = []
    for char in word:
        if char not in valid_char_set:
            if char.lower() in valid_char_set:
                new_word.append(char.lower())
                if line_number is not None:
                    print(f"{YELLOW}Warning: word '{word}' on line {line_number} is replaced by '{''.join(new_word)}' because of invalid character '{char}'{RESET}")
                else:
                    print(f"{YELLOW}Warning: word '{word}' is replaced by '{''.join(new_word)}' because of invalid character '{char}'{RESET}")
            elif char.upper() in valid_char_set:
                new_word.append(char.upper())
                if line_number is not None:
                    print(f"{YELLOW}Warning: word '{word}' on line {line_number} is replaced by '{''.join(new_word)}' because of invalid character '{char}'{RESET}")
                else:
                    print(f"{YELLOW}Warning: word '{word}' is replaced by '{''.join(new_word)}' because of invalid character '{char}'{RESET}")
            else:
                new_word.append("")
                if line_number is not None:
                    print(f"{RED}Error: word '{word}' on line {line_number} contains invalid character '{char}' and cannot be replaced. Removing the character instead.{RESET}")
                else:
                    print(f"{RED}Error: word '{word}' contains invalid character '{char}' and cannot be replaced. Removing the character instead.{RESET}")
        else:
            new_word.append(char)
    return ''.join(new_word)

def segment_string_block(string_block, box_width, num_lines, char_widths, valid_char_set, max_char_per_line):
    words = string_block.split()
    lines = []
    line_lengths = []
    current_line = ""
    line_number = 1

    for i, word in enumerate(words):
        valid_word = replace_invalid_chars(word, valid_char_set, line_number)
        if valid_word is None:
            continue

        word_length = approximate_word_length(valid_word, font_width, char_widths)
        current_line_length = approximate_word_length(current_line, font_width, char_widths)

        if current_line_length + word_length <= box_width and len(current_line) + len(valid_word) + 1 <= max_char_per_line:
            if current_line:
                current_line += " " + valid_word
            else:
                current_line = valid_word
        else:
            lines.append(current_line)
            line_lengths.append(current_line_length)
            current_line = valid_word
            line_number += 1

            if len(lines) >= num_lines:
                print("Warning: Exceeded the maximum number of lines.")
                print("Remaining unfitted words:", " ".join(words[i:]))
                return lines, line_lengths

    if current_line:
        lines.append(current_line)
        line_lengths.append(approximate_word_length(current_line, font_width, char_widths))

    return lines, line_lengths

# Load string_block from block_text.txt
with open('input_text.txt', 'r', encoding='utf-8') as file:
    string_block = file.read()

# Segment the string_block into lines
segmented_lines, line_lengths = segment_string_block(string_block, box_width, num_lines, char_widths, valid_char_set, max_char_per_line)

with open('lines_text.txt', 'w', encoding='utf-8') as file:
    for line in segmented_lines:
        file.write(line + '\n')