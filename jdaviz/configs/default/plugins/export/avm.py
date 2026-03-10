
import os
import numpy as np
from PIL import Image

from astropy.wcs.utils import fit_wcs_from_points
from pyavm import AVM


def png_to_jpg_avm(viz, viewer, png_filename):
    """Convert a PNG screenshot to JPG with Astronomy Visualization Metadata (AVM).

    Parameters
    ----------
    viz : jdaviz.configs.imviz.helper.Imviz
        Imviz helper.
    viewer : jdaviz.configs.imviz.plugins.viewers.ImvizImageVew
        Glue viewer exported in the PNG screenshot screenshot
    png_filename : path-like, str
        Path to PNG screenshot
    """
    # open temporary PNG
    img = Image.open(png_filename)
    png_shape = img.size

    # get the viewer limits in refdata pixel coords
    refdata_wcs = viewer.state.reference_data.coords
    xy_ref = (
        np.array([
            viewer.state.x_min,
            viewer.state.x_min,
            viewer.state.x_max,
            viewer.state.x_max,
            0.5 * (viewer.state.x_min + viewer.state.x_max)]),
        np.array([
            viewer.state.y_min,
            viewer.state.y_max,
            viewer.state.y_min,
            viewer.state.y_max,
            0.5 * (viewer.state.y_min + viewer.state.y_max)]),
    )
    # pixel coordinates for the corners and center of the image
    xy_png = (
        np.array([0, 0, png_shape[0], png_shape[0], png_shape[0] / 2]),
        np.array([0, png_shape[1], 0, png_shape[1], png_shape[1] / 2])
    )

    # convert observation pixel coords to world
    world = refdata_wcs.pixel_to_world(*xy_ref)

    # fit for WCS using these five points
    png_wcs = fit_wcs_from_points(xy_png, world, proj_point=world[0])

    # assemble AVM with this WCS:
    png_avm = AVM().from_wcs(png_wcs, png_shape)

    # add AVM tags required for the aladin-lite parser:
    png_avm.Creator = 'jdaviz'
    png_avm.Rights = ''
    png_avm.Credit = ''
    png_avm.ID = ''
    png_avm.MetadataDate = ''

    jpg_path = str(png_filename).replace('.png', '.jpg')

    try:
        jpg_path_tmp = str(png_filename).replace('.png', '_tmp.jpg')

        # write out temporary JPG (drop alpha channel)
        img.convert('RGB').save(jpg_path_tmp)

        # embed AVM into final JPG
        png_avm.embed(jpg_path_tmp, jpg_path, verify=True)
    finally:
        # ensure tmp file gets removed
        os.remove(jpg_path_tmp)
