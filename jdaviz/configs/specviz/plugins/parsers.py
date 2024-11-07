import os
import pathlib
from collections import defaultdict

import numpy as np
from astropy.io.registry import IORegistryError
from astropy.nddata import StdDevUncertainty
from astropy.io import fits
from specutils import Spectrum1D, SpectrumList, SpectrumCollection

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import data_parser_registry
from jdaviz.utils import standardize_metadata, download_uri_to_path


__all__ = ["specviz_spectrum1d_parser"]


@data_parser_registry("specviz-spectrum1d-parser")
def specviz_spectrum1d_parser(app, data, data_label=None, format=None, show_in_viewer=True,
                              concat_by_file=False, cache=None, local_path=os.curdir, timeout=None,
                              load_as_list=False):
    """
    Loads a data file or `~specutils.Spectrum1D` object into Specviz.

    Parameters
    ----------
    data : str, `~specutils.Spectrum1D`, or `~specutils.SpectrumList`
        Spectrum1D, SpectrumList, or path to compatible data file.
    data_label : str
        The Glue data label found in the ``DataCollection``.
    format : str
        Loader format specification used to indicate data format in
        `~specutils.Spectrum1D.read` io method.
    concat_by_file : bool
        If True and there is more than one available extension, concatenate
        the extensions within each spectrum file passed to the parser and
        add a concatenated spectrum to the data collection.
    cache : None, bool, or str
        Cache the downloaded file if the data are retrieved by a query
        to a URL or URI.
    local_path : str, optional
        Cache remote files to this path. This is only used if data is
        requested from `astroquery.mast`.
    timeout : float, optional
        If downloading from a remote URI, set the timeout limit for
        remote requests in seconds (passed to
        `~astropy.utils.data.download_file` or
        `~astroquery.mast.Conf.timeout`).
    load_as_list : bool, optional
        Force the parser to load the input file with the `~specutils.SpectrumList` read function
        instead of `~specutils.Spectrum1D`.
    """

    spectrum_viewer_reference_name = app._jdaviz_helper._default_spectrum_viewer_reference_name
    # If no data label is assigned, give it a unique name
    if not data_label:
        data_label = app.return_data_label(data, alt_name="specviz_data")
    # Still need to standardize the label
    elif isinstance(data_label, (list, tuple)):
        data_label = [app.return_data_label(label, alt_name="specviz_data") for label in data_label]  # noqa
    else:
        data_label = app.return_data_label(data_label, alt_name="specviz_data")

    if isinstance(data, SpectrumCollection):
        raise TypeError("SpectrumCollection detected."
                        " Please provide a Spectrum1D or SpectrumList")
    elif isinstance(data, Spectrum1D):
        # Handle the possibility of 2D spectra by splitting into separate spectra
        if data.flux.ndim == 1:
            data_label = [data_label]
            data = [data]
        elif data.flux.ndim == 2:
            data = split_spectrum_with_2D_flux_array(data)
            data_label = [f"{data_label} [{i}]" for i in range(len(data))]
    # No special processing is needed in this case, but we include it for completeness
    elif isinstance(data, SpectrumList):
        pass
    elif isinstance(data, list):
        # special processing for HDUList
        if isinstance(data, fits.HDUList):
            data = [Spectrum1D.read(data)]
            data_label = [data_label]
        else:
            # list treated as SpectrumList if not an HDUList
            data = SpectrumList.read(data, format=format)
    else:
        # try parsing file_obj as a URI/URL:
        data = download_uri_to_path(data, cache=cache, local_path=local_path, timeout=timeout)

        path = pathlib.Path(data)

        if path.is_dir() or load_as_list:
            data = SpectrumList.read(str(path), format=format)
            if data == []:
                raise ValueError(f"`specutils.SpectrumList.read('{str(path)}')` "
                                 "returned an empty list")
        elif path.is_file():
            try:
                data = Spectrum1D.read(str(path), format=format)
                if data.flux.ndim == 2:
                    data = split_spectrum_with_2D_flux_array(data)
                else:
                    data = [data]
                    data_label = [app.return_data_label(data_label, alt_name="specviz_data")]

            except IORegistryError:
                # Multi-extension files may throw a registry error
                data = SpectrumList.read(str(path), format=format)
        else:
            raise FileNotFoundError("No such file: " + str(path))

    # step through SpectrumList and convert any 2D spectra to 1D spectra
    if isinstance(data, SpectrumList):
        new_data = []
        for spec in data:
            if spec.flux.ndim == 2:
                new_data.extend(split_spectrum_with_2D_flux_array(spec))
            else:
                new_data.append(spec)
        data = SpectrumList(new_data)

        if not isinstance(data_label, (list, tuple)):
            data_label = [f"{data_label} [{i}]" for i in range(len(data))]
        elif len(data_label) != len(data):
            raise ValueError(f"Length of data labels list ({len(data_label)}) is different"
                             f" than length of list of data ({len(data)})")

        # these are used to build a combined spectrum with all
        # input spectra included (taken from https://github.com/spacetelescope/
        # dat_pyinthesky/blob/main/jdat_notebooks/MRS_Mstar_analysis/
        # JWST_Mstar_dataAnalysis_analysis.ipynb)
        wlallorig = []  # to collect wavelengths
        fnuallorig = []  # fluxes
        dfnuallorig = []  # and uncertanties (if present)

        for spec in data:
            for wlind in range(len(spec.spectral_axis)):
                wlallorig.append(spec.spectral_axis[wlind].value)
                fnuallorig.append(spec.flux[wlind].value)

                # because some spec in the list might have uncertainties and
                # others may not, if uncert is None, set to list of NaN. later,
                # if the concatenated list of uncertanties is all nan (meaning
                # they were all nan to begin with, or all None), it will be set
                # to None on the final Spectrum1D
                if spec.uncertainty is not None and spec.uncertainty[wlind] is not None:
                    dfnuallorig.append(spec.uncertainty[wlind].array)
                else:
                    dfnuallorig.append(np.nan)

    # if the entire uncert. array is Nan and the data is not, model fitting won't
    # work (more generally, if uncert[i] is nan/inf and flux[i] is not, fitting will
    # fail, but just deal with the all nan case here since it is straightforward).
    # set uncerts. to None if they are all nan/inf, and display a warning message.
    set_nans_to_none = False
    if isinstance(data, SpectrumList):
        uncerts = dfnuallorig  # alias these for clarity later on
        if uncerts is not None and not np.any(uncerts):
            uncerts = None
            set_nans_to_none = True
    else:
        if data[0].uncertainty is not None:
            uncerts_finite = np.isfinite(data[0].uncertainty.array)
            if not np.any(uncerts_finite):
                data[0].uncertainty = None
                set_nans_to_none = True

    if set_nans_to_none:
        # alert user that we have changed their all-nan uncertainty array to None
        msg = 'All uncertainties are nonfinite, replacing with uncertainty=None.'
        app.hub.broadcast(SnackbarMessage(msg, color="warning", sender=app))

    with app.data_collection.delay_link_manager_update():
        for i, spec in enumerate(data):
            # note: if SpectrumList, this is just going to be the last unit when
            # combined in the next block. should put a check here to make sure
            # units are all the same or collect them in a list?
            wave_units = spec.spectral_axis.unit
            flux_units = spec.flux.unit

            # Make metadata layout conform with other viz.
            spec.meta = standardize_metadata(spec.meta)

            app.add_data(spec, data_label[i])

            # handle display, with the SpectrumList special case in mind.
            if i == 0 and show_in_viewer:
                app.add_data_to_viewer(spectrum_viewer_reference_name, data_label[i])

        if concat_by_file and isinstance(data, SpectrumList):
            # If >1 spectra in the list were opened from the same FITS file,
            # group them by their original FITS filenames and add their combined
            # 1D spectrum to the DataCollection.
            unique_files = group_spectra_by_filename(app.data_collection)
            for filename, datasets in unique_files.items():
                if len(datasets) > 1:
                    spec = combine_lists_to_1d_spectrum(wlallorig, fnuallorig,
                                                        dfnuallorig, wave_units,
                                                        flux_units)

                    # Make metadata layout conform with other viz.
                    spec.meta = standardize_metadata(spec.meta)

                    label = f"Combined [{filename}]"
                    app.add_data(spec, label)

                    if show_in_viewer:
                        app.add_data_to_viewer(spectrum_viewer_reference_name, label)


