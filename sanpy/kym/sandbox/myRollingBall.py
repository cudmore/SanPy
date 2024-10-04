import matplotlib.pyplot as plt
import numpy as np
import pywt

import tifffile

from skimage import data, restoration  # use util to invert if needed

def plot_result(image, background):
    fig, ax = plt.subplots(nrows=1, ncols=3)

    ax[0].imshow(image, cmap='gray')
    ax[0].set_title('Original image')
    ax[0].axis('off')

    ax[1].imshow(background, cmap='gray')
    ax[1].set_title('Background')
    ax[1].axis('off')

    ax[2].imshow(image - background, cmap='gray')
    ax[2].set_title('Result')
    ax[2].axis('off')

    fig.tight_layout()


# image = data.coins()

path = '/Users/cudmore/Dropbox/data/colin/sanAtp/ISAN Linescan 3.tif'
image = tifffile.imread(path)
if len(image.shape) > 2:
    image = image[:, :, 1]
# image = np.rot90(image)

_rollingBallRadius = 50
background = restoration.rolling_ball(image, radius=_rollingBallRadius)

print(f'   background:{background.shape} min:{np.min(background)} max:{np.max(background)} mean:{np.mean(background)}')

plot_result(image, background)
plt.show()