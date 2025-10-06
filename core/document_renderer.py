"""
Document rendering system for converting processed text and strokes to SVG output.
"""

import svgwrite
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

from .config import document_config, text_config, calculate_text_width, TextAlignment, PageType

@dataclass
class WordLayout:
    """Layout information for a single word"""
    text: str
    strokes: np.ndarray
    x_position: float
    y_position: float
    width: float
    page_number: int = 1

@dataclass
class LineLayout:
    """Layout information for a single line"""
    words: List[WordLayout]
    line_number: int
    alignment: TextAlignment
    y_position: float
    page_number: int = 1
    page_type: PageType = PageType.ODD

class DocumentRenderer:
    """Renders processed text and handwriting strokes to SVG format"""
    
    def __init__(self):
        self.doc_config = document_config
        self.text_config = text_config
    
    def create_line_layout(self, words: List[str], strokes_list: List[np.ndarray], 
                          line_number: int, alignment: TextAlignment, 
                          page_number: int = 1, page_type: PageType = PageType.ODD) -> LineLayout:
        """
        Create layout information for a line of text with proper baseline positioning.
        """
        # Get page-specific margins and text area
        text_area_x, text_area_y, text_area_width, text_area_height = self.doc_config.get_text_area(page_type)
        
        # Calculate Y position for text BASELINE (text_area_y is already adjusted for baseline)
        y_position = text_area_y + (line_number * self.doc_config.line_height)
        
        # Calculate word positions based on alignment
        word_positions = self._calculate_word_positions(
            words, strokes_list, alignment, text_area_width, text_area_x
        )
        
        # Create WordLayout objects
        word_layouts = []
        for word, strokes, x_pos in zip(words, strokes_list, word_positions):
            word_width = self._calculate_stroke_width(strokes) if len(strokes) > 0 else calculate_text_width(word, self.text_config.font_width)
            
            word_layouts.append(WordLayout(
                text=word,
                strokes=strokes,
                x_position=x_pos,
                y_position=y_position,  # This is now the baseline position
                width=word_width,
                page_number=page_number
            ))
        
        return LineLayout(
            words=word_layouts,
            line_number=line_number,
            alignment=alignment,
            y_position=y_position,
            page_number=page_number,
            page_type=page_type
        )
    
    def _calculate_word_positions(self, words: List[str], strokes_list: List[np.ndarray], 
                                 alignment: TextAlignment, text_area_width: float, 
                                 text_area_x: float) -> List[float]:
        """Calculate x positions for words based on alignment"""
        if not words:
            return []
        
        positions = []
        space_width = calculate_text_width(' ', self.text_config.font_width)
        
        # Calculate actual widths of words from strokes
        word_widths = []
        for word, strokes in zip(words, strokes_list):
            if len(strokes) > 0:
                width = self._calculate_stroke_width(strokes)
            else:
                width = calculate_text_width(word, self.text_config.font_width)
            word_widths.append(width)
        
        total_word_width = sum(word_widths)
        total_space_width = (len(words) - 1) * space_width if len(words) > 1 else 0
        total_content_width = total_word_width + total_space_width
        
        if alignment == TextAlignment.LEFT:
            x_pos = text_area_x
            for word_width in word_widths:
                positions.append(x_pos)
                x_pos += word_width + space_width
                
        elif alignment == TextAlignment.RIGHT:
            start_x = text_area_x + text_area_width - total_content_width
            x_pos = max(text_area_x, start_x)  # Don't go beyond left edge
            for word_width in word_widths:
                positions.append(x_pos)
                x_pos += word_width + space_width
                
        elif alignment == TextAlignment.CENTER:
            start_x = text_area_x + (text_area_width - total_content_width) / 2
            x_pos = max(text_area_x, start_x)  # Don't go beyond left edge
            for word_width in word_widths:
                positions.append(x_pos)
                x_pos += word_width + space_width
                
        elif alignment == TextAlignment.JUSTIFY:
            if len(words) == 1:
                # Single word - align left
                positions.append(text_area_x)
            else:
                # Distribute words across the line
                available_space = text_area_width - total_word_width
                space_between_words = available_space / (len(words) - 1)
                
                x_pos = text_area_x
                for word_width in word_widths:
                    positions.append(x_pos)
                    x_pos += word_width + space_between_words
        
        return positions
    
    def _calculate_stroke_width(self, strokes: np.ndarray) -> float:
        """Calculate the width of a stroke sequence"""
        if len(strokes) == 0:
            return 0.0
        return abs(strokes[-1, 0] - strokes[0, 0])
    
    def render_to_svg(self, line_layouts: List[LineLayout], filename: str, 
                    stroke_color: str = 'black', stroke_width: float = 1.0) -> str:
        """
        Render the document to SVG format with proper multi-page support.
        """
        svg_filename = f"{filename}.svg"
        
        # Group lines by page
        pages = {}
        for line in line_layouts:
            page_num = line.page_number
            if page_num not in pages:
                pages[page_num] = []
            pages[page_num].append(line)
        
        # Calculate total document height (pages stacked vertically)
        num_pages = len(pages) if pages else 1
        total_height = num_pages * self.doc_config.page.height_px
        
        # Create SVG drawing with full document height
        dwg = svgwrite.Drawing(
            filename=svg_filename,
            size=(self.doc_config.page.width_px, total_height)
        )
        dwg.viewbox(width=self.doc_config.page.width_px, height=total_height)
        
        # Add CSS for page breaks when printing
        dwg.defs.add(dwg.style("""
            @media print {
                .page {
                    page-break-after: always;
                    page-break-inside: avoid;
                }
                .page:last-child {
                    page-break-after: auto;
                }
            }
        """))
        
        # Render each page
        for page_num in sorted(pages.keys()):
            page_lines = pages[page_num]
            # Ensure correct page type determination
            page_type = PageType.ODD if page_num % 2 == 1 else PageType.EVEN
            
            # Calculate page Y offset
            page_y_offset = (page_num - 1) * self.doc_config.page.height_px
            
            # Create page group
            page_group = dwg.g(class_="page", id=f"page-{page_num}")
            
            # Add page background
            page_group.add(dwg.rect(
                insert=(0, page_y_offset),
                size=(self.doc_config.page.width_px, self.doc_config.page.height_px),
                fill='white',
                stroke='lightgray',
                stroke_width=0.5
            ))
            
            # Get page-specific margins and text area - RECALCULATE for this page
            text_area_x, text_area_y, text_area_width, text_area_height = self.doc_config.get_text_area(page_type)
            
            # Add text area border if enabled - show the actual margins being used
            if self.doc_config.draw_guidelines:
                page_group.add(dwg.rect(
                    insert=(text_area_x, text_area_y + page_y_offset),
                    size=(text_area_width, text_area_height),
                    stroke='lightblue',
                    fill='none',
                    stroke_width=0.5,
                    opacity=0.3
                ))
                
                # Add margin info as text for debugging
                left, right, top, bottom = self.doc_config.margins.get_margins(page_type)
                page_group.add(dwg.text(
                    f"Page {page_num} ({'Odd' if page_type == PageType.ODD else 'Even'}) - L:{left} R:{right}",
                    insert=(10, page_y_offset + 20),
                    fill='red',
                    font_size='12px'
                ))
                
                # Add line guidelines
                for i in range(1, self.doc_config.num_lines):
                    y = text_area_y + page_y_offset + i * self.doc_config.line_height
                    page_group.add(dwg.line(
                        start=(text_area_x, y),
                        end=(text_area_x + text_area_width, y),
                        stroke='lightblue',
                        stroke_width=0.3,
                        opacity=0.3
                    ))
            
            # Render lines on this page - ensure they use the correct margins
            for line_layout in page_lines:
                # Override the line's page type to ensure consistency
                line_layout.page_type = page_type
                for word_layout in line_layout.words:
                    # Adjust word position for page offset
                    adjusted_word = WordLayout(
                        text=word_layout.text,
                        strokes=word_layout.strokes,
                        x_position=word_layout.x_position,
                        y_position=word_layout.y_position + page_y_offset,
                        width=word_layout.width,
                        page_number=word_layout.page_number
                    )
                    self._render_word_strokes(page_group, adjusted_word, stroke_color, stroke_width)
            
            dwg.add(page_group)
        
        # Save SVG
        dwg.save()
        print(f"Multi-page SVG saved: {svg_filename} ({num_pages} pages)")
        
        return svg_filename
    
    def _render_word_strokes(self, parent_group: svgwrite.container.Group, 
                            word_layout: WordLayout, stroke_color: str, stroke_width: float):
        """Render strokes for a single word with proper baseline positioning"""
        if len(word_layout.strokes) == 0:
            return
        
        # Apply scaling and positioning
        strokes = word_layout.strokes.copy()
        strokes[:, :2] *= self.text_config.scale
        
        # Position the word
        if len(strokes) > 0:
            # Normalize strokes
            strokes[:, 0] -= strokes[0, 0]  # Start at x=0
            
            # For Y positioning: word_layout.y_position is the baseline
            # We need to position the strokes so their baseline aligns with this
            stroke_bottom = strokes[:, 1].max()  # Bottom of the strokes
            strokes[:, 1] = word_layout.y_position - (strokes[:, 1] - stroke_bottom)
            
            # Apply X positioning
            strokes[:, 0] += word_layout.x_position
        
        # Generate SVG path
        path_data = ""
        prev_eos = 1.0
        
        for x, y, eos in strokes:
            if prev_eos == 1.0:
                path_data += f"M{x:.2f},{y:.2f} "
            else:
                path_data += f"L{x:.2f},{y:.2f} "
            prev_eos = eos
        
        # Add path to SVG
        if path_data.strip():
            path = svgwrite.path.Path(path_data)
            path = path.stroke(color=stroke_color, width=stroke_width, linecap='round').fill("none")
            parent_group.add(path)
    
    def create_document_metadata(self, line_layouts: List[LineLayout]) -> Dict:
        """Create metadata about the rendered document"""
        total_words = sum(len(line.words) for line in line_layouts)
        total_chars = sum(sum(len(word.text) for word in line.words) for line in line_layouts)
        
        # Count pages
        pages = set(line.page_number for line in line_layouts)
        num_pages = len(pages) if pages else 1
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_lines': len(line_layouts),
            'total_words': total_words,
            'total_characters': total_chars,
            'total_pages': num_pages,
            'page_config': {
                'width_px': self.doc_config.page.width_px,
                'height_px': self.doc_config.page.height_px,
            }
        }