def group_spectra_by_filename(datasets):
    """
    Organize the elements of a `~glue.core.data_collection.DataCollection` by the name of
    the FITS file they came from, if available via the header card "FILENAME".

    Parameters
    ----------
    datasets : `~glue.core.data_collection.DataCollection`
        Collection of datasets.

    Returns
    -------
    spectra_to_combine : dict
        Datasets of spectra organized by their filename.
    """
    spectra_to_combine = defaultdict(list)

    for data in datasets:
        filename = data.meta.get("FILENAME")
        spectra_to_combine[filename].append(data)

    return spectra_to_combine


def combine_lists_to_1d_spectrum(wl, fnu, dfnu, wave_units, flux_units):
    """
    Combine lists of 1D spectra into a composite `~specutils.Spectrum1D` object.

    Parameters
    ----------
    wl : list of `~astropy.units.Quantity`s
        Wavelength in each spectral channel
    fnu : list of `~astropy.units.Quantity`s
        Flux in each spectral channel
    dfnu : list of `~astropy.units.Quantity`s or None
        Uncertainty on each flux

    Returns
    -------
    spec : `~specutils.Spectrum1D`
        Composite 1D spectrum.
    """
    wlallarr = np.array(wl)
    fnuallarr = np.array(fnu)
    srtind = np.argsort(wlallarr)
    if dfnu is not None:
        dfnuallarr = np.array(dfnu)
        fnuallerr = dfnuallarr[srtind]
    wlall = wlallarr[srtind]
    fnuall = fnuallarr[srtind]

    # units are not being handled properly yet.
    if dfnu is not None:
        unc = StdDevUncertainty(fnuallerr * flux_units)
    else:
        unc = None

    spec = Spectrum1D(flux=fnuall * flux_units, spectral_axis=wlall * wave_units,
                      uncertainty=unc)
    return spec


def split_spectrum_with_2D_flux_array(data):
    """
    Helper function to split Spectrum1D of 2D flux to a SpectrumList of nD objects.

    Parameters
    ----------
    data : `~specutils.Spectrum1D`
        Spectrum with 2D flux array

    Returns
    -------
    new_data : `~specutils.SpectrumList`
        List of unpacked spectra.
    """
    new_data = []
    for i in range(data.flux.shape[0]):
        unc = None
        mask = None
        if data.uncertainty is not None:
            unc = data.uncertainty[i, :]
        if data.mask is not None:
            mask = data.mask[i, :]
        new_data.append(Spectrum1D(flux=data.flux[i, :], spectral_axis=data.spectral_axis,
                                   uncertainty=unc, mask=mask, meta=data.meta))

    return new_data
