from traitlets import Unicode

from jdaviz.core.registries import tool_registry
from jdaviz.core.template_mixin import TemplateMixin

__all__ = ['CoordsInfo']


@tool_registry('g-coords-info')
class CoordsInfo(TemplateMixin):
    template_file = __file__, "coords_info.vue"
    pixel = Unicode("").tag(sync=True)
    value = Unicode("").tag(sync=True)
    world_label_prefix = Unicode("\u00A0").tag(sync=True)
    world_label_icrs = Unicode("\u00A0").tag(sync=True)
    world_label_deg = Unicode("\u00A0").tag(sync=True)
    world_ra = Unicode("").tag(sync=True)
    world_dec = Unicode("").tag(sync=True)
    world_ra_deg = Unicode("").tag(sync=True)
    world_dec_deg = Unicode("").tag(sync=True)

    def reset_coords_display(self):
        self.world_label_prefix = '\u00A0'
        self.world_label_icrs = '\u00A0'
        self.world_label_deg = '\u00A0'
        self.world_ra = ''
        self.world_dec = ''
        self.world_ra_deg = ''
        self.world_dec_deg = ''

    def set_coords(self, sky):
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
