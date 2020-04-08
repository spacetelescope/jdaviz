from glue.core.message import Message


class ChangeSliderMessage(Message):
    def __init__(self, value, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._value = value

    @property
    def value(self):
        return self._value


class CreateCubeViewerMessage(Message):
    def __init__(self, viewer, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._viewer = viewer

    @property
    def viewer(self):
        return self._viewer