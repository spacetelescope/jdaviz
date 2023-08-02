import bqplot
from traitlets import Bool, Float, List, Unicode, observe
from regions import regions

from jdaviz.core.custom_traitlets import FloatHandleEmpty
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import (PluginTemplateMixin, ViewerSelectMixin,
                                        SelectPluginComponent, EditableSelectPluginComponent)
from jdaviz.core.user_api import PluginUserApi

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

    # PRESET FOOTPRINTS AND OPTIONS
    instrument_items = List().tag(sync=True)
    instrument_selected = Unicode().tag(sync=True)

    ra = FloatHandleEmpty().tag(sync=True)
    dec = FloatHandleEmpty().tag(sync=True)
    ra_dec_instruments = List(['nirspec', 'nircam short', 'nircam long']).tag(sync=True)  # read-only
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
#                                                       on_add=self._on_footprint_add,
                                                       on_rename=self._on_footprint_rename,
                                                       on_remove=self._on_footprint_remove)

        self.instrument = SelectPluginComponent(self,
                                                items='instrument_items',
                                                selected='instrument_selected',
                                                manual_options=['nirspec',
                                                                'nircam short',
                                                                'nircam long',
                                                                'From File...'])

        # force the original entry in ephemerides with defaults
        self._change_footprint()

    @property
    def user_api(self):
        def instrument_in(instruments=[]):
            return lambda instrument: instrument in instruments

        # TODO: implement hidden_if in pluginuserapi
        return PluginUserApi(self, expose=('footprint',
                                           'rename_footprint', 'add_footprint', 'remove_footprint',
                                           'viewer', 'visible', 'color',
                                           'instrument', 'ra', 'dec',
                                           'v2_offset', 'v3_offset'))

#                             hidden_if={'ra': instrument_in(self.ra_dec_instruments),
#                                        'dec': instrument_in(self.ra_dec_instruments),
#                                        'v2_offset': instrument_in(self.offset_instruments),
#                                        'v3_offset': instrument_in(self.offset_instruments)})

    def rename_footprint(self, old_lbl, new_lbl):
        # NOTE: the footprint will call _on_footprint_rename after updating
        self.footprint.rename_choice(old_lbl, new_lbl)

    def add_footprint(self, lbl, set_as_selected=True):
        self.footprint.add_choice(lbl, set_as_selected=set_as_selected)

    def remove_footprint(self, lbl):
        # NOTE: the footprint will call _on_footprint_remove after updating
        self.footprint.remove_choice(lbl)

    def _on_footprint_rename(self, old_lbl, new_lbl):
        # this is triggered when the plugin footprint detects a change to the footprint name
        self._footprints[new_lbl] = self._footprints.pop(old_lbl, {})

    def _on_footprint_remove(self, lbl):
        _ = self._footprints.pop(lbl, {})
        # TODO: remove all marks associated with this footprint

    @observe('is_active')
    def _on_is_active_changed(self, *args):
        pass
        # toggle visibility of overlays

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
        # traitlets simultaneously and THEN revising the footprint once all are set
        self._ignore_traitlet_change = True
        for attr in ('instrument_selected', 'visible', 'color', 'viewer_selected',
                     'ra', 'dec', 'v2_offset', 'v3_offset'):
            if attr in ('ra', 'dec') and self.instrument_selected not in self.ra_dec_instruments:
                _ = fp.pop(attr, None)  # TODO: this isn't actually removing from the dict
                continue
            if attr in ('v2_offset', 'v3_offset') and self.instrument_selected not in self.offset_instruments:
                _ = fp.pop(attr, None)  # TODO: this isn't actually removing from the dict
                continue

            if attr in fp:
                setattr(self, attr, fp[attr])
            else:
                fp[attr.split('_selected')[0]] = getattr(self, attr)
        self._ignore_traitlet_change = False

    @observe('viewer_selected', 'visible', 'color')
    def _overlay_args_changed(self, msg):
        if self._ignore_traitlet_change:
            return
        if not self.footprint_selected:
            return
        name = msg.get('name').split('_selected')[0]
        self._footprints[self.footprint_selected][name] = msg.get('new')

        # update existing mark (or add/remove from viewers)

    @observe('instrument_selected', 'ra', 'dec', 'v2_offset', 'v3_offset')
    def _footprint_args_changed(self, msg):
        if self._ignore_traitlet_change:
            return
        if not self.footprint_selected:
            return
        name = msg.get('name').split('_selected')[0]
        self._footprints[self.footprint_selected][name] = msg.get('new')

        # construct callable function to get region from preset_regions.py
        # create (or update) marks in bqplot (possibly just calling _overlay_args_changed)


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
