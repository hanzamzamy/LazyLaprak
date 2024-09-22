![](img/banner.svg)
# Handwriting Synthesis
Implementation of the handwriting synthesis experiments in the paper <a href="https://arxiv.org/abs/1308.0850">Generating Sequences with Recurrent Neural Networks</a> by Alex Graves.  The implementation closely follows the original paper, with a few slight deviations, and the generated samples are of similar quality to those presented in the paper.

Web demo from original github (which I forked) is available <a href="https://seanvasquez.com/handwriting-generation/">here</a>.

## Usage
1. Paste your texts on input_text.txt
2. Run 'python block_to_lines.py', this will convert your texts into lines required for synthesizing
3. Run 'synthesize.py', wait for a few seconds (or minutes), there will be .svg and .gcode file on output folder according to the current time

Additionally you can configure the number of lines, font sizes, etc on config.py, you can also modify the style/bias for each lines for synthesizing by modifying the code on synthesize.py (too lazy to implement it on config.py)