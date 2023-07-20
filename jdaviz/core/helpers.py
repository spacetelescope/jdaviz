"""
Helper classes are meant to provide a convenient user API for specific
configurations. They allow a separation of "viztool-specific" API and the glue
application objects.

See also https://github.com/spacetelescope/jdaviz/issues/104 for more details
on the motivation behind this concept.
"""
import re
import warnings
from contextlib import contextmanager
from inspect import isclass

import numpy as np
import astropy.units as u
from astropy.wcs.wcsapi import BaseHighLevelWCS
from astropy.nddata import CCDData, StdDevUncertainty
from regions.core.core import Region
from glue.core import HubListener
from glue.core.edit_subset_mode import NewMode
from glue.core.message import SubsetCreateMessage, SubsetDeleteMessage
from glue.core.subset import Subset, MaskSubsetState
from glue.config import data_translator
from ipywidgets.widgets import widget_serialization
from specutils import Spectrum1D, SpectralRegion


from jdaviz.app import Application
from jdaviz.core.events import SnackbarMessage, ExitBatchLoadMessage
from jdaviz.core.template_mixin import show_widget

__all__ = ['ConfigHelper', 'ImageConfigHelper']


class ConfigHelper(HubListener):
    """The Base Helper Class.
    Provides shared abstracted helper methods to the user.

    Subclasses should set ``_default_configuration`` if they are meant to be
    used with a specific configuration.

    Parameters
    ----------
    app : `~jdaviz.app.Application` or `None`
        The application object, or if `None`, creates a new one based on the
        default configuration for this helper.
    verbosity : {'debug', 'info', 'warning', 'error'}
        Verbosity of the popup messages in the application.
    history_verbosity : {'debug', 'info', 'warning', 'error'}
        Verbosity of the history logger in the application.
    """
    _default_configuration = 'default'

    def __init__(self, app=None, verbosity='warning', history_verbosity='info'):
        if app is None:
            self.app = Application(configuration=self._default_configuration)
        else:
            self.app = app
        self.app.verbosity = verbosity
        self.app.history_verbosity = history_verbosity

        # give a reference from the app back to this config helper.  These can be accessed from a
        # viewer via viewer.jdaviz_app and viewer.jdaviz_helper
        # if the helper has already been set, this is probably a nested viz tool. Don't overwrite
        if self.app._jdaviz_helper is None:
            self.app._jdaviz_helper = self

        self.app.hub.subscribe(self, SubsetCreateMessage,
                               handler=lambda msg: self._propagate_callback_to_viewers('_on_subset_create', msg)) # noqa
        self.app.hub.subscribe(self, SubsetDeleteMessage,
                               handler=lambda msg: self._propagate_callback_to_viewers('_on_subset_delete', msg)) # noqa

        self._in_batch_load = 0
        self._delayed_show_in_viewer_labels = {}  # label: viewer_reference pairs

    def _propagate_callback_to_viewers(self, method, msg):
        # viewers don't have access to the app/hub to subscribe to messages, so we'll
        # catch all messages here and pass them on to each of the viewers that
        # have the applicable method implemented.
        for viewer in self.app._viewer_store.values():
            if hasattr(viewer, method):
                getattr(viewer, method)(msg)

    @contextmanager
    def batch_load(self):
        """
        Context manager to delay linking and loading data into viewers
        """
        # we'll use a counter instead of a boolean to allow the user to nest multiple
        # context managers.  Once they're all exited, then the linking/showing will
        # take place.
        self._in_batch_load += 1
        with self.app.data_collection.delay_link_manager_update():
            # user entrypoint (anything within the with-statement will get called here)
            yield

        self._in_batch_load -= 1
        if not self._in_batch_load:
            self.app.hub.broadcast(ExitBatchLoadMessage(sender=self.app))

            # add any data to viewers that were requested but deferred
            for data_label, viewer_ref in self._delayed_show_in_viewer_labels.items():
                self.app.set_data_visibility(viewer_ref, data_label,
                                             visible=True, replace=False)
            self._delayed_show_in_viewer_labels = {}

    def load_data(self, data, data_label=None, parser_reference=None, **kwargs):
        if data_label:
            kwargs['data_label'] = data_label
        self.app.load_data(data, parser_reference=parser_reference, **kwargs)

    @property
    def plugins(self):
        """
        Access API objects for plugins in the plugin tray.

        Returns
        -------
        plugins : dict
            dict of plugin objects
        """
        return {item['label']: widget_serialization['from_json'](item['widget'], None).user_api
                for item in self.app.state.tray_items}

    @property
    def fitted_models(self):
        """
        Returns the fitted models.

        Returns
        -------
        parameters : dict
            dict of `astropy.modeling.Model` objects, or None.
        """

        return self.app.fitted_models

    def get_models(self, models=None, model_label=None, x=None, y=None):
        """
        Loop through all models and output models of the label model_label.
        If x or y is set, return model_labels of those (x, y) coordinates.
        If x and y are None, print all models regardless of coordinates.

        Parameters
        ----------
        models : dict
            A dict of models, with the key being the label name and the value
            being an `astropy.modeling.CompoundModel` object. Defaults to
            `fitted_models` if no parameter is provided.
        model_label : str
            The name of the model that will be found and returned. If it
            equals default, every model present will be returned.
        x : int
            The x coordinate of the model spaxels that will be returned.
        y : int
            The y coordinate of the model spaxels that will be returned.

        Returns
        -------
        selected_models : dict
            Dictionary of the selected models.
        """
        selected_models = {}
        # If models is not provided, use the app's fitted models
        if not models:
            models = self.fitted_models

        # Loop through all keys in the dict models
        for label in models:
            # Prevent "Model 2" from being returned when model_label is "Model"
            if model_label is not None:
                if label.split(" (")[0] != model_label:
                    continue

            # If no label was provided, use label name without coordinates.
            if model_label is None and " (" in label:
                find_label = label.split(" (")[0]
            # If coordinates are not present, just use the label.
            elif model_label is None:
                find_label = label
            else:
                find_label = model_label

            # If x and y are set, return keys that match the model plus that
            # coordinate pair. If only x or y is set, return keys that fit
            # that value for the appropriate coordinate.
            if x is not None and y is not None:
                find_label = r"{} \({}, {}\)".format(find_label, x, y)
            elif x:
                find_label = r"{} \({}, .+\)".format(find_label, x)
            elif y:
                find_label = r"{} \(.+, {}\)".format(find_label, y)

            if re.search(find_label, label):
                selected_models[label] = models[label]

        return selected_models

    def get_model_parameters(self, models=None, model_label=None, x=None, y=None):
        """
        Convert each parameter of model inside models into a coordinate that
        maps the model name and parameter name to a `astropy.units.Quantity`
        object.

        Parameters
        ----------
        models : dict
            A dictionary where the key is a model name and the value is an
            `astropy.modeling.CompoundModel` object.
        model_label : str
            Get model parameters for a particular model by inputting its label.
        x : int
            The x coordinate of the model spaxels that will be returned from
            get_models.
        y : int
            The y coordinate of the model spaxels that will be returned from
            get_models.

        Returns
        -------
        :dict: a dictionary of the form
            {model name: {parameter name: [[`astropy.units.Quantity`]]}}
            for 3d models or
            {model name: {parameter name: `astropy.units.Quantity`}} where the
            Quantity object represents the parameter value and unit of one of
            spaxel models or the 1d models, respectively.
        """
        if models and model_label:
            models = self.get_models(models=models, model_label=model_label, x=x, y=y)
        elif models is None and model_label:
            models = self.get_models(model_label=model_label, x=x, y=y)
        elif models is None:
            models = self.fitted_models

        data_shapes = {}
        for label in models:
            data_label = label.split(" (")[0]
            if data_label not in data_shapes:
                data_shapes[data_label] = self.app.data_collection[data_label].data.shape

        param_dict = {}
        parameters_cube = {}
        param_x_y = {}
        param_units = {}

        for label in models:
            # 3d models take the form of "Model (1,2)" so this if statement
            # looks for that style and separates out the pertinent information.
            if " (" in label:
                label_split = label.split(" (")
                model_name = label_split[0]
                x = int(label_split[1].split(", ")[0])
                y = int(label_split[1].split(", ")[1][:-1])

                # x and y values are added to this dict where they will be used
                # to convert the models of each spaxel into a single
                # coordinate in the parameters_cube dictionary.
                if model_name not in param_x_y:
                    param_x_y[model_name] = {'x': [], 'y': []}
                if x not in param_x_y[model_name]['x']:
                    param_x_y[model_name]['x'].append(x)
                if y not in param_x_y[model_name]['y']:
                    param_x_y[model_name]['y'].append(y)

            # 1d models will be handled by this else statement.
            else:
                model_name = label

            if model_name not in param_dict:
                param_dict[model_name] = list(models[label].param_names)

        # This adds another dictionary as the value of
        # parameters_cube[model_name] where the key is the parameter name
        # and the value is either a 2d array of zeros or a single value, depending
        # on whether the model in question is 3d or 1d, respectively.
        for model_name in param_dict:
            if model_name in param_x_y:
                parameters_cube[model_name] = {x: np.zeros(shape=data_shapes[model_name][:2])
                                               for x in param_dict[model_name]}
            else:
                parameters_cube[model_name] = {x: 0
                                               for x in param_dict[model_name]}

        # This loop handles the actual placement of param.values and
        # param.units into the parameter_cubes dictionary.
        for label in models:
            if " (" in label:
                label_split = label.split(" (")
                model_name = label_split[0]

                # If the get_models method is used to build a dictionary of
                # models and a value is set for the x or y parameters, that
                # will mean that only one x or y value is present in the
                # models.
                if len(param_x_y[model_name]['x']) == 1:
                    x = 0
                else:
                    x = int(label_split[1].split(", ")[0])

                if len(param_x_y[model_name]['y']) == 1:
                    y = 0
                else:
                    y = int(label_split[1].split(", ")[1][:-1])

                param_units[model_name] = {}

                for name in param_dict[model_name]:
                    param = getattr(models[label], name)
                    parameters_cube[model_name][name][x][y] = param.value
                    param_units[model_name][name] = param.unit
            else:
                model_name = label
                param_units[model_name] = {}

                # 1d models do not have anything set of param.unit, so the
                # return_units and input_units properties need to be used
                # instead, depending on the type of parameter `name` is.
                for name in param_dict[model_name]:
                    param = getattr(models[label], name)
                    parameters_cube[model_name][name] = param.value
                    param_units[model_name][name] = param.unit

        # Convert values of parameters_cube[key][param_name] into u.Quantity
        # objects that contain the appropriate unit set in
        # param_units[key][param_name]
        for key in parameters_cube:
            for param_name in parameters_cube[key]:
                parameters_cube[key][param_name] = u.Quantity(
                    parameters_cube[key][param_name],
                    param_units[key].get(param_name, None))

        return parameters_cube

    def show(self, loc="inline", title=None, height=None):  # pragma: no cover
        """Display the Jdaviz application.

        Parameters
        ----------
        loc : str
            The display location determines where to present the viz app.
            Supported locations:

            "inline": Display the Jdaviz application inline in a notebook.
            Note this is functionally equivalent to displaying the cell
            ``viz.app`` in the notebook.

            "sidecar": Display the Jdaviz application in a separate JupyterLab window from the
            notebook, the location of which is decided by the 'anchor.' right is the default

                Other anchors:

                * ``sidecar:right`` (The default, opens a tab to the right of display)
                * ``sidecar:tab-before`` (Full-width tab before the current notebook)
                * ``sidecar:tab-after`` (Full-width tab after the current notebook)
                * ``sidecar:split-right`` (Split-tab in the same window right of the notebook)
                * ``sidecar:split-left`` (Split-tab in the same window left of the notebook)
                * ``sidecar:split-top`` (Split-tab in the same window above the notebook)
                * ``sidecar:split-bottom`` (Split-tab in the same window below the notebook)

                See `jupyterlab-sidecar <https://github.com/jupyter-widgets/jupyterlab-sidecar>`_
                for the most up-to-date options.

            "popout": Display the Jdaviz application in a detached display. By default, a new
            window will open. Browser popup permissions required.

                Other anchors:

                * ``popout:window`` (The default, opens Jdaviz in a new, detached popout)
                * ``popout:tab`` (Opens Jdaviz in a new, detached tab in your browser)

        title : str, optional
            The title of the sidecar tab.  Defaults to the name of the
            application; e.g., "specviz".

            NOTE: Only applicable to a "sidecar" display.

        height: int, optional
            The height of the top-level application widget, in pixels. Applies to all
            instances of the same application in the notebook.

        Notes
        -----
        If "sidecar" is requested in the "classic" Jupyter notebook, the app will appear inline,
        as only JupyterLab has a mechanism to have multiple tabs.
        """
        title = self.app.config if title is None else title
        if height is not None:
            if isinstance(height, int):
                height = f"{height}px"
            self.app.layout.height = height
            self.app.state.settings['context']['notebook']['max_height'] = height

        show_widget(self.app, loc=loc, title=title)

    def show_in_sidecar(self, anchor=None, title=None):  # pragma: no cover
        """
        Preserved for backwards compatibility
        Shows Jdaviz in a sidecar with the default anchor: right
        """
        warnings.warn('show_in_sidecar has been replaced with show(loc="sidecar")',
                      DeprecationWarning)
        location = 'sidecar' if anchor is None else f"sidecar:{anchor}"
        return self.show(loc=location, title=title)

    def show_in_new_tab(self, title=None):  # pragma: no cover
        """
        Preserved for backwards compatibility
        Shows Jdaviz in a sidecar in a new tab to the right
        """
        warnings.warn('show_in_new_tab has been replaced with show(loc="sidecar:tab-after")',
                      DeprecationWarning)
        return self.show(loc="sidecar:tab-after", title=title)

    def _get_data(self, data_label=None, spatial_subset=None, spectral_subset=None,
                  mask_subset=None, function=None, cls=None, use_display_units=False):
        def _handle_display_units(data, use_display_units):
            if use_display_units:
                if isinstance(data, Spectrum1D):
                    spectral_unit = self.app._get_display_unit('spectral')
                    if not spectral_unit:
                        return data
                    if self.app.config == 'cubeviz' and spectral_unit == 'deg':
                        # this happens before the correct axis is set for the spectrum-viewer
                        # and would result in a unit-conversion error if attempting to convert
                        # to the display units.  This should only ever be temporary during
                        # app intialization.
                        return data
                    flux_unit = self.app._get_display_unit('flux')
                    # TODO: any other attributes (meta, wcs, etc)?
                    # TODO: implement uncertainty.to upstream
                    uncertainty = data.uncertainty
                    if uncertainty is not None:
                        # convert the uncertainties to StdDevUncertainties, since
                        # that is assumed in a few places in jdaviz:
                        if uncertainty.unit is None:
                            uncertainty.unit = data.flux.unit
                        if hasattr(uncertainty, 'represent_as'):
                            new_uncert = uncertainty.represent_as(
                                StdDevUncertainty
                            ).quantity.to(flux_unit)
                        else:
                            # if not specified as NDUncertainty, assume stddev:
                            new_uncert = uncertainty.quantity.to(flux_unit)
                        new_uncert = StdDevUncertainty(new_uncert, unit=flux_unit)
                    else:
                        new_uncert = None

                    data = Spectrum1D(spectral_axis=data.spectral_axis.to(spectral_unit,
                                                                          u.spectral()),
                                      flux=data.flux.to(flux_unit,
                                                        u.spectral_density(data.spectral_axis)),
                                      uncertainty=new_uncert)
                else:  # pragma: nocover
                    raise NotImplementedError(f"converting {data.__class__.__name__} to display units is not supported")  # noqa
            return data

        list_of_valid_function_values = ('minimum', 'maximum', 'mean',
                                         'median', 'sum')
        if function and function not in list_of_valid_function_values:
            raise ValueError(f"function {function} not in list of valid"
                             f" function values {list_of_valid_function_values}")

        list_of_valid_subset_names = [x.label for x in self.app.data_collection.subset_groups]
        for subset in (spatial_subset, spectral_subset, mask_subset):
            if subset and subset not in list_of_valid_subset_names:
                raise ValueError(f"Subset {subset} not in list of valid"
                                 f" subset names {list_of_valid_subset_names}")

        if data_label and data_label not in self.app.data_collection.labels:
            raise ValueError(f'{data_label} not in {self.app.data_collection.labels}.')
        elif not data_label and len(self.app.data_collection) > 1:
            raise ValueError('data_label must be set if more than'
                             ' one data exists in data_collection.')
        elif not data_label and len(self.app.data_collection) == 1:
            data_label = self.app.data_collection[0].label

        if cls is not None and not isclass(cls):
            raise TypeError(
                "cls in get_data must be a class or None.")

        if spectral_subset:
            if mask_subset is not None:
                raise ValueError("cannot use both mask_subset and spectral_subset")
            # spectral_subset is applied as a mask, the only difference is that it has
            # its own set of validity checks (whereas mask_subset can be used by downstream
            # apps which would then need to do their own type checks, if necessary)
            mask_subset = spectral_subset

        # End validity checks and start data retrieval
        data = self.app.data_collection[data_label]

        if not cls:
            if 'Trace' in data.meta:
                cls = None
            elif data.ndim == 2 and self.app.config == "specviz2d":
                cls = Spectrum1D
            elif data.ndim == 2:
                cls = CCDData
            elif data.ndim in [1, 3]:
                cls = Spectrum1D

        object_kwargs = {}
        if cls == Spectrum1D:
            object_kwargs['statistic'] = function

        if not spatial_subset and not mask_subset:
            if 'Trace' in data.meta:
                if cls is not None:  # pragma: no cover
                    raise ValueError("cls not supported for Trace object")
                data = data.get_object()
            else:
                data = data.get_object(cls=cls, **object_kwargs)

            return _handle_display_units(data, use_display_units)

        if not cls and spatial_subset:
            raise AttributeError(f"A valid cls must be provided to"
                                 f" apply subset {spatial_subset} to data. "
                                 f"Instead, {cls} was given.")
        elif not cls and mask_subset:
            raise AttributeError(f"A valid cls must be provided to"
                                 f" apply subset {mask_subset} to data. "
                                 f"Instead, {cls} was given.")

        # Now we work on applying subsets to the data
        all_subsets = self.app.get_subsets(object_only=True)

        # Handle spatial subset
        if spatial_subset and not isinstance(all_subsets[spatial_subset][0],
                                             Region):
            raise ValueError(f"{spatial_subset} is not a spatial subset.")
        elif spatial_subset:
            real_spatial = [sub for subsets in self.app.data_collection.subset_groups
                            for sub in subsets.subsets
                            if sub.data.label == data_label and subsets.label == spatial_subset][0]
            handler, _ = data_translator.get_handler_for(cls)
            try:
                data = handler.to_object(real_spatial, **object_kwargs)
            except Exception as e:
                warnings.warn(f"Not able to get {data_label} returned with"
                              f" subset {spatial_subset} applied of type {cls}."
                              f" Exception: {e}")
        elif function:
            # This covers the case where cubeviz.get_data is called using a spectral_subset
            # with function set.
            data = data.get_object(cls=cls, **object_kwargs)

        # Handle spectral subset, including case where spatial subset is also set
        if spectral_subset and not isinstance(all_subsets[spectral_subset],
                                              SpectralRegion):
            raise ValueError(f"{spectral_subset} is not a spectral subset.")

        if mask_subset:
            real_spectral = [sub for subsets in self.app.data_collection.subset_groups
                             for sub in subsets.subsets
                             if sub.data.label == data_label and subsets.label == mask_subset][0] # noqa

            handler, _ = data_translator.get_handler_for(cls)
            try:
                spec_subset = handler.to_object(real_spectral, **object_kwargs)
            except Exception as e:
                warnings.warn(f"Not able to get {data_label} returned with"
                              f" subset {mask_subset} applied of type {cls}."
                              f" Exception: {e}")
            if spatial_subset or function:
                # Return collapsed Spectrum1D object with spectral subset mask applied
                data.mask = spec_subset.mask
            else:
                data = spec_subset

        return _handle_display_units(data, use_display_units)

    def get_data(self, data_label=None, cls=None, use_display_units=False, **kwargs):
        """
        Returns data with name equal to data_label of type cls.

        Parameters
        ----------
        data_label : str, optional
            Provide a label to retrieve a specific data set from data_collection.
        cls : `~specutils.Spectrum1D`, `~astropy.nddata.CCDData`, optional
            The type that data will be returned as.
        use_display_units : bool, optional
            Whether to convert to the display units defined in the <unit-conversion> plugin.
        kwargs : dict
            For Cubeviz, you could also pass in ``function`` (str) to collapse
            the cube into 1D spectrum using provided function.

        Returns
        -------
        data : cls
            Data is returned as type ``cls``.

        """
        return self._get_data(data_label=data_label,
                              cls=cls, use_display_units=use_display_units, **kwargs)


