import warnings

import asdf
import numpy as np
from astropy import units as u
from astropy.io import fits
from astropy.nddata import NDData, CCDData
from astropy.utils.exceptions import AstropyWarning
from astropy.wcs import WCS
from glue.core.data import Component, Data
from gwcs import WCS as GWCS
from stdatamodels import asdf_in_fits
from traitlets import Bool, List, Any, observe

from jdaviz.core.template_mixin import SelectFileExtensionComponent, DatasetSelect

from jdaviz.core.loaders.importers import BaseImporterToDataCollection
from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.user_api import ImporterUserApi

from jdaviz.utils import (
    PRIHDR_KEY, standardize_metadata, standardize_roman_metadata,
    _try_gwcs_to_fits_sip
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
    input_has_extensions = Bool(False).tag(sync=True)
    extension_items = List().tag(sync=True)
    extension_selected = Any().tag(sync=True)
    extension_multiselect = Bool(True).tag(sync=True)

    # Data-association
    parent_items = List().tag(sync=True)
    parent_selected = Any().tag(sync=True)

    # Use FITS approximation instead of original image GWCS
    gwcs_to_fits_sip = Bool(False).tag(sync=True)

    # user-settable option to treat the data_label as prefix and append the extension later
    data_label_as_prefix = Bool(False).tag(sync=True)
    # whether the current data_label should be treated as a prefix
    # either based on user-setting above or current extension selection
    data_label_is_prefix = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.parent = DatasetSelect(self, 'parent_items', 'parent_selected',
                                    multiselect=None, manual_options=['Auto'])
        self.parent.add_filter('is_image', 'not_from_plugin')
        self.parent.selected = 'Auto'

        input = self.input
        if isinstance(input, fits.hdu.image.ImageHDU):
            input = fits.HDUList([input])

        input_is_roman = (HAS_ROMAN_DATAMODELS and
                          isinstance(input, (rdd.ImageModel, rdd.DataModel)))
        self.input_has_extensions = (isinstance(input, fits.HDUList) or
                                     input_is_roman)
        if self.input_has_extensions:
            if isinstance(input, fits.HDUList):
                filters = [_validate_fits_image2d]
                ext_options = [{'label': f"{index}: [{hdu.name},{hdu.ver}]",
                                'name': hdu.name,
                                'ver': hdu.ver,
                                'name_ver': f"{hdu.name},{hdu.ver}",
                                'index': index,
                                'obj': hdu}
                               for index, hdu in enumerate(input)]
            elif input_is_roman:
                filters = [_validate_roman_ext]
                ext_options = [{'label': f"{index}: {key}",
                                'name': key,
                                'ver': None,
                                'name_ver': key,
                                'index': index,
                                'obj': value}
                               for index, (key, value) in enumerate(input.items())]
            else:
                raise NotImplementedError()

            self.extension = SelectFileExtensionComponent(self,
                                                          items='extension_items',
                                                          selected='extension_selected',
                                                          multiselect='extension_multiselect',
                                                          manual_options=ext_options,
                                                          filters=filters)

            # changing selected extension will call _set_default_data_label
            self.extension.selected = [self.extension.choices[0]]
        else:
            self._set_default_data_label()

    @staticmethod
    def _get_supported_viewers():
        return [{'label': 'Image', 'reference': 'imviz-image-viewer'}]

    @property
    def user_api(self):
        expose = ['parent', 'data_label_as_prefix', 'gwcs_to_fits_sip']
        if self.input_has_extensions:
            expose += ['extension']
        return ImporterUserApi(self, expose)

    @property
    def is_valid(self):
        if self.app.config not in ('deconfigged', 'imviz', 'mastviz'):
            # NOTE: temporary during deconfig process
            return False
        # flat image, not a cube
        # isinstance NDData
        return (isinstance(self.input, (fits.HDUList, fits.hdu.image.ImageHDU,
                                        NDData, np.ndarray, asdf.AsdfFile)) or
                (HAS_ROMAN_DATAMODELS and isinstance(self.input, (rdd.DataModel, rdd.ImageModel))))

    def _glue_data_wcs_to_fits(self, glue_data):
        """
        Re-set data.coords to a SIP approximation of the GWCS, if
        gwcs_to_fits_sip is True and data.coords is a GWCS. If these conditions
        are met but this approximation is not possible, a warning will be
        emitted and the original GWCS will be used.
        """
        if isinstance(glue_data.coords, GWCS):
            glue_data.coords = _try_gwcs_to_fits_sip(glue_data.coords)
        return glue_data

    def _get_label_with_extension(self, prefix, ext=None, ver=None):
        full_ext = ",".join([str(e) for e in (ext, ver) if e is not None])
        return f"{prefix}[{full_ext}]" if len(full_ext) else prefix

    @observe('extension_selected', 'data_label_as_prefix')
    def _set_default_data_label(self, *args):
        if self.default_data_label_from_resolver:
            prefix = self.default_data_label_from_resolver
        else:
            prefix = "Image"

        if self.input_has_extensions and hasattr(self, 'extension'):
            if self.extension.selected_name is None:
                return
            if len(self.extension.selected_name) == 1 and not self.data_label_as_prefix:
                # selected_obj may be an ndarray object if input is a roman data model
                ver = getattr(self.extension.selected_obj[0], 'ver', None)
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
        input = self.input

        # ImageHDU - treat as HDUList with single extension
        if isinstance(input, fits.hdu.image.ImageHDU):
            input = fits.HDUList([self.input])

        if isinstance(input, NDData):
            data = _nddata_to_glue_data(input)  # list of Data
        elif isinstance(input, np.ndarray):
            data = [_ndarray_to_glue_data(input)]
        # asdf
        elif (isinstance(input, asdf.AsdfFile)):
            data = [_roman_asdf_2d_to_glue_data(input, ext='data')]
        # roman data models
        elif HAS_ROMAN_DATAMODELS and isinstance(input, (rdd.DataModel, rdd.ImageModel)):
            data = [_roman_asdf_2d_to_glue_data(input, ext=ext)
                    for ext in self.extension.selected_name]
        # JWST ASDF-in-FITS
        elif isinstance(input, fits.HDUList) and 'ASDF' in input:
            data = [_jwst2data(hdu, input) for hdu in self.extension.selected_obj]
        # FITS
        else:
            data = [_hdu2data(hdu, input) for hdu in self.extension.selected_obj]

        ext_names = self.extension.selected_name if self.input_has_extensions else [None] * len(data)  # noqa
        for d, ext_name in zip(data, ext_names):
            if d is None:
                continue
            d.meta['_extname'] = ext_name
            for component_id in d.main_components:
                if component_id.label.lower().startswith("dq"):
                    # for DQ components, map zeros to nans
                    # so that they are not displayed in the DQ colormap
                    cid = d.get_component(component_id)
                    data_arr = np.float32(cid.data)
                    data_arr[data_arr == 0] = np.nan
                    d.update_components({cid: data_arr})

        return data

    def __call__(self):

        base_data_label = self.data_label_value
        # self.output is always a list of Data objects
        outputs = self.output

        if self.input_has_extensions:
            ext_items = self.extension.selected_item_list
        elif isinstance(self.input, NDData):
            ext_items = [{'name': name} for name in ('DATA', 'MASK', 'UNCERTAINTY')]  # noqa must match order in _nddata_to_glue_data
        else:
            ext_items = [{}] * len(outputs)

        parent_selected = self.parent.selected
        for output, ext_item in zip(outputs, ext_items):
            if output is None:
                # needed for NDData where one of the "extensions" might
                # not be present.  Remove this once users can select
                # which to import.
                continue

            # Determine data label
            if self.data_label_is_prefix:
                # If data_label is a prefix, we need to append the extension
                # to the data label.
                data_label = self._get_label_with_extension(base_data_label,
                                                            ext_item.get('name'),
                                                            ver=ext_item.get('ver', None))
            else:
                # If data_label is not a prefix, we use it as is.
                data_label = base_data_label

            # Determine parent
            if (parent_selected == 'Auto' and
                    len(ext_items) > 1 and
                    getattr(self.input, 'meta', {}).get('plugin', None) is None):
                # If parent is set to 'Auto', use SCI/DATA extension
                # as parent of any other selected extensions with same ver (if applicable)
                for other_ext_item in ext_items:
                    if (other_ext_item.get('name') in ('SCI', 'sci', 'DATA', 'data')
                            and other_ext_item.get('ver', None) == ext_item.get('ver', None)):
                        parent_ext_item = other_ext_item
                        break
                else:
                    # No SCI/DATA extension found, so default to no parent
                    parent_ext_item = None
                    parent_data_label = None
                if parent_ext_item is not None:
                    # assume self.data_label_is_prefix is True
                    parent_data_label = self._get_label_with_extension(base_data_label,
                                                                       parent_ext_item.get('name'),
                                                                       ver=parent_ext_item.get('ver', None))  # noqa
            elif parent_selected == 'Auto':
                parent_data_label = None
            else:
                parent_data_label = parent_selected

            if self.gwcs_to_fits_sip:
                output = self._glue_data_wcs_to_fits(output)

            self.add_to_data_collection(output, data_label,
                                        parent=parent_data_label if parent_data_label != data_label else None,  # noqa
                                        cls=CCDData)


def _validate_fits_image2d(item):
    hdu = item.get('obj')
    return hdu.data is not None and hdu.is_image and hdu.data.ndim == 2


def _validate_roman_ext(item):
    name = item.get('name')
    return name in ['data', 'dq', 'err', 'var_poisson', 'var_rnoise']


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
        raise ValueError(f'Cannot load as image with ndim={arr.ndim}')

    data = Data()
    component = Component.autotyped(arr)
    data.add_component(component=component, label='DATA')
    return data


def _nddata_to_glue_data(ndd):
    if ndd.data.ndim != 2:
        raise ValueError(f'Cannot load as image with ndim={ndd.data.ndim}')

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


def _roman_asdf_2d_to_glue_data(file_obj, ext=None, try_gwcs_to_fits_sip=False):
    meta = standardize_roman_metadata(file_obj)
    gwcs = meta.get('wcs', None)

    if try_gwcs_to_fits_sip and gwcs is not None:
        coords = _try_gwcs_to_fits_sip(gwcs)
    else:
        coords = gwcs

    comp_label = ext.upper()
    data = Data(coords=coords)

    if HAS_ROMAN_DATAMODELS and isinstance(file_obj, (rdd.DataModel, rdd.ImageModel)):
        ext_values = file_obj[ext]
    else:
        ext_values = file_obj['roman'][ext]
    bunit = getattr(ext_values, 'unit', '')
    component = Component(np.array(ext_values), units=bunit)
    data.add_component(component=component, label=comp_label)
    data.meta.update(standardize_metadata(dict(meta)))

    return data


def _jwst2data(hdu, hdulist, try_gwcs_to_fits_sip=False):
    comp_label = hdu.name.lower()
    if comp_label.startswith("sci"):
        comp_label = 'data'
    data = Data()
    unit_attr = f'bunit_{comp_label}'

    try:
        # This is very specific to JWST pipeline image output.
        with asdf_in_fits.open(hdulist) as af:
            dm = af.tree
            dm_meta = af.tree["meta"]
            data.meta.update(standardize_metadata(dm_meta))

            if unit_attr in dm_meta:
                bunit = _validate_bunit(dm_meta[unit_attr], raise_error=False)
            else:
                bunit = ''

            # This is instance of gwcs.WCS, not astropy.wcs.WCS
            if 'wcs' in dm_meta:
                gwcs = dm_meta['wcs']

                if try_gwcs_to_fits_sip:
                    data.coords = _try_gwcs_to_fits_sip(gwcs)
                else:
                    data.coords = gwcs
            # keys in the asdf tree are lower case
            imdata = dm[comp_label]
            component = Component.autotyped(imdata, units=bunit)

            # Might have bad GWCS. If so, we exclude it.
            try:
                data.add_component(component=component, label=comp_label)

            except Exception:  # pragma: no cover
                data.coords = None
                data.add_component(component=component, label=comp_label)

    # TODO: Do not need this when jwst.datamodels finally its own package.
    # This might happen for grism image; fall back to FITS loader without WCS.
    except Exception:
        if comp_label == 'data':
            new_ext = 'sci'
        else:
            new_ext = hdu.name
        new_hdu = hdulist[new_ext]
        return _hdu2data(new_hdu, hdulist, include_wcs=False)

    return data
