"""
Advanced handwriting synthesis system with markup support, flexible margins,
and Flask-based online editing capabilities with SVG viewer.
"""

import re
import json
import os
import copy
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict, replace
from enum import Enum
from flask import Flask, render_template, request, jsonify, send_file, session, send_from_directory
from flask_socketio import SocketIO, emit
import threading
import uuid
import time

from core.config import (
    document_config, rnn_config, text_config, PREDEFINED_STYLES,
    TextAlignment, PageType, TextStyle, PageMargins
)
from core.text_processor import TextProcessor
from core.handwriting_engine import HandwritingEngine
from core.document_renderer import DocumentRenderer

class WordRegenerationManager:
    """Manages word-specific regeneration with custom parameters"""
    
    def __init__(self):
        self.word_overrides = {}  # word -> {bias, style, attempts}
        self.regeneration_history = {}  # word -> list of attempts
    
    def add_word_override(self, word: str, bias: float = None, style: int = None):
        """Add custom parameters for a specific word"""
        self.word_overrides[word] = {
            'bias': bias,
            'style': style,
            'attempts': self.word_overrides.get(word, {}).get('attempts', 0) + 1
        }
        
        if word not in self.regeneration_history:
            self.regeneration_history[word] = []
        
        self.regeneration_history[word].append({
            'bias': bias,
            'style': style,
            'timestamp': datetime.now().isoformat()
        })
    
    def get_word_parameters(self, word: str, default_bias: float, default_style: int) -> Tuple[float, int]:
        """Get effective parameters for a word"""
        if word in self.word_overrides:
            override = self.word_overrides[word]
            bias = override.get('bias', default_bias)
            style = override.get('style', default_style)
            return bias, style
        return default_bias, default_style
    
    def clear_word_override(self, word: str):
        """Remove override for a specific word"""
        if word in self.word_overrides:
            del self.word_overrides[word]

