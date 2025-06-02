import ipyvuetify as v
from echo import CallbackProperty

from glue.viewers.image.layer_artist import ImageLayerArtist
from glue.viewers.matplotlib.state import DeferredDrawCallbackProperty as DDCProperty
from glue.viewers.image.state import ImageLayerState

from glue_jupyter import link

__all__ = ['SonifiedLayerStateWidget', 'SonifiedDataLayerArtist']


class SonifiedLayerState(ImageLayerState):
    volume = DDCProperty(100, docstring='The volume level of this layer')
    sonification_enabled = CallbackProperty(True, 'whether audio will be allowed to play')

    def __init__(self, *args, **kwargs):

        super(SonifiedLayerState, self).__init__(*args, **kwargs)
        self.alpha = 0
        # self.add_callback('sonification_enabled', self._update_volume)
        self.previous_volume = self.volume

    def _update_volume(self, ignore=None):
        print("in layer state volume changed", self.sonification_enabled)
        if not self.sonification_enabled:
            self.previous_volume = self.volume
            self.volume = 0
        else:
            self.volume = self.previous_volume


class SonifiedDataLayerArtist(ImageLayerArtist):

    _layer_state_cls = SonifiedLayerState

    def __init__(self, view, *args, **kwargs):
        super().__init__(view, *args, **kwargs)
        self.view = view
        # link((self. _layer_state_cls, 'sonification_enabled'), (self, 'visible'))

    @property
    def sonified(self):
        return self.state.sonification_enabled

    @sonified.setter
    def sonified(self, value=None):
        print("setter ", self.state.sonification_enabled, value)
        if value is None:
            return
        self.state.sonification_enabled = value
        # self.redraw()

    def enable(self):
        if self.enabled:
            return

    def redraw(self):
        print("redraw")
        if self.view:
            # needs to run after a sonified layer is removed from the viewer and
            # then added back
            self.view.recalculate_combined_sonified_grid()

    def remove(self):
        print("remove")
        super().remove()
        self.sonified = False
        # self.view.recalculate_combined_sonified_grid()



class SonifiedLayerStateWidget(v.VuetifyTemplate):
    template_file = (__file__, 'layer_sonified.vue')

    def __init__(self, layer, *args, **kwargs):
        super().__init__(*args, **kwargs)
