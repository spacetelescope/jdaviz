import os
import warnings
from copy import deepcopy
from pathlib import Path
from zipfile import is_zipfile

import numpy as np
from astropy import units as u
from astropy.coordinates import SkyCoord
from astropy.table import QTable
from echo import delay_callback
from glue.core.data import Data
from glue.core.exceptions import IncompatibleAttribute

from jdaviz.core.helpers import ConfigHelper
from jdaviz.core.events import SnackbarMessage, TableClickMessage, RedshiftMessage, RowLockMessage
from jdaviz.configs.specviz import Specviz
from jdaviz.configs.specviz.helper import _apply_redshift_to_spectra
from jdaviz.configs.specviz2d import Specviz2d
from jdaviz.configs.mosviz.plugins import jwst_header_to_skyregion
from jdaviz.configs.mosviz.plugins.parsers import (
    FALLBACK_NAME, mos_spec1d_parser, mos_spec2d_parser)
from jdaviz.configs.default.plugins.line_lists.line_list_mixin import LineListMixin

__all__ = ['Mosviz']


class Mosviz(ConfigHelper, LineListMixin):
    """Mosviz Helper class"""

    _default_configuration = "mosviz"
    _default_image_viewer_reference_name = "image-viewer"
    _default_spectrum_viewer_reference_name = "spectrum-viewer"
    _default_spectrum_2d_viewer_reference_name = "spectrum-2d-viewer"
    _default_table_viewer_reference_name = "table-viewer"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        spec1d = self.app.get_viewer(self._default_spectrum_viewer_reference_name)
        spec2d = self.app.get_viewer(self._default_spectrum_2d_viewer_reference_name)

        image_viewer = self.app.get_viewer(self._default_image_viewer_reference_name)

        # Choose which viewers will have state frozen during a row change.
        # This should be a list of tuples, where each entry has the state as the
        # first item in the tuple, and a list of frozen attributes as the second.
        self._freezable_states = [(spec1d.state, ['x_min', 'x_max']),
                                  (spec2d.state, ['x_min', 'x_max']),
                                  (image_viewer.state, []),
                                  ]

        self._freezable_layers = [(spec1d.state, ['linewidth']),
                                  (spec2d.state, ['stretch', 'percentile', 'v_min', 'v_max']),
                                  (image_viewer.state, ['stretch', 'percentile', 'v_min', 'v_max'])]
        self._frozen_layers_cache = []
        self._freeze_states_on_row_change = False

        # Add callbacks to table-viewer to enable/disable the state freeze
        table = self.app.get_viewer(self._default_table_viewer_reference_name)
        table._on_row_selected_begin = self._on_row_selected_begin
        table._on_row_selected_end = self._on_row_selected_end

        # Listen for clicks on the table in case we need to zoom the image
        self.app.hub.subscribe(self, TableClickMessage,
                               handler=self._row_click_message_handler)

        self.app.hub.subscribe(self, RowLockMessage,
                               handler=self._row_lock_changed)

        # Listen for new redshifts from the redshift slider (NOT YET IMPLEMENTED)
        self.app.hub.subscribe(self, RedshiftMessage,
                               handler=self._redshift_listener)

        self._shared_image = False

        self._update_in_progress = False

        self._initialize_table()
        self._default_visible_columns = []

    def _initialize_table(self, label="MOS Table", table_viewer_reference_name='table-viewer'):
        '''
        Setup the MOS Table data container and add it to the viewer

        Parameters
        ----------
        label : str
            The Glue Data Label to reference the table data as
        table_viewer_reference_name : str
            The reference name of the table viewer to add this data to
        '''
        table_data = Data(label=label)
        self.app.add_data(table_data, notify_done=False)

        # Add the table to the table viewer
        self.app.get_viewer(table_viewer_reference_name).add_data(table_data)

    def _row_lock_changed(self, msg):
        self._freeze_states_on_row_change = msg.is_locked

    def _on_row_selected_begin(self, event):
        self._redshift_cache = self.get_column("Redshift")[event['new']]

        if not self._freeze_states_on_row_change:
            return

        for state, attrs in self._freezable_states:
            state._frozen_state = attrs

        # Make a copy of layer attributes (these can't be frozen since it will
        # technically be a NEW layer instance).  Note: this assumes that
        # layers[0] points to the data (and all other indices point to subsets)
        self._frozen_layers_cache = [{a: getattr(state.layers[0], a) for a in attrs}
                                     for state, attrs in self._freezable_layers
                                     if len(state.layers)]

    def _on_row_selected_end(self, event):
        self._apply_redshift_from_table(value=self._redshift_cache, row=None)

        if not self._freeze_states_on_row_change:
            return

        for state, attrs in self._freezable_states:
            state._frozen_state = []

        # Restore data-layer states from cache, then reset cache
        for (state, attrs), cache in zip(self._freezable_layers, self._frozen_layers_cache):
            state.layers[0].update_from_dict(cache)

        self._frozen_layers_cache = []

    def _redshift_listener(self, msg):
        '''Save new redshifts (including from the helper itself)'''
        if self._update_in_progress:
            # then ignore messages for now, the final redshift will be set once the
            # data is loaded and the row change is complete.
            return

        if msg.param == "redshift":
            row = self.app.get_viewer(self._default_table_viewer_reference_name).current_row
            # NOTE: this updates the value in the table for the current row.  This
            # in turn will feedback to call _apply_redshift_from_table and set
            # the internal value.
            if msg.value == self.get_column("Redshift")[row]:
                # avoid race condition
                return
            self.update_column('Redshift', msg.value, row=row)

    def _apply_redshift_from_table(self, row, value=None):
        # apply redshift from a specific row in the table (current row)
        # to the underlying spectrum viewers (and therefore both the
        # redshift slider as well as exposing when accessing specviz.get_spectra(...))
        if value is None and row is not None:
            value = self.get_column('Redshift')[row]

        if value is not None:
            self.specviz.set_redshift(value)

    def _row_click_message_handler(self, msg):
        self._handle_image_zoom(msg)
        # expose the row to vue for each of the viewers
        self.app.state.settings = {**self.app.state.settings, 'mosviz_row': msg.selected_index}

    def _handle_image_zoom(self, msg):
        mos_data = self.app.data_collection['MOS Table']

        if mos_data.find_component_id("Images") is None:
            return

        imview = self.app.get_viewer(self._default_image_viewer_reference_name)

        # trigger zooming the image, if there is an image
        if msg.shared_image:
            center, height = self._zoom_to_object_params(msg)
        else:
            center, height = self._zoom_to_slit_params(msg)

        if height is not None:
            image_axis_ratio = (abs(imview.state.x_max - imview.state.x_min) /
                                abs(imview.state.y_max - imview.state.y_min))
            x_height = image_axis_ratio * height
            cur_xcen = (imview.state.x_min + imview.state.x_max) * 0.5
            cur_ycen = (imview.state.y_min + imview.state.y_max) * 0.5

            with delay_callback(imview.state, 'x_min', 'x_max', 'y_min', 'y_max'):
                imview.state.x_min = cur_xcen - x_height
                imview.state.y_min = cur_ycen - height
                imview.state.x_max = cur_xcen + x_height
                imview.state.y_max = cur_ycen + height

        if center is not None:
            imview.center_on(center)

    def _zoom_to_object_params(self, msg):

        table_data = self.app.data_collection['MOS Table']
        specview = self.app.get_viewer(self._default_spectrum_2d_viewer_reference_name)

        if ("R.A." not in table_data.component_ids() or
                "Dec." not in table_data.component_ids()):
            return None, None

        ra = table_data["R.A."][msg.selected_index]
        dec = table_data["Dec."][msg.selected_index]

        if (ra == FALLBACK_NAME) or (dec == FALLBACK_NAME):
            return None, None

        try:
            pixel_height = abs(specview.axis_y.scale.max - specview.axis_y.scale.min) * 0.5
        except Exception:
            pixel_height = None
        else:
            if pixel_height < 1:
                pixel_height = None
        sky = SkyCoord(ra, dec, unit='deg')

        return sky, pixel_height

    def _zoom_to_slit_params(self, msg):
        imview = self.app.get_viewer(self._default_image_viewer_reference_name)
        specview = self.app.get_viewer(self._default_spectrum_2d_viewer_reference_name)

        try:
            sky_region = jwst_header_to_skyregion(specview.layers[0].layer.meta)
        except Exception:
            # If the header didn't have slit params, can't zoom to it.
            return None, None

        sky = sky_region.center
        w = imview.layers[0].layer.coords
        pix = w.world_to_pixel(sky)
        upper = w.world_to_pixel(SkyCoord(sky.ra, sky.dec + sky_region.height))
        pixel_height = abs(upper[1] - pix[1])  # y

        return pix, pixel_height

    def _add_redshift_column(self):
        # Parse any information from the files into columns in the table
        def _get_sp_attribute(table_data, row, attr, fill=None):
            try:
                sp1_name = table_data['1D Spectra'][row]
            except IncompatibleAttribute:
                sp1_val = None
            else:
                sp1 = self.app.data_collection[sp1_name].get_object()
                sp1_val = getattr(sp1, attr, None)

            try:
                sp2_name = table_data['2D Spectra'][row]
            except IncompatibleAttribute:
                sp2_val = None
            else:
                sp2 = self.app.data_collection[sp2_name].get_object()
                sp2_val = getattr(sp2, attr, sp1_val)

            if sp1_val is not None and sp1_val != sp2_val:
                # then there was a conflict
                msg = f"Warning: value for {attr} in row {row} in disagreement between Spectrum1D and Spectrum2D" # noqa
                msg = SnackbarMessage(msg, color='warning', sender=self)
                self.app.hub.broadcast(msg)

            if sp2_val is None:
                return fill

            return sp2_val

        table_data = self.app.data_collection['MOS Table']
        redshifts = np.asarray([_get_sp_attribute(table_data, row, 'redshift', 0)
                                for row in range(int(table_data.size))])
        self._add_or_update_column(column_name='Redshift', data=redshifts,
                                   show=np.any(redshifts != 0))

    def load_data(self, spectra_1d=None, spectra_2d=None, images=None,
                  spectra_1d_label=None, spectra_2d_label=None,
                  images_label=None, directory=None, instrument=None):
        """
        Load and parse a set of MOS spectra and images.

        Parameters
        ----------
        spectra_1d : list or str
            A list of spectra as translatable container objects (e.g.
            ``Spectrum1D``) that can be read by glue-jupyter. Alternatively,
            can be a string file path.

        spectra_2d : list or str
            A list of spectra as translatable container objects (e.g.
            ``Spectrum1D``) that can be read by glue-jupyter. Alternatively,
            can be a string file path.

        images : list of obj, str, or `None`
            A list of images as translatable container objects
            (string file path, FITS HDU, FITS HDUList, NDData, or numpy array).
            Alternatively, can be a string file path. If `None`, no images are displayed.

        spectra_1d_label : str or list
            String representing the label for the data item loaded via
            ``spectra_1d``. Can be a list of strings representing data labels
            for each item in ``spectra_1d`` if  ``spectra_1d`` is a list.

        spectra_2d_label : str or list
            String representing the label for the data item loaded via
            ``spectra_2d``. Can be a list of strings representing data labels
            for each item in ``spectra_2d`` if  ``spectra_2d`` is a list.

        images_label : str or list
            String representing the label for the data item loaded via
            ``images``. Can be a list of strings representing data labels
            for each item in ``images`` if  ``images`` is a list.

        directory : str, optional
            Instead of loading lists of spectra and images, the path to a directory
            containing all files for a single JWST observation may be given.
            If this is provided, all the above inputs are ignored.

        instrument : {'niriss', 'nircam', 'nirspec'}, optional
            Required and only used if ``directory`` is specified. Value is not case sensitive.
        """
        # Link data after everything is loaded
        self.app.auto_link = False
        allow_link_table = True

        if isinstance(instrument, str):
            instrument = instrument.lower()

        if images is not None and not isinstance(images, (list, tuple)):
            single_image = True
        else:
            single_image = False

        if directory is not None:
            if is_zipfile(str(directory)):
                raise TypeError("Please extract your data first and provide the directory")
            elif os.path.isdir(directory):
                if instrument not in ('nirspec', 'niriss', 'nircam'):
                    raise ValueError(
                        "Ambiguous MOS Instrument: Only JWST NIRSpec, NIRCam, and "
                        f"NIRISS folder parsing are currently supported but got '{instrument}'")
                if instrument == "nirspec":
                    super().load_data(directory, parser_reference="mosviz-nirspec-directory-parser")
                else:  # niriss or nircam
                    self.load_jwst_directory(directory, instrument=instrument)
            else:
                raise NotImplementedError(f"{directory} is not a directory")

        # For the following, always load in this order: 1d, 2d, images, metadata

        elif (spectra_1d is not None and spectra_2d is not None
                and images is not None):
            n_specs = self.load_1d_spectra(spectra_1d, spectra_1d_label)
            self.load_2d_spectra(spectra_2d, spectra_2d_label)

            # If we have a single image for multiple spectra, tell the table viewer.
            if single_image:
                self._shared_image = True
                self.app.get_viewer(self._default_table_viewer_reference_name)._shared_image = True
                if n_specs > 1:
                    self.load_images(images, images_label, share_image=n_specs)
                else:
                    self.load_images(images, images_label)
            else:
                self.load_images(images, images_label)

            self.load_metadata()

        elif spectra_1d is not None and spectra_2d is not None:
            self.load_1d_spectra(spectra_1d, spectra_1d_label)
            self.load_2d_spectra(spectra_2d, spectra_2d_label)
            self.load_metadata()

        elif spectra_1d and images:
            n_specs = self.load_1d_spectra(spectra_1d, spectra_1d_label)

            # If we have a single image for multiple spectra, tell the table viewer.
            if single_image:
                self._shared_image = True
                self.app.get_viewer(self._default_table_viewer_reference_name)._shared_image = True
                if n_specs > 1:
                    self.load_images(images, images_label, share_image=n_specs)
                else:
                    self.load_images(images, images_label)
            else:
                self.load_images(images, images_label)

            allow_link_table = False

        elif spectra_2d and images:
            n_specs = self.load_2d_spectra(spectra_2d, spectra_2d_label)

            # If we have a single image for multiple spectra, tell the table viewer.
            if single_image:
                self._shared_image = True
                self.app.get_viewer(self._default_table_viewer_reference_name)._shared_image = True
                if n_specs > 1:
                    self.load_images(images, images_label, share_image=n_specs)
                else:
                    self.load_images(images, images_label)
            else:
                self.load_images(images, images_label)

            allow_link_table = False

        elif spectra_1d:
            self.load_1d_spectra(spectra_1d, spectra_1d_label)
            allow_link_table = False

        elif spectra_2d:
            self.load_2d_spectra(spectra_2d, spectra_2d_label)
            allow_link_table = False

        else:
            raise NotImplementedError("Please set valid values for the Mosviz.load_data() method")

        if allow_link_table:
            self.link_table_data(None)

        self._add_redshift_column()

        # Any subsequently added data will automatically be linked
        # with data already loaded in the app
        self.app.auto_link = True

        # Manually set viewer options
        self.app.get_viewer(
            self._default_spectrum_viewer_reference_name
        ).figure.axes[1].tick_format = '0.1e'
        self.app.get_viewer(
            self._default_image_viewer_reference_name
        ).figure.axes[1].label_offset = "-50"

        # Load the first object into the viewers automatically
        self.app.get_viewer(self._default_table_viewer_reference_name).figure_widget.highlighted = 0

        # Notify the user that this all loaded successfully
        self.app.hub.broadcast(SnackbarMessage(
            "MOS data loaded successfully", color="success", sender=self))

        self._default_visible_columns = self.get_column_names(True)

    def link_table_data(self, data_obj):
        """
        Batch link data in the Mosviz table rather than doing it on
        data load.

        Parameters
        ----------
        data_obj : obj
            Input for Mosviz data parsers.
        """
        super().load_data(data_obj, parser_reference="mosviz-link-data")

    def load_spectra(self, spectra_1d, spectra_2d):
        """
        Load 1D and 2D spectra using lists or strings to represent each.

        Parameters
        ----------
        spectra_1d : list or str
            A list of spectra as translatable container objects (e.g.
            ``Spectrum1D``) that can be read by glue-jupyter. Alternatively,
            can be a string file path.

        spectra_2d : list or str
            A list of spectra as translatable container objects (e.g.
            ``Spectrum1D``) that can be read by glue-jupyter. Alternatively,
            can be a string file path.
        """

        self.load_data(spectra_1d=spectra_1d, spectra_2d=spectra_2d)

    def load_spectra_from_directory(self, directory, instrument):
        """
        Load 1D and 2D spectra from a directory.

        Parameters
        ----------
        directory : str
            The path of the directory where Mosviz data is located.

        instrument : str
            The instrument the Mosviz data originated from.
        """
        self.load_data(directory=directory, instrument=instrument)

    def load_metadata(self):
        """
        Parse the internal meta for our expected information
        """
        self.app.load_data(file_obj=None, parser_reference="mosviz-metadata-parser")

    def load_1d_spectra(self, data_obj, data_labels=None, add_redshift_column=False):
        """
        Load and parse a set of 1D spectra objects.

        Parameters
        ----------
        data_obj : list or str
            A list of spectra as translatable container objects (e.g.
            ``Spectrum1D``) that can be read by glue-jupyter. Alternatively,
            can be a string file path.
        data_labels : str or list
            String representing the label for the data item loaded via
            ``data_obj``. Can be a list of strings representing data labels
            for each item in ``data_obj`` if  ``data_obj`` is a list.
        add_redshift_column : bool
            Add redshift column to Mosviz table.

        Returns
        -------
        n_specs : int
            Number of data objects loaded.

        """
        n_specs = mos_spec1d_parser(self.app, data_obj, data_labels=data_labels)
        if add_redshift_column:
            self._add_redshift_column()
        return n_specs

    def load_2d_spectra(self, data_obj, data_labels=None, add_redshift_column=False):
        """
        Load and parse a set of 2D spectra objects.

        Parameters
        ----------
        data_obj : list or str
            A list of 2D spectra as translatable container objects (e.g.
            ``Spectrum1D``) that can be read by glue-jupyter. Alternatively,
            can be a string file path.
        data_labels : str or list
            String representing the label for the data item loaded via
            ``data_obj``. Can be a list of strings representing data labels
            for each item in ``data_obj`` if  ``data_obj`` is a list.
        add_redshift_column : bool
            Add redshift column to Mosviz table.

        Returns
        -------
        n_specs : int
            Number of data objects loaded.

        """
        n_specs = mos_spec2d_parser(self.app, data_obj, data_labels=data_labels)
        if add_redshift_column:
            self._add_redshift_column()
        return n_specs

    def load_jwst_directory(self, data_obj, data_labels=None, instrument=None,
                            add_redshift_column=False):
        """Load NIRISS or NIRCam data from a directory."""
        self.app.auto_link = False
        super().load_data(data_obj, parser_reference="mosviz-niriss-parser",
                          instrument=instrument)

        self.link_table_data(data_obj)
        if add_redshift_column:
            self._add_redshift_column()

        self.app.auto_link = True

    def load_images(self, data_obj, data_labels=None, share_image=0, add_redshift_column=False):
        """
        Load and parse a set of image objects. If providing a file path, it
        must be readable by ``astropy.io.fits``.

        Parameters
        ----------
        data_obj : list of obj, str, or `None`
            A list of images as translatable container objects
            (FITS HDU, FITS HDUList, NDData, or numpy array). Alternatively,
            can be a string file path. If `None`, no images are displayed.
        data_labels : str or list
            String representing the label for the data item loaded via
            ``data_obj``. Can be a list of strings representing data labels
            for each item in ``data_obj`` if  ``data_obj`` is a list.
        share_image : int, optional
            If 0, images are treated as applying to individual spectra. If non-zero,
            a single image will be shared by multiple spectra so that clicking a
            different row in the table does not reload the displayed image.
            Currently, if non-zero, the provided number must match the number of
            spectra.
        add_redshift_column : bool
            Add redshift column to Mosviz table.
        """
        super().load_data(data_obj, parser_reference="mosviz-image-parser",
                          data_labels=data_labels, share_image=share_image)
        if add_redshift_column:
            self._add_redshift_column()

    def get_column_names(self, visible=None):
        """
        List the names of the columns in the table.

        Parameters
        ----------
        visible: bool or None
            If None (default): will show all available column names.
            If True: will only show columns names currently shown in the table.
            If False: will only show column names currently not shown in the table.
        """
        if visible is None:
            return [c.label for c in self.app.data_collection['MOS Table'].components]
        elif visible is True:
            return [h['value'] for h in self.app.get_viewer(
                self._default_table_viewer_reference_name
            ).widget_table.headers]
        elif visible is False:
            return [cn for cn in self.get_column_names() if cn not in self.get_column_names(True)]
        else:
            raise ValueError("visible must be one of None, True, or False.")

    def set_visible_columns(self, column_names=None):
        """
        Set the columns to be visible in the table.

        Parameters
        ----------
        column_names: list or None
            list of columns to be visible in the table.  If None, will default to original
            visible columns.
        """
        if column_names is None:
            column_names = self._default_visible_columns
        if not isinstance(column_names, list):
            raise TypeError("column_names must be of type list")
        avail_names = self.get_column_names()
        if not np.all([c in avail_names for c in column_names]):
            raise ValueError("not all entries of column_names are valid")
        is_sortable = ['Redshift']
        headers = [{'text': cn, 'value': cn, 'sortable': cn in is_sortable} for cn in column_names]
        wt = self.app.get_viewer(self._default_table_viewer_reference_name).widget_table
        wt.set_state({'headers': headers})
        wt.send_state()

    def hide_column(self, column_name):
        """
        Hide a single column in the table.

        Parameters
        ----------
        column_name: str
            Name of the column to hide
        """
        if not isinstance(column_name, str):
            raise TypeError("column_name must be of type str")

        column_names = self.get_column_names()
        if column_name not in column_names:
            raise ValueError(f"{column_name} not in available columns ({column_names})")
        new_column_names = [cn for cn in self.get_column_names(True)
                            if cn not in column_name]
        return self.set_visible_columns(new_column_names)

    def show_column(self, column_name):
        """
        Show a hidden column in the table.

        Parameters
        ----------
        column_name: str
            Name of the column to show
        """
        if not isinstance(column_name, str):
            raise TypeError("column_name must be of type str")

        vis_column_names = self.get_column_names(True)
        if column_name not in vis_column_names:
            all_column_names = self.get_column_names()
            if column_name in all_column_names:
                return self.set_visible_columns(vis_column_names+[column_name])
            else:
                raise ValueError(f"{column_name} not in available columns ({all_column_names})")

    def get_column(self, column_name):
        """
        Get the data from a column in the table.

        Parameters
        ----------
        column_name: str
            Header string of an existing column in the table.

        Returns
        -------
        array
            copy of the data array.
        """
        return np.asarray(deepcopy(self.app.data_collection['MOS Table'].get_component(column_name).data)) # noqa

    def _add_or_update_column(self, column_name, data=None, show=True):
        if not isinstance(column_name, str):
            raise TypeError("column_name must be of type str")

        table_data = self.app.data_collection['MOS Table']

        if data is None:
            data = [None]*table_data.size
        if not isinstance(data, (list, tuple, np.ndarray)):
            raise TypeError("data must be array-like")
        if len(data) != table_data.size:
            raise ValueError(f"data must have length {table_data.size} (rows in table)")

        if column_name == 'Redshift':
            # then we should raise errors in advance if the values would fail
            # when applied to the spectra
            try:
                _ = u.Quantity(data)
            except TypeError:
                raise TypeError("Redshift values must be floats or quantity objects")

        if column_name in self.get_column_names():
            table_data.update_components({table_data.get_component(column_name): data})
        else:
            table_data.add_component(data, column_name)
        if show is True:
            self.show_column(column_name)
        elif not show and show is not None:
            self.hide_column(column_name)

        if column_name == 'Redshift':
            # apply the value in the current row to the specviz object
            row = self.app.get_viewer(self._default_table_viewer_reference_name).current_row
            if row is not None:
                self._apply_redshift_from_table(value=data[row], row=row)

        return self.get_column(column_name)

    def add_column(self, column_name, data=None, show=True):
        """
        Add a new data column to the table.

        If ``column_name`` is 'Redshift', the column will be synced with the redshift
        in the respective spectrum objects.

        Parameters
        ----------
        column_name : str
            Header string to be shown in the table.  If already exists as a column in
            the table, the data for that column will be updated.
        data : array-like
            Array-like set of data values, e.g. redshifts, RA, DEC, etc.
        show: bool or None
            Whether to show the column in the table (defaults to True).  If None, will
            show if the column is new, otherwise will leave at current state.

        Returns
        -------
        array
            copy of the data in the added or edited column.
        """
        if column_name in self.get_column_names():
            raise ValueError(f"{column_name} already exists.  Use update_column to update contents")

        return self._add_or_update_column(column_name, data, show=show)

    def update_column(self, column_name, data, row=None):
        """
        Update the data in an existing column.

        If ``column_name`` is 'Redshift', the column will be synced with the redshift
        in the respective spectrum objects.

        Parameters
        ----------
        column_name: str
            Name of the existing column to update
        data: array-like or float/int/string
            Array-like set of data values or value at a single index (in which
            case ``row`` must be provided)
        row: None or int
            Index of the row to replace.  If None, will replace entire column
            and ``data`` must be array-like with the appropriate length.

        Returns
        -------
        array
            copy of the data in the edited column
        """
        if column_name not in self.get_column_names():
            raise ValueError(f"{column_name} is not an existing column label")

        if row is not None:
            replace_value = data
            data = self.get_column(column_name)
            if not isinstance(row, int):
                raise TypeError("row must be an integer or None")
            if row < 0 or row >= len(data):
                raise ValueError("row out of range of table")

            data[row] = replace_value

        return self._add_or_update_column(column_name, data, show=None)

    def to_table(self):
        """
        Creates an astropy `~astropy.table.QTable` object from the MOS table
        viewer.

        Returns
        -------
        `~astropy.table.QTable`
            An astropy table constructed from the loaded mos data.
        """
        table_data = self.app.data_collection['MOS Table']

        data_dict = {}

        for cid in table_data.components:
            comp = table_data.get_component(cid)
            # Rename the first column to something more sensible
            if cid.label == "Pixel Axis 0 [x]":
                label = "Table Index"
            else:
                label = cid.label

            if comp.units is not None:
                if comp.units == "":
                    data_dict[label] = comp.data
                else:
                    unit = u.Unit(comp.units)
                    data_dict[label] = comp.data * unit
            else:
                data_dict[label] = comp.data

        return QTable(data_dict)

    def to_csv(self, filename="MOS_data.csv", selected=False, overwrite=False):
        """
        Creates a csv file with the contents of the MOS table viewer

        Parameters
        ----------
        filename: str
            Filename for the output CSV file.
        selected: bool
            If set to True, only the checked rows in the table will be output.
        """

        path = Path(filename)
        if path.is_file():
            if not overwrite:
                raise FileExistsError(f"File {filename} exists, choose another"
                                      " file name or set overwrite=True")

        table_df = self.app.data_collection['MOS Table'].to_dataframe()

        if filename[-4:] != ".csv":
            filename += ".csv"

        # Restrict to only checked rows if desired
        if selected:
            checked_rows = self.app.get_viewer(
                self._default_table_viewer_reference_name
            ).widget_table.checked
            table_df = table_df.iloc[checked_rows]

        # This column is an artifact of the table widget construction with no meaning
        table_df = table_df.drop(labels="Pixel Axis 0 [x]", axis=1)

        table_df.to_csv(filename, index_label="Table Index")

    @property
    def specviz(self):
        """
        A Specviz helper (:class:`~jdaviz.configs.specviz.helper.Specviz`) for the Jdaviz
        application that is wrapped by Mosviz.
        """
        if not hasattr(self, '_specviz'):
            self._specviz = Specviz(app=self.app)
        return self._specviz

    @property
    def specviz2d(self):
        """
        A Specviz2d helper (:class:`~jdaviz.configs.specviz2d.helper.Specviz2d`) for the Jdaviz
        application that is wrapped by Mosviz.
        """
        if not hasattr(self, '_specviz2d'):
            self._specviz2d = Specviz2d(app=self.app)
        return self._specviz2d

    def _get_spectrum(self, column, row=None, apply_slider_redshift="Warn"):
        if row is None:
            row = self.app.get_viewer(self._default_table_viewer_reference_name).current_row
        if not isinstance(row, (int, np.int64)):
            raise TypeError("row not of type int")

        data_labels = self.get_column(column)
        if row < 0 or row >= len(data_labels):
            raise ValueError(f"row must be between 0 and {len(data_labels)-1}")

        data_label = data_labels[row]
        spectra = self.app.data_collection[data_label].get_object()
        if not apply_slider_redshift:
            return spectra
        else:
            redshift = self.get_column("Redshift")[row]
            if apply_slider_redshift == "Warn":
                warnings.warn("Warning: Applying the value from the redshift "
                              "slider to the output spectra. To avoid seeing this "
                              "warning, explicitly set the apply_slider_redshift "
                              "keyword option to True or False.")

            return _apply_redshift_to_spectra(spectra, redshift)

    def get_spectrum_1d(self, row=None, apply_slider_redshift="Warn"):
        """
        Access a 1D spectrum for any row in the Table.

        Parameters
        ----------
        row: int or None
            Row index in the Table. If not provided or None, will access
            from the currently selected row.
        apply_slider_redshift: bool or "Warn"
            Whether to apply the redshift in the Table to the returned
            Spectrum.  If not provided or "Warn", will apply the redshift
            but raise a warning.

        Returns
        -------
        `~specutils.Spectrum1D`
        """
        return self._get_spectrum('1D Spectra', row, apply_slider_redshift)

    def get_spectrum_2d(self, row=None, apply_slider_redshift="Warn"):
        """
        Access a 2D spectrum for any row in the Table.

        Parameters
        ----------
        row: int or None
            Row index in the Table. If not provided or None, will access
            from the currently selected row.
        apply_slider_redshift: bool or "Warn"
            Whether to apply the redshift in the Table to the returned
            Spectrum.  If not provided or "Warn", will apply the redshift
            but raise a warning.

        Returns
        -------
        `~specutils.Spectrum1D`
        """
        return self._get_spectrum('2D Spectra', row, apply_slider_redshift)

    def get_data(self, data_label=None, spectral_subset=None, cls=None):
        """
        Returns data with name equal to data_label of type cls with subsets applied from
        spectral_subset.

        Parameters
        ----------
        data_label : str, optional
            Provide a label to retrieve a specific data set from data_collection.
        spectral_subset : str, optional
            Spectral subset applied to data.
        cls : `~specutils.Spectrum1D`, `~astropy.nddata.CCDData`, optional
            The type that data will be returned as.

        Returns
        -------
        data : cls
            Data is returned as type cls with subsets applied.

        """
        return self._get_data(data_label=data_label, spectral_subset=spectral_subset, cls=cls)
