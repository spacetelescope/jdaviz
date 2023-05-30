import numpy as np
from astropy.io import fits
from astropy.io import registry as io_registry
from glue.core import BaseData
from specutils import Spectrum1D
from specutils.io.registers import _astropy_has_priorities

from jdaviz.core.helpers import ImageConfigHelper
from jdaviz.configs.default.plugins.line_lists.line_list_mixin import LineListMixin
from jdaviz.configs.specviz import Specviz
from jdaviz.core.events import (AddDataMessage,
                                SliceSelectSliceMessage)

__all__ = ['Cubeviz']


class Cubeviz(ImageConfigHelper, LineListMixin):
    """Cubeviz Helper class"""
    _default_configuration = 'cubeviz'
    _default_spectrum_viewer_reference_name = "spectrum-viewer"
    _default_uncert_viewer_reference_name = "uncert-viewer"
    _default_flux_viewer_reference_name = "flux-viewer"
    _default_image_viewer_reference_name = "image-viewer"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.app.hub.subscribe(self, AddDataMessage,
                               handler=self._set_spectrum_x_axis)

    def _set_spectrum_x_axis(self, msg):
        viewer = self.app.get_viewer(self._default_spectrum_viewer_reference_name)
        if msg.viewer_id != viewer.reference_id:
            return
        ref_data = viewer.state.reference_data
        if ref_data and ref_data.ndim == 3:
            for att_name in ["Wave", "Wavelength", "Freq", "Frequency",
                             "Wavenumber", "Velocity", "Energy"]:
                if att_name in ref_data.component_ids():
                    if viewer.state.x_att != ref_data.id[att_name]:
                        viewer.state.x_att = ref_data.id[att_name]
                        viewer.state.reset_limits()
                    break
            else:
                viewer.state.x_att = ref_data.id["Pixel Axis 2 [x]"]
                viewer.state.reset_limits()

    def load_data(self, data, data_label=None, override_cube_limit=False, **kwargs):
        """
        Load and parse a data cube with Cubeviz.
        (Note that only one cube may be loaded per Cubeviz instance.)

        Parameters
        ----------
        data : str, `~astropy.io.fits.HDUList`, `~specutils.Spectrum1D`, or ndarray
            A string file path, astropy FITS object pointing to the
            data cube, a spectrum object, or a Numpy array cube.
            If plain array is given, axes order must be ``(x, y, z)``.
        data_label : str or `None`
            Data label to go with the given data. If not given,
            one will be automatically generated.
        override_cube_limit : bool
            Override internal cube count limitation and load the data anyway.
            Setting this to `True` is not recommended unless you know what
            you are doing.
        **kwargs : dict
            Extra keywords accepted by Jdaviz application-level parser.

        """
        if not override_cube_limit and len(self.app.state.data_items) != 0:
            raise RuntimeError('Only one cube may be loaded per Cubeviz instance')
        if data_label:
            kwargs['data_label'] = data_label

        super().load_data(data, parser_reference="cubeviz-data-parser", **kwargs)

    def select_slice(self, slice):
        """
        Select a slice by index.

        Parameters
        ----------
        slice : int
            Slice integer to select
        """
        if not isinstance(slice, int):
            raise TypeError("slice must be an integer")
        if slice < 0:
            raise ValueError("slice must be positive")
        msg = SliceSelectSliceMessage(slice=slice, sender=self)
        self.app.hub.broadcast(msg)

    def select_wavelength(self, wavelength):
        """
        Select the slice closest to the provided wavelength.

        Parameters
        ----------
        wavelength : float
            Wavelength to select in units of the x-axis of the spectrum.  The nearest slice will
            be selected.
        """
        if not isinstance(wavelength, (int, float)):
            raise TypeError("wavelength must be a float or int")
        # Retrieve the x slices from the spectrum viewer's marks
        sv = self.app.get_viewer(self._default_spectrum_viewer_reference_name)
        x_all = sv.native_marks[0].x
        if sv.state.layers[0].as_steps:
            # then the marks have been doubled in length (each point duplicated)
            x_all = x_all[::2]
        index = np.argmin(abs(x_all - wavelength))
        return self.select_slice(int(index))

    @property
    def specviz(self):
        """
        A Specviz helper (:class:`~jdaviz.configs.specviz.helper.Specviz`) for the Jdaviz
        application that is wrapped by Cubeviz.
        """
        if not hasattr(self, '_specviz'):
            self._specviz = Specviz(app=self.app)
        return self._specviz

    def get_data(self, data_label=None, spatial_subset=None, spectral_subset=None, function=None,
                 cls=None, use_display_units=False):
        """
        Returns data with name equal to ``data_label`` of type ``cls`` with subsets applied from
        ``spatial_subset`` and/or ``spectral_subset`` using ``function`` if applicable.

        Parameters
        ----------
        data_label : str, optional
            Provide a label to retrieve a specific data set from data_collection.
        spatial_subset : str, optional
            Spatial subset applied to data.
        spectral_subset : str, optional
            Spectral subset applied to data.
        function : {True, False, 'minimum', 'maximum', 'mean', 'median', 'sum'}, optional
            Ignored if ``data_label`` does not point to cube-like data.
            If True, will collapse according to the current collapse function defined in the
            spectrum viewer.  If provided as a string, the cube will be collapsed with the provided
            function.  If False, None, or not passed, the entire cube will be returned (unless there
            are values for ``spatial_subset`` and ``spectral_subset``).
        cls : `~specutils.Spectrum1D`, `~astropy.nddata.CCDData`, optional
            The type that data will be returned as.

        Returns
        -------
        data : cls
            Data is returned as type cls with subsets applied.

        """
        # If function is a value ('sum' or 'minimum') or True and spatial and spectral
        # are set, then we collapse the cube along the spatial subset using the function, then
        # we apply the mask from the spectral subset.
        # If function is any value other than False, we use specviz
        if (function is not False and spectral_subset and spatial_subset) or function:
            return self.specviz.get_data(data_label=data_label, spectral_subset=spectral_subset,
                                         cls=cls, spatial_subset=spatial_subset, function=function)
        elif function is False and spectral_subset:
            raise ValueError("function cannot be False if spectral_subset"
                             " is set")
        elif function is False:
            function = None
        return self._get_data(data_label=data_label, spatial_subset=spatial_subset,
                              spectral_subset=spectral_subset, function=function,
                              cls=cls, use_display_units=use_display_units)


