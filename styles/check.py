import numpy as np
import matplotlib.pyplot as plt

def plot_strokes(strokes, title="Handwriting Prime Data"):
    """
    Plots handwriting stroke data from a NumPy array.
    The input array is expected to have 3 columns:
    [x_offset, y_offset, end_of_stroke_flag]
    """
    # Calculate absolute coordinates by taking the cumulative sum of the offsets
    points = np.cumsum(strokes[:, :2], axis=0)

    # Find the indices where the pen was lifted
    # We add 1 to split the array *after* the pen lift point
    pen_lift_indices = np.where(strokes[:, 2] == 1)[0] + 1

    # Split the points array into a list of continuous strokes
    stroke_list = np.split(points, pen_lift_indices)

    # --- Plotting ---
    fig, ax = plt.subplots()

    # Plot each continuous stroke as a separate line
    for stroke in stroke_list:
        if stroke.shape[0] > 0: # Ensure the stroke segment is not empty
            ax.plot(stroke[:, 0], stroke[:, 1], 'b-')

    # Set plot aesthetics for better visualization
    ax.set_title(title)
    ax.set_aspect('equal', adjustable='box') # Ensure correct aspect ratio
    plt.axis('off') # Hide the axes for a cleaner look

    # Show the plot
    plt.show()

strokes = np.load("style-20-strokes.npy", allow_pickle=True)
print(strokes.shape)
chars = np.load("style-20-chars.npy", allow_pickle=True)
chars = str(chars)
plot_strokes(strokes, chars)
