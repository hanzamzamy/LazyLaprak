from hand import Hand
from datetime import datetime
from config import bias, style

def read_lines_from_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.read().splitlines()
    return lines

if __name__ == "__main__":
    hand = Hand()

    lines = read_lines_from_file('lines_text.txt')
    biases = [bias for i in lines]
    styles = [style for i in lines]
    stroke_widths = [1 for i in lines]
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"output/{timestamp}"
    hand.write(
        filename=filename,
        lines=lines,
        biases=biases,
        styles=styles,
        stroke_widths=stroke_widths,
    )
