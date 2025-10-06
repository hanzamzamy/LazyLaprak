"""
Enhanced text processor with markup support and page-aware layout.
"""

import re
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass

from .config import document_config, calculate_text_width, PageType, TextStyle
from .markup_parser import MarkupParser, TextBlock

@dataclass
class ProcessedWord:
    """Word with processing metadata"""
    text: str
    style_overrides: Dict[str, Any]
    estimated_width: float
    
@dataclass
class ProcessedLine:
    """Line with layout information"""
    words: List[ProcessedWord]
    style: TextStyle
    line_number: int
    page_number: int
    page_type: PageType
    
@dataclass
class ProcessedPage:
    """Page with all its lines"""
    lines: List[ProcessedLine]
    page_number: int
    page_type: PageType

class TextProcessor:
    """Enhanced text processor with markup and page layout support"""
    
    def __init__(self):
        self.markup_parser = MarkupParser()
        self.doc_config = document_config
        
    def process_markup_text(self, markup_text: str) -> List[ProcessedPage]:
        """Process markup text into pages with proper layout"""
        # Parse markup into text blocks
        text_blocks = self.markup_parser.parse(markup_text)
        
        pages = []
        current_page_lines = []
        current_page_number = 1
        current_line_number = 0
        
        for block in text_blocks:
            if block.text == "[PAGE_BREAK]":
                # Finish current page
                if current_page_lines:
                    page_type = PageType.ODD if current_page_number % 2 == 1 else PageType.EVEN
                    pages.append(ProcessedPage(
                        lines=current_page_lines,
                        page_number=current_page_number,
                        page_type=page_type
                    ))
                    current_page_lines = []
                    current_page_number += 1
                    current_line_number = 0
                continue
            
            if block.text == "[LINE_BREAK]":
                current_line_number += 1
                continue
            
            # Process text block into lines
            block_lines = self._process_text_block(
                block, 
                current_page_number, 
                current_line_number
            )
            
            for line in block_lines:
                # Check if we need to start a new page
                if current_line_number >= self.doc_config.num_lines:
                    # Finish current page
                    if current_page_lines:
                        page_type = PageType.ODD if current_page_number % 2 == 1 else PageType.EVEN
                        pages.append(ProcessedPage(
                            lines=current_page_lines,
                            page_number=current_page_number,
                            page_type=page_type
                        ))
                        current_page_lines = []
                        current_page_number += 1
                        current_line_number = 0
                
                # Update line metadata
                line.line_number = current_line_number
                line.page_number = current_page_number
                line.page_type = PageType.ODD if current_page_number % 2 == 1 else PageType.EVEN
                
                current_page_lines.append(line)
                current_line_number += 1
        
        # Add final page if it has content
        if current_page_lines:
            page_type = PageType.ODD if current_page_number % 2 == 1 else PageType.EVEN
            pages.append(ProcessedPage(
                lines=current_page_lines,
                page_number=current_page_number,
                page_type=page_type
            ))
        
        return pages
    
    def _process_text_block(self, block: TextBlock, page_number: int, start_line: int) -> List[ProcessedLine]:
        """Process a text block into lines"""
        # Get page type and text area
        page_type = PageType.ODD if page_number % 2 == 1 else PageType.EVEN
        text_area_x, text_area_y, text_area_width, text_area_height = self.doc_config.get_text_area(page_type)
        
        # Split text into words
        words = re.findall(r'\S+', block.text)
        
        # Process words with style overrides
        processed_words = []
        for word in words:
            style_overrides = block.custom_words.get(word, {})
            estimated_width = calculate_text_width(word, block.style.font_width)
            
            processed_words.append(ProcessedWord(
                text=word,
                style_overrides=style_overrides,
                estimated_width=estimated_width
            ))
        
        # Fit words into lines
        lines = []
        remaining_words = processed_words
        line_number = start_line
        
        while remaining_words:
            line_words, remaining_words = self._fit_words_to_line(
                remaining_words, 
                text_area_width, 
                block.style
            )
            
            if not line_words:
                # Skip problematic word
                if remaining_words:
                    print(f"Warning: Skipping word '{remaining_words[0].text}' - too long for line")
                    remaining_words = remaining_words[1:]
                continue
            
            lines.append(ProcessedLine(
                words=line_words,
                style=block.style,
                line_number=line_number,
                page_number=page_number,
                page_type=page_type
            ))
            
            line_number += 1
        
        return lines
    
    def _fit_words_to_line(self, words: List[ProcessedWord], max_width: float, 
                          style: TextStyle) -> Tuple[List[ProcessedWord], List[ProcessedWord]]:
        """Fit words to a line considering text style AND character limit"""
        fitted_words = []
        current_width = 0.0
        current_chars = 0
        space_width = calculate_text_width(' ', style.font_width)
        
        for i, word in enumerate(words):
            word_width = word.estimated_width
            word_chars = len(word.text)
            
            # Add space width if not first word
            total_width = current_width + word_width
            total_chars = current_chars + word_chars
            
            if fitted_words:
                total_width += space_width
                total_chars += 1  # Count the space
            
            # Check both width and character limits
            from .config import text_config
            width_ok = total_width <= max_width
            chars_ok = total_chars <= text_config.max_chars_per_line
            
            if width_ok and chars_ok:
                fitted_words.append(word)
                current_width = total_width
                current_chars = total_chars
            else:
                return fitted_words, words[i:]
        
        return fitted_words, []
    
    def get_word_style_params(self, word: ProcessedWord, base_style: TextStyle) -> Dict[str, Any]:
        """Get effective style parameters for a word"""
        params = {
            'bias': base_style.bias,
            'style': base_style.style,
            'scale': base_style.scale
        }
        
        # Apply word-specific overrides
        params.update(word.style_overrides)
        
        return params