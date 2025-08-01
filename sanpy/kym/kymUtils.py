import numpy as np
from sanpy.sanpyLogger import get_logger


logger = get_logger(__name__)

# found 20240925 at
# https://forum.image.sc/t/macro-for-image-adjust-brightness-contrast-auto-button/37157/5

# Python rewriting of ImageJ's auto-threshold option (Image > Adjust > Brightness/Contrast > 'Auto' button)
# Based on https://github.com/imagej/ImageJ/blob/706f894269622a4be04053d1f7e1424094ecc735/ij/plugin/frame/ContrastAdjuster.java#L780
# (function autoAdjust)
# The algorithm is basically a contrast setting the max white value to the max of the image (and same for black for
# min), with some saturation : i.e., it's not the max(min) of the image which is actually used but a lower(higher)
# value to eliminate the thin "tails" of the histogram and get an output dynamic range which allows for good
# visualisation of most of the image's pixels (at the expense of a few saturated pixels).
# While some (most ?) algorithms parametrize this saturation to eliminate a set percentage of pixels,
# ImageJ's algorithm selects the closest values to the max(min) values whose count are over a certain proportion of the
# total amount of pixels.


def getAutoContrast(imgData: np.ndarray):

    im = imgData

    im_type = im.dtype
    im_min = np.min(im)
    im_max = np.max(im)

    # converting image =================================================================================================

    # case of color image : contrast is computed on image cast to grayscale
    if len(im.shape) == 3 and im.shape[2] == 3:
        # depending on the options you chose in ImageJ, conversion can be done either in a weighted or unweighted way
        # go to Edit > Options > Conversion to verify if the "Weighted RGB conversion" box is checked.
        # if it's not checked, use this line
        # im = np.mean(im, axis = -1)
        # instead of the following
        im = 0.3 * im[:, :, 2] + 0.59 * im[:, :, 1] + 0.11 * im[:, :, 0]
        im = im.astype(im_type)

    # histogram computation =============================================================================================

    # parameters of histogram computation depend on image dtype.
    # following https://imagej.nih.gov/ij/developer/macro/functions.html#getStatistics
    # 'The histogram is returned as a 256 element array. For 8-bit and RGB images, the histogram bin width is one.
    # for 16-bit and 32-bit images, the bin width is (max-min)/256.'
    if im_type in (np.uint8, np.int8):  # abb np.int8
        hist_min = 0
        hist_max = 256
    elif im_type in (np.uint16, np.int16, np.int32):
        # use img min/max
        hist_min = im_min
        hist_max = im_max
    else:
        raise NotImplementedError(f"Not implemented for dtype {im_type}. Acceptable dtypes are: np.uint8, np.int8, np.uint16, np.int16, np.int32")

    # compute histogram
    histogram = np.histogram(im, bins=256, range=(hist_min, hist_max))[0]
    bin_size = (hist_max - hist_min) / 256

    # compute output min and max bins =================================================================================

    # various algorithm parameters
    h, w = im.shape[:2]
    pixel_count = h * w
    # the following values are taken directly from the ImageJ file.
    limit = pixel_count / 10
    const_auto_threshold = 5000
    auto_threshold = 0

    auto_threshold = (
        const_auto_threshold if auto_threshold <= 10 else auto_threshold / 2
    )
    threshold = int(pixel_count / auto_threshold)

    # setting the output min bin
    i = -1
    found = False
    # going through all bins of the histogram in increasing order until you reach one where the count if more than
    # pixel_count/auto_threshold
    # while not found and i <= 255:
    while not found and i < 255:
        i += 1

        try:
            count = histogram[i]
        except IndexError as e:
            logger.error(
                f'histogram.shape:{histogram.shape} i:{i} threshold:{threshold} {e}'
            )
            logger.error(
                f'  hist_min:{hist_min} hist_max:{hist_max} threshold:{threshold} {e}'
            )

        if count > limit:
            count = 0
        found = count > threshold
    hmin = i
    found = False

    # setting the output max bin : same thing but starting from the highest bin.
    i = 256
    while not found and i > 0:
        i -= 1
        count = histogram[i]
        if count > limit:
            count = 0
        found = count > threshold
    hmax = i

    # compute output min and max pixel values from output min and max bins ===============================================
    if hmax >= hmin:
        min_ = hist_min + hmin * bin_size
        max_ = hist_min + hmax * bin_size
        # bad case number one, just return the min and max of the histogram
        if min_ == max_:
            min_ = hist_min
            max_ = hist_max
    # bad case number two, same
    else:
        min_ = hist_min
        max_ = hist_max

    # apply the contrast ================================================================================================
    # imr = (im-min_)/(max_-min_) * 255

    # return imr
    min_ = int(min_)
    max_ = int(max_)

    logger.info(f'min_:{min_} max_:{max_}')

    return min_, max_
