import warnings

import asdf
import numpy as np
from astropy import units as u
from astropy.io import fits
from astropy.nddata import NDData, CCDData
from astropy.utils.exceptions import AstropyWarning
from astropy.wcs import WCS
from glue.core.data import Component, Data
from traitlets import Bool, List, Any, observe


from jdaviz.core.template_mixin import SelectFileExtensionComponent, DatasetSelect

from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.loaders.importers import BaseImporterToDataCollection
from jdaviz.core.user_api import ImporterUserApi

from jdaviz.utils import (
    standardize_metadata, standardize_roman_metadata, PRIHDR_KEY
)

try:
    from roman_datamodels import datamodels as rdd
except ImportError:
    HAS_ROMAN_DATAMODELS = False
else:
    HAS_ROMAN_DATAMODELS = True


__all__ = ['ImageImporter']


@loader_importer_registry('Image')
class ImageImporter(BaseImporterToDataCollection):
    template_file = __file__, "./image.vue"

    # HDUList-specific options
    input_hdulist = Bool(False).tag(sync=True)
    extension_items = List().tag(sync=True)
    extension_selected = Any().tag(sync=True)
    extension_multiselect = Bool(True).tag(sync=True)

    # Data-association
    parent_items = List().tag(sync=True)
    parent_selected = Any().tag(sync=True)

    # user-settable option to treat the data_label as prefix and append the extension later
    data_label_as_prefix = Bool(False).tag(sync=True)
    # whether the current data_label should be treated as a prefix
    # either based on user-setting above or current extension selection
    data_label_is_prefix = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.default_data_label_from_resolver:
            self.data_label_default = self.default_data_label_from_resolver
        elif self.app.config == 'imviz':
            self.data_label_default = 'Image'

        self.parent = DatasetSelect(self, 'parent_items', 'parent_selected',
                                    multiselect=None, manual_options=['Auto'])
        self.parent.add_filter('is_image', 'not_from_plugin')
        self.parent.selected = 'Auto'

        input = self.input
        if isinstance(input, fits.hdu.image.ImageHDU):
            input = fits.HDUList([input])

        self.input_hdulist = isinstance(input, (fits.HDUList, rdd.ImageModel, rdd.DataModel))
        if self.input_hdulist:
            filters = ([_validate_fits_image2d] if isinstance(input, fits.HDUList)
                       else [_validate_roman_ext])
            self.extension = SelectFileExtensionComponent(self,
                                                          items='extension_items',
                                                          selected='extension_selected',
                                                          multiselect='extension_multiselect',
                                                          manual_options=input,
                                                          filters=filters)
            self.extension.selected = [self.extension.choices[0]]
        else:
            self._set_default_data_label()

    @property
    def user_api(self):
        expose = ['parent', 'data_label_as_prefix']
        if self.input_hdulist:
            expose += ['extension']
        return ImporterUserApi(self, expose)

    @property
    def is_valid(self):
        if self.app.config not in ('deconfigged', 'imviz', 'mastviz'):
            # NOTE: temporary during deconfig process
            return False
        # flat image, not a cube
        # isinstance NDData
        return isinstance(self.input, (fits.HDUList, fits.hdu.image.ImageHDU,
                                       NDData, np.ndarray, asdf.AsdfFile, rdd.DataModel,
                                       rdd.ImageModel))

    @property
    def default_viewer_reference(self):
        # returns the registry name of the default viewer
        # only used if `show_in_viewer=True` and no existing viewers can accept the data
        return 'imviz-image-viewer'

    def _get_label_with_extension(self, prefix, ext=None, ver=None):
        full_ext = ",".join([str(e) for e in (ext, ver) if e is not None])
        return f"{prefix}[{full_ext}]" if len(full_ext) else prefix

    @observe('extension_selected', 'data_label_as_prefix')
    def _set_default_data_label(self, *args):
        if self.default_data_label_from_resolver:
            prefix = self.default_data_label_from_resolver
        else:
            prefix = "Image"
        if self.input_hdulist:
            if len(self.extension.selected_name) == 1 and not self.data_label_as_prefix:
                # selected_hdu may be an ndarray object if input is a roman data model
                ver = getattr(self.extension.selected_hdu[0], 'ver', None)
                # only a single extension selected
                self.data_label_default = self._get_label_with_extension(prefix,
                                                                         ext=self.extension.selected_name[0],  # noqa
                                                                         ver=ver)  # noqa
                self.data_label_is_prefix = False
            else:
                # multiple extensions selected,
                # only show the prefix and append the extension later during import
                self.data_label_default = prefix
                self.data_label_is_prefix = True
        elif (self.data_label_as_prefix or
              (isinstance(self.input, NDData) and
               getattr(self.input, 'meta', {}).get('plugin', None) is None)):
            # will append with [DATA]/[UNCERTAINTY]/[MASK] later
            # TODO: allow user to select extensions and include in same logic as HDUList
            self.data_label_default = prefix
            self.data_label_is_prefix = True
        else:
            self.data_label_default = prefix
            self.data_label_is_prefix = False

    @property
    def output(self):
        # NOTE: this should ALWAYS return a list of objects able to be imported into DataCollection
        # NDData or ndarray
        # ImageHDU
        input = self.input
        if isinstance(input, fits.hdu.image.ImageHDU):
            input = fits.HDUList([self.input])

        if isinstance(input, NDData):
            return _nddata_to_glue_data(input)  # list of Data
        elif isinstance(input, np.ndarray):
            return [_ndarray_to_glue_data(input)]
        # asdf
        elif (isinstance(input, asdf.AsdfFile) or
              (HAS_ROMAN_DATAMODELS and isinstance(input, (rdd.DataModel, rdd.ImageModel)))):
            return [_roman_asdf_2d_to_glue_data(input, ext=ext)
                    for ext in self.extension.selected_name]  # list of Data
        # fits
        return [_hdu2data(hdu, input) for hdu in self.extension.selected_hdu]

    def __call__(self, show_in_viewer=True):
        base_data_label = self.data_label_value
        # self.output is always a list of Data objects
        outputs = self.output

        if self.input_hdulist:
            exts = self.extension.selected_name
            hdus = self.extension.selected_hdu
        elif isinstance(self.input, NDData):
            exts = ['DATA', 'MASK', 'UNCERTAINTY']  # must match order in _nddata_to_glue_data
            hdus = [None] * len(outputs)
        else:
            exts = [None] * len(outputs)
            hdus = [None] * len(outputs)

        # If parent is set to 'Auto', use any present SCI/DATA extension as parent
        # of any other extensions
        if (self.parent.selected == 'Auto' and
                len(exts) > 1 and
                getattr(self.input, 'meta', {}).get('plugin', None) is None):
            for ext in ('SCI', 'DATA'):
                if ext in exts:
                    parent_ext = ext
                    break
                # Roman data model extensions are lower case
                elif ext.lower() in exts:
                    parent_ext = ext.lower()
                    break
            else:
                parent_ext = None
                parent = None
            if parent_ext is not None:
                parent_index = exts.index(parent_ext)
                sort_inds = [parent_index] + [i for i in range(len(exts)) if i != parent_index]
                outputs = [outputs[i] for i in sort_inds]
                exts = [exts[i] for i in sort_inds]
                hdus = [hdus[i] for i in sort_inds]

                parent_hdu = hdus[parent_index]
                # Handle case for rdd.ImageModel where hdu is an ndarray
                ver = getattr(parent_hdu, 'ver', None)

                # assume self.data_label_is_prefix is True
                parent = self._get_label_with_extension(base_data_label,
                                                        parent_ext,
                                                        ver=ver)
        elif self.parent.selected == 'Auto':
            parent = None
        else:
            parent = self.parent.selected

        for output, ext, hdu in zip(outputs, exts, hdus):
            if output is None:
                # needed for NDData where one of the "extensions" might
                # not be present.  Remove this once users can select
                # which to import.
                continue
            if self.data_label_is_prefix:
                # Handle case where hdu is an ndarray
                ver = getattr(hdu, 'ver', None)
                # If data_label is a prefix, we need to append the extension
                # to the data label.
                data_label = self._get_label_with_extension(base_data_label,
                                                            ext,
                                                            ver=ver)
            else:
                # If data_label is not a prefix, we use it as is.
                data_label = base_data_label
            self.add_to_data_collection(output, data_label,
                                        parent=parent if parent != data_label else None,
                                        show_in_viewer=show_in_viewer,
                                        cls=CCDData)


