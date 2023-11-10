from traitlets import Bool, List, Unicode, observe
import numpy as np
import regions

from glue.core.message import DataCollectionAddMessage, DataCollectionDeleteMessage

from jdaviz.core.custom_traitlets import FloatHandleEmpty
from jdaviz.core.events import LinkUpdatedMessage
from jdaviz.core.marks import FootprintOverlay
from jdaviz.core.region_translators import regions2roi
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin, ViewerSelectMixin,
                                        EditableSelectPluginComponent,
                                        FileImportSelectPluginComponent, HasFileImportSelect)
from jdaviz.core.user_api import PluginUserApi

from jdaviz.configs.imviz.plugins.footprints import preset_regions


__all__ = ['Footprints']


@tray_registry('imviz-footprints', label="Footprints")
class Footprints(PluginTemplateMixin, ViewerSelectMixin, HasFileImportSelect):
    """
    See the :ref:`Footprints Plugin Documentation <imviz-footprints>` for more details.

    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.close_in_tray`
    * ``overlay`` (:class:`~jdaviz.core.template_mixin.EditableSelectPluginComponent`): the
        currently active overlay (all other traitlets control this overlay instance)
    * :meth:`rename_overlay`
        rename any overlay
    * :meth:`add_overlay`
        add a new overlay instance (and select as active)
    * :meth:`remove_overlay`
        remove any overlay
    * ``viewer`` (:class:`~jdaviz.core.template_mixin.ViewerSelect`):
        viewer(s) to show the current overlay
    * ``visible``
        whether the currently selected overlay should be visible in the selected viewers
    * ``color``
        color of the currently selected overlay
    * ``fill_opacity``
        opacity of the filled region of the currently selected overlay
    * ``preset`` (:class:`~jdaviz.core.template_mixin.SelectPluginComponent`):
        selected overlay preset
    * :meth:`import_region`
    * :meth:`center_on_viewer`
    * ``ra``
        central right ascension for the footprint overlay
    * ``dec``
        central declination (in degrees) for the footprint overlay
    * ``pa``
        position angle (in degrees) measured from North to central vertical axis in North to East
        direction.
    * ``v2_offset``
        Additional V2 offset in telescope coordinates to apply to instrument center, as from a
        dither pattern.
    * ``v3_offset``
        Additional V3 offset in telescope coordinates to apply to instrument center, as from a
        dither pattern.
    * :meth:`overlay_regions`
    """
    template_file = __file__, "footprints.vue"
    uses_active_status = Bool(True).tag(sync=True)

    is_pixel_linked = Bool(True).tag(sync=True)  # plugin disabled if linked by pixel (default)

    # OVERLAY LABEL
    overlay_mode = Unicode().tag(sync=True)
    overlay_edit_value = Unicode().tag(sync=True)
    overlay_items = List().tag(sync=True)
    overlay_selected = Unicode().tag(sync=True)

    # STYLING OPTIONS
    # viewer (via mixin)
    visible = Bool(True).tag(sync=True)
    color = Unicode('#c75109').tag(sync=True)  # "active" orange
    fill_opacity = FloatHandleEmpty(0.1).tag(sync=True)

    # PRESET OVERLAYS AND OPTIONS
    has_pysiaf = Bool(preset_regions._has_pysiaf).tag(sync=True)
    preset_items = List().tag(sync=True)
    preset_selected = Unicode().tag(sync=True)

    ra = FloatHandleEmpty().tag(sync=True)
    dec = FloatHandleEmpty().tag(sync=True)
    pa = FloatHandleEmpty().tag(sync=True)
    v2_offset = FloatHandleEmpty().tag(sync=True)
    v3_offset = FloatHandleEmpty().tag(sync=True)
    # TODO: dithering/mosaic options?

    def __init__(self, *args, **kwargs):
        self._ignore_traitlet_change = False
        self._overlays = {}

        super().__init__(*args, **kwargs)
        self.viewer.multiselect = True  # multiselect always enabled
        # require a viewer's reference data to have WCS so that footprints can be mapped to sky
        self.viewer.add_filter('reference_has_wcs')

        self.overlay = EditableSelectPluginComponent(self,
                                                     name='overlay',
                                                     mode='overlay_mode',
                                                     edit_value='overlay_edit_value',
                                                     items='overlay_items',
                                                     selected='overlay_selected',
                                                     manual_options=['default'],
                                                     on_rename=self._on_overlay_rename,
                                                     on_remove=self._on_overlay_remove)

        if self.has_pysiaf:
            preset_options = list(preset_regions._instruments.keys())
        else:
            preset_options = ['None']
        preset_options.append('From File...')
        self.preset = FileImportSelectPluginComponent(self,
                                                      items='preset_items',
                                                      selected='preset_selected',
                                                      manual_options=preset_options)

        # set the custom file parser for importing catalogs
        self.preset._file_parser = self._file_parser

        # disable if pixel-linked AND only a single item in the data collection
        self.hub.subscribe(self, LinkUpdatedMessage, handler=self._on_link_type_updated)
        self.hub.subscribe(self, DataCollectionAddMessage, handler=self._on_link_type_updated)
        self.hub.subscribe(self, DataCollectionDeleteMessage, handler=self._on_link_type_updated)
        self._on_link_type_updated()

    @property
    def user_api(self):
        return PluginUserApi(self, expose=('overlay',
                                           'rename_overlay', 'add_overlay', 'remove_overlay',
                                           'viewer', 'visible', 'color', 'fill_opacity',
                                           'preset', 'import_region',
                                           'center_on_viewer', 'ra', 'dec', 'pa',
                                           'v2_offset', 'v3_offset',
                                           'overlay_regions'))

    def _get_marks(self, viewer, overlay=None):
        matches = [mark for mark in viewer.figure.marks
                   if (isinstance(mark, FootprintOverlay) and
                       (mark.overlay == overlay or overlay is None))]
        return matches

    @property
    def marks(self):
        # {overlay: {viewer: [list_of_marks]}}
        return {overlay: {viewer_id: self._get_marks(viewer, overlay)
                          for viewer_id, viewer in self.app._viewer_store.items()
                          if hasattr(viewer, 'figure')}
                for overlay in self.overlay.choices}

    @staticmethod
    def _file_parser(path):
        def _ensure_sky(region):
            if isinstance(region, regions.Regions):
                return np.all([_ensure_sky(reg) for reg in region.regions])
            return hasattr(region, 'to_pixel')

        if isinstance(path, (regions.Region, regions.Regions)):
            if not _ensure_sky(path):
                return 'Region is not a SkyRegion', {}
            from_file_string = f'API: {path.__class__.__name__} object'
            return '', {from_file_string: path}

        try:
            region = regions.Regions.read(path)
        except Exception:
            return 'Could not parse region from file', {}
        if not _ensure_sky(region):
            return 'Region is not a SkyRegion', {}
        return '', {path: region}

    def _on_link_type_updated(self, msg=None):
        self.is_pixel_linked = (getattr(self.app, '_link_type', None) == 'pixels' and
                                len(self.app.data_collection) > 1)
        # toggle visibility as necessary
        self._on_is_active_changed()

    def vue_link_by_wcs(self, *args):
        # call other plugin so that other options (wcs_use_affine, wcs_use_fallback)
        # are retained.  Remove this method if support for plotting footprints
        # when pixel-linked is reintroduced.
        self.app._jdaviz_helper.plugins['Links Control'].link_type = 'WCS'

    def _ensure_first_overlay(self):
        if not len(self._overlays):
            # create the first default overlay
            self._change_overlay()
            # update the marks
            self._preset_args_changed()

    def rename_overlay(self, old_lbl, new_lbl):
        """
        Rename an existing overlay instance

        Parameters
        ----------
        old_lbl : string
            current label of the overlay
        new_lbl : string
            new label of the overlay
        """
        # NOTE: the overlay will call _on_overlay_rename after updating
        self.overlay.rename_choice(old_lbl, new_lbl)

    def add_overlay(self, lbl):
        """
        Add a new overlay instance, and set it as selected.  Once selected, the traitlets
        will then control the options of the new overlay.

        Parameters
        ----------
        lbl : string
            label of the overlay
        """
        # TODO: ability to pass options which would avoid updating the marks until all are set,
        # probably by setattr(self.user_api, k, v) (and checks in advance that all are valid?)
        self.overlay.add_choice(lbl, set_as_selected=True)

    def remove_overlay(self, lbl):
        """
        Remove a overlay instance.  If selected, the selected overlay will default to the
        first entry in the list.

        Parameters
        ----------
        lbl : string
            label of the overlay
        """
        # NOTE: the overlay will call _on_overlay_remove after updating
        self.overlay.remove_choice(lbl)

    def _on_overlay_rename(self, old_lbl, new_lbl):
        # this is triggered when the plugin overlay detects a change to the overlay name
        self._overlays[new_lbl] = self._overlays.pop(old_lbl, {})

        # change the reference on any marks entries for this overlay (in any viewer)
        for viewer_id, viewer in self.app._viewer_store.items():
            if not hasattr(viewer, 'figure'):  # pragma: nocover
                # should only be table viewers in mosviz, but will leave this in case we
                # ever enable the plugin for the image-viewer in mosviz
                continue
            for mark in self._get_marks(viewer, old_lbl):
                mark._overlay = new_lbl

    def _on_overlay_remove(self, lbl):
        _ = self._overlays.pop(lbl, {})

        # remove any marks objects (corresponding to this overlay) from all figures
        for viewer_id, viewer in self.app._viewer_store.items():
            if not hasattr(viewer, 'figure'):  # pragma: nocover
                # should only be table viewers in mosviz, but will leave this in case we
                # ever enable the plugin for the image-viewer in mosviz
                continue
            viewer.figure.marks = [m for m in viewer.figure.marks
                                   if getattr(m, 'overlay', None) != lbl]

    @observe('is_active', 'viewer_items')
    # NOTE: intentionally not using skip_if_no_updates_since_last_active since this only controls
    # visibility of overlay (and creating the first instance)
    def _on_is_active_changed(self, *args):
        if not hasattr(self, 'overlay'):  # pragma: nocover
            # plugin/traitlet startup
            return
        if len(self.disabled_msg):
            # no pysiaf, we don't want to try updating overlays
            return

        if not len(self.viewer.choices):
            # no valid viewers to show footprints
            # TODO: if a viewer becomes valid, we want to call the block below
            return

        if self.is_active:
            self._ensure_first_overlay()

        for overlay, viewer_marks in self.marks.items():
            for viewer_id, marks in viewer_marks.items():
                visible = self._mark_visible(viewer_id, overlay)
                for mark in marks:
                    mark.visible = visible

    def center_on_viewer(self, viewer_ref=None):
        """
        Center the values of RA and DEC based on the current zoom-limits of a viewer.

        Parameters
        ----------
        viewer_ref : string, optional
            Reference of the viewer to center, will default to the first selected viewer
        """
        if viewer_ref is None:
            if not len(self.viewer.selected):  # pragma: nocover
                raise ValueError("no viewers selected, provide viewer reference")
            viewer_ref = self.viewer.selected[0]
        viewer = self.app.get_viewer(viewer_ref)
        center_coord = viewer._get_center_skycoord()
        self._ignore_traitlet_change = True
        self.ra = center_coord.ra.to_value('deg')
        self.dec = center_coord.dec.to_value('deg')
        self._ignore_traitlet_change = False
        self._preset_args_changed()  # process ra/dec simultaneously

    def vue_center_on_viewer(self, viewer_ref):
        self.center_on_viewer(viewer_ref)

    @observe('overlay_selected')
    def _change_overlay(self, *args):
        if not hasattr(self, 'overlay'):  # pragma: nocover
            # plugin/traitlet startup
            return
        if self.overlay_selected == '':
            # no overlay selected (this can happen when removing all overlays)
            return

        if self.overlay_selected not in self._overlays:
            # create new entry with defaults (any defaults not provided here will be carried over
            # from the previous selection based on current traitlet values)

            # if this is the first overlay, there is a chance the traitlet for color was already set
            # to something other than the default, so we want to use that, otherwise for successive
            # new overlays, we want to ignore the traitlet and default back to "active" orange.
            default_color = '#c75109' if len(self._overlays) else self.color
            self._overlays[self.overlay_selected] = {'color': default_color}

            # similarly, if the user called any import APIs before opening the plugin, we want to
            # respect that, but when creating successive overlays, any selection from file/region
            # should be cleared for the next selection
            if self.preset_selected == 'From File...' and len(self._overlays) > 1:
                self._overlays[self.overlay_selected]['from_file'] = ''
                self._overlays[self.overlay_selected]['preset'] = self.preset.choices[0]

            # for the first overlay only, default the position to be centered on the current
            # zoom limits of the first selected viewer
            if len(self._overlays) == 1 and len(self.viewer.selected):
                self.center_on_viewer(self.viewer.selected[0])

        fp = self._overlays[self.overlay_selected]

        # we'll temporarily disable updating the overlays so that we can set all
        # traitlets simultaneously (and since we're only updating traitlets to a previously-set
        # overlay, we shouldn't have to update anything with the marks themselves)
        self._ignore_traitlet_change = True
        for attr in ('from_file', 'preset_selected',
                     'visible', 'color', 'fill_opacity', 'viewer_selected',
                     'ra', 'dec', 'pa', 'v2_offset', 'v3_offset'):
            key = attr.split('_selected')[0]

            if key in fp:
                # then take the value previously set in the dictionary and apply it to the traitlet
                # (which corresponds to the current selection).
                setattr(self, attr, fp[key])
            else:
                # then adopt the value from the traitlet (copy from the previous selection).
                # This should only ever occur for entries that are not defined in the default
                # dict above.
                fp[key] = getattr(self, attr)
        self._ignore_traitlet_change = False
        self._preset_args_changed()

    def _mark_visible(self, viewer_id, overlay=None):
        if not self.is_active:
            return False
        if self.is_pixel_linked:
            return False
        if overlay is None:
            overlay = self.overlay_selected
        fp = self._overlays[overlay]
        if viewer_id not in fp.get('viewer', []):
            return False
        else:
            return fp.get('visible', False)

    @observe('viewer_selected', 'visible', 'color', 'fill_opacity')
    def _display_args_changed(self, msg={}):
        if self._ignore_traitlet_change:
            return
        if not self.overlay_selected:
            return
        if self.overlay_selected not in self._overlays:
            # default dictionary has not been created yet
            return
        self._ensure_first_overlay()
        name = msg.get('name', '').split('_selected')[0]
        if len(name):
            self._overlays[self.overlay_selected][name] = msg.get('new')
        if not self.is_active:
            return

        # update existing mark (or add/remove from viewers)
        for viewer_id, viewer in self.app._viewer_store.items():
            visible = self._mark_visible(viewer_id)
            existing_marks = self._get_marks(viewer, self.overlay_selected)

            if visible and not len(existing_marks):
                # then we need to create new marks at least for this viewer
                self._preset_args_changed()
                return

            for mark in existing_marks:
                mark.visible = visible
                mark.colors = [self.color]
                mark.fill_opacities = [self.fill_opacity]

    def import_region(self, region):
        """
        Import an Astropy regions object (or file).

        Parameters
        ----------
        region : str or regions.Regions object
        """
        self._ensure_first_overlay()
        if isinstance(region, (regions.Region, regions.Regions)):
            self.preset.import_obj(region)
        elif isinstance(region, str):  # TODO: support path objects?
            self.preset.import_file(region)
        else:
            raise TypeError("region must be a regions.Regions object or string (file path)")
        # _preset_args_changed was probably already triggered by from_file traitlet changing, but
        # that may have been before the file was fully parsed and available from preset.selected_obj
        self._preset_args_changed()

    @property
    def overlay_regions(self):
        """
        Access the regions objects corresponding to the current settings
        """

        callable_kwargs = {k: getattr(self, k)
                           for k in ('ra', 'dec', 'pa', 'v2_offset', 'v3_offset')}

        if self.preset_selected == 'From File...':
            # we need to cache these locally in order to support multiple files/regions between
            # different overlay entries all selecting From File...
            overlay = self._overlays.get(self.overlay_selected, {})
            if ('regions' not in overlay
                    and isinstance(self.preset.selected_obj, (regions.Region, regions.Regions))):
                regs = self.preset.selected_obj
                if not isinstance(regs, regions.Regions):
                    # then this is a single region, but to be compatible with looping logic,
                    # let's just put as a single entry in a list
                    regs = [regs]
                overlay['regions'] = regs
            regs = overlay.get('regions', [])
        elif self.has_pysiaf and self.preset_selected in preset_regions._instruments:
            regs = preset_regions.jwst_footprint(self.preset_selected, **callable_kwargs)
        else:  # pragma: no cover
            regs = []
        return regs

    @observe('preset_selected', 'from_file', 'ra', 'dec', 'pa', 'v2_offset', 'v3_offset')
    def _preset_args_changed(self, msg={}):
        if self._ignore_traitlet_change:
            return
        if not self.overlay_selected:
            return

        name = msg.get('name', '').split('_selected')[0]

        if self.overlay_selected not in self._overlays:
            # default dictionary has not been created yet
            return

        if len(name):
            self._overlays[self.overlay_selected][name] = msg.get('new')
        if name == 'from_file' and 'regions' in self._overlays[self.overlay_selected]:
            # then the file may have been changed from the API, so we need to clear the cache
            # the cache will then be re-populated on the call to self.overlay_regions below
            del self._overlays[self.overlay_selected]['regions']

        regs = self.overlay_regions

        for viewer_id, viewer in self.app._viewer_store.items():
            visible = self._mark_visible(viewer_id)
            # TODO: need to re-call this logic when the reference_data is changed... which might
            # warrant some refactoring so we don't have to loop over all viewers if it has only
            # changed in one viewer
            wcs = getattr(viewer.state.reference_data, 'coords', None)
            if wcs is None:
                continue
            existing_overlays = self._get_marks(viewer, self.overlay_selected)
            update_existing = len(existing_overlays) == len(regs)
            if not update_existing and len(existing_overlays):
                # clear any existing marks (length has changed, perhaps a new preset)
                viewer.figure.marks = [m for m in viewer.figure.marks
                                       if getattr(m, 'overlay', None) != self.overlay_selected]

            # the following logic is adapted from
            # https://github.com/spacetelescope/jwst_novt/blob/main/jwst_novt/interact/display.py
            new_marks = []
            for i, reg in enumerate(regs):
                if (not isinstance(reg, regions.Region)
                        or not hasattr(reg, 'to_pixel')):   # pragma: no cover
                    # NOTE: this is pre-checked for API/file selection in the file-parser
                    # and built-in presets should be designed to never hit this error
                    # in the future we may support pixel regions as well, but need to decide how
                    # to properly handle those scenarios for both WCS and pixel-linking
                    raise NotImplementedError("regions must all be SkyRegions")

                pixel_region = reg.to_pixel(wcs)

                if isinstance(pixel_region, regions.PolygonPixelRegion):
                    x_coords = pixel_region.vertices.x
                    y_coords = pixel_region.vertices.y

                # bqplot marker does not respect image pixel sizes, so need to render as polygon.
                elif isinstance(pixel_region, regions.RectanglePixelRegion):
                    pixel_region = pixel_region.to_polygon()
                    x_coords = pixel_region.vertices.x
                    y_coords = pixel_region.vertices.y
                elif isinstance(pixel_region, (regions.CirclePixelRegion,
                                               regions.EllipsePixelRegion,
                                               regions.CircleAnnulusPixelRegion)):
                    roi = regions2roi(pixel_region)
                    x_coords, y_coords = roi.to_polygon()
                else:  # pragma: no cover
                    raise NotImplementedError("could not parse coordinates from regions - please report this issue")  # noqa

                if update_existing:
                    mark = existing_overlays[i]
                    with mark.hold_sync():
                        mark.x = x_coords
                        mark.y = y_coords
                else:
                    mark = FootprintOverlay(
                        viewer,
                        self.overlay_selected,
                        x=x_coords,
                        y=y_coords,
                        colors=[self.color],
                        fill_opacities=[self.fill_opacity],
                        visible=visible)
                    new_marks.append(mark)

            if not update_existing and len(new_marks):
                viewer.figure.marks = viewer.figure.marks + new_marks
