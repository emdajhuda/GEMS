# v1.0
# plots/array_plot.py
# set of functions that plot array results

import matplotlib.pyplot as plt
import numpy as np

from matplotlib import cm

###################################################################################################
def pixel_intensity(image_array_list, y_positions_pixel, image_ref=False,
                    save_path=None, colormap='tab10', ind=0):
    """
    Plot the pixel intensity along the X-axis for given Y-pixel positions in an image.

    Parameters
    ----------
    image_array : numpy.ndarray
        2D image array containing pixel intensity values.
    y_positions_pixel : int or list of int
        Single Y-pixel position or a list of Y-pixel positions to analyze.
    image_ref : bool
        If True, the reference image will be shown at the first panel.
    save_path : str, optional
        If provided, the figure will be saved at this path instead of being displayed.
    colormap : str
        Name of the matplotlib colormap to assign distinct colors to each curve.
    ind : int, optional
        Index used as referential imagen from image_array_list
    """
    

    # Ensure y_positions_pixel is a list (even if a single int was passed)
    if isinstance(y_positions_pixel, int):
        y_positions_pixel = [y_positions_pixel]

    # number of subplots to create: ref + len(y_positions_pixel)
    npanels = 1 + len(y_positions_pixel) if image_ref else len(y_positions_pixel)
      
    # Create subplots: one row with npanels columns
    fig, axes = plt.subplots(1, npanels, figsize=(npanels * 5, 4))

    # Ensure axes is iterable (if npanels == 1, make it a list)
    if npanels == 1:
        axes = [axes]
    
    # Colormap
    cmap = cm.get_cmap(colormap, len(y_positions_pixel))
    lines = ['-', ':', '.-','--']
    colors = []

    
    # Loop over each subplot axis
    axes_intensity = axes[1:] if image_ref else axes
    colors = []
    for i, ax in enumerate(axes_intensity):
        y_pixel = y_positions_pixel[i]

        # Plot the pixel intensity along the X-axis for the given Y position
        color = cmap(i)
        maxpixel = np.max(image_array_list)
        for j, image_array in enumerate(image_array_list):
            line = lines[j]
            ax.plot(image_array[y_pixel, :]/maxpixel, label=rf'Y-Pixel: {y_pixel}', color=color, ls=line)  # line = 
        colors.append(color)  # Save color for later use # old line[0].get_color()

        # Add legend without frame
        ax.legend(frameon=False)

        # Label axes
        ax.set_xlabel(r'X-pixel')
        ax.set_ylabel(r'Pixel Intensity Profile')
    
    if image_ref:
        vmin, vmax = np.nanpercentile(image_array_list[ind], 1), np.nanpercentile(image_array_list[ind], 99)
        axes[0].imshow(image_array_list[ind], origin='lower', cmap="gray", vmin=vmin, vmax=vmax)

        # draw the horizontal lines corresponding to the Y-pixel positions
        for (y_pixel, color) in zip(y_positions_pixel, colors):
            axes[0].axhline(y=y_pixel, color=color, linestyle='--', linewidth=2)
        
        axes[0].set_title("Reference Image", fontsize=12)
        axes[0].axis("off")

    # Adjust layout for better spacing
    plt.tight_layout()

    # Save or show the figure depending on argument
    if save_path is not None:
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        print(f"[INFO] Figure saved to {save_path}")        
    else:
        plt.show()
    
    # Free memory after plotting
    plt.close(fig)
        
    return None