class EnhancedMarkupProcessor:
    """Enhanced markup processor using the new config system"""
    
    def __init__(self):
        self.patterns = {
            'style': r'\[style:(\w+)\](.*?)\[/style\]',
            'align': r'\[align:(\w+)\](.*?)\[/align\]', 
            'bias': r'\[bias:([\d.]+)\](.*?)\[/bias\]',
            'word': r'\[word:([^\]]+)\](\w+)\[/word\]',
            'page_break': r'\[page-break\]',
            'line_break': r'\[line-break\]',
            'margin': r'\[margin:([^\]]+)\](.*?)\[/margin\]',
        }
    
    def preview_markup(self, text: str) -> List[Dict]:
        """Preview markup structure for the web interface"""
        preview = []
        remaining_text = text
        
        while remaining_text.strip():
            # Check for page/line breaks
            page_break_match = re.match(self.patterns['page_break'], remaining_text)
            if page_break_match:
                preview.append({'type': 'break', 'text': '[PAGE_BREAK]'})
                remaining_text = remaining_text[page_break_match.end():].strip()
                continue
                
            line_break_match = re.match(self.patterns['line_break'], remaining_text)
            if line_break_match:
                preview.append({'type': 'break', 'text': '[LINE_BREAK]'})
                remaining_text = remaining_text[line_break_match.end():].strip()
                continue
            
            # Extract text block with style
            block_info, remaining_text = self._extract_block_info(remaining_text)
            
            if block_info:
                custom_words = self._extract_custom_words(block_info['text'])
                
                preview.append({
                    'type': 'text',
                    'text': self._clean_text_for_preview(block_info['text']),
                    'style': {
                        'alignment': block_info['style'].alignment.value,
                        'bias': block_info['style'].bias,
                        'style': block_info['style'].style, 
                        'font_scale': block_info['style'].scale,
                        'font_size': block_info['style'].font_size
                    },
                    'custom_words': custom_words,
                    'margins': block_info.get('margins', {})
                })
            else:
                break
                
        return preview
    
    def _extract_block_info(self, text: str) -> Tuple[Optional[Dict], str]:
        """Extract block information with style and margins"""
        text = text.strip()
        if not text:
            return None, ""
        
        # Check for style blocks
        style_match = re.match(self.patterns['style'], text, re.DOTALL | re.IGNORECASE)
        if style_match:
            style_name = style_match.group(1).lower()
            content = style_match.group(2).strip()
            remaining = text[style_match.end():].strip()
            
            if style_name in PREDEFINED_STYLES:
                # Create a copy of the predefined style using replace()
                style = replace(PREDEFINED_STYLES[style_name])
            else:
                style = replace(PREDEFINED_STYLES['body'])  # default
                
            return {
                'text': content,
                'style': style,
                'style_name': style_name
            }, remaining
        
        # Check for alignment blocks
        align_match = re.match(self.patterns['align'], text, re.DOTALL | re.IGNORECASE)
        if align_match:
            align_name = align_match.group(1).upper()
            content = align_match.group(2).strip()
            remaining = text[align_match.end():].strip()
            
            try:
                alignment = TextAlignment(align_name)
                # Create new TextStyle with custom alignment
                base_style = PREDEFINED_STYLES['body']
                style = replace(base_style, alignment=alignment)
            except ValueError:
                style = replace(PREDEFINED_STYLES['body'])
                
            return {
                'text': content,
                'style': style
            }, remaining
        
        # Check for bias blocks
        bias_match = re.match(self.patterns['bias'], text, re.DOTALL | re.IGNORECASE)
        if bias_match:
            bias_val = float(bias_match.group(1))
            content = bias_match.group(2).strip()
            remaining = text[bias_match.end():].strip()
            
            # Create new TextStyle with custom bias
            base_style = PREDEFINED_STYLES['body']
            style = replace(base_style, bias=bias_val)
            
            return {
                'text': content,
                'style': style
            }, remaining
        
        # Check for margin blocks
        margin_match = re.match(self.patterns['margin'], text, re.DOTALL | re.IGNORECASE)
        if margin_match:
            margin_params = margin_match.group(1)
            content = margin_match.group(2).strip()
            remaining = text[margin_match.end():].strip()
            
            margins = self._parse_margin_params(margin_params)
            style = replace(PREDEFINED_STYLES['body'])
            
            return {
                'text': content,
                'style': style,
                'margins': margins
            }, remaining
        
        # No markup found, extract paragraph until next markup
        next_markup_pos = float('inf')
        for pattern in self.patterns.values():
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                next_markup_pos = min(next_markup_pos, match.start())
        
        if next_markup_pos == float('inf'):
            # No more markup, return all remaining text
            return {
                'text': text,
                'style': replace(PREDEFINED_STYLES['body'])
            }, ""
        else:
            # Return text up to next markup
            content = text[:next_markup_pos].strip()
            remaining = text[next_markup_pos:].strip()
            return {
                'text': content,
                'style': replace(PREDEFINED_STYLES['body'])
            }, remaining
    
    def _parse_margin_params(self, params_str: str) -> Dict[str, float]:
        """Parse margin parameters from string"""
        margins = {}
        for param in params_str.split(','):
            if '=' in param:
                key, value = param.split('=', 1)
                margins[key.strip()] = float(value.strip())
        return margins
    
    def _extract_custom_words(self, text: str) -> Dict[str, Dict]:
        """Extract custom word parameters from text"""
        custom_words = {}
        
        for match in re.finditer(self.patterns['word'], text):
            params_str = match.group(1)
            word = match.group(2)
            
            params = {}
            for param in params_str.split(','):
                if '=' in param:
                    key, value = param.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    if key == 'bias':
                        params['bias'] = float(value)
                    elif key == 'style':
                        params['style'] = int(value)
            
            custom_words[word] = params
            
        return custom_words
    
    def _clean_text_for_preview(self, text: str) -> str:
        """Clean markup tags from text for preview"""
        clean_text = text
        # Remove word tags
        clean_text = re.sub(self.patterns['word'], r'\2', clean_text)
        return clean_text.strip()

