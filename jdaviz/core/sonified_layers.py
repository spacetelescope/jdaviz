import ipyvuetify as v
from echo import CallbackProperty

from glue.viewers.image.layer_artist import ImageLayerArtist
from glue.viewers.matplotlib.state import DeferredDrawCallbackProperty as DDCProperty
from glue.viewers.image.state import ImageLayerState


__all__ = ['SonifiedLayerStateWidget', 'SonifiedDataLayerArtist']


class SonifiedLayerState(ImageLayerState):
    volume = DDCProperty(100, docstring='The volume level of this layer')
    audible = CallbackProperty(True, 'whether audio will be allowed to play')

    def __init__(self, *args, **kwargs):

        super(SonifiedLayerState, self).__init__(*args, **kwargs)
        self.alpha = 0
        self.previous_volume = self.volume

    def _update_volume(self, ignore=None):
        if not self.audible:
            self.previous_volume = self.volume
            self.volume = 0
        else:
            self.volume = self.previous_volume


class SonifiedDataLayerArtist(ImageLayerArtist):

    _layer_state_cls = SonifiedLayerState

    def __init__(self, view, *args, **kwargs):
        super().__init__(view, *args, **kwargs)
        self.view = view

    @property
    def audible(self):
        return self.state.audible

    @audible.setter
    def audible(self, value=None):
        if value is None:
            return
        self.state.audible = value

    def enable(self):
        if self.enabled:
            return

    def redraw(self):
        if self.view:
            # needs to run after a sonified layer is removed from the viewer and
            # then added back
            self.view.recalculate_combined_sonified_grid()

    def remove(self):
        super().remove()
        self.audible = False


class SonifiedLayerStateWidget(v.VuetifyTemplate):
    template_file = (__file__, 'layer_sonified.vue')

    def __init__(self, layer, *args, **kwargs):
        super().__init__(*args, **kwargs)
