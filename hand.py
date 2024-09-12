import drawing
from rnn import rnn
import numpy as np
import svgwrite


import logging
import os

import io
from PIL import Image, ImageDraw
import cairosvg
from const import *


def get_spaces(strokes, box_x, box_width, space_threshold, space_min_x_threshold):
    prev_eos = 1.0
    drawn_x_values = set()  # Set to keep track of drawn x values

    for x, y, eos in zip(*strokes.T):
        if eos == 0.0 and prev_eos != 1.0:
            drawn_x_values.add(int(x))
        prev_eos = eos
    
    # Calculate uninterrupted x_not_drawn lengths
    x_not_drawn = [x for x in range(box_x, box_x + box_width) if x not in drawn_x_values]
    uninterrupted_segments = []
    current_segment = []

    for i in range(len(x_not_drawn) - 1):
        if x_not_drawn[i] + 1 == x_not_drawn[i + 1]:
            current_segment.append(x_not_drawn[i])
        else:
            if current_segment:
                current_segment.append(x_not_drawn[i])
                uninterrupted_segments.append(current_segment)
            current_segment = []

    if current_segment:
        current_segment.append(x_not_drawn[-1])
        uninterrupted_segments.append(current_segment)

    # Identify segments that are spaces
    spaces = [segment for segment in uninterrupted_segments if len(segment) > space_threshold]
    if spaces and (spaces[0][0] - box_x) < space_min_x_threshold:
        del spaces[0]
    return spaces

