import logging

import numpy as np
from pathlib import Path
from time import time

import astropy.units as u
from astropy.table import QTable
from astropy.coordinates import SkyCoord
from echo import delay_callback

from jdaviz.core.helpers import ConfigHelper
from jdaviz.core.events import SnackbarMessage, TableClickMessage
from jdaviz.configs.specviz import Specviz
from jdaviz.configs.mosviz.plugins import jwst_header_to_skyregion

__all__ = ['Mosviz', 'MosViz']


class Mosviz(ConfigHelper):
    """Mosviz Helper class"""

    _default_configuration = "mosviz"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        spec1d = self.app.get_viewer("spectrum-viewer")
        spec1d.scales['x'].observe(self._update_spec2d_x_axis, names=['min', 'max'])

        spec2d = self.app.get_viewer("spectrum-2d-viewer")
        spec2d.scales['x'].observe(self._update_spec1d_x_axis, names=['min', 'max'])

        # Listen for clicks on the table in case we need to zoom the image
        self.app.hub.subscribe(self, TableClickMessage,
                               handler=self._row_click_message_handler)

        self._shared_image = False

        self._scales1d = spec1d.scales['x']
        self._scales2d = spec2d.scales['x']

        self._panning_warning_triggered = False
        self._last_panning_warning = 0

        self._update_in_progress = False

    def _extend_world(self, spec1d, ext):
        # Extend 1D spectrum world axis to enable panning (within reason) past
        # the bounds of data
        world = self.app.data_collection[spec1d]["World 0"].copy()
        dw = world[1]-world[0]
        prepend = np.linspace(world[0]-dw*ext, world[0]-dw, ext)
        dw = world[-1]-world[-2]
        append = np.linspace(world[-1]+dw, world[-1]+dw*ext, ext)
        world = np.hstack((prepend, world, append))
        return world

    def _update_spec2d_x_axis(self, change):
        # This assumes the two spectrum viewers have the same x-axis shape and
        # wavelength solution, which should always hold
        table_viewer = self.app.get_viewer('table-viewer')

        if self._update_in_progress or table_viewer.row_selection_in_progress:
            return

        min_1d = self._scales1d.min
        max_1d = self._scales1d.max

        spec1d = table_viewer._selected_data["spectrum-viewer"]
        extend_by = int(self.app.data_collection[spec1d]["World 0"].shape[0])
        world = self._extend_world(spec1d, extend_by)

        # Workaround for flipped data
        min_world, max_world = ((world[0], world[-1]) if not self._is_world_flipped()
                                else (world[-1], world[0]))

        # Warn the user if they've panned far enough away from the data
        # that the viewers will desync
        if min_1d < min_world or max_1d > max_world:
            self._show_panning_warning()
            return

        self._panning_warning_triggered = False

        idx_min = float((np.abs(world - min_1d)).argmin()) - extend_by
        idx_max = float((np.abs(world - max_1d)).argmin()) - extend_by

        self._update_in_progress = True
        with self._scales2d.hold_sync():
            self._scales2d.min = idx_min
            self._scales2d.max = idx_max

        self._update_in_progress = False

    def _update_spec1d_x_axis(self, change):
        # This assumes the two spectrum viewers have the same x-axis shape and
        # wavelength solution, which should always hold
        table_viewer = self.app.get_viewer('table-viewer')

        if self._update_in_progress or table_viewer.row_selection_in_progress:
            return

        min_2d = self._scales2d.min
        max_2d = self._scales2d.max

        spec1d = table_viewer._selected_data["spectrum-viewer"]
        extend_by = int(self.app.data_collection[spec1d]["World 0"].shape[0])
        world = self._extend_world(spec1d, extend_by)

        idx_min = int(np.around(min_2d)) + extend_by
        idx_max = int(np.around(max_2d)) + extend_by

        # Warn the user if they've panned far enough away from the data
        # that the viewers will desync
        # Note: Because of the flipped data workaround, idx_min can be > idx_max
        max_world = len(world)
        if not (0 <= idx_min < max_world and 0 <= idx_max < max_world):
            self._show_panning_warning()
            return

        self._panning_warning_triggered = False

        self._update_in_progress = True
        with self._scales1d.hold_sync():
            self._scales1d.min = world[idx_min]
            self._scales1d.max = world[idx_max]

        self._update_in_progress = False

    def _show_panning_warning(self):
        now = time()

        # Limit the number of messages that can be send to 1 per 5 seconds
        panning_warning_timeout = 5

        if (not self._panning_warning_triggered
                and now > self._last_panning_warning + panning_warning_timeout):
            self._panning_warning_triggered = True
            self._last_panning_warning = now
            msg = ("Warning: panning too far away from the data may desync"
                   "the 1D and 2D spectrum viewers")
            msg = SnackbarMessage(msg, color='warning', sender=self)
            self.app.hub.broadcast(msg)

    def _is_world_flipped(self):
        spec1d = self.app.get_viewer('table-viewer')._selected_data.get("spectrum-viewer")
        if not spec1d:
            return False
        world = self.app.data_collection[spec1d]["World 0"]
        return world[0] > world[-1]

    def _row_click_message_handler(self, msg):
        self._handle_image_zoom(msg)
        self._handle_flipped_data()

    def _handle_image_zoom(self, msg):
        mos_data = self.app.data_collection['MOS Table']

        # trigger zooming the image, if there is an image
        if mos_data.find_component_id("Images") is not None:
            if msg.shared_image:
                center, height = self._zoom_to_object_params(msg)
            else:
                try:
                    center, height = self._zoom_to_slit_params(msg)
                except IndexError:
                    # If there's nothing in the spectrum2d viewer, we can't get slit info
                    return

            if center is None or height is None:
                # Can't zoom if we couldn't figure out where to zoom (e.g. if RA/Dec not in table)
                return

            imview = self.app.get_viewer("image-viewer")

            image_axis_ratio = ((imview.axis_x.scale.max - imview.axis_x.scale.min) /
                                (imview.axis_y.scale.max - imview.axis_y.scale.min))

            with delay_callback(imview.state, 'x_min', 'x_max', 'y_min', 'y_max'):
                imview.state.x_min = center[0] - image_axis_ratio*height
                imview.state.y_min = center[1] - height
                imview.state.x_max = center[0] + image_axis_ratio*height
                imview.state.y_max = center[1] + height

    def _handle_flipped_data(self):
        # Workaround for flipped data
        if self._is_world_flipped():
            min, max = self._scales2d.max, self._scales2d.min
            with self._scales2d.hold_sync():
                self._scales2d.min = min
                self._scales2d.max = max

    def _zoom_to_object_params(self, msg):

        table_data = self.app.data_collection['MOS Table']
        imview = self.app.get_viewer("image-viewer")
        specview = self.app.get_viewer("spectrum-2d-viewer")

        if ("R.A." not in table_data.component_ids() or
                "Dec." not in table_data.component_ids()):
            return None, None

        ra = table_data["R.A."][msg.selected_index]
        dec = table_data["Dec."][msg.selected_index]

        pixel_height = 0.5*(specview.axis_y.scale.max - specview.axis_y.scale.min)
        point = SkyCoord(ra*u.deg, dec*u.deg)

        pix = imview.layers[0].layer.coords.world_to_pixel(point)

        return pix, pixel_height

    def _zoom_to_slit_params(self, msg):
        imview = self.app.get_viewer("image-viewer")
        specview = self.app.get_viewer("spectrum-2d-viewer")

        try:
            sky_region = jwst_header_to_skyregion(specview.layers[0].layer.meta)
        except KeyError:
            # If the header didn't have slit params, can't zoom to it.
            return None, None
        ra = sky_region.center.ra.deg
        dec = sky_region.center.dec.deg

        pix = imview.layers[0].layer.coords.world_to_pixel(sky_region.center)

        # Height of slit in decimal degrees
        height = sky_region.height.deg

        upper = imview.layers[0].layer.coords.world_to_pixel(SkyCoord(ra*u.deg,
                                                             (dec + height)*u.deg))
        pixel_height = upper[1] - pix[1]

        return pix, pixel_height

    def load_data(self, spectra_1d=None, spectra_2d=None, images=None,
                  spectra_1d_label=None, spectra_2d_label=None,
                  images_label=None, *args, **kwargs):
        """
        Load and parse a set of MOS spectra and images

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
            ``onedspectra``. Can be a list of strings representing data labels
            for each item in ``data_obj`` if  ``data_obj`` is a list.

        spectra_2d_label : str or list
            String representing the label for the data item loaded via
            ``twodspectra``. Can be a list of strings representing data labels
            for each item in ``data_obj`` if  ``data_obj`` is a list.

        images_label : str or list
            String representing the label for the data item loaded via
            ``images``. Can be a list of strings representing data labels
            for each item in ``data_obj`` if  ``data_obj`` is a list.
        """
        # Link data after everything is loaded
        self.app.auto_link = False

        directory = kwargs.pop('directory', None)
        instrument = kwargs.pop('instrument', None)
        msg = ""

        if directory is not None and instrument is not None:
            if instrument.lower() == "nirspec":
                super().load_data(directory, "mosviz-nirspec-directory-parser")
            elif instrument.lower() == "niriss":
                self.load_niriss_data(directory)
            else:
                msg = "Warning: Data is not from NIRISS or Nirspec, " \
                      "data loading may not work"
                super().load_data(directory, "mosviz-nirspec-directory-parser")

        elif directory is not None:
            msg = "Warning: Please provide the name of the instrument" \
                  " in the load_data method"

        elif (spectra_1d is not None and spectra_2d is not None
                and images is not None):
            # If we have a single image for multiple spectra, tell the table viewer
            if not isinstance(images, (list, tuple)) and isinstance(spectra_1d, (list, tuple)):
                self._shared_image = True
                self.app.get_viewer('table-viewer')._shared_image = True
                self.load_images(images, images_label, share_image=len(spectra_1d))
            else:
                self.load_images(images, images_label)

            if images is not None and not self._shared_image:
                self.load_metadata(images, ids=images)

            self.load_2d_spectra(spectra_2d, spectra_2d_label)
            self.load_1d_spectra(spectra_1d, spectra_1d_label)
            self.load_metadata(spectra_2d, spectra=True)

        elif spectra_1d is not None and spectra_2d is not None:
            self.load_2d_spectra(spectra_2d, spectra_2d_label)
            self.load_1d_spectra(spectra_1d, spectra_1d_label)
            self.load_metadata(spectra_2d, spectra=True)
            self.load_metadata(spectra_1d, spectra=True, sp1d=True, ids=spectra_1d)

        else:
            msg = "Warning: Please set valid values for the load_data() method"

        if msg:
            logging.warning(msg)
            msg = SnackbarMessage(msg, color='warning', sender=self)
            self.app.hub.broadcast(msg)

        self.link_table_data(None)

        # Any subsequently added data will automatically be linked
        # with data already loaded in the app
        self.app.auto_link = True

        # Manually set viewer options
        self.app.get_viewer("spectrum-viewer").figure.axes[1].tick_format = '0.1e'
        self.app.get_viewer("image-viewer").figure.axes[1].label_offset = "-50"

        # Load the first object into the viewers automatically
        self.app.get_viewer("table-viewer").figure_widget.highlighted = 0

        # Notify the user that this all loaded successfully
        loaded_msg = SnackbarMessage("MOS data loaded successfully", color="success", sender=self)
        self.app.hub.broadcast(loaded_msg)

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

    def load_metadata(self, data_obj, ids=None, spectra=False, sp1d=False):
        """
        Load and parse a set of FITS objects to extract any relevant metadata.

        Parameters
        ----------
        data_obj : list or str
            A list of FITS objects with parseable headers. Alternatively,
            can be a string file path.
        ids : list of str
            A list with identification strings to be used to label mosviz
            table rows. Typically, a list with file names.
        spectra : Boolean
            In case the FITS objects are related to spectral data.
        sp1d : Boolean
            In case the FITS objects are related to 1d spectral data.
        """
        self.app.load_data(data_obj, ids=ids, spectra=spectra, sp1d=sp1d,
                           parser_reference="mosviz-metadata-parser")

    def load_1d_spectra(self, data_obj, data_labels=None):
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
        """
        super().load_data(data_obj, parser_reference="mosviz-spec1d-parser",
                          data_labels=data_labels)

    def load_2d_spectra(self, data_obj, data_labels=None):
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
        """
        super().load_data(data_obj, parser_reference="mosviz-spec2d-parser",
                          data_labels=data_labels)

    def load_niriss_data(self, data_obj, data_labels=None):
        self.app.auto_link = False

        super().load_data(data_obj, parser_reference="mosviz-niriss-parser")

        self.link_table_data(data_obj)

        self.app.auto_link = True

    def load_images(self, data_obj, data_labels=None, share_image=0):
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
        """
        super().load_data(data_obj, parser_reference="mosviz-image-parser",
                          data_labels=data_labels, share_image=share_image)

    def add_column(self, data, column_name=None):
        """
        Add a new data column to the table.

        Parameters
        ----------
        data : array-like
            Array-like set of data values, e.g. redshifts, RA, DEC, etc.
        column_name : str
            Header string to be shown in the table.
        """
        table_data = self.app.data_collection['MOS Table']
        table_data.add_component(data, column_name)

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
            checked_rows = self.app.get_viewer("table-viewer").widget_table.checked
            table_df = table_df.iloc[checked_rows]

        # This column is an artifact of the table widget construction with no meaning
        table_df = table_df.drop(labels="Pixel Axis 0 [x]", axis=1)

        table_df.to_csv(filename, index_label="Table Index")

    @property
    def specviz(self):
        """
        A specviz helper (`~jdaviz.configs.specviz.Specviz`) for the Jdaviz
        application that is wrapped by mosviz
        """
        if not hasattr(self, '_specviz'):
            self._specviz = Specviz(app=self.app)
        return self._specviz


# TODO: Officially deprecate this with coordination with JDAT notebooks team.
# For backward compatibility only.
class MosViz(Mosviz):
    """This class is pending deprecation. Please use `Mosviz` instead."""
    pass
