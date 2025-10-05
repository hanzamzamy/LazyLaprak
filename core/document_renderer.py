"""
Document rendering system for converting processed text and strokes to SVG output.
"""

import svgwrite
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

from .config import document_config, text_config, calculate_text_width, TextAlignment

@dataclass
class WordLayout:
    """Layout information for a single word"""
    text: str
    strokes: np.ndarray
    x_position: float
    y_position: float
    width: float

@dataclass
class LineLayout:
    """Layout information for a single line"""
    words: List[WordLayout]
    line_number: int
    alignment: TextAlignment
    y_position: float

class DocumentRenderer:
    """Renders processed text and handwriting strokes to SVG format"""
    
    def __init__(self):
        self.doc_config = document_config
        self.text_config = text_config
    
    def create_line_layout(self, words: List[str], strokes_list: List[np.ndarray], 
                          line_number: int, alignment: TextAlignment) -> LineLayout:
        """
        Create layout information for a line of text.
        
        Args:
            words: List of words in the line
            strokes_list: List of stroke arrays for each word
            line_number: Line number (0-indexed)
            alignment: Text alignment for this line
            
        Returns:
            LineLayout object with positioning information
        """
        y_position = self.doc_config.text_area_y + (line_number * self.doc_config.line_height)
        
        # Calculate word positions based on alignment
        word_positions = self._calculate_word_positions(words, strokes_list, alignment)
        
        # Create WordLayout objects
        word_layouts = []
        for word, strokes, x_pos in zip(words, strokes_list, word_positions):
            word_width = self._calculate_stroke_width(strokes) if len(strokes) > 0 else calculate_text_width(word, self.text_config.font_width)
            
            word_layouts.append(WordLayout(
                text=word,
                strokes=strokes,
                x_position=x_pos,
                y_position=y_position,
                width=word_width
            ))
        
        return LineLayout(
            words=word_layouts,
            line_number=line_number,
            alignment=alignment,
            y_position=y_position
        )
    
    def _calculate_word_positions(self, words: List[str], strokes_list: List[np.ndarray], 
                                 alignment: TextAlignment) -> List[float]:
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
        total_space_width = (len(words) - 1) * space_width
        total_content_width = total_word_width + total_space_width
        
        if alignment == TextAlignment.LEFT:
            x_pos = self.doc_config.text_area_x
            for word_width in word_widths:
                positions.append(x_pos)
                x_pos += word_width + space_width
                
        elif alignment == TextAlignment.RIGHT:
            start_x = self.doc_config.text_area_x + self.doc_config.text_area_width - total_content_width
            x_pos = start_x
            for word_width in word_widths:
                positions.append(x_pos)
                x_pos += word_width + space_width
                
        elif alignment == TextAlignment.CENTER:
            start_x = self.doc_config.text_area_x + (self.doc_config.text_area_width - total_content_width) / 2
            x_pos = start_x
            for word_width in word_widths:
                positions.append(x_pos)
                x_pos += word_width + space_width
                
        elif alignment == TextAlignment.JUSTIFY:
            if len(words) == 1:
                # Single word - align left
                positions.append(self.doc_config.text_area_x)
            else:
                # Distribute words across the line
                available_space = self.doc_config.text_area_width - total_word_width
                space_between_words = available_space / (len(words) - 1)
                
                x_pos = self.doc_config.text_area_x
                for word_width in word_widths:
                    positions.append(x_pos)
                    x_pos += word_width + space_between_words
        
        return positions
    
    def _calculate_stroke_width(self, strokes: np.ndarray) -> float:
        """Calculate the width of a stroke sequence"""
        if len(strokes) == 0:
            return 0.0
        return strokes[-1, 0] - strokes[0, 0]
    
    def render_to_svg(self, line_layouts: List[LineLayout], filename: str, 
                     stroke_color: str = 'black', stroke_width: float = 1.0) -> str:
        """
        Render the document to SVG format.
        
        Args:
            line_layouts: List of line layouts to render
            filename: Output filename (without extension)
            stroke_color: Color for handwriting strokes
            stroke_width: Width of strokes
            
        Returns:
            Full path to the generated SVG file
        """
        svg_filename = f"{filename}.svg"
        
        # Create SVG drawing
        dwg = svgwrite.Drawing(
            filename=svg_filename,
            size=(self.doc_config.page.width_px, self.doc_config.page.height_px)
        )
        dwg.viewbox(width=self.doc_config.page.width_px, height=self.doc_config.page.height_px)
        
        # Add white background
        dwg.add(dwg.rect(
            insert=(0, 0),
            size=(self.doc_config.page.width_px, self.doc_config.page.height_px),
            fill='white'
        ))
        
        # Add text area border if enabled
        if self.doc_config.draw_guidelines:
            dwg.add(dwg.rect(
                insert=(self.doc_config.text_area_x, self.doc_config.text_area_y),
                size=(self.doc_config.text_area_width, self.doc_config.text_area_height),
                stroke='lightgray',
                fill='none',
                stroke_width=0.5
            ))
            
            # Add line guidelines
            for i in range(1, self.doc_config.num_lines):
                y = self.doc_config.text_area_y + i * self.doc_config.line_height
                dwg.add(dwg.line(
                    start=(self.doc_config.text_area_x, y),
                    end=(self.doc_config.text_area_x + self.doc_config.text_area_width, y),
                    stroke='lightgray',
                    stroke_width=0.3
                ))
        
        # Render each line
        for line_layout in line_layouts:
            for word_layout in line_layout.words:
                self._render_word_strokes(dwg, word_layout, stroke_color, stroke_width)
        
        # Save SVG
        dwg.save()
        print(f"SVG saved: {svg_filename}")
        
        return svg_filename
    
    def _render_word_strokes(self, dwg: svgwrite.Drawing, word_layout: WordLayout, 
                            stroke_color: str, stroke_width: float):
        """Render strokes for a single word"""
        if len(word_layout.strokes) == 0:
            return
        
        # Apply scaling and positioning
        strokes = word_layout.strokes.copy()
        strokes[:, :2] *= self.text_config.scale
        
        # Position the word
        if len(strokes) > 0:
            # Normalize to start at (0,0)
            strokes[:, 0] -= strokes[0, 0]
            strokes[:, 1] -= strokes[:, 1].min()
            
            # Apply positioning
            strokes[:, 0] += word_layout.x_position
            strokes[:, 1] = word_layout.y_position - strokes[:, 1]  # Flip Y and position
        
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
            dwg.add(path)
    
    def create_document_metadata(self, line_layouts: List[LineLayout]) -> Dict:
        """Create metadata about the rendered document"""
        total_words = sum(len(line.words) for line in line_layouts)
        total_chars = sum(sum(len(word.text) for word in line.words) for line in line_layouts)
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_lines': len(line_layouts),
            'total_words': total_words,
            'total_characters': total_chars,
            'page_config': {
                'width_px': self.doc_config.page.width_px,
                'height_px': self.doc_config.page.height_px,
                'text_area_width': self.doc_config.text_area_width,
                'text_area_height': self.doc_config.text_area_height,
            }
        }