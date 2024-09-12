# Define the valid character set
valid_char_set = {"'", ' ', '#', '!', '(', 'r', 'N', 'V', 'R', 'E', 'U', '0', 'P', 'z', 'H', 'b', 'G', '9', '4', 'I', 'l', 'p', 'w', 'j', '"', 'f', '1', 's', 't', 'D', 'u', 'v', 'a', 'y', ':', '.', 'T', 'h', 'O', 'k', 'c', '?', ')', '7', 'F', '8', 'Y', 'L', 'W', '2', 'J', 'M', 'q', '\x00', 'K', '3', 'A', 'C', 'e', '-', 'g', 'm', 'n', 'o', ',', ';', 'd', 'x', '6', 'i', '5', 'S', 'B'}

# Function to filter a string based on the valid character set
def filter_string(s, valid_char_set):
    return ''.join([char for char in s if char in valid_char_set])

    # Original lines
lines = [
    "abcdefghijklmnopqrstuvwxyz",
    "ABCDEFGHIJKLMNO",
    "PQRSTUVWXYZ",
    "0123456789",
    " .,!?-_:;()[]{}@#$%^&*+=/\\|",
    "nyoba flkasjfdkasdjf pass is not enabled",
    "nyoba dikatakanlah pass is not enabled"
]

# Filtered lines
filtered_lines = [filter_string(line, valid_char_set) for line in lines]

print(filtered_lines)