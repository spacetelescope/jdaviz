# !/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Filename: data_identifiers.py
# Project: core
# Author: Brian Cherinka
# Created: Tuesday, 23rd June 2020 12:09:16 pm
# License: BSD 3-clause "New" or "Revised" License
# Copyright (c) 2020 Brian Cherinka
# Last Modified: Tuesday, 23rd June 2020 12:09:16 pm
# Modified By: Brian Cherinka


from __future__ import print_function, division, absolute_import
from astropy.io import fits
import contextlib

# TODO - decide where these identifiers should live (in specutils? or here)
# from specutils.io.default_loaders.jwst_reader import (identify_jwst_s2d_fits,
#                                                       identify_jwst_x1d_fits,
#                                                       identify_jwst_s3d_fits)

#
# copying JWST identify functions from specutils here since specutils versions are attached to
# classes whose identity must be passed in as first "origin" arguement. These are unnecessary here.
#


@contextlib.contextmanager
def openfile(filename):
    try:
        with fits.open(filename, memmap=False) as hdulist:
            yield hdulist
    except Exception:
        yield False


def _identify_jwst_fits(filename):
    """
    Check whether the given file is a JWST data product.
    """
    try:
        with fits.open(filename, memmap=False) as hdulist:
            return "ASDF" in hdulist and hdulist[0].header["TELESCOP"] == "JWST"
    # This probably means we didn't have a FITS file
    except Exception:
        return False


def identify_jwst_x1d_fits(filename):
    """
    Check whether the given file is a JWST x1d spectral data product.
    """
    is_jwst = _identify_jwst_fits(filename)
    with fits.open(filename, memmap=False) as hdulist:
        return (is_jwst and 'EXTRACT1D' in hdulist and ('EXTRACT1D', 2) not in hdulist
                and "SCI" not in hdulist)


def identify_jwst_s2d_fits(filename):
    """
    Check whether the given file is a JWST s2d spectral data product.
    """
    is_jwst = _identify_jwst_fits(filename)
    with fits.open(filename, memmap=False) as hdulist:
        return (is_jwst and "SCI" in hdulist and ("SCI", 2) not in hdulist
                and "EXTRACT1D" not in hdulist and len(hdulist["SCI"].data.shape) == 2)


def identify_jwst_s3d_fits(filename):
    """
    Check whether the given file is a JWST s3d spectral data product.
    """
    is_jwst = _identify_jwst_fits(filename)
    with fits.open(filename, memmap=False) as hdulist:
        return (is_jwst and "SCI" in hdulist and "EXTRACT1D" not in hdulist
                and len(hdulist["SCI"].data.shape) == 3)


def _identify_sdss_fits(filename):
    """
    Check whether the given file is a SDSS data product.
    """
    try:
        with fits.open(filename, memmap=False) as hdulist:
            return hdulist[0].header["TELESCOP"] == "SDSS 2.5-M"
    except Exception:
        return False


def identify_sdss_manga_cube_fits(filename):
    """
    Check whether the given file is a MaNGA LOGCUBE.
    """
    is_sdss = _identify_sdss_fits(filename)
    with fits.open(filename, memmap=False) as hdulist:
        return (is_sdss and "FLUX" in hdulist and hdulist[1].header['INSTRUME'] == 'MaNGA'
                and hdulist[1].header["NAXIS"] == 3)


def identify_generic_cube(filename):
    with fits.open(filename, memmap=False) as hdulist:
        return (hdulist[1].header["NAXIS"] == 3)


def identify_generic_fits_image(filename):
    with fits.open(filename, memmap=False) as hdulist:
        return (hdulist[1].header["NAXIS"] == 2)
