from traitlets import Bool, Unicode

from jdaviz.configs.specviz.plugins.viewers import SpecvizProfileView
from jdaviz.core.registries import tool_registry
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.core.marks import PluginScatter

__all__ = ['CoordsInfo']


@tool_registry('g-coords-info')
class CoordsInfo(TemplateMixin):
    template_file = __file__, "coords_info.vue"
    icon = Unicode("").tag(sync=True)
    pixel = Unicode("").tag(sync=True)
    value = Unicode("").tag(sync=True)
    world_label_prefix = Unicode("\u00A0").tag(sync=True)
    world_label_prefix_2 = Unicode("\u00A0").tag(sync=True)
    world_label_icrs = Unicode("\u00A0").tag(sync=True)
    world_label_deg = Unicode("\u00A0").tag(sync=True)
    world_ra = Unicode("").tag(sync=True)
    world_dec = Unicode("").tag(sync=True)
    world_ra_deg = Unicode("").tag(sync=True)
    world_dec_deg = Unicode("").tag(sync=True)
    unreliable_world = Bool(False).tag(sync=True)
    unreliable_pixel = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._marks = {}

    @property
    def marks(self):
        """
        Access the marks created by this plugin.
        """
        if self._marks:
            # TODO: replace with cache property?
            return self._marks

        # create marks for each of the spectral viewers (will need a listener event to create marks
        # for new viewers if dynamic creation of spectral viewers is ever supported)
        for id, viewer in self.app._viewer_store.items():
            if isinstance(viewer, SpecvizProfileView):
                self._marks[id] = PluginScatter(viewer, visible=False)
                viewer.figure.marks = viewer.figure.marks + [self._marks[id]]
        return self._marks

    def reset_coords_display(self):
        self.world_label_prefix = '\u00A0'
        self.world_label_prefix_2 = '\u00A0'
        self.world_label_icrs = '\u00A0'
        self.world_label_deg = '\u00A0'
        self.world_ra = ''
        self.world_dec = ''
        self.world_ra_deg = ''
        self.world_dec_deg = ''
        self.unreliable_world = False
        self.unreliable_pixel = False

    def set_coords(self, sky, unreliable_world=False, unreliable_pixel=False):
        celestial_coordinates = sky.to_string('hmsdms', precision=4, pad=True).split()
        celestial_coordinates_deg = sky.to_string('decimal', precision=10, pad=True).split()
        world_ra = celestial_coordinates[0]
        world_dec = celestial_coordinates[1]
        world_ra_deg = celestial_coordinates_deg[0]
        world_dec_deg = celestial_coordinates_deg[1]

        if "nan" in (world_ra, world_dec, world_ra_deg, world_dec_deg):
            self.reset_coords_display()
        else:
            self.world_label_prefix = 'World'
            self.world_label_icrs = '(ICRS)'
            self.world_label_deg = '(deg)'
            self.world_ra = world_ra
            self.world_dec = world_dec
            self.world_ra_deg = world_ra_deg
            self.world_dec_deg = world_dec_deg
            self.unreliable_world = unreliable_world
            self.unreliable_pixel = unreliable_pixel
            if unreliable_world:
                self.world_label_prefix_2 = '(est.)'
            else:
                self.world_label_prefix_2 = '\u00A0'