class AdvancedHandwritingSynthesizer:
    """Advanced synthesizer with enhanced config system"""
    
    def __init__(self, checkpoint_dir: str = 'checkpoints'):
        self.text_processor = TextProcessor()
        self.handwriting_engine = HandwritingEngine(checkpoint_dir)
        self.document_renderer = DocumentRenderer()
        self.markup_processor = EnhancedMarkupProcessor()
        self.word_manager = WordRegenerationManager()
        
        # Use the enhanced config system
        self.doc_config = document_config
        
        # Store current document state for regeneration
        self.current_markup = ""
        self.current_margins = None
        self.current_output_name = ""
        
    def preview_document(self, markup_text: str) -> List[Dict]:
        """Preview document structure"""
        return self.markup_processor.preview_markup(markup_text)
    
    def regenerate_word_multiple(self, word: str, bias: float = None, style: int = None, attempts: int = 3) -> List[Dict]:
        """Generate multiple versions of a word"""
        versions = []
        
        base_bias = bias or rnn_config.default_bias
        base_style = style or rnn_config.default_style
        
        for i in range(attempts):
            # Vary parameters slightly for each attempt
            attempt_bias = base_bias + (i * 0.2 - 0.2)
            attempt_style = base_style + (i * 2 - 2)
            
            # Clear cache for this specific combination
            cache_key = f"{word}_{attempt_bias}_{attempt_style}"
            if hasattr(self.handwriting_engine, '_stroke_cache'):
                self.handwriting_engine._stroke_cache.pop(cache_key, None)
            
            strokes, width = self.handwriting_engine.generate_word_strokes(word, attempt_bias, attempt_style)
            
            versions.append({
                'bias': float(attempt_bias),  # Convert to Python float
                'style': int(attempt_style),  # Convert to Python int
                'width': float(width),        # Convert to Python float
                'version': i + 1
            })
        
        return versions
    
    def apply_word_regeneration(self, word: str, bias: float, style: int) -> Dict[str, Any]:
        """Apply word regeneration and re-synthesize the document"""
        if not self.current_markup:
            return {'success': False, 'error': 'No current document to regenerate'}
        
        # Add word override
        self.word_manager.add_word_override(word, bias, style)
        
        # Re-synthesize the document with the same parameters
        result = self.synthesize_document_with_markup(
            markup_text=self.current_markup,
            custom_margins=self.current_margins,
            output_filename=f"output/{self.current_output_name}_regenerated_{int(time.time())}",
            progress_callback=None  # No progress callback for regeneration
        )
        
        return {
            'success': True,
            'result': result,
            'word_overrides': dict(self.word_manager.word_overrides)
        }
    
    def synthesize_document_with_markup(self, 
                                      markup_text: str,
                                      custom_margins: PageMargins = None,
                                      output_filename: str = None,
                                      progress_callback=None) -> Dict[str, Any]:
        """Synthesize document from markup text using enhanced processor"""
        
        # Store current state for regeneration
        self.current_markup = markup_text
        self.current_margins = custom_margins
        if output_filename:
            self.current_output_name = os.path.basename(output_filename)
        
        if output_filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"output/document_{timestamp}"
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_filename) if os.path.dirname(output_filename) else 'output', exist_ok=True)
        
        if progress_callback:
            progress_callback({'progress': 10, 'message': 'Processing markup text...'})
        
        # Update margins if provided
        if custom_margins:
            self.doc_config.margins = custom_margins
        
        # Use enhanced processing with proper markup handling
        try:
            processed_blocks = self._enhanced_process_markup(markup_text)
        except Exception as e:
            print(f"Error in markup processing: {e}")
            # Fallback to simple processing
            processed_blocks = self._fallback_process_text(markup_text)
        
        if progress_callback:
            progress_callback({'progress': 30, 'message': f'Processing {len(processed_blocks)} blocks...'})
        
        # Generate handwriting for all blocks
        all_line_layouts = []
        total_blocks = len(processed_blocks)
        
        current_line_number = 0
        current_page = 1
        
        for block_idx, block_info in enumerate(processed_blocks):
            if progress_callback:
                progress = 30 + (block_idx / total_blocks) * 50
                progress_callback({'progress': int(progress), 'message': f'Processing block {block_idx + 1}/{total_blocks}...'})
            
            # Handle special blocks
            if block_info.get('type') == 'page_break':
                current_page += 1
                current_line_number = 0
                continue
            elif block_info.get('type') == 'line_break':
                current_line_number += 1
                if current_line_number >= self.doc_config.num_lines:
                    current_page += 1
                    current_line_number = 0
                continue
            
            # Apply custom margins if specified
            if block_info.get('margins'):
                self._apply_custom_margins(block_info['margins'])
            
            # Determine page type
            page_type = PageType.ODD if current_page % 2 == 1 else PageType.EVEN
            
            # Get page-specific margins and text area
            text_area_x, text_area_y, text_area_width, text_area_height = self.doc_config.get_text_area(page_type)
            
            # Process text into words and lines
            words = re.findall(r'\S+', block_info['text'])
            
            # Fit words into lines
            remaining_words = words
            while remaining_words and current_line_number < self.doc_config.num_lines:
                # Fit words to current line
                fitted_words, remaining_words = self._fit_words_to_line(
                    remaining_words, text_area_width, block_info['style']
                )
                
                if not fitted_words:
                    # Skip problematic word
                    if remaining_words:
                        print(f"Warning: Skipping word '{remaining_words[0]}' (too long)")
                        remaining_words = remaining_words[1:]
                    continue
                
                # Generate strokes for words in this line
                strokes_list = []
                for word in fitted_words:
                    # Get effective style parameters
                    bias = block_info['style'].bias
                    style_id = block_info['style'].style
                    
                    # Check for word-level overrides
                    bias, style_id = self.word_manager.get_word_parameters(word, bias, style_id)
                    
                    # Generate strokes
                    strokes, _ = self.handwriting_engine.generate_word_strokes(word, bias, style_id)
                    strokes_list.append(strokes)
                
                # Create line layout
                line_layout = self._create_simple_line_layout(
                    word_texts=fitted_words,
                    strokes_list=strokes_list,
                    line_number=current_line_number,
                    style=block_info['style'],
                    text_area_x=text_area_x,
                    text_area_y=text_area_y,
                    text_area_width=text_area_width,
                    page_number=current_page
                )
                
                all_line_layouts.append(line_layout)
                current_line_number += 1
                
                # Check if we need a new page
                if current_line_number >= self.doc_config.num_lines:
                    current_page += 1
                    current_line_number = 0
        
        if progress_callback:
            progress_callback({'progress': 80, 'message': 'Rendering document...'})
        
        # Render document
        svg_filename = self.document_renderer.render_to_svg(
            line_layouts=all_line_layouts,
            filename=output_filename
        )
        
        if progress_callback:
            progress_callback({'progress': 90, 'message': 'Creating metadata...'})
        
        # Create metadata
        metadata = {
            'timestamp': datetime.now().isoformat(),
            'total_pages': max(1, (len(all_line_layouts) // self.doc_config.num_lines) + 1),
            'total_lines': len(all_line_layouts),
            'margins': asdict(self.doc_config.margins),
            'word_overrides': dict(self.word_manager.word_overrides),
            'total_blocks': len(processed_blocks)
        }
        
        metadata_filename = f"{output_filename}_metadata.json"
        with open(metadata_filename, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        if progress_callback:
            progress_callback({'progress': 100, 'message': 'Complete!'})
        
        return {
            'svg_filename': svg_filename,
            'metadata_filename': metadata_filename,
            'metadata': metadata,
            'line_count': len(all_line_layouts),
            'page_count': metadata['total_pages']
        }
    
    def _enhanced_process_markup(self, markup_text: str) -> List[Dict]:
        """Enhanced markup processing with proper break and margin handling"""
        blocks = []
        remaining_text = markup_text
        
        while remaining_text.strip():
            # Check for page breaks
            page_break_match = re.match(r'\[page-break\]', remaining_text)
            if page_break_match:
                blocks.append({'type': 'page_break'})
                remaining_text = remaining_text[page_break_match.end():].strip()
                continue
            
            # Check for line breaks
            line_break_match = re.match(r'\[line-break\]', remaining_text)
            if line_break_match:
                blocks.append({'type': 'line_break'})
                remaining_text = remaining_text[line_break_match.end():].strip()
                continue
            
            # Extract regular text blocks
            block_info, remaining_text = self.markup_processor._extract_block_info(remaining_text)
            
            if block_info:
                blocks.append(block_info)
            else:
                # No more markup, add remaining text as body style
                if remaining_text.strip():
                    blocks.append({
                        'text': remaining_text.strip(),
                        'style': replace(PREDEFINED_STYLES['body'])
                    })
                break
        
        return blocks
    
    def _apply_custom_margins(self, margins: Dict[str, float]):
        """Apply custom margins to document config"""
        current_margins = asdict(self.doc_config.margins)
        current_margins.update(margins)
        self.doc_config.margins = PageMargins(**current_margins)
    
    def _simple_process_markup(self, markup_text: str) -> List[Dict]:
        """Simple markup processing that creates blocks with styles"""
        blocks = []
        remaining_text = markup_text
        
        while remaining_text.strip():
            block_info, remaining_text = self.markup_processor._extract_block_info(remaining_text)
            
            if block_info:
                blocks.append(block_info)
            else:
                # No more markup, add remaining text as body style
                if remaining_text.strip():
                    blocks.append({
                        'text': remaining_text.strip(),
                        'style': replace(PREDEFINED_STYLES['body'])
                    })
                break
        
        return blocks
    
    def _fallback_process_text(self, markup_text: str) -> List[Dict]:
        """Fallback text processing if everything else fails"""
        # Remove all markup and treat as plain text
        clean_text = re.sub(r'\[.*?\]', '', markup_text)
        
        return [{
            'text': clean_text.strip(),
            'style': replace(PREDEFINED_STYLES['body'])
        }]
    
    def _fit_words_to_line(self, words: List[str], max_width: float, style: TextStyle) -> Tuple[List[str], List[str]]:
        """Fit words to a line based on estimated widths"""
        fitted_words = []
        current_width = 0.0
        space_width = style.font_width * 0.3
        
        for i, word in enumerate(words):
            # Estimate word width
            word_width = len(word) * style.font_width * style.scale
            
            # Calculate total width including space
            total_width = current_width + word_width
            if fitted_words:  # Add space if not first word
                total_width += space_width
            
            if total_width <= max_width:
                fitted_words.append(word)
                current_width = total_width
            else:
                # Return fitted words and remaining
                return fitted_words, words[i:]
        
        # All words fit
        return fitted_words, []
    
    def _create_simple_line_layout(self, word_texts, strokes_list, line_number, style, 
                                 text_area_x, text_area_y, text_area_width, page_number=1):
        """Create line layout using simple positioning"""
        from core.document_renderer import LineLayout, WordLayout, PageType
        
        # Determine page type
        page_type = PageType.ODD if page_number % 2 == 1 else PageType.EVEN
        
        # Calculate line number within the page
        line_within_page = line_number % self.doc_config.num_lines
        
        # Calculate Y position within the page
        y_position = text_area_y + (line_within_page * self.doc_config.line_height)
        
        # Calculate word positions
        word_positions = self._calculate_simple_word_positions(
            word_texts, strokes_list, style.alignment, text_area_width, text_area_x, style
        )
        
        # Create word layouts
        word_layouts = []
        for word_text, strokes, x_pos in zip(word_texts, strokes_list, word_positions):
            word_width = self._calculate_stroke_width(strokes) if len(strokes) > 0 else 0
            
            # Apply style scaling
            scaled_strokes = strokes.copy() if len(strokes) > 0 else strokes
            if len(scaled_strokes) > 0:
                scaled_strokes[:, :2] *= style.scale
            
            word_layouts.append(WordLayout(
                text=word_text,
                strokes=scaled_strokes,
                x_position=x_pos,
                y_position=y_position,
                width=word_width * style.scale,
                page_number=page_number
            ))
        
        return LineLayout(
            words=word_layouts,
            line_number=line_within_page,
            alignment=style.alignment,
            y_position=y_position,
            page_number=page_number,
            page_type=page_type
        )
    
    def _calculate_simple_word_positions(self, word_texts, strokes_list, alignment, 
                                       text_area_width, text_area_x, style):
        """Calculate word positions with simple logic"""
        positions = []
        space_width = style.font_width * 0.3
        
        # Calculate actual word widths
        word_widths = []
        for word_text, strokes in zip(word_texts, strokes_list):
            if len(strokes) > 0:
                width = self._calculate_stroke_width(strokes) * style.scale
            else:
                width = len(word_text) * style.font_width * style.scale
            word_widths.append(width)
        
        total_word_width = sum(word_widths)
        total_space_width = (len(word_widths) - 1) * space_width if len(word_widths) > 1 else 0
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
            if len(word_widths) == 1:
                positions.append(text_area_x)
            else:
                available_space = text_area_width - total_word_width
                space_between_words = available_space / (len(word_widths) - 1) if len(word_widths) > 1 else 0
                
                x_pos = text_area_x
                for word_width in word_widths:
                    positions.append(x_pos)
                    x_pos += word_width + space_between_words
        
        return positions
    
    def _calculate_stroke_width(self, strokes):
        """Calculate width of stroke array"""
        if len(strokes) == 0:
            return 0.0
        return abs(strokes[-1, 0] - strokes[0, 0])

# Flask Web Application
app = Flask(__name__)
app.secret_key = 'handwriting_synthesizer_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global synthesizer instance
synthesizer = None
active_tasks = {}

# Built-in templates
TEMPLATES = {
    'markup_demo': """[style:title]Markup Demonstration Document[/style]

[style:body]This document demonstrates all the markup features including margins, breaks, and word customization.[/style]

[style:heading1]Page and Line Breaks[/style]

[style:body]This is the first paragraph on page 1.[/style]

[line-break]

[style:body]This text appears after a line break.[/style]

[page-break]

[style:heading1]Page 2 Content[/style]

[style:body]This content appears on page 2 after the page break.[/style]

[style:heading1]Custom Word Styling[/style]

[style:body]Here is some text with [word:bias=1.5,style=15]custom[/word] word parameters. The word "custom" should have different handwriting characteristics.[/style]

[style:heading1]Margin Control[/style]

[margin:odd_left=5.0,odd_right=2.0]
[style:body]This paragraph uses custom margins with wider left margin on odd pages.[/style]
[/margin]

[style:heading1]Alignment Examples[/style]

[align:left]This text is left-aligned.[/align]

[align:center]This text is centered on the page.[/align]

[align:right]This text is right-aligned.[/align]

[align:justify]This is justified text that should spread evenly across the full width of the text area with proper spacing between words.[/align]

[style:heading1]Bias Variations[/style]

[bias:1.0]This text uses bias 1.0 for very tight handwriting.[/bias]

[bias:2.0]This text uses bias 2.0 for normal handwriting.[/bias]

[bias:3.0]This text uses bias 3.0 for looser handwriting.[/bias]""",
    'simple_test': """[style:title]Simple Test Document[/style]

[style:body]This is a simple test document to verify the handwriting synthesis system is working properly.[/style]

[style:heading1]Section 1[/style]

[style:body]This section contains regular body text with standard formatting and alignment.[/style]

[align:center]This text is centered on the page.[/align]

[bias:1.5]This text uses a lower bias value for different handwriting characteristics.[/bias]""",

    'formal_letter': """[style:title]Formal Business Letter[/style]

[align:left]Your Name
Your Address
City, State ZIP Code
Email Address

Date

Recipient Name
Company Name
Address
City, State ZIP Code[/align]

[style:body]Dear [Recipient Name],

I am writing to [purpose of letter]. This letter serves to [explain the main point or request].

In the first paragraph, introduce yourself and state the purpose of your letter clearly.

The second paragraph should provide supporting details and any necessary background information.

In the final paragraph, summarize your request and indicate what action you would like the recipient to take.[/style]

[align:left]Sincerely,

Your Signature
Your Typed Name[/align]""",

    'margin_test': """[style:title]Margin Test Document[/style]

[style:body]This document demonstrates the flexible margin system. On odd pages, the left margin should be wider to accommodate binding. On even pages, the margins are mirrored.[/style]

[style:body]Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.[/style]

[style:body]Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum.[/style]"""
}

@socketio.on('connect')
def handle_connect():
    emit('connected', {'message': 'Connected to handwriting synthesizer'})

@app.route('/')
def index():
    return render_template('editor.html')

@app.route('/viewer')
def viewer():
    """SVG viewer page"""
    return render_template('viewer.html')

@app.route('/viewer/<filename>')
def view_document(filename):
    """View a specific document"""
    return render_template('viewer.html', filename=filename)

@app.route('/api/preview', methods=['POST'])
def api_preview():
    try:
        data = request.json
        markup_text = data.get('markup', '')
        
        preview = synthesizer.preview_document(markup_text)
        
        # Count words
        word_count = 0
        for block in preview:
            if block['type'] == 'text':
                words = block['text'].split()
                word_count += len(words)
        
        return jsonify({
            'success': True,
            'preview': preview,
            'word_count': word_count
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/apply_word_regeneration', methods=['POST'])
def api_apply_word_regeneration():
    try:
        data = request.json
        word = data.get('word')
        bias = data.get('bias')
        style = data.get('style')
        
        if not all([word, bias is not None, style is not None]):
            return jsonify({'success': False, 'error': 'Missing parameters'}), 400
        
        result = synthesizer.apply_word_regeneration(word, float(bias), int(style))
        
        if result['success']:
            # Extract just the filename without path for the viewer
            svg_filename = os.path.basename(result['result']['svg_filename'])
            result['svg_filename'] = svg_filename
            result['viewer_url'] = f'/viewer/{svg_filename}'
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/templates')
def api_templates():
    return jsonify({
        'templates': list(TEMPLATES.keys()),
        'template_data': TEMPLATES
    })

@app.route('/api/synthesize', methods=['POST'])
def api_synthesize():
    try:
        data = request.json
        markup_text = data.get('markup', '')
        output_name = data.get('output_name', f'document_{int(time.time())}')
        margins_data = data.get('margins', {})
        
        # Create custom margins if provided
        custom_margins = None
        if margins_data:
            custom_margins = PageMargins(**margins_data)
        
        task_id = str(uuid.uuid4())
        
        # Store task data
        active_tasks[task_id] = {
            'status': 'processing',
            'progress': 0,
            'message': 'Starting synthesis...'
        }
        
        def process_document():
            try:
                def progress_callback(update):
                    active_tasks[task_id].update(update)
                    socketio.emit('synthesis_update', {
                        'task_id': task_id,
                        'status': 'processing',
                        **update
                    })
                
                result = synthesizer.synthesize_document_with_markup(
                    markup_text=markup_text,
                    custom_margins=custom_margins,
                    output_filename=f"output/{output_name}",
                    progress_callback=progress_callback
                )
                
                # Extract just the filename without path for the viewer
                svg_filename = os.path.basename(result['svg_filename'])
                
                active_tasks[task_id] = {
                    'status': 'completed',
                    'progress': 100,
                    'message': 'Synthesis complete!',
                    'result': result,
                    'svg_filename': svg_filename,
                    'viewer_url': f'/viewer/{svg_filename}'
                }
                
                socketio.emit('synthesis_update', {
                    'task_id': task_id,
                    'status': 'completed',
                    'progress': 100,
                    'message': 'Synthesis complete!',
                    'result': result,
                    'svg_filename': svg_filename,
                    'viewer_url': f'/viewer/{svg_filename}'
                })
                
            except Exception as e:
                error_msg = f'Error: {str(e)}'
                print(f"Synthesis error: {e}")
                
                active_tasks[task_id] = {
                    'status': 'error',
                    'progress': 0,
                    'message': error_msg
                }
                
                socketio.emit('synthesis_update', {
                    'task_id': task_id,
                    'status': 'error',
                    'progress': 0,
                    'message': error_msg
                })
        
        threading.Thread(target=process_document).start()
        
        return jsonify({'success': True, 'task_id': task_id})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/regenerate_word', methods=['POST'])
def api_regenerate_word():
    try:
        data = request.json
        word = data.get('word')
        bias = data.get('bias')
        style = data.get('style')
        attempts = data.get('attempts', 3)
        
        versions = synthesizer.regenerate_word_multiple(word, bias, style, attempts)
        
        return jsonify({
            'success': True,
            'versions': versions
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/documents')
def api_list_documents():
    """List all generated documents"""
    try:
        output_dir = 'output'
        if not os.path.exists(output_dir):
            return jsonify({'documents': []})
        
        documents = []
        for filename in os.listdir(output_dir):
            if filename.endswith('.svg'):
                file_path = os.path.join(output_dir, filename)
                metadata_path = file_path.replace('.svg', '_metadata.json')
                
                doc_info = {
                    'filename': filename,
                    'name': filename.replace('.svg', ''),
                    'created': datetime.fromtimestamp(os.path.getctime(file_path)).isoformat(),
                    'size': os.path.getsize(file_path)
                }
                
                # Add metadata if available
                if os.path.exists(metadata_path):
                    try:
                        with open(metadata_path, 'r') as f:
                            metadata = json.load(f)
                            doc_info.update({
                                'total_pages': metadata.get('total_pages', 1),
                                'total_lines': metadata.get('total_lines', 0),
                                'timestamp': metadata.get('timestamp')
                            })
                    except:
                        pass
                
                documents.append(doc_info)
        
        # Sort by creation date, newest first
        documents.sort(key=lambda x: x['created'], reverse=True)
        
        return jsonify({'documents': documents})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/svg/<filename>')
def api_get_svg(filename):
    """Get SVG content for viewing"""
    try:
        file_path = os.path.join('output', filename)
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()
            return jsonify({'svg_content': svg_content})
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/output/<filename>')
def serve_output_file(filename):
    """Serve files from output directory"""
    return send_from_directory('output', filename)

@app.route('/api/download/<filename>')
def api_download(filename):
    try:
        file_path = os.path.join('output', filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def run_web_app(checkpoint_dir='checkpoints', host='127.0.0.1', port=5000, debug=False):
    """Run the Flask web application"""
    global synthesizer
    
    print("Initializing handwriting synthesizer...")
    synthesizer = AdvancedHandwritingSynthesizer(checkpoint_dir)
    
    # Create directories
    os.makedirs('templates', exist_ok=True)
    os.makedirs('output', exist_ok=True)
    
    print(f"Starting web server on http://{host}:{port}")
    print(f"Document viewer available at http://{host}:{port}/viewer")
    socketio.run(app, host=host, port=port, debug=debug)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Advanced Handwriting Synthesizer")
    parser.add_argument("--web", action="store_true", help="Run web interface")
    parser.add_argument("--host", default="127.0.0.1", help="Web host")
    parser.add_argument("--port", type=int, default=5000, help="Web port")
    parser.add_argument("--input", help="Input markup file")
    parser.add_argument("--output", help="Output filename")
    parser.add_argument("--checkpoint-dir", default="checkpoints", help="Model checkpoint directory")
    
    args = parser.parse_args()
    
    if args.web:
        run_web_app(args.checkpoint_dir, args.host, args.port)
    elif args.input:
        synthesizer = AdvancedHandwritingSynthesizer(args.checkpoint_dir)
        
        with open(args.input, 'r', encoding='utf-8') as f:
            markup_text = f.read()
        
        result = synthesizer.synthesize_document_with_markup(
            markup_text=markup_text,
            output_filename=args.output
        )
        
        print(f"Document generated: {result['svg_filename']}")
        synthesizer.handwriting_engine.close()
    else:
        print("Use --web for web interface or --input for CLI processing")