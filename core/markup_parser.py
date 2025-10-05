"""
Enhanced markup parser supporting multiple text styles and formatting.
"""

import re
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass

from .config import TextStyle, PREDEFINED_STYLES, TextAlignment

@dataclass
class TextBlock:
    """Represents a block of text with specific styling"""
    text: str
    style: TextStyle
    custom_words: Dict[str, Dict[str, Any]] = None  # Word-specific overrides
    
    def __post_init__(self):
        if self.custom_words is None:
            self.custom_words = {}

class MarkupParser:
    """
    Parser for custom markup language supporting multiple text styles.
    
    Supported markup:
    - [style:name]text[/style] - Apply predefined style
    - [align:left|center|right|justify]text[/align] - Override alignment
    - [bias:2.5]text[/bias] - Override bias
    - [word:bias=2.5,style=20]specific_word[/word] - Word-specific settings
    - [page-break] - Force page break
    - [line-break] - Force line break
    """
    
    def __init__(self):
        self.style_pattern = re.compile(r'\[style:(\w+)\](.*?)\[/style\]', re.DOTALL)
        self.align_pattern = re.compile(r'\[align:(left|center|right|justify)\](.*?)\[/align\]', re.DOTALL)
        self.bias_pattern = re.compile(r'\[bias:([\d.]+)\](.*?)\[/bias\]', re.DOTALL)
        self.word_pattern = re.compile(r'\[word:(.*?)\](.*?)\[/word\]')
        self.page_break_pattern = re.compile(r'\[page-break\]')
        self.line_break_pattern = re.compile(r'\[line-break\]')
        
    def parse(self, markup_text: str) -> List[TextBlock]:
        """Parse markup text into styled text blocks"""
        blocks = []
        
        # Split by page breaks first
        pages = self.page_break_pattern.split(markup_text)
        
        for page_text in pages:
            if not page_text.strip():
                continue
                
            page_blocks = self._parse_page(page_text)
            blocks.extend(page_blocks)
            
            # Add page break marker (except for last page)
            if page_text != pages[-1]:
                blocks.append(TextBlock(text="[PAGE_BREAK]", style=PREDEFINED_STYLES['body']))
        
        return blocks
    
    def _parse_page(self, page_text: str) -> List[TextBlock]:
        """Parse a single page of text"""
        blocks = []
        
        # Process different markup types in order of precedence
        remaining_text = page_text
        
        while remaining_text.strip():
            # Look for the next markup
            next_match, match_type = self._find_next_markup(remaining_text)
            
            if next_match is None:
                # No more markup, process remaining text as body
                if remaining_text.strip():
                    blocks.append(self._create_text_block(remaining_text, PREDEFINED_STYLES['body']))
                break
            
            # Add text before the markup (if any)
            before_text = remaining_text[:next_match.start()]
            if before_text.strip():
                blocks.append(self._create_text_block(before_text, PREDEFINED_STYLES['body']))
            
            # Process the markup
            if match_type == 'style':
                blocks.append(self._parse_style_block(next_match))
            elif match_type == 'align':
                blocks.append(self._parse_align_block(next_match))
            elif match_type == 'bias':
                blocks.append(self._parse_bias_block(next_match))
            elif match_type == 'line_break':
                blocks.append(TextBlock(text="[LINE_BREAK]", style=PREDEFINED_STYLES['body']))
            
            # Continue with remaining text
            remaining_text = remaining_text[next_match.end():]
        
        return blocks
    
    def _find_next_markup(self, text: str) -> Tuple[Optional[re.Match], Optional[str]]:
        """Find the next markup element in the text"""
        matches = [
            (self.style_pattern.search(text), 'style'),
            (self.align_pattern.search(text), 'align'),
            (self.bias_pattern.search(text), 'bias'),
            (self.line_break_pattern.search(text), 'line_break'),
        ]
        
        # Filter out None matches and find the earliest one
        valid_matches = [(match, match_type) for match, match_type in matches if match is not None]
        
        if not valid_matches:
            return None, None
        
        # Return the match that appears first in the text
        earliest_match = min(valid_matches, key=lambda x: x[0].start())
        return earliest_match
    
    def _parse_style_block(self, match: re.Match) -> TextBlock:
        """Parse a style block [style:name]text[/style]"""
        style_name = match.group(1)
        text_content = match.group(2)
        
        style = PREDEFINED_STYLES.get(style_name, PREDEFINED_STYLES['body']).copy()
        
        # Process word-specific overrides within the block
        custom_words = self._extract_word_overrides(text_content)
        
        # Remove word markup from text
        clean_text = self.word_pattern.sub(r'\2', text_content)
        
        return TextBlock(text=clean_text, style=style, custom_words=custom_words)
    
    def _parse_align_block(self, match: re.Match) -> TextBlock:
        """Parse an alignment block [align:direction]text[/align]"""
        align_name = match.group(1)
        text_content = match.group(2)
        
        style = PREDEFINED_STYLES['body'].copy()
        style.alignment = TextAlignment(align_name)
        
        custom_words = self._extract_word_overrides(text_content)
        clean_text = self.word_pattern.sub(r'\2', text_content)
        
        return TextBlock(text=clean_text, style=style, custom_words=custom_words)
    
    def _parse_bias_block(self, match: re.Match) -> TextBlock:
        """Parse a bias block [bias:value]text[/bias]"""
        bias_value = float(match.group(1))
        text_content = match.group(2)
        
        style = PREDEFINED_STYLES['body'].copy()
        style.bias = bias_value
        
        custom_words = self._extract_word_overrides(text_content)
        clean_text = self.word_pattern.sub(r'\2', text_content)
        
        return TextBlock(text=clean_text, style=style, custom_words=custom_words)
    
    def _extract_word_overrides(self, text: str) -> Dict[str, Dict[str, Any]]:
        """Extract word-specific style overrides"""
        custom_words = {}
        
        for match in self.word_pattern.finditer(text):
            params_str = match.group(1)
            word = match.group(2)
            
            # Parse parameters
            params = {}
            for param in params_str.split(','):
                if '=' in param:
                    key, value = param.strip().split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Convert values to appropriate types
                    if key in ['bias']:
                        params[key] = float(value)
                    elif key in ['style']:
                        params[key] = int(value)
                    else:
                        params[key] = value
            
            custom_words[word] = params
        
        return custom_words
    
    def _create_text_block(self, text: str, base_style: TextStyle) -> TextBlock:
        """Create a text block with word overrides processed"""
        custom_words = self._extract_word_overrides(text)
        clean_text = self.word_pattern.sub(r'\2', text)
        
        return TextBlock(text=clean_text, style=base_style, custom_words=custom_words)