def _validate_fits_image2d(hdu, raise_error=False):
    valid = hdu.data is not None and hdu.is_image and hdu.data.ndim == 2
    if not valid and raise_error:
        if hdu.data is not None and hdu.is_image:
            ndim = hdu.data.ndim
        else:
            ndim = None
        raise ValueError(
            f'Imviz cannot load this HDU ({hdu}): '
            f'has_data={hdu.data is not None}, is_image={hdu.is_image}, '
            f'name={hdu.name}, ver={hdu.ver}, ndim={ndim}')
    return valid


def _validate_roman_ext(ext):
    valid = ext in ['data', 'dq', 'err', 'var_poisson', 'var_rnoise']
    return valid


def _hdu2data(hdu, hdulist, include_wcs=True):
    if 'BUNIT' in hdu.header:
        bunit = _validate_bunit(hdu.header['BUNIT'], raise_error=False)
    else:
        bunit = ''

    comp_label = f'{hdu.name.upper()},{hdu.ver}'

    data = Data()
    if hdulist is not None and hdu.name != 'PRIMARY' and 'PRIMARY' in hdulist:
        data.meta[PRIHDR_KEY] = standardize_metadata(hdulist['PRIMARY'].header)
    data.meta.update(standardize_metadata(hdu.header))
    if include_wcs:
        data.coords = WCS(hdu.header, hdulist)
    component = Component.autotyped(hdu.data, units=bunit)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', category=AstropyWarning)
        data.add_component(component=component, label=comp_label)

    return data


