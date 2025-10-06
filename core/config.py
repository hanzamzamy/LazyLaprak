"""
Enhanced configuration with page layout and markup support.
"""

from dataclasses import dataclass, field
from typing import Dict, Set, List, Optional, Tuple
from enum import Enum
import re

class TextAlignment(Enum):
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"
    JUSTIFY = "justify"

class PageType(Enum):
    ODD = "odd"
    EVEN = "even"

@dataclass
class RNNConfig:
    """RNN model configuration"""
    default_bias: float = 2.0
    default_style: int = 20
    lstm_size: int = 400
    output_mixture_components: int = 20
    attention_mixture_components: int = 10

@dataclass
class PageMargins:
    """Page margins that can differ between odd/even pages"""
    odd_left: float = 4.0
    odd_right: float = 3.0
    odd_top: float = 3.0
    odd_bottom: float = 3.0
    
    even_left: float = 3.0
    even_right: float = 4.0
    even_top: float = 3.0
    even_bottom: float = 3.0
    
    def get_margins(self, page_type: PageType) -> Tuple[float, float, float, float]:
        """Get margins as (left, right, top, bottom) for given page type"""
        if page_type == PageType.ODD:
            return (self.odd_left, self.odd_right, self.odd_top, self.odd_bottom)
        else:
            return (self.even_left, self.even_right, self.even_top, self.even_bottom)

@dataclass
class PageConfig:
    """Enhanced page configuration"""
    width_mm: float = 210.0
    height_mm: float = 297.0
    mm_to_px: float = 3.78
    cm_to_px: float = 37.8
    
    @property
    def width_px(self) -> int:
        return int(self.width_mm * self.mm_to_px)
    
    @property
    def height_px(self) -> int:
        return int(self.height_mm * self.mm_to_px)
    
@dataclass
class TextConfig:
    """Text rendering configuration"""
    scale: float = 0.8
    base_font_size: float = 18.0
    max_chars_per_line: int = 68
    
    @property
    def font_height(self) -> float:
        return self.base_font_size * self.scale
    
    @property
    def font_width(self) -> float:
        return self.base_font_size * self.scale

@dataclass
class TextStyle:
    """Text styling configuration"""
    alignment: TextAlignment = TextAlignment.JUSTIFY
    bias: float = 1.75
    style: int = 20
    scale: float = 0.8
    font_size: float = 18.0
    line_spacing: float = 1.2
    
    @property
    def font_height(self) -> float:
        return self.font_size * self.scale
    
    @property
    def font_width(self) -> float:
        return self.font_size * self.scale

    def copy(self) -> "TextStyle":
        return TextStyle(
            alignment=self.alignment,
            bias=self.bias,
            style=self.style,
            scale=self.scale,
            font_size=self.font_size,
            line_spacing=self.line_spacing
        )

@dataclass
class DocumentConfig:
    """Enhanced document configuration"""
    num_lines: int = 32
    draw_guidelines: bool = False
    margins: PageMargins = field(default_factory=PageMargins)
    page: PageConfig = field(default_factory=PageConfig)
    
    def get_text_area(self, page_type: PageType) -> Tuple[int, int, int, int]:
        """Get text area as (x, y, width, height) for given page type"""
        left, right, top, bottom = self.margins.get_margins(page_type)
        
        # Convert to pixels
        left_px = int(left * self.page.cm_to_px)
        right_px = int(right * self.page.cm_to_px)
        top_px = int(top * self.page.cm_to_px)
        bottom_px = int(bottom * self.page.cm_to_px)
        
        x = left_px
        # Use a local reference to text_config instead of the global one
        font_height = 18.0 * 0.8  # base_font_size * scale from TextConfig
        y = top_px + int(font_height)  # Start at baseline, not top of text
        width = self.page.width_px - left_px - right_px
        # Adjust height to account for baseline positioning
        height = self.page.height_px - top_px - bottom_px - int(font_height)
        
        return (x, y, width, height)
    
    @property
    def line_height(self) -> float:
        _, _, _, height = self.get_text_area(PageType.ODD)
        return height / self.num_lines

