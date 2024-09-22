#GCode output config
gcode_output = True # Set to True to generate GCode output
feedrate = 300 # Feedrate in mm/min
gcode_header = f"""
G21
G90;svg > rect
G1 X0 Y297 F300
G1 X209.8145833333333 Y297 F300
G1 X209.8145833333333 Y0 F300
G1 X0 Y0 F300
G1 X0 Y297 F300;svg > path
G1 X0 Y297 F300
"""

#Drawing config
# A4 page dimensions in mm (1mm ≈ 3.78 pixels)
a4_width_mm = 210
a4_height_mm = 297
a4_width_px = int(a4_width_mm * 3.78)
a4_height_px = int(a4_height_mm * 3.78)

view_width = a4_width_px
view_height = a4_height_px

# Margins in cm
left_margin_cm = 3
right_margin_cm = 4
top_margin_cm = 3
bottom_margin_cm = 3.3

left_margin_px = int(left_margin_cm * 37.8)
right_margin_px = int(right_margin_cm * 37.8)
top_margin_px = int(top_margin_cm * 37.8)
bottom_margin_px = int(bottom_margin_cm * 37.8)

# Define the dimensions and position of the box
box_x = left_margin_px
box_y = top_margin_px
box_width = view_width - left_margin_px - right_margin_px
box_height = view_height - top_margin_px - bottom_margin_px

num_lines = 32
draw_tatakan = False

# Calculate the height of each line
line_height_px = box_height / num_lines

text_scale = 0.8
font_height = 18 * text_scale
font_width = 18 * text_scale
space_threshold = 3  # Threshold to consider a space between words
space_min_x_threshold = 30  # Minimum x value from start to consider a space between words
vertical_offset = (line_height_px - font_height) / 2
horizontal_offset = font_width

#Synthesizer config
max_char_per_line = 75
bias = 2.5
style = 3
char_widths = {
    'a': 0.6, 'b': 0.6, 'c': 0.6, 'd': 0.6, 'e': 0.6, 'f': 0.4, 'g': 0.6, 'h': 0.6, 'i': 0.3, 'j': 0.3, 'k': 0.6, 'l': 0.3, 'm': 0.9, 'n': 0.6, 'o': 0.6, 'p': 0.6, 'q': 0.6, 'r': 0.4, 's': 0.6, 't': 0.4, 'u': 0.6, 'v': 0.6, 'w': 0.9, 'x': 0.6, 'y': 0.6, 'z': 0.6,
    'A': 0.7, 'B': 0.7, 'C': 0.7, 'D': 0.7, 'E': 0.7, 'F': 0.7, 'G': 0.7, 'H': 0.7, 'I': 0.4, 'J': 0.4, 'K': 0.7, 'L': 0.7, 'M': 0.9, 'N': 0.7, 'O': 0.7, 'P': 0.7, 'Q': 0.7, 'R': 0.7, 'S': 0.7, 'T': 0.7, 'U': 0.7, 'V': 0.7, 'W': 0.9, 'X': 0.7, 'Y': 0.7, 'Z': 0.7,
    ' ': 0.3, '.': 0.3, ',': 0.3, '!': 0.3, '?': 0.3, '-': 0.3, '_': 0.3, ':': 0.3, ';': 0.3, '(': 0.3, ')': 0.3, '[': 0.3, ']': 0.3, '{': 0.3, '}': 0.3, '/': 0.3, '\\': 0.3, '|': 0.3, '@': 0.9, '#': 0.9, '$': 0.9, '%': 0.9, '^': 0.9, '&': 0.9, '*': 0.9, '+': 0.9, '=': 0.9,
    '0': 0.6, '1': 0.6, '2': 0.6, '3': 0.6, '4': 0.6, '5': 0.6, '6': 0.6, '7': 0.6, '8': 0.6, '9': 0.6,
    'q': 0.6, 'Q': 0.7, 'S': 0.7, 'X': 0.7, 'Z': 0.7, '\x00': 0.3
}

valid_char_set = {'9', 'l', 'd', 'D', 'J', 'c', '6', 'V', '\x00', '-', '"', 'H', 't', 'r', '(', 'N', 'u', 'y', 'I', ';', '!', 'F', 'j', ')', '#', 'B', 'O', '4', 'M', 'W', 'f', '?', '8', 'g', ',', '1', 'w', "'", 'A', 'm', 'K', 'C', 'o', ' ', ':', 'n', 'U', 'h', 's', 'q', '5', 'x', 'k', 'S', '0', 'Y', 'p', 'e', 'P', 'a', 'R', 'b', '2', '3', 'v', 'E', 'i', 'G', 'T', '7', '.', 'z', 'L'}

def approximate_line_length(line, font_width, char_widths):
    total_length = 0
    for char in line:
        total_length += char_widths.get(char, font_width) * font_width
    return total_length

def approximate_word_length(word, font_width, char_widths):
    total_length = 0
    for char in word:
        total_length += char_widths.get(char, font_width) * font_width
    return total_length