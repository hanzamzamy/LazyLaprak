"""
Core handwriting synthesis engine using the RNN model.
Handles word-by-word inference and stroke generation.
"""

import numpy as np
import tensorflow.compat.v1 as tf
from typing import List, Dict, Tuple, Optional
import os
import logging

# Disable TensorFlow v2 behavior and logging
tf.disable_v2_behavior()
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

from rnn import rnn
import drawing
from .config import rnn_config

class HandwritingEngine:
    """Core engine for generating handwriting strokes from text"""
    
    def __init__(self, checkpoint_dir: str = 'checkpoints', warm_start_step: int = 17900):
        """
        Initialize the handwriting engine.
        
        Args:
            checkpoint_dir: Directory containing model checkpoints
            warm_start_step: Step number to load for warm start
        """
        self.checkpoint_dir = checkpoint_dir
        self.warm_start_step = warm_start_step
        self._model = None
        self._session = None
        self._stroke_cache = {}  # Cache for generated strokes
        
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize the RNN model"""
        print("Initializing handwriting model...")
        
        # Suppress TensorFlow logging
        logging.getLogger('tensorflow').setLevel(logging.ERROR)
        
        self._model = rnn(
            log_dir='logs',
            checkpoint_dir=self.checkpoint_dir,
            prediction_dir='predictions',
            learning_rates=[.0001, .00005, .00002],
            batch_sizes=[32, 64, 64],
            patiences=[1500, 1000, 500],
            beta1_decays=[.9, .9, .9],
            validation_batch_size=32,
            optimizer='rms',
            num_training_steps=100000,
            warm_start_init_step=self.warm_start_step,
            regularization_constant=0.0,
            keep_prob=1.0,
            enable_parameter_averaging=False,
            min_steps_to_checkpoint=2000,
            log_interval=20,
            logging_level=logging.CRITICAL,
            grad_clip=10,
            lstm_size=rnn_config.lstm_size,
            output_mixture_components=rnn_config.output_mixture_components,
            attention_mixture_components=rnn_config.attention_mixture_components
        )
        
        # Restore the model
        self._model.restore()
        self._session = self._model.session
        print("Model initialized successfully")
    
    def generate_word_strokes(self, word: str, bias: float = None, style: int = None) -> Tuple[np.ndarray, float]:
        """
        Generate handwriting strokes for a single word.
        
        Args:
            word: The word to generate strokes for
            bias: RNN bias parameter (default from config)
            style: Style parameter (default from config)
            
        Returns:
            Tuple of (strokes, actual_width)
        """
        if bias is None:
            bias = rnn_config.default_bias
        if style is None:
            style = rnn_config.default_style
        
        # Check cache
        cache_key = f"{word}_{bias}_{style}"
        if cache_key in self._stroke_cache:
            return self._stroke_cache[cache_key]
        
        try:
            strokes = self._generate_strokes([word], [bias], [style])[0]
            
            # Process strokes
            strokes = self._process_strokes(strokes)
            
            # Calculate actual width
            if len(strokes) > 0:
                actual_width = strokes[-1, 0] - strokes[0, 0]
            else:
                actual_width = 0.0
            
            # Cache the result
            result = (strokes, actual_width)
            self._stroke_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            print(f"Error generating strokes for word '{word}': {e}")
            # Return empty strokes as fallback
            return np.array([[0, 0, 1]]), 0.0
    
    def _generate_strokes(self, words: List[str], biases: List[float], styles: List[int]) -> List[np.ndarray]:
        """Generate strokes for multiple words using the RNN model"""
        num_samples = len(words)
        max_tsteps = 100 * max(len(word) for word in words)
        
        # Prepare character arrays
        x_prime = np.zeros([num_samples, 1600, 3])
        x_prime_len = np.zeros([num_samples])
        chars = np.zeros([num_samples, 160])
        chars_len = np.zeros([num_samples])
        
        # Check if we should use style priming
        use_styles = any(style is not None for style in styles)
        
        if use_styles:
            for i, (word, style) in enumerate(zip(words, styles)):
                if style is not None:
                    try:
                        x_p = np.load(f'styles/style-{style}-strokes.npy')
                        c_p = np.load(f'styles/style-{style}-chars.npy').tostring().decode('utf-8')
                        c_p = str(c_p) + " " + word
                        c_p = drawing.encode_ascii(c_p)
                        c_p = np.array(c_p)
                        
                        x_prime[i, :len(x_p), :] = x_p
                        x_prime_len[i] = len(x_p)
                        chars[i, :len(c_p)] = c_p
                        chars_len[i] = len(c_p)
                    except FileNotFoundError:
                        print(f"Warning: Style {style} not found, using default")
                        encoded = drawing.encode_ascii(word)
                        chars[i, :len(encoded)] = encoded
                        chars_len[i] = len(encoded)
                else:
                    encoded = drawing.encode_ascii(word)
                    chars[i, :len(encoded)] = encoded
                    chars_len[i] = len(encoded)
        else:
            for i, word in enumerate(words):
                encoded = drawing.encode_ascii(word)
                chars[i, :len(encoded)] = encoded
                chars_len[i] = len(encoded)
        
        # Run the model
        [samples] = self._session.run(
            [self._model.sampled_sequence],
            feed_dict={
                self._model.prime: use_styles,
                self._model.x_prime: x_prime,
                self._model.x_prime_len: x_prime_len,
                self._model.num_samples: num_samples,
                self._model.sample_tsteps: max_tsteps,
                self._model.c: chars,
                self._model.c_len: chars_len,
                self._model.bias: biases
            }
        )
        
        # Clean up samples
        samples = [sample[~np.all(sample == 0.0, axis=1)] for sample in samples]
        return samples
    
    def _process_strokes(self, strokes: np.ndarray) -> np.ndarray:
        """Process raw strokes from the model"""
        if len(strokes) == 0:
            return strokes
        
        # Convert offsets to coordinates
        coords = drawing.offsets_to_coords(strokes)
        
        # Apply denoising
        coords = drawing.denoise(coords)
        
        # Align strokes
        coords[:, :2] = drawing.align(coords[:, :2])
        
        return coords
    
    def close(self):
        """Clean up resources"""
        if self._session:
            self._session.close()
        print("Handwriting engine closed")