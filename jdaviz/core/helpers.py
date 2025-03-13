"""
Helper classes are meant to provide a convenient user API for specific
configurations. They allow a separation of "viztool-specific" API and the glue
application objects.

See also https://github.com/spacetelescope/jdaviz/issues/104 for more details
on the motivation behind this concept.
"""
import warnings
from contextlib import contextmanager
from inspect import isclass

import numpy as np
from glue.core import HubListener
from glue.core.edit_subset_mode import NewMode
from glue.core.message import SubsetCreateMessage, SubsetDeleteMessage
from glue.core.subset import Subset, MaskSubsetState
from glue.config import data_translator
from ipywidgets.widgets import widget_serialization

from astropy.nddata import NDDataArray, CCDData, StdDevUncertainty
import astropy.units as u
from astropy.utils.decorators import deprecated
from regions.core.core import Region
from specutils import Spectrum1D, SpectralRegion

from jdaviz.app import Application
from jdaviz.core.events import SnackbarMessage, ExitBatchLoadMessage, SliceSelectSliceMessage
from jdaviz.core.loaders.resolvers import find_matching_resolver
from jdaviz.core.template_mixin import show_widget
from jdaviz.utils import data_has_valid_wcs
from jdaviz.core.unit_conversion_utils import (all_flux_unit_conversion_equivs,
                                               check_if_unit_is_per_solid_angle,
                                               flux_conversion_general,
                                               spectral_axis_conversion)