# Example markup templates
MARKUP_TEMPLATES = {
    'academic_paper': """[style:title]Research Paper Title[/style]

[style:heading1]Abstract[/style]
[style:body]This is the abstract of the research paper. It provides a brief overview of the research objectives, methodology, and key findings.[/style]

[style:heading1]1. Introduction[/style]
[style:body]The introduction section provides background information and sets the context for the research.[/style]

[style:heading2]1.1 Research Objectives[/style]
[style:body]This subsection outlines the specific objectives of the research.[/style]

[style:heading1]2. Methodology[/style]
[style:body]This section describes the research methodology and approach used in the study.[/style]

[style:heading1]3. Results and Discussion[/style]
[style:body]The results section presents the findings of the research and discusses their implications.[/style]

[style:heading1]4. Conclusion[/style]
[style:body]The conclusion summarizes the key findings and suggests areas for future research.[/style]""",

    'business_letter': """[align:right]Your Company Name
Your Address
City, State ZIP Code
Date[/align]

[align:left]Recipient Name
Recipient Company
Recipient Address
City, State ZIP Code[/align]

[style:body]Dear Mr./Ms. [Recipient Name],[/style]

[style:body]This is the opening paragraph of your business letter. It should clearly state the purpose of your correspondence.[/style]

[style:body]This is the body paragraph where you provide additional details and supporting information.[/style]

[style:body]This is the closing paragraph that summarizes your main points and indicates the next steps or desired action.[/style]

[align:left]Sincerely,

Your Name
Your Title[/align]""",

    'report': """[style:title]Monthly Report[/style]
[align:center]Month Year[/align]

[style:heading1]Executive Summary[/style]
[style:body]This section provides a high-level overview of the key points covered in the report.[/style]

[style:heading1]Key Metrics[/style]
[style:body]This section presents the important metrics and data for the reporting period.[/style]

[style:heading2]Performance Indicators[/style]
[style:body]Detailed analysis of performance indicators and trends.[/style]

[style:heading1]Recommendations[/style]
[style:body]Based on the analysis, this section provides recommendations for improvement and future actions.[/style]"""
}