# Predefined text styles
PREDEFINED_STYLES = {
    'title': TextStyle(alignment=TextAlignment.CENTER, scale=1.2, font_size=24.0, bias=1.5),
    'heading1': TextStyle(alignment=TextAlignment.LEFT, scale=1.0, font_size=20.0, bias=1.5),
    'heading2': TextStyle(alignment=TextAlignment.LEFT, scale=0.9, font_size=18.0, bias=1.5),
    'heading3': TextStyle(alignment=TextAlignment.LEFT, scale=0.8, font_size=16.0, bias=1.5),
    'body': TextStyle(alignment=TextAlignment.JUSTIFY, scale=0.8, font_size=18.0, bias=1.5),
    'quote': TextStyle(alignment=TextAlignment.CENTER, scale=0.7, font_size=16.0, bias=1.5),
    'caption': TextStyle(alignment=TextAlignment.CENTER, scale=0.6, font_size=14.0, bias=1.5),
}

# Character widths and valid characters (from original config)
CHAR_WIDTHS: Dict[str, float] = {
    'a': 0.6, 'b': 0.6, 'c': 0.6, 'd': 0.6, 'e': 0.6, 'f': 0.4, 'g': 0.6, 'h': 0.6, 
    'i': 0.3, 'j': 0.3, 'k': 0.6, 'l': 0.3, 'm': 0.9, 'n': 0.6, 'o': 0.6, 'p': 0.6, 
    'q': 0.6, 'r': 0.4, 's': 0.6, 't': 0.4, 'u': 0.6, 'v': 0.6, 'w': 0.9, 'x': 0.6, 
    'y': 0.6, 'z': 0.6,
    'A': 0.7, 'B': 0.7, 'C': 0.7, 'D': 0.7, 'E': 0.7, 'F': 0.7, 'G': 0.7, 'H': 0.7, 
    'I': 0.4, 'J': 0.4, 'K': 0.7, 'L': 0.7, 'M': 0.9, 'N': 0.7, 'O': 0.7, 'P': 0.7, 
    'Q': 0.7, 'R': 0.7, 'S': 0.7, 'T': 0.7, 'U': 0.7, 'V': 0.7, 'W': 0.9, 'X': 0.7, 
    'Y': 0.7, 'Z': 0.7,
    '0': 0.6, '1': 0.6, '2': 0.6, '3': 0.6, '4': 0.6, '5': 0.6, '6': 0.6, '7': 0.6, 
    '8': 0.6, '9': 0.6,
    ' ': 0.3, '.': 0.3, ',': 0.3, '!': 0.3, '?': 0.3, '-': 0.3, '_': 0.3, ':': 0.3, 
    ';': 0.3, '(': 0.3, ')': 0.3, '[': 0.3, ']': 0.3, '{': 0.3, '}': 0.3, '/': 0.3, 
    '\\': 0.3, '|': 0.3, '@': 0.9, '#': 0.9, '$': 0.9, '%': 0.9, '^': 0.9, '&': 0.9, 
    '*': 0.9, '+': 0.9, '=': 0.9, '"': 0.3, "'": 0.3, '\x00': 0.3
}

VALID_CHARS: Set[str] = {
    '9', 'l', 'd', 'D', 'J', 'c', '6', 'V', '\x00', '-', '"', 'H', 't', 'r', '(', 'N', 
    'u', 'y', 'I', ';', '!', 'F', 'j', ')', '#', 'B', 'O', '4', 'M', 'W', 'f', '?', 
    '8', 'g', ',', '1', 'w', "'", 'A', 'm', 'K', 'C', 'o', ' ', ':', 'n', 'U', 'h', 
    's', 'q', '5', 'x', 'k', 'S', '0', 'Y', 'p', 'e', 'P', 'a', 'R', 'b', '2', '3', 
    'v', 'E', 'i', 'G', 'T', '7', '.', 'z', 'L'
}

def calculate_text_width(text: str, font_width: float) -> float:
    """Calculate the approximate width of text in pixels"""
    total_width = 0.0
    for char in text:
        char_width = CHAR_WIDTHS.get(char, 1.0)
        total_width += char_width * font_width
    return total_width

# Global instances
document_config = DocumentConfig()
rnn_config = RNNConfig()
text_config = TextConfig()