__all__ = ['ConfigHelper', 'ImageConfigHelper', 'CubeConfigHelper']


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
    def loaders(self):
        """
        Access API objects for data loaders in the import dialog.

        Returns
        -------
        loaders : dict
            dict of loader objects
        """
        if not self.app.state.dev_loaders:
            raise NotImplementedError("loaders is under active development and requires a dev-flag to test")  # noqa
        loaders = {item['label']: widget_serialization['from_json'](item['widget'], None).user_api
                   for item in self.app.state.loader_items}
        return loaders

    def _load(self, inp=None, loader=None, format=None, target=None, **kwargs):
        """
        Load data into the app.  A single valid loader/importer must be able to be
        matched based on the input, otherwise an error will be raised suggesting
        what further information to provide.  For an interactive approach,
        see ``loaders``.

        Parameters
        ----------
        inp : string or object or None
            Input filename, url, data object, etc.
        loader : string, optional
            Only consider a specific loader/resolver
        format : string, optional
            Only consider a specific format
        target : string, optional
            Only consider a specific target
        kwargs :
            Additional kwargs are passed on to both the loader and importer, as applicable.
            Any kwargs that do not match valid inputs are silently ignored.
        """
        resolver = find_matching_resolver(self.app, inp,
                                          resolver=loader,
                                          format=format,
                                          target=target,
                                          **kwargs)

        importer = resolver.importer
        for k, v in kwargs.items():
            if hasattr(importer, k):
                setattr(importer, k, v)
        return importer()

    @property
    def data_labels(self):
        """
        List of data labels loaded and available in jdaviz

        Returns
        -------
        data_labels : list
            list of strings
        """
        return [data.label for data in self.app.data_collection]

    @property
    def plugins(self):
        """
        Access API objects for plugins in the plugin tray.

        Returns
        -------
        plugins : dict
            dict of plugin objects
        """
        plugins = {item['label']: widget_serialization['from_json'](item['widget'], None).user_api
                   for item in self.app.state.tray_items if item['is_relevant']}

        # handle renamed plugins during deprecation
        if 'Image Profiles (XY)' in plugins:
            # renamed in 4.0
            plugins['Imviz Line Profiles (XY)'] = plugins['Image Profiles (XY)']._obj.user_api
            plugins['Imviz Line Profiles (XY)']._deprecation_msg = 'in the future, the formerly named \"Imviz Line Profiles (XY)\" plugin will only be available by its new name: \"Image Profiles (XY)\".'  # noqa

        return plugins

    @property
    def plugin_tables(self):
        return self.app._plugin_tables

    @property
    def plugin_plots(self):
        return self.app._plugin_plots

    @property
    def viewers(self):
        """
        Access API objects for any viewer.

        Returns
        -------
        viewers : dict
            dict of viewer objects
        """
        return {viewer._ref_or_id: viewer.user_api
                for viewer in self.app._viewer_store.values()}

    @property
    @deprecated(since="4.2", alternative="plugins['Model Fitting'].fitted_models")
    def fitted_models(self):
        """
        Returns the fitted models.

        Returns
        -------
        parameters : dict
            dict of `astropy.modeling.Model` objects, or None.
        """
        plg = self.plugins.get('Model Fitting', None)
        if plg is None:
            raise ValueError("Model Fitting plugins is not loaded")
        return plg.fitted_models

    @deprecated(since="4.2", alternative="plugins['Model Fitting'].get_models")
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
        plg = self.plugins.get('Model Fitting', None)
        if plg is None:
            raise ValueError("Model Fitting plugins is not loaded")
        return plg._obj.get_models(models=models,
                                   model_label=model_label,
                                   x=x, y=y)

    @deprecated(since="4.2")
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
        plg = self.plugins.get('Model Fitting', None)
        if plg is None:
            raise ValueError("Model Fitting plugins is not loaded")
        return plg._obj.get_model_parameters(models=models,
                                             model_label=model_label,
                                             x=x, y=y)

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

    def toggle_api_hints(self, enabled=None):
        """
        Toggle the visibility of API hints in the application.

        Parameters
        ----------
        enabled : bool, optional
            If `True`, show API hints. If `False`, hide API hints.
            If `None`, toggle the current state.
        """
        if enabled is None:
            enabled = not self.app.state.show_api_hints
        self.app.state.show_api_hints = enabled

    def _handle_display_units(self, data, use_display_units=True):
        if use_display_units:
            if isinstance(data, Spectrum1D):
                spectral_unit = self.app._get_display_unit('spectral')
                if not spectral_unit:
                    return data
                y_unit = self.app._get_display_unit('spectral_y')

                # if there is no pixel scale factor, and the requested conversion
                # is between flux/sb, then skip. this case is encountered when
                # starting the app? ideally this should raise an error, and this
                # should allow pix2/spaxel but it doesn't - keeping this
                # condition as-is until further investigation
                orig_sa = check_if_unit_is_per_solid_angle(u.Unit(data.flux.unit))
                targ_sa = check_if_unit_is_per_solid_angle(u.Unit(y_unit))
                skip_flux_conv = ('_pixel_scale_factor' not in data.meta) & (orig_sa != targ_sa)

                # equivalencies for flux/sb unit conversions
                pixar_sr = data.meta.get('_pixel_scale_factor', None)
                eqv = all_flux_unit_conversion_equivs(pixar_sr=pixar_sr,
                                                      cube_wave=data.spectral_axis)

                # TODO: any other attributes (meta, wcs, etc)?
                # TODO: implement uncertainty.to upstream
                uncertainty = data.uncertainty
                if uncertainty is not None:
                    # convert the uncertainties to StdDevUncertainties, since
                    # that is assumed in a few places in jdaviz:
                    if uncertainty.unit is None:
                        uncertainty.unit = data.flux.unit
                    if hasattr(uncertainty, 'represent_as'):
                        new_uncert = uncertainty.represent_as(StdDevUncertainty)
                    else:
                        # if not specified as NDUncertainty, assume stddev:
                        new_uncert = uncertainty

                    # convert uncertainty units to display units
                    if skip_flux_conv:
                        new_uncert = StdDevUncertainty(new_uncert, unit=data.flux.unit)
                    else:
                        new_uncert_conv = flux_conversion_general(new_uncert.quantity.value,
                                                                  new_uncert.unit,
                                                                  y_unit,
                                                                  eqv,
                                                                  with_unit=False)
                        new_uncert = StdDevUncertainty(new_uncert_conv,
                                                       unit=y_unit)
                else:
                    new_uncert = None

                # convert flux/sb units to display units
                if skip_flux_conv:
                    new_y = data.flux.value * u.Unit(data.flux.unit)
                else:
                    # multiply by unit rather than using with_unit because of
                    # edge case for dimensionless we want here
                    new_y = flux_conversion_general(data.flux.value,
                                                    data.flux.unit,
                                                    y_unit,
                                                    eqv, with_unit=False) * u.Unit(y_unit)

                # convert spectral axis to display units
                new_spec = (spectral_axis_conversion(data.spectral_axis.value,
                                                     data.spectral_axis.unit,
                                                     spectral_unit)
                            * u.Unit(spectral_unit))

                data = Spectrum1D(spectral_axis=new_spec,
                                  flux=new_y,
                                  uncertainty=new_uncert,
                                  mask=data.mask)
            else:  # pragma: nocover
                raise NotImplementedError(f"converting {data.__class__.__name__} to display units is not supported")  # noqa
        return data

    def _get_data(self, data_label=None, spatial_subset=None, spectral_subset=None,
                  temporal_subset=None, mask_subset=None, cls=None, use_display_units=False):
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

        if temporal_subset:
            if mask_subset is not None:
                raise ValueError("cannot use both mask_subset and spectral_subset")
            mask_subset = temporal_subset

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
                if self.app.config == 'rampviz':
                    cls = NDDataArray
                else:
                    # for cubeviz, specviz, mosviz, this must be a spectrum:
                    cls = Spectrum1D

        object_kwargs = {}
        if cls == Spectrum1D:
            object_kwargs['statistic'] = None

        if not spatial_subset and not mask_subset:
            if 'Trace' in data.meta:
                if cls is not None:  # pragma: no cover
                    raise ValueError("cls not supported for Trace object")
                data = data.get_object()
            else:
                data = data.get_object(cls=cls, **object_kwargs)

            return self._handle_display_units(data, use_display_units)

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
            if spatial_subset:
                # Return collapsed Spectrum1D object with spectral subset mask applied
                data.mask = spec_subset.mask
            else:
                data = spec_subset

        return self._handle_display_units(data, use_display_units)

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

        Returns
        -------
        data : cls
            Data is returned as type ``cls``.

        """
        return self._get_data(data_label=data_label,
                              cls=cls, use_display_units=use_display_units)


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
        return self._default_viewer.user_api

    @deprecated(since="4.2", alternative="subset_tools.import_region")
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

    @deprecated(since="4.2", alternative="subset_tools.import_region")
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

        max_num_regions : int or `None`
            Maximum number of regions to load, starting from top of the list.
            Default is to load everything.

        refdata_label : str or `None`
            Label of data to use for sky-to-pixel conversion for a region, or
            mask creation. Data must already be loaded into Jdaviz.
            If `None`, defaults to the reference data in the default viewer.
            Choice of this data is particularly important when sky
            region is involved.

        return_bad_regions : bool
            If `True`, return the regions that failed to load (see ``bad_regions``);
            This is useful for debugging. If `False`, do not return anything (`None`).

        kwargs : dict
            Extra keywords to be passed into the region's ``to_mask`` method.
            **This is ignored if the region can be made interactive.**

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
            data = self.default_viewer._obj.state.reference_data
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

            if (isinstance(region, (CircularAperture, EllipticalAperture,
                                    RectangularAperture, CircularAnnulus,
                                    CirclePixelRegion, EllipsePixelRegion,
                                    RectanglePixelRegion, CircleAnnulusPixelRegion))
                    and self.app._align_by == "wcs"):
                bad_regions.append((region, 'Pixel region provided by data is linked by WCS'))
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
                self.default_viewer._obj.apply_roi(state)
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

                # Boolean mask as input is supported but not advertised.
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

    @deprecated(since="4.1", alternative="subset_tools.get_regions")
    def get_interactive_regions(self):
        """
        Return spatial regions that can be interacted with in the viewer.
        This does not return masked regions added via :meth:`load_regions`.

        Unsupported region shapes will be skipped. When that happens,
        a yellow snackbar message will appear on display.

        Returns
        -------
        regions : dict
            Dictionary mapping interactive region names to respective Astropy
            ``regions`` objects.

        """
        from glue_astronomy.translators.regions import roi_subset_state_to_region

        regions = {}
        failed_regs = set()
        to_sky = self.app._align_by == 'wcs'

        # Subset is global, so we just use default viewer.
        for lyr in self.default_viewer._obj.layers:
            if (not hasattr(lyr, 'layer') or not isinstance(lyr.layer, Subset)
                    or lyr.layer.ndim not in (2, 3)):
                continue

            subset_data = lyr.layer
            subset_label = subset_data.label

            try:
                if self.app.config == "imviz" and to_sky:
                    region = roi_subset_state_to_region(subset_data.subset_state, to_sky=to_sky)
                else:
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

    # TODO: Make this public API?
    def _delete_region(self, subset_label):
        """Delete region given the Subset label."""
        all_subset_labels = [s.label for s in self.app.data_collection.subset_groups]
        if subset_label not in all_subset_labels:
            return
        i = all_subset_labels.index(subset_label)
        subset_grp = self.app.data_collection.subset_groups[i]
        self.app.data_collection.remove_subset_group(subset_grp)


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


class CubeConfigHelper(ImageConfigHelper):
    """Base config helper class for cubes"""

    _loaded_flux_cube = None
    _loaded_uncert_cube = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @deprecated(since="4.1", alternative="plugins['Slice'].slice")
    def select_slice(self, value):
        """
        Select the slice closest to the provided value.

        Parameters
        ----------
        value : float or int, optional
            Slice value to select in units of the x-axis of the profile viewer.
            The nearest slice will be selected if "snap to slice" is enabled in
            the slice plugin.
        """
        msg = SliceSelectSliceMessage(value=value, sender=self)
        self.app.hub.broadcast(msg)
