from traitlets import Bool, List, Unicode, observe
import regions

from jdaviz.core.custom_traitlets import FloatHandleEmpty
from jdaviz.core.marks import FootprintOverlay
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin, ViewerSelectMixin,
                                        SelectPluginComponent, EditableSelectPluginComponent)
from jdaviz.core.user_api import PluginUserApi

from . import preset_regions


__all__ = ['Footprints']


@tray_registry('imviz-footprints', label="Footprints")
class Footprints(PluginTemplateMixin, ViewerSelectMixin):
    """
    See the :ref:`Footprints Plugin Documentation <imviz-footprints>` for more details.

    Only the following attributes and methods are available through the
    :ref:`public plugin API <plugin-apis>`:

    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.show`
    * :meth:`~jdaviz.core.template_mixin.PluginTemplateMixin.open_in_tray`
    * ``overlay`` (:class:`~jdaviz.core.template_mixin.EditableSelectPluginComponent`): the
        currently active overlay (all other traitlets control this overlay instance)
    * :meth:``rename_overlay``
        rename any overlay
    * :meth:``add_overlay``
        add a new overlay instance (and select as active)
    * :meth:``remove_overlay``
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
    * :meth:``overlay_regions``
    """
    template_file = __file__, "footprints.vue"
    uses_active_status = Bool(True).tag(sync=True)

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
    preset_items = List().tag(sync=True)
    preset_selected = Unicode().tag(sync=True)

    ra = FloatHandleEmpty().tag(sync=True)
    dec = FloatHandleEmpty().tag(sync=True)
    pa = FloatHandleEmpty().tag(sync=True)
    v2_offset = FloatHandleEmpty().tag(sync=True)
    v3_offset = FloatHandleEmpty().tag(sync=True)
    # TODO: dithering/mosaic options?

    def __init__(self, *args, **kwargs):
        if not preset_regions._has_pysiaf:  # pragma: nocover
            # NOTE: if we want to keep this as a soft-dependency and implement other
            # footprint/region options later, we could just disable the JWST presets
            # instead of the entire plugin
            self.disabled_msg = 'this plugin requires pysiaf to be installed'

        self._ignore_traitlet_change = False
        self._overlays = {}

        super().__init__(*args, **kwargs)
        self.viewer.multiselect = True  # multiselect always enabled

        self.overlay = EditableSelectPluginComponent(self,
                                                     name='overlay',
                                                     mode='overlay_mode',
                                                     edit_value='overlay_edit_value',
                                                     items='overlay_items',
                                                     selected='overlay_selected',
                                                     manual_options=['default'],
                                                     on_rename=self._on_overlay_rename,
                                                     on_remove=self._on_overlay_remove)

        # FUTURE IMPROVEMENT: could add 'From File...' entry here that works similar to that in
        # the catalogs plugin, loads in a region file, and replaces any input UI elements with just
        # a reference to the filename or some text
        self.preset = SelectPluginComponent(self,
                                            items='preset_items',
                                            selected='preset_selected',
                                            manual_options=preset_regions._instruments.keys())

        # force the original entry in overlay with defaults
        self._change_overlay()

    @property
    def user_api(self):
        return PluginUserApi(self, expose=('overlay',
                                           'rename_overlay', 'add_overlay', 'remove_overlay',
                                           'viewer', 'visible', 'color', 'fill_opacity',
                                           'preset', 'ra', 'dec', 'pa',
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

    @observe('is_active')
    def _on_is_active_changed(self, *args):
        if not hasattr(self, 'overlay'):  # pragma: nocover
            # plugin/traitlet startup
            return

        if self.is_active:
            if not len(self._overlays):
                # create the first default overlay
                self._change_overlay()
            self._preset_args_changed()

        for overlay, viewer_marks in self.marks.items():
            for viewer_id, marks in viewer_marks.items():
                visible = self._mark_visible(viewer_id, overlay)
                for mark in marks:
                    mark.visible = visible

    @observe('overlay_selected')
    def _change_overlay(self, *args):
        if not hasattr(self, 'overlay'):  # pragma: nocover
            # plugin/traitlet startup
            return
        if self.overlay_selected == '':
            # no overlay selected (this can happen when removing all overlays)
            return
        if not self.is_active:
            return

        if self.overlay_selected not in self._overlays:
            # create new entry with defaults (any defaults not provided here will be carried over
            # from the previous selection based on current traitlet values)
            self._overlays[self.overlay_selected] = {'color': '#c75109'}
            if len(self._overlays) == 1 and len(self.viewer.selected):
                # default to the center of the current zoom limits of the first selected viewer
                center_coord = self.viewer.selected_obj[0]._get_center_skycoord()
                self._overlays[self.overlay_selected]['ra'] = center_coord.ra.to_value('deg')
                self._overlays[self.overlay_selected]['dec'] = center_coord.dec.to_value('deg')

        fp = self._overlays[self.overlay_selected]

        # we'll temporarily disable updating the overlays so that we can set all
        # traitlets simultaneously (and since we're only updating traitlets to a previously-set
        # overlay, we shouldn't have to update anything with the marks themselves)
        self._ignore_traitlet_change = True
        for attr in ('preset_selected', 'visible', 'color', 'fill_opacity', 'viewer_selected',
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

    def _mark_visible(self, viewer_id, overlay=None):
        if not self.is_active:
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
        if not self.is_active:
            return
        name = msg.get('name', '').split('_selected')[0]
        if len(name):
            self._overlays[self.overlay_selected][name] = msg.get('new')

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

    @property
    def overlay_regions(self):
        """
        Access the regions objects corresponding to the current settings
        """

        callable_kwargs = {k: getattr(self, k)
                           for k in ('ra', 'dec', 'pa', 'v2_offset', 'v3_offset')}

        regs = preset_regions.jwst_footprint(self.preset_selected, **callable_kwargs)
        return regs

    @observe('preset_selected', 'ra', 'dec', 'pa', 'v2_offset', 'v3_offset')
    def _preset_args_changed(self, msg={}):
        if self._ignore_traitlet_change:
            return
        if not self.overlay_selected:
            return

        name = msg.get('name', '').split('_selected')[0]

        if self.overlay_selected not in self._overlays:
            # default dictionary has not been created yet
            return
        if not self.is_active:
            return

        if len(name):
            self._overlays[self.overlay_selected][name] = msg.get('new')

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
            regs = [r for r in regs if isinstance(r, regions.PolygonSkyRegion)]
            update_existing = len(existing_overlays) == len(regs)
            if not update_existing and len(existing_overlays):
                # clear any existing marks (length has changed, perhaps a new preset)
                viewer.figure.marks = [m for m in viewer.figure.marks
                                       if getattr(m, 'overlay', None) != self.overlay_selected]

            # the following logic is adapted from
            # https://github.com/spacetelescope/jwst_novt/blob/main/jwst_novt/interact/display.py
            new_marks = []
            for i, reg in enumerate(regs):
                pixel_region = reg.to_pixel(wcs)
                if not isinstance(reg, regions.PolygonSkyRegion):  # pragma: nocover
                    # if we ever want to support plotting centers as well,
                    # see jwst_novt/interact/display.py
                    continue

                x_coords = pixel_region.vertices.x
                y_coords = pixel_region.vertices.y
                if update_existing:
                    mark = existing_overlays[i]
                    with mark.hold_sync():
                        mark.x = x_coords
                        mark.y = y_coords
                else:
                    # instrument aperture regions
                    mark = FootprintOverlay(
                        viewer,
                        self.overlay_selected,
                        x=x_coords,
                        y=y_coords,
                        colors=[self.color],
                        fill_opacities=[self.fill_opacity],
                        visible=visible
                    )
                    new_marks.append(mark)

            if not update_existing and len(new_marks):
                viewer.figure.marks = viewer.figure.marks + new_marks
