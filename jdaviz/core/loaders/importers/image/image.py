import warnings

import asdf
import numpy as np
from astropy import units as u
from astropy.io import fits
from astropy.nddata import NDData, CCDData
from astropy.wcs import WCS
from glue.core.data import Component, Data
from traitlets import Bool, List, Any


from jdaviz.core.template_mixin import SelectFileExtensionComponent

from jdaviz.core.registries import loader_importer_registry
from jdaviz.core.loaders.importers import BaseImporterToDataCollection

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.default_data_label_from_resolver:
            self.data_label_default = self.default_data_label_from_resolver
        elif self.app.config == 'imviz':
            self.data_label_default = 'Image'

        self.input_hdulist = isinstance(self.input, fits.HDUList)
        if self.input_hdulist:
            self.extension = SelectFileExtensionComponent(self,
                                                          items='extension_items',
                                                          selected='extension_selected',
                                                          multiselect='extension_multiselect',
                                                          manual_options=self.input,
                                                          filters=[_validate_fits_image2d])
            self.extension.selected = [self.extension.choices[0]]

    @property
    def is_valid(self):
        if self.app.config not in ('deconfigged', 'imviz', 'mastviz'):
            # NOTE: temporary during deconfig process
            return False
        # flat image, not a cube
        # isinstance NDData
        return isinstance(self.input, (fits.HDUList, fits.hdu.image.ImageHDU,
                                       NDData, np.ndarray, asdf.AsdfFile))

    @property
    def default_viewer_reference(self):
        # returns the registry name of the default viewer
        # only used if `show_in_viewer=True` and no existing viewers can accept the data
        return 'imviz-image-viewer'

    @property
    def output(self):
        # NDData or ndarray
        if isinstance(self.input, NDData) or isinstance(self.input, np.ndarray):
            return self.input
        # asdf
        elif (isinstance(self.input, asdf.AsdfFile) or
              (HAS_ROMAN_DATAMODELS and isinstance(self.input, rdd.DataModel))):
            return self.input
        # ImageHDU
        elif isinstance(self.input, fits.hdu.image.ImageHDU):
            return [_hdu2data(self.input, self.data_label_value, None, False)]
        # fits
        hdulist = self.input
        return [_hdu2data(hdu, self.data_label_value, hdulist)[0]
                for hdu in self.extension.selected_hdu]

    def __call__(self, show_in_viewer=True):
        data_label = self.data_label_value
        output = self.output
        # nddata
        if isinstance(output, NDData):
            returned_data = _nddata_to_glue_data(output, data_label)
            for data_label, data in returned_data.items():
                self.add_to_data_collection(data, f"{data_label}", show_in_viewer=show_in_viewer,
                                            cls=CCDData)
        # ndarray
        elif isinstance(output, np.ndarray):
            data = _ndarray_to_glue_data(output, data_label)
            self.add_to_data_collection(data, f"{data_label}", show_in_viewer=show_in_viewer,
                                        cls=CCDData)
        # asdf
        elif (isinstance(output, asdf.AsdfFile) or
              (HAS_ROMAN_DATAMODELS and isinstance(output, rdd.DataModel))):
            returned_data = _roman_asdf_2d_to_glue_data(output, data_label)
            for data_label, data in returned_data.items():
                self.add_to_data_collection(data, f"{data_label}", show_in_viewer=show_in_viewer,
                                            cls=CCDData)
        # ImageHDU
        elif isinstance(self.input, fits.hdu.image.ImageHDU):
            # data, data_label = _hdu2data(self.input, self.data_label_value, None, True)
            for data, data_label in output:
                self.add_to_data_collection(data, f"{data_label}", show_in_viewer=show_in_viewer,
                                            cls=CCDData)
        # fits
        else:
            with self.app._jdaviz_helper.batch_load():
                for ext, ext_output in zip(self.extension.selected_name, output):
                    self.add_to_data_collection(ext_output, ext_output.label,
                                                show_in_viewer=show_in_viewer,
                                                cls=CCDData)
                    # self.add_to_data_collection(ext_output, f"{data_label}[{ext}]",
                    #                             show_in_viewer=show_in_viewer,
                    #                             cls=CCDData)


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


def _hdu2data(hdu, data_label, hdulist, include_wcs=True):
    if 'BUNIT' in hdu.header:
        bunit = _validate_bunit(hdu.header['BUNIT'], raise_error=False)
    else:
        bunit = ''

    comp_label = f'{hdu.name.upper()},{hdu.ver}'
    new_data_label = f'{data_label}[{comp_label}]'

    data = Data(label=new_data_label)
    if hdulist is not None and hdu.name != 'PRIMARY' and 'PRIMARY' in hdulist:
        data.meta[PRIHDR_KEY] = standardize_metadata(hdulist['PRIMARY'].header)
    data.meta.update(standardize_metadata(hdu.header))
    if include_wcs:
        data.coords = WCS(hdu.header, hdulist)
    component = Component.autotyped(hdu.data, units=bunit)
    data.add_component(component=component, label=comp_label)

    return data, new_data_label


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


def _ndarray_to_glue_data(arr, data_label):
    if arr.ndim != 2:
        raise ValueError(f'Imviz cannot load this array with ndim={arr.ndim}')

    data = Data(label=data_label)
    component = Component.autotyped(arr)
    data.add_component(component=component, label='DATA')
    return data


def _nddata_to_glue_data(ndd, data_label):
    if ndd.data.ndim != 2:
        raise ValueError(f'Imviz cannot load this NDData with ndim={ndd.data.ndim}')

    returned_data = {}
    for attrib in ('data', 'mask', 'uncertainty'):
        arr = getattr(ndd, attrib)
        if arr is None:
            continue
        comp_label = attrib.upper()
        # Do not add extension if data is coming from orientation plugin
        if 'plugin' in ndd.meta.keys() and ndd.meta['plugin'] == 'orientation':
            cur_label = f'{data_label}'
        else:
            cur_label = f'{data_label}[{comp_label}]'
        cur_data = Data(label=cur_label)
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
        returned_data[cur_label] = cur_data
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


def _roman_asdf_2d_to_glue_data(file_obj, data_label, ext=None, try_gwcs_to_fits_sip=False):
    if ext == '*':
        # NOTE: Update as needed. Should cover all the image extensions available.
        ext_list = ('data', 'dq', 'err', 'var_poisson', 'var_rnoise')
    elif ext is None:
        ext_list = ('data', )
    elif isinstance(ext, (list, tuple)):
        ext_list = ext
    else:
        ext_list = (ext, )

    meta = standardize_roman_metadata(file_obj)
    gwcs = meta.get('wcs', None)

    if try_gwcs_to_fits_sip and gwcs is not None:
        coords = _try_gwcs_to_fits_sip(gwcs)
    else:
        coords = gwcs
    returned_data = {}

    for cur_ext in ext_list:
        comp_label = cur_ext.upper()
        new_data_label = f'{data_label}[{comp_label}]'
        data = Data(coords=coords, label=new_data_label)

        # This could be a quantity or a ndarray:
        if HAS_ROMAN_DATAMODELS and isinstance(file_obj, rdd.DataModel):
            ext_values = getattr(file_obj, cur_ext)
        else:
            ext_values = file_obj['roman'][cur_ext]
        bunit = getattr(ext_values, 'unit', '')
        component = Component(np.array(ext_values), units=bunit)
        data.add_component(component=component, label=comp_label)
        data.meta.update(standardize_metadata(dict(meta)))
        if comp_label == 'DQ':
            prep_data_layer_as_dq(data)
        returned_data[new_data_label] = data

    return returned_data