def layer_is_cube_image_data(layer):
    return isinstance(layer, BaseData) and layer.ndim in (2, 3)


# TODO: We can remove this when specutils supports it, i.e.,
#       https://github.com/astropy/specutils/issues/592 and
#       https://github.com/astropy/specutils/pull/1009
# NOTE: Cannot use custom_write decorator from specutils because
#       that involves asking user to manually put something in
#       their ~/.specutils directory.

def jdaviz_cube_fitswriter(spectrum, file_name, **kwargs):
    """This is a custom writer for Spectrum1D data cube.
    This writer is specifically targetting data cube
    generated from Cubeviz plugins (e.g., cube fitting)
    with FITS WCS. It writes out data in the following format
    (with MASK only exist when applicable)::

        No.    Name      Ver    Type
          0  PRIMARY       1 PrimaryHDU
          1  SCI           1 ImageHDU (float32)
          2  MASK          1 ImageHDU (uint16)

    The FITS file generated by this writer does not need a
    custom reader to be read back into Spectrum1D.

    Examples
    --------
    To write out a Spectrum1D cube using this writer:

    >>> spec.write("my_output.fits", format="jdaviz-cube", overwrite=True)  # doctest: +SKIP

    """
    pri_hdu = fits.PrimaryHDU()

    flux = spectrum.flux
    sci_hdu = fits.ImageHDU(flux.value.astype(np.float32))
    sci_hdu.name = "SCI"
    sci_hdu.header.update(spectrum.meta)
    sci_hdu.header.update(spectrum.wcs.to_header())
    sci_hdu.header['BUNIT'] = flux.unit.to_string(format='fits')

    hlist = [pri_hdu, sci_hdu]

    # https://specutils.readthedocs.io/en/latest/spectrum1d.html#including-masks
    # Good: False or 0
    # Bad: True or non-zero
    if spectrum.mask is not None:
        mask_hdu = fits.ImageHDU(spectrum.mask.astype(np.uint16))
        mask_hdu.name = "MASK"
        hlist.append(mask_hdu)

    hdulist = fits.HDUList(hlist)
    hdulist.writeto(file_name, **kwargs)


if _astropy_has_priorities():
    kwargs = {"priority": 0}
else:  # pragma: no cover
    kwargs = {}
io_registry.register_writer(
    "jdaviz-cube", Spectrum1D, jdaviz_cube_fitswriter, force=False, **kwargs)
