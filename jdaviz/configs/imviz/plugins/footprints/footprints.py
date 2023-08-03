#import bqplot
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
    """
    template_file = __file__, "footprints.vue"
    uses_active_status = Bool(True).tag(sync=True)

    # FOOTPRINT LABEL
    footprint_mode = Unicode().tag(sync=True)
    footprint_edit_value = Unicode().tag(sync=True)
    footprint_items = List().tag(sync=True)
    footprint_selected = Unicode().tag(sync=True)

    # STYLING OPTIONS
    # viewer
    visible = Bool(True).tag(sync=True)
    color = Unicode('#c75109').tag(sync=True)  # "active" orange
    fill_opacity = FloatHandleEmpty(0.1).tag(sync=True)

    # PRESET FOOTPRINTS AND OPTIONS
    instrument_items = List().tag(sync=True)
    instrument_selected = Unicode().tag(sync=True)

    ra = FloatHandleEmpty().tag(sync=True)
    dec = FloatHandleEmpty().tag(sync=True)
    pa = FloatHandleEmpty().tag(sync=True)
    pos_instruments = List(['nirspec', 'nircam short', 'nircam long']).tag(sync=True)  # read-only
    v2_offset = FloatHandleEmpty().tag(sync=True)
    v3_offset = FloatHandleEmpty().tag(sync=True)
    offset_instruments = List(['nircam short', 'nircam long']).tag(sync=True)  # read-only
    # TODO: dithering/mosaic options?

    def __init__(self, *args, **kwargs):
        self._ignore_traitlet_change = False
        self._footprints = {'default': {}}

        super().__init__(*args, **kwargs)
        self.viewer.multiselect = True  # multiselect always enabled
        self.keep_active = True

        # TODO: migrate from lcviz to here (as part of this PR)
        self.footprint = EditableSelectPluginComponent(self,
                                                       mode='footprint_mode',
                                                       edit_value='footprint_edit_value',
                                                       items='footprint_items',
                                                       selected='footprint_selected',
                                                       manual_options=['default'],
                                                      #on_add=self._on_footprint_add,
                                                       on_rename=self._on_footprint_rename,
                                                       on_remove=self._on_footprint_remove)

        # FUTURE IMPROVEMENT: could add 'From File...' entry here that works similar to that in
        # the catalogs plugin, loads in a region file, and replaces any input UI elements with just
        # a reference to the filename or some text
        self.instrument = SelectPluginComponent(self,
                                                items='instrument_items',
                                                selected='instrument_selected',
                                                manual_options=['nirspec',
                                                                'nircam short',
                                                                'nircam long'])


        # force the original entry in ephemerides with defaults
        self._change_footprint()

    @property
    def user_api(self):
        def instrument_in(instruments=[]):
            return lambda instrument: instrument in instruments

        # TODO: implement hidden_if in pluginuserapi
        return PluginUserApi(self, expose=('footprint',
                                           'rename_footprint', 'add_footprint', 'remove_footprint',
                                           'viewer', 'visible', 'color', 'fill_opacity',
                                           'instrument', 'ra', 'dec', 'pa',
                                           'v2_offset', 'v3_offset',
                                           'footprint_regions'))

#                             hidden_if={'ra': instrument_in(self.'pos_instruments'),
#                                        'dec': instrument_in(self.pos_instruments),
#                                        'pa': instrument_in(self.pos_instruments),
#                                        'v2_offset': instrument_in(self.offset_instruments),
#                                        'v3_offset': instrument_in(self.offset_instruments)})

    def _get_marks(self, viewer, footprint=None):
        matches = [mark for mark in viewer.figure.marks if isinstance(mark, FootprintOverlay) and (mark.footprint == footprint or footprint is None)]
        return matches

#        mark = FootprintOverlay(viewer, footprint)  # TODO: will need multiple instances, and that depends on the instrument (probably re-create on new instrument?)
#        viewer.figure.marks = viewer.figure.marks + [mark]
#        return mark

    @property
    def marks(self):
        # {footprint: {viewer: [list_of_marks]}}
        return {footprint: {viewer_id: self._get_marks(viewer, footprint)
                            for viewer_id, viewer in self.app._viewer_store.items()
                            if hasattr(viewer, 'figure')}
                for footprint in self.footprint.choices}

    def rename_footprint(self, old_lbl, new_lbl):
        # NOTE: the footprint will call _on_footprint_rename after updating
        self.footprint.rename_choice(old_lbl, new_lbl)

    def add_footprint(self, lbl, set_as_selected=True):
        # TODO: ability to pass options which would avoid updating the marks until all are set,
        # probably by setattr(self.user_api, k, v) (and checks in advance that all are valid?)
        self.footprint.add_choice(lbl, set_as_selected=set_as_selected)
        if not set_as_selected:
            # NOTE: otherwise will trigger _change_footprint via the observe on footprint_selected
            print("*** TODO: need to handle creating mark for footprint that isn't selected (or not allow set_as_selected=False)!")

    def remove_footprint(self, lbl):
        # NOTE: the footprint will call _on_footprint_remove after updating
        self.footprint.remove_choice(lbl)

    def _on_footprint_rename(self, old_lbl, new_lbl):
        # this is triggered when the plugin footprint detects a change to the footprint name
        self._footprints[new_lbl] = self._footprints.pop(old_lbl, {})

        # change the reference on any marks entries for this footprint (in any viewer)
        for viewer_id, viewer in self.app._viewer_store.items():
            if not hasattr(viewer, 'figure'):
                continue
            for mark in self._get_marks(viewer, old_lbl):
                mark._footprint = new_lbl

    def _on_footprint_remove(self, lbl):
        _ = self._footprints.pop(lbl, {})

        # remove any marks objects (corresponding to this footprint) from all figures
        for viewer_id, viewer in self.app._viewer_store.items():
            if not hasattr(viewer, 'figure'):
                continue
            viewer.figure.marks = [m for m in viewer.figure.marks if getattr(m, 'footprint', None) != lbl]

    @observe('is_active')
    def _on_is_active_changed(self, *args):
        if not hasattr(self, 'footprint'):
            # plugin/traitlet startup
            return

        if self.is_active:
            self._footprint_args_changed()

        for footprint, viewer_marks in self.marks.items():
            for viewer_id, marks in viewer_marks.items():
                visible = self._mark_visible(viewer_id, footprint)
                for mark in marks:
                    mark.visible = visible

    @observe('footprint_selected')
    def _change_footprint(self, *args):
        if not hasattr(self, 'footprint'):
            # plugin/traitlet startup
            return
        if self.footprint_selected == '':
            # no footprintt selected (this can happen when removing all footprints)
            return

        if self.footprint_selected not in self._footprints:
            self._footprints[self.footprint_selected] = {}

        fp = self._footprints[self.footprint_selected]

        # we'll temporarily disable updating the footprints so that we can set all
        # traitlets simultaneously (and since we're only updating traitlets to a previously-set
        # footprint, we shouldn't have to update anything with the marks themselves)
        self._ignore_traitlet_change = True
        for attr in ('instrument_selected', 'visible', 'color', 'fill_opacity', 'viewer_selected',
                     'ra', 'dec', 'pa', 'v2_offset', 'v3_offset'):
            key = attr.split('_selected')[0]
            if attr in ('ra', 'dec', 'pa') and self.instrument_selected not in self.pos_instruments:
                _ = fp.pop(attr, None)  # TODO: this isn't actually removing from the dict
                continue
            if attr in ('v2_offset', 'v3_offset') and self.instrument_selected not in self.offset_instruments:
                _ = fp.pop(attr, None)  # TODO: this isn't actually removing from the dict
                continue

            if key in fp:
                setattr(self, attr, fp[key])
            else:
                fp[key] = getattr(self, attr)
        self._ignore_traitlet_change = False

    def _mark_visible(self, viewer_id, footprint=None):
        if not self.is_active:
            return False
        if footprint is None:
            footprint = self.footprint_selected
        fp = self._footprints[footprint]
        if viewer_id not in fp.get('viewer', []):
            return False
        else:
            return fp.get('visible', False)

    @observe('viewer_selected', 'visible', 'color', 'fill_opacity')
    def _overlay_args_changed(self, msg={}):
        if self._ignore_traitlet_change:
            return
        if not self.footprint_selected:
            return
        name = msg.get('name', '').split('_selected')[0]
        if len(name):
            self._footprints[self.footprint_selected][name] = msg.get('new')

        # TODO: need to create marks instances (with visible=False) when a new viewer is created

        # update existing mark (or add/remove from viewers)
        for viewer_id, viewer in self.app._viewer_store.items():
            visible = self._mark_visible(viewer_id)
            existing_marks = self._get_marks(viewer, self.footprint_selected)

            if visible and not len(existing_marks):
                # then we need to create new marks at least for this viewer
                self._footprint_args_changed()
                return

            for mark in existing_marks:
                mark.visible = visible
                mark.colors = [self.color]
                mark.fill_opacities = [self.fill_opacity]

    @property
    def footprint_regions(self):
        """
        Access the regions objects corresponding to the current settings
        """
        # construct callable function to get region from preset_regions.py
        callable = getattr(preset_regions,
                           f"{self.instrument_selected.replace(' ', '_').lower()}_footprint")

        callable_kwargs = {}
        if self.instrument_selected in self.pos_instruments:
            for arg in ('ra', 'dec', 'pa'):
                callable_kwargs[arg] = getattr(self, arg)
        if self.instrument_selected in self.offset_instruments:
            for arg in ('v2_offset', 'v3_offset'):
                callable_kwargs[arg] = getattr(self, arg)

        regs = callable(**callable_kwargs)
        return regs

    @observe('instrument_selected', 'ra', 'dec', 'pa', 'v2_offset', 'v3_offset')
    def _footprint_args_changed(self, msg={}):
        if self._ignore_traitlet_change:
            return
        if not self.footprint_selected:
            return
        if not self.is_active:
            return
        name = msg.get('name', '').split('_selected')[0]
        if len(name):
            self._footprints[self.footprint_selected][name] = msg.get('new')

        regs = self.footprint_regions

        for viewer_id, viewer in self.app._viewer_store.items():
            visible = self._mark_visible(viewer_id)
            wcs = getattr(viewer.state.reference_data, 'coords', None)
            if wcs is None:
#                print("*** skipping viewer because ref data has no WCS")
                continue
            existing_overlays = self._get_marks(viewer, self.footprint_selected)
            regs = [r for r in regs if isinstance(r, regions.PolygonSkyRegion)]
            update_existing = len(existing_overlays) == len(regs)
            if not update_existing and len(existing_overlays):
                # clear any existing marks (length has changed, perhaps a new instrument)
                viewer.figure.marks = [m for m in viewer.figure.marks if getattr(m, 'footprint', None) != self.footprint_selected]
#            print("*** viewer, update_existing:", update_existing, len(regs))
            new_marks = []
            for i, reg in enumerate(regs):
                pixel_region = reg.to_pixel(wcs)
                if not isinstance(reg, regions.PolygonSkyRegion):
#                    print(f"*** skipping reg {i}/{len(regs)} because not PolygonSkyRegion")
                    continue
#                if isinstance(pixel_region, regions.PointPixelRegion):
#                    continue
#                    if update_existing:
#                        mark = existing_overlays[i]
#                        with mark.hold_sync():
#                            mark.x = [pixel_region.center.x]
#                            mark.y = [pixel_regions.center.y]
#                    else:
#                        # instrument center point
#                        # TODO: need to make this a FootprintOverlay object of some sort, even though its scatter
#                        mark = bqplot.Scatter(
#                            x=[pixel_region.center.x],
#                            y=[pixel_region.center.y],
#                            scales=scales,   # TODO: scales
#                            colors=[self.color],
#                            marker="plus",
#                        )
#                        new_marks.append(mark)

                else:
#                    print(f"*** processing reg {i}/{len(regs)}")
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
                            self.footprint_selected,
                            x=x_coords,
                            y=y_coords,
                            colors=[self.color],
                            fill_opacities=[self.fill_opacity],
                            visible=visible
                        )
                        new_marks.append(mark)

            if not update_existing and len(new_marks):
                viewer.figure.marks = viewer.figure.marks + new_marks


"""
    def region_to_marks(self):
        marks = []
        for i, reg in enumerate(regs):
            pixel_region = reg.to_pixel(wcs)
            if isinstance(pixel_region, regions.PointPixelRegion):
                if update_patches is not None:
                    mark = update_patches[i]
                    with mark.hold_sync():
                        mark.x = [pixel_region.center.x]
                        mark.y = [pixel_region.center.y]
                        mark.colors = [color]
                        mark.default_opacities = [alpha]
                else:
                    # instrument center point
                    mark = bqplot.Scatter(
                        x=[pixel_region.center.x],
                        y=[pixel_region.center.y],
                        scales=scales,
                        colors=[color],
                        marker="plus",
                    )
                    mark.default_opacities = [alpha]
            else:
                x_coords = pixel_region.vertices.x
                y_coords = pixel_region.vertices.y
                if update_patches is not None:
                    mark = update_patches[i]
                    with mark.hold_sync():
                        mark.x = x_coords
                        mark.y = y_coords
                        mark.fill = fill
                        mark.colors = [color]
                        mark.opacities = [alpha]
                        mark.fill_opacities = [fill_alpha]
                else:
                    # instrument aperture regions
                    mark = bqplot.Lines(
                        x=x_coords,
                        y=y_coords,
                        scales=scales,
                        fill=fill,
                        colors=[color],
                        stroke_width=2,
                        close_path=True,
                        opacities=[alpha],
                        fill_opacities=[fill_alpha],
                    )

            mark.visible = visible
            marks.append(mark)

        if update_patches is None:
            fig.marks = fig.marks + marks
        return marks
"""