def _validate_bunit(bunit, raise_error=False):
    # TODO: Handle weird FITS BUNIT values here, as needed.
    if bunit == 'ELECTRONS/S':
        valid = 'electron/s'
    elif bunit == 'ELECTRONS':
        valid = 'electron'
    else:
        try:
            u.Unit(bunit)
        except Exception:
            if raise_error:
                raise
            valid = ''
        else:
            valid = bunit
    return valid


def _ndarray_to_glue_data(arr):
    if arr.ndim != 2:
        raise ValueError(f'Imviz cannot load this array with ndim={arr.ndim}')

    data = Data()
    component = Component.autotyped(arr)
    data.add_component(component=component, label='DATA')
    return data


def _nddata_to_glue_data(ndd):
    if ndd.data.ndim != 2:
        raise ValueError(f'Imviz cannot load this NDData with ndim={ndd.data.ndim}')

    returned_data = []
    for attrib in ('data', 'mask', 'uncertainty'):
        arr = getattr(ndd, attrib)
        if arr is None:
            returned_data.append(None)
            continue
        comp_label = attrib.upper()
        cur_data = Data()
        cur_data.meta.update(standardize_metadata(ndd.meta))
        if ndd.wcs is not None:
            cur_data.coords = ndd.wcs
        raw_arr = arr
        if attrib == 'data':
            bunit = ndd.unit or ''
        elif attrib == 'uncertainty':
            raw_arr = arr.array
            bunit = arr.unit or ''
        else:
            bunit = ''
        component = Component.autotyped(raw_arr, units=bunit)
        cur_data.add_component(component=component, label=comp_label)
        returned_data.append(cur_data)
    return returned_data


def _try_gwcs_to_fits_sip(gwcs):
    """
    Try to convert this GWCS to FITS SIP. Some GWCS models
    cannot be converted to FITS SIP. In that case, a warning
    is raised and the GWCS is used, as is.
    """
    try:
        result = WCS(gwcs.to_fits_sip())
    except ValueError as err:
        warnings.warn(
            "The GWCS coordinates could not be simplified to "
            "a SIP-based FITS WCS, the following error was "
            f"raised: {err}",
            UserWarning
        )
        result = gwcs

    return result


def prep_data_layer_as_dq(data):
    # nans are used to mark "good" flags in the DQ colormap, so
    # convert DQ array to float to support nans:
    for component_id in data.main_components:
        if component_id.label.startswith("DQ"):
            break

    cid = data.get_component(component_id)
    data_arr = np.float32(cid.data)
    data_arr[data_arr == 0] = np.nan
    data.update_components({cid: data_arr})


def _roman_asdf_2d_to_glue_data(file_obj, ext=None, try_gwcs_to_fits_sip=False):
    meta = standardize_roman_metadata(file_obj)
    gwcs = meta.get('wcs', None)

    if try_gwcs_to_fits_sip and gwcs is not None:
        coords = _try_gwcs_to_fits_sip(gwcs)
    else:
        coords = gwcs

    comp_label = ext.upper()
    data = Data(coords=coords)

    # This could be a quantity or a ndarray:
    if HAS_ROMAN_DATAMODELS and isinstance(file_obj, (rdd.DataModel, rdd.ImageModel)):
        ext_values = getattr(file_obj, ext)
    else:
        ext_values = file_obj['roman'][ext]
    bunit = getattr(ext_values, 'unit', '')
    component = Component(np.array(ext_values), units=bunit)
    data.add_component(component=component, label=comp_label)
    data.meta.update(standardize_metadata(dict(meta)))
    if comp_label == 'DQ':
        prep_data_layer_as_dq(data)

    return data