class Hand(object):

    def __init__(self):
        os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
        self.nn = rnn(
            log_dir='logs',
            checkpoint_dir='checkpoints',
            prediction_dir='predictions',
            learning_rates=[.0001, .00005, .00002],
            batch_sizes=[32, 64, 64],
            patiences=[1500, 1000, 500],
            beta1_decays=[.9, .9, .9],
            validation_batch_size=32,
            optimizer='rms',
            num_training_steps=100000,
            warm_start_init_step=17900,
            regularization_constant=0.0,
            keep_prob=1.0,
            enable_parameter_averaging=False,
            min_steps_to_checkpoint=2000,
            log_interval=20,
            logging_level=logging.CRITICAL,
            grad_clip=10,
            lstm_size=400,
            output_mixture_components=20,
            attention_mixture_components=10
        )
        self.nn.restore()

    def write(self, filename, lines, biases=None, styles=None, stroke_colors=None, stroke_widths=None):
        valid_char_set = set(drawing.alphabet)
        for line_num, line in enumerate(lines):
            if len(line) > 75:
                raise ValueError(
                    (
                        "Each line must be at most 75 characters. "
                        "Line {} contains {}"
                    ).format(line_num, len(line))
                )

            for char in line:
                if char not in valid_char_set:
                    raise ValueError(
                        (
                            "Invalid character {} detected in line {}. "
                            "Valid character set is {}"
                        ).format(char, line_num, valid_char_set)
                    )

        strokes = self._sample(lines, biases=biases, styles=styles)
        self._draw(strokes, lines, filename, stroke_colors=stroke_colors, stroke_widths=stroke_widths)

    def _sample(self, lines, biases=None, styles=None):
        num_samples = len(lines)
        max_tsteps = 40*max([len(i) for i in lines])
        biases = biases if biases is not None else [0.5]*num_samples

        x_prime = np.zeros([num_samples, 1200, 3])
        x_prime_len = np.zeros([num_samples])
        chars = np.zeros([num_samples, 120])
        chars_len = np.zeros([num_samples])

        if styles is not None:
            for i, (cs, style) in enumerate(zip(lines, styles)):
                x_p = np.load('styles/style-{}-strokes.npy'.format(style))
                c_p = np.load('styles/style-{}-chars.npy'.format(style)).tostring().decode('utf-8')
                c_p = str(c_p) + " " + cs
                c_p = drawing.encode_ascii(c_p)
                c_p = np.array(c_p)
                x_prime[i, :len(x_p), :] = x_p
                x_prime_len[i] = len(x_p)
                chars[i, :len(c_p)] = c_p
                chars_len[i] = len(c_p)
                # print(drawing.decode_ascii(c_p))
                

        else:
            for i in range(num_samples):
                encoded = drawing.encode_ascii(lines[i])
                chars[i, :len(encoded)] = encoded
                chars_len[i] = len(encoded)

        [samples] = self.nn.session.run(
            [self.nn.sampled_sequence],
            feed_dict={
                self.nn.prime: styles is not None,
                self.nn.x_prime: x_prime,
                self.nn.x_prime_len: x_prime_len,
                self.nn.num_samples: num_samples,
                self.nn.sample_tsteps: max_tsteps,
                self.nn.c: chars,
                self.nn.c_len: chars_len,
                self.nn.bias: biases
            }
        )
        samples = [sample[~np.all(sample == 0.0, axis=1)] for sample in samples]
        
        return samples

    def _draw(self, strokes, lines, filename, stroke_colors=None, stroke_widths=None):
        stroke_colors = stroke_colors or ['black']*len(lines)
        stroke_widths = stroke_widths or [2]*len(lines)

        # Create the canvas for the SVG
        dwg = svgwrite.Drawing(filename=filename, size=(view_width, view_height))
        dwg.viewbox(width=view_width, height=view_height)
        dwg.add(dwg.rect(insert=(0, 0), size=(view_width, view_height), fill='white'))

        # Add the thin box to the SVG
        if draw_tatakan:
            dwg.add(dwg.rect(insert=(box_x, box_y), size=(box_width, box_height), stroke='black', fill='none', stroke_width=1))
        
        y_lines = [box_y + i * line_height_px for i in range(num_lines)]

        # Draw horizontal lines within the box
        for i in range(1, num_lines):
            y = box_y + i * line_height_px
            if draw_tatakan:
                dwg.add(dwg.line(start=(box_x, y), end=(box_x + box_width, y), stroke='black', stroke_width=0.5))

        initial_coord = np.array([horizontal_offset, -y_lines[0] - vertical_offset])        
        for iteration_number, (offsets, line, color, width) in enumerate(zip(strokes, lines, stroke_colors, stroke_widths)):
            if not line:
                initial_coord[1] -= line_height_px  # Move to the next line
                continue
            
            offsets[:, :2] *= text_scale
            strokes = drawing.offsets_to_coords(offsets)
            strokes = drawing.denoise(strokes)
            strokes[:, :2] = drawing.align(strokes[:, :2])

            strokes[:, 1] *= -1
            strokes[:, :2] -= strokes[:, :2].min() + initial_coord
            strokes[:, 0] += box_x  # Align to the left margin of the box
            
            if strokes[0,0] < box_x: # Avoid the first stroke clipping outside tatakan
                strokes[0,0] = box_x
            
            actual_length = strokes[-1, 0] - strokes[0, 0]
            approximate_length = approximate_line_length(line, font_width, char_widths)
            
            if approximate_length > actual_length:
                print(f"Warning: Approximate length ({approximate_length}) is longer than actual length ({actual_length}) on line {iteration_number + 1}")
            # else:
            #     print(f"Approximate length ({approximate_length}) is shorter than actual length ({actual_length}) on line {iteration_number + 1}")
            
            spaces = get_spaces(strokes, box_x, box_width, space_threshold, space_min_x_threshold)    
            
            # Calculate total offset needed
            total_offset = 0
            if len(spaces) > 1:
                last_word_end = strokes[-1, 0]
                total_offset = (box_x + box_width) - last_word_end

            # Find the index of the last word strokes
            last_word_start_index = None
            if len(spaces) > 1:
                second_last_space_end = spaces[-2][-1]
                for i in range(len(strokes)):
                    if strokes[i, 0] > second_last_space_end:
                        last_word_start_index = i
                        break

            # Apply the total offset to the last word
            if last_word_start_index is not None:
                for i in range(last_word_start_index, len(strokes)):
                    strokes[i, 0] += total_offset
            
            # Recalculate the spaces
            spaces = get_spaces(strokes, box_x, box_width, space_threshold, space_min_x_threshold)
            
            
            # Distribute the offset across the strokes between the first and last word
            current_offset = 0
            space_index = 0
            num_spaces = len(spaces) - 1  # Exclude the last space

            for i in range(len(strokes)):
                if space_index < num_spaces and strokes[i, 0] > spaces[space_index][-1]:
                    current_offset += total_offset / num_spaces
                    space_index += 1
                if last_word_start_index is not None and i < last_word_start_index:
                    strokes[i, 0] += current_offset

            prev_eos = 1.0
            p = "M{},{} ".format(0, 0)
            for x, y, eos in zip(*strokes.T):
                p += '{}{},{} '.format('M' if prev_eos == 1.0 else 'L', x, y)
                prev_eos = eos
            
            path = svgwrite.path.Path(p)
            path = path.stroke(color=color, width=width, linecap='round').fill("none")
            dwg.add(path)

            initial_coord[1] -= line_height_px  # Move to the next line

        dwg.save()