class ImageConfigHelper(ConfigHelper):
    """`ConfigHelper` that uses an image viewer as its primary viewer.
    For example, Imviz and Cubeviz.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # NOTE: The first viewer must always be there and is an image viewer.
        self._default_viewer = self.app.get_viewer_by_id(f'{self.app.config}-0')

    @property
    def default_viewer(self):
        """Default viewer instance. This is typically the first viewer
        (e.g., "imviz-0" or "cubeviz-0")."""
        return self._default_viewer

    def load_regions_from_file(self, region_file, region_format='ds9', max_num_regions=20,
                               **kwargs):
        """Load regions defined in the given file.
        See :ref:`regions:regions_io` for supported file formats.
        See :meth:`load_regions` for how regions are loaded.

        Parameters
        ----------
        region_file : str
            Path to region file.

        region_format : {'crtf', 'ds9', 'fits'}
            See :meth:`regions.Regions.get_formats`.

        max_num_regions : int or `None`
            Maximum number of regions to read from the file, starting
            from top of the file. Default is first 20 regions that
            can be successfully loaded. If `None`, it will load everything.

        kwargs : dict
            See :meth:`load_regions`.

        Returns
        -------
        bad_regions : list of (obj, str) or `None`
            See :meth:`load_regions`.

        """
        from regions import Regions
        raw_regs = Regions.read(region_file, format=region_format)
        return self.load_regions(raw_regs, max_num_regions=max_num_regions, **kwargs)

    def load_regions(self, regions, max_num_regions=None, refdata_label=None,
                     return_bad_regions=False, **kwargs):
        """Load given region(s) into the viewer.
        WCS-to-pixel translation and mask creation, if needed, is relative
        to the image defined by ``refdata_label``. Meanwhile, the rest of
        the Subset operations are based on reference image as defined by Glue.

        .. note:: Loading too many regions will affect performance.

        A valid region can be loaded into one of the following categories:

        * An interactive Subset, as if it was drawn by hand. This is
          always done for supported shapes. Its label will be
          ``'Subset N'``, where ``N`` is an integer.
        * A masked Subset that will display on the image but cannot be
          modified once loaded. This is done if the shape cannot be
          made interactive. Its label will be ``'MaskedSubset N'``,
          where ``N`` is an integer.

        Parameters
        ----------
        regions : list of obj
            A list of region objects. A region object can be one of the following:

            * Astropy ``regions`` object
            * ``photutils`` apertures (limited support until ``photutils``
              fully supports ``regions``)
            * Numpy boolean array (shape must match data, dtype should be ``np.bool_``)

        max_num_regions : int or `None`
            Maximum number of regions to load, starting from top of the list.
            Default is to load everything.

        refdata_label : str or `None`
            Label of data to use for sky-to-pixel conversion for a region, or
            mask creation. Data must already be loaded into Jdaviz.
            If `None`, defaults to the reference data in the default viewer.
            Choice of this data is particularly important when sky or masked
            region is involved.

        return_bad_regions : bool
            If `True`, return the regions that failed to load (see ``bad_regions``);
            This is useful for debugging. If `False`, do not return anything (`None`).

        kwargs : dict
            Extra keywords to be passed into the region's ``to_mask`` method.
            **This is ignored if the region can be made interactive or
            if a Numpy array is given.**

        Returns
        -------
        bad_regions : list of (obj, str) or `None`
            If requested (see ``return_bad_regions`` option), return a
            list of ``(region, reason)`` tuples for region objects that failed to load.
            If all the regions loaded successfully, this list will be empty.
            If not requested, return `None`.

        """
        if len(self.app.data_collection) == 0:
            raise ValueError('Cannot load regions without data.')

        from photutils.aperture import (CircularAperture, SkyCircularAperture,
                                        EllipticalAperture, SkyEllipticalAperture,
                                        RectangularAperture, SkyRectangularAperture,
                                        CircularAnnulus, SkyCircularAnnulus)
        from regions import (Regions, CirclePixelRegion, CircleSkyRegion,
                             EllipsePixelRegion, EllipseSkyRegion,
                             RectanglePixelRegion, RectangleSkyRegion,
                             CircleAnnulusPixelRegion, CircleAnnulusSkyRegion)
        from jdaviz.core.region_translators import regions2roi, aperture2regions

        # If user passes in one region obj instead of list, try to be smart.
        if not isinstance(regions, (list, tuple, Regions)):
            regions = [regions]

        n_loaded = 0
        bad_regions = []

        # To keep track of masked subsets.
        msg_prefix = 'MaskedSubset'
        msg_count = _next_subset_num(msg_prefix, self.app.data_collection.subset_groups)

        # Subset is global but reference data is viewer-dependent.
        if refdata_label is None:
            data = self.default_viewer.state.reference_data
        else:
            data = self.app.data_collection[refdata_label]

        # TODO: Make this work for data cube.
        # https://github.com/glue-viz/glue-astronomy/issues/75
        has_wcs = data_has_valid_wcs(data, ndim=2)

        for region in regions:
            if (isinstance(region, (SkyCircularAperture, SkyEllipticalAperture,
                                    SkyRectangularAperture, SkyCircularAnnulus,
                                    CircleSkyRegion, EllipseSkyRegion,
                                    RectangleSkyRegion, CircleAnnulusSkyRegion))
                    and not has_wcs):
                bad_regions.append((region, 'Sky region provided but data has no valid WCS'))
                continue

            # photutils: Convert to regions shape first
            if isinstance(region, (CircularAperture, SkyCircularAperture,
                                   EllipticalAperture, SkyEllipticalAperture,
                                   RectangularAperture, SkyRectangularAperture,
                                   CircularAnnulus, SkyCircularAnnulus)):
                region = aperture2regions(region)

            # regions: Convert to ROI.
            # NOTE: Out-of-bounds ROI will succeed; this is native glue behavior.
            if isinstance(region, (CirclePixelRegion, CircleSkyRegion,
                                   EllipsePixelRegion, EllipseSkyRegion,
                                   RectanglePixelRegion, RectangleSkyRegion,
                                   CircleAnnulusPixelRegion, CircleAnnulusSkyRegion)):
                state = regions2roi(region, wcs=data.coords)

                # TODO: Do we want user to specify viewer? Does it matter?
                self.app.session.edit_subset_mode._mode = NewMode
                self.default_viewer.apply_roi(state)
                self.app.session.edit_subset_mode.edit_subset = None  # No overwrite next iteration # noqa

            # Last resort: Masked Subset that is static (if data is not a cube)
            elif data.ndim == 2:
                im = None
                if hasattr(region, 'to_pixel'):  # Sky region: Convert to pixel region
                    if not has_wcs:
                        bad_regions.append((region, 'Sky region provided but data has no valid WCS'))  # noqa
                        continue
                    region = region.to_pixel(data.coords)

                if hasattr(region, 'to_mask'):
                    try:
                        mask = region.to_mask(**kwargs)
                        im = mask.to_image(data.shape)  # Can be None
                    except Exception as e:  # pragma: no cover
                        bad_regions.append((region, f'Failed to load: {repr(e)}'))
                        continue

                elif (isinstance(region, np.ndarray) and region.shape == data.shape
                        and region.dtype == np.bool_):
                    im = region

                if im is None:
                    bad_regions.append((region, 'Mask creation failed'))
                    continue

                # NOTE: Region creation info is thus lost.
                try:
                    subset_label = f'{msg_prefix} {msg_count}'
                    state = MaskSubsetState(im, data.pixel_component_ids)
                    self.app.data_collection.new_subset_group(subset_label, state)
                    msg_count += 1
                except Exception as e:  # pragma: no cover
                    bad_regions.append((region, f'Failed to load: {repr(e)}'))
                    continue

            else:
                bad_regions.append((region, 'Mask creation failed'))
                continue

            n_loaded += 1
            if max_num_regions is not None and n_loaded >= max_num_regions:
                break

        n_reg_in = len(regions)
        n_reg_bad = len(bad_regions)
        if n_loaded == 0:
            snack_color = "error"
        elif n_reg_bad > 0:
            snack_color = "warning"
        else:
            snack_color = "success"
        self.app.hub.broadcast(SnackbarMessage(
            f"Loaded {n_loaded}/{n_reg_in} regions, max_num_regions={max_num_regions}, "
            f"bad={n_reg_bad}", color=snack_color, timeout=8000, sender=self.app))

        if return_bad_regions:
            return bad_regions

    def get_interactive_regions(self):
        """Return spatial regions that can be interacted with in the viewer.
        This does not return masked regions added via :meth:`load_regions`.

        Unsupported region shapes will be skipped. When that happens,
        a yellow snackbar message will appear on display.

        Returns
        -------
        regions : dict
            Dictionary mapping interactive region names to respective Astropy
            ``regions`` objects.

        """
        regions = {}
        failed_regs = set()

        # Subset is global, so we just use default viewer.
        for lyr in self.default_viewer.layers:
            if (not hasattr(lyr, 'layer') or not isinstance(lyr.layer, Subset)
                    or lyr.layer.ndim not in (2, 3)):
                continue

            subset_data = lyr.layer
            subset_label = subset_data.label

            # TODO: Remove this when Jdaviz support round-tripping, see
            # https://github.com/spacetelescope/jdaviz/pull/721
            if not subset_label.startswith('Subset'):
                continue

            try:
                region = subset_data.data.get_selection_definition(
                    subset_id=subset_label, format='astropy-regions')
            except (NotImplementedError, ValueError):
                failed_regs.add(subset_label)
            else:
                regions[subset_label] = region

        if len(failed_regs) > 0:
            self.app.hub.broadcast(SnackbarMessage(
                f"Regions skipped: {', '.join(sorted(failed_regs))}",
                color="warning", timeout=8000, sender=self.app))

        return regions

    # See https://github.com/glue-viz/glue-jupyter/issues/253
    def _apply_interactive_region(self, toolname, from_pix, to_pix):
        """Mimic interactive region drawing.
        This is for internal testing only.
        """
        self.app.session.edit_subset_mode._mode = NewMode
        tool = self.default_viewer.toolbar.tools[toolname]
        tool.activate()
        tool.interact.brushing = True
        tool.interact.selected = [from_pix, to_pix]
        tool.interact.brushing = False
        self.app.session.edit_subset_mode.edit_subset = None  # No overwrite next iteration

    # TODO: Make this public API?
    def _delete_region(self, subset_label):
        """Delete region given the Subset label."""
        all_subset_labels = [s.label for s in self.app.data_collection.subset_groups]
        if subset_label not in all_subset_labels:
            return
        i = all_subset_labels.index(subset_label)
        subset_grp = self.app.data_collection.subset_groups[i]
        self.app.data_collection.remove_subset_group(subset_grp)

    # TODO: Make this public API?
    def _delete_all_regions(self):
        """Delete all regions."""
        for subset_grp in self.app.data_collection.subset_groups:  # should be a copy
            self.app.data_collection.remove_subset_group(subset_grp)


def data_has_valid_wcs(data, ndim=None):
    """Check if given glue Data has WCS that is compatible with APE 14."""
    status = hasattr(data, 'coords') and isinstance(data.coords, BaseHighLevelWCS)
    if ndim is not None:
        status = status and data.coords.world_n_dim == ndim
    return status


def _next_subset_num(label_prefix, subset_groups):
    """Assumes ``prefix i`` format.
    Does not go back and fill in lower but available numbers. This is consistent with Glue.
    """
    max_i = 0

    for sg in subset_groups:
        if sg.label.startswith(label_prefix):
            sub_label = sg.label.split(' ')
            if len(sub_label) > 1:
                i_str = sub_label[-1]
                try:
                    i = int(i_str)
                except Exception:  # nosec
                    continue
                else:
                    if i > max_i:
                        max_i = i

    return max_i + 1
