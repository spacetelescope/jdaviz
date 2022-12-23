from traitlets import Bool

from jdaviz.core.events import SnackbarMessage
from jdaviz.core.registries import tray_registry
from jdaviz.core.template_mixin import PluginTemplateMixin, DatasetSelectMixin

try:
    from reproject import reproject_interp
    from reproject.mosaicking import find_optimal_celestial_wcs
except ImportError:
    HAS_REPROJECT = False
else:
    HAS_REPROJECT = True

__all__ = ['Reproject']


@tray_registry('imviz-reproject', label="Reproject")
class Reproject(PluginTemplateMixin, DatasetSelectMixin):
    template_file = __file__, "reproject.vue"

    reproject_in_progress = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not HAS_REPROJECT:
            self.disabled_msg = 'Please install reproject and restart Jdaviz to use this plugin'
            return

    def vue_do_reproject(self, *args, **kwargs):
        if (not HAS_REPROJECT or self.dataset_selected not in self.data_collection
                or self.reproject_in_progress):
            return

        data = self.data_collection[self.dataset_selected]
        wcs_in = data.coords
        if wcs_in is None:
            return

        from astropy.nddata import NDData

        self.reproject_in_progress = True
        try:
            # TODO: Support GWCS (https://github.com/astropy/reproject/issues/328)
            # Find WCS where North is pointing up.
            wcs_out, shape_out = find_optimal_celestial_wcs([(data.shape, wcs_in)], frame='icrs')

            # Reproject image to new WCS.
            comp = data.get_component(data.main_components[0])
            new_arr = reproject_interp((comp.data, wcs_in), wcs_out, shape_out=shape_out,
                                       return_footprint=False)

            # TODO: Let user customize new label; have default label not be so ugly.
            new_label = f'{self.dataset_selected} (reprojected)'

            # Stuff it back into Imviz.
            # We don't want to inherit input metadata because it might have wrong (unrotated)
            # WCS info in the header metadata.
            ndd = NDData(new_arr, wcs=wcs_out)
            self.app._jdaviz_helper.load_data(ndd, data_label=new_label)

        except Exception as e:
            self.hub.broadcast(SnackbarMessage(
                f"Failed to reproject {self.dataset_selected}: {repr(e)}",
                color='error', sender=self))

        finally:
            self.reproject_in_progress = False
