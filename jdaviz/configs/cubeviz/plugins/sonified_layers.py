from echo import CallbackProperty
import ipyvuetify as v

from glue.viewers.image.layer_artist import ImageLayerArtist, BaseImageLayerArtist
from glue.viewers.matplotlib.state import DeferredDrawCallbackProperty as DDCProperty
from glue.viewers.image.state import ImageLayerState

__all__ = ['SonifiedLayerStateWidget', 'SonifiedSubsetLayerStateWidget',
           'SonifiedDataLayerArtist', 'SonifiedDataSubsetLayerArtist']


class SonifiedLayerState(ImageLayerState):
    bitmap_visible = CallbackProperty(False, 'whether to show the image as a bitmap')
    contour_visible = CallbackProperty(False, 'whether to show the image as contours')
    volume = DDCProperty(50, docstring='The volume level of this layer')

    def __init__(self, *args, **kwargs):

        super(SonifiedLayerState, self).__init__(*args, **kwargs)


class SonifiedDataLayerArtist(ImageLayerArtist):

    _layer_state_cls = SonifiedLayerState

    def __init__(self, view, *args, **kwargs):
        super().__init__(view, *args, **kwargs)
        self.view = view

    def enable(self):
        if self.enabled:
            return

    def redraw(self):
        pass


class SonifiedLayerStateWidget(v.VuetifyTemplate):
    template_file = (__file__, 'layer_sonified.vue')

    def __init__(self, layer, *args, **kwargs):
        super().__init__(*args, **kwargs)


class SonifiedSubsetLayerState(ImageLayerState):
    bitmap_visible = CallbackProperty(False, 'whether to show the image as a bitmap')
    contour_visible = CallbackProperty(False, 'whether to show the image as contours')
    volume = DDCProperty(50, docstring='The volume level of this layer')

    def __init__(self, *args, **kwargs):

        super(SonifiedSubsetLayerState, self).__init__(*args, **kwargs)


class SonifiedSubsetLayerStateWidget(v.VuetifyTemplate):

    def __init__(self, layer_state, *args, **kwargs):
        super().__init__(layer_state, *args, **kwargs)


class SonifiedDataSubsetLayerArtist(BaseImageLayerArtist):

    _layer_state_cls = SonifiedSubsetLayerStateWidget

    def __init__(self, view, *args, **kwargs):
        super().__init__(view, *args, **kwargs)
