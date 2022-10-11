from pathlib import Path

from specutils import Spectrum1D
from astropy.io import fits
import astropy.units as u
import numpy as np

from jdaviz.core.registries import data_parser_registry
from jdaviz.utils import standardize_metadata, PRIHDR_KEY

__all__ = ['spec2d_1d_parser']


def _check_is_file(path):
    return isinstance(path, str) and Path(path).is_file()


@data_parser_registry("spec2d-1d-parser")
def spec2d_1d_parser(app, data_obj, data_label=None, show_in_viewer=True):
    """
    Generate a quicklook 1D spectrum from an input 2D spectrum by summing
    over the cross-dispersion axis.

    Notes
    -----
    This currently only works with JWST-type data in which the data is in the
    second hdu of the fits file.

    Parameters
    ----------
    app : `~jdaviz.app.Application`
        The application-level object used to reference the viewers.
    data_obj : str or list or spectrum-like
        File path, list, or spectrum-like object to be read as a new row in
        the mosviz table.
    data_labels : str, optional
        The label applied to the glue data component.
    """
    if _check_is_file(data_obj):
        with fits.open(data_obj) as hdulist:
            data = hdulist[1].data
            header = hdulist[1].header
            prihdr = hdulist[0].header

        # Should only be 2D, so DISPAXIS-1 should be 0 or -1 and sum over the
        # correct axis. If Unit doesn't understand the BUNIT we leave flux
        # unitless
        try:
            flux = np.sum(data, header['DISPAXIS']-1)*u.Unit(header["BUNIT"])
        except ValueError:
            flux = u.Quantity(np.sum(data, header['DISPAXIS']-1))

        if "WAVEND" in header and "WAVSTART" in header:
            step = (header["WAVEND"] - header["WAVSTART"]) / flux.size
            spectral_axis = np.arange(header["WAVSTART"], header["WAVEND"],
                                      step) * u.m
        else:
            # u.Unit("m") is used if WAVEND and WAVSTART are present so
            # we use it here as well, even though the actual unit is pixels
            spectral_axis = np.arange(1, flux.size + 1, 1) * u.m

        metadata = standardize_metadata(header)
        metadata[PRIHDR_KEY] = standardize_metadata(prihdr)

        data_obj = Spectrum1D(flux, spectral_axis=spectral_axis, meta=metadata)

        data_label = app.return_data_label(data_label, alt_name="specviz2d_data")
        app.data_collection[data_label] = data_obj

    else:
        raise NotImplementedError("Spectrum2d parser only takes a filename")

    if show_in_viewer:
        app.add_data_to_viewer(
            app._default_spectrum_viewer_reference_name, data_label
        )
