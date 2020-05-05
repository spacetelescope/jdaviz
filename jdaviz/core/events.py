from glue.core.message import Message

__all__ = ['NewViewerMessage', 'AddViewerMessage', 'LoadDataMessage',
           'DataSelectedMessage', 'ViewerSelectedMessage',
           'RemoveStackMessage', 'SplitStackMessage', 'RemoveItemMessage',
           'AddDataMessage']


class NewViewerMessage(Message):
    def __init__(self, cls, data, x_attr=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._cls = cls
        self._data = data
        self._x_attr = x_attr

    @property
    def cls(self):
        return self._cls

    @property
    def data(self):
        return self._data

    @property
    def x_attr(self):
        return self._x_attr


class AddViewerMessage(Message):
    def __init__(self, viewer, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._viewer = viewer

    @property
    def viewer(self):
        return self._viewer


class LoadDataMessage(Message):
    def __init__(self, path, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._path = path

    @property
    def path(self):
        return self._path


class DataSelectedMessage(Message):
    def __init__(self, indicies, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._indicies = indicies

    @property
    def indicies(self):
        return self._indicies


class ViewerSelectedMessage(Message):
    def __init__(self, viewer, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._viewer = viewer

    @property
    def viewer(self):
        return self._viewer


class RemoveStackMessage(Message):
    def __init__(self, stack, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._stack = stack

    @property
    def stack(self):
        return self._stack


class SplitStackMessage(Message):
    def __init__(self, item, horizontal, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._item = item
        self._horizontal = horizontal

    @property
    def item(self):
        return self._item

    @property
    def horizontal(self):
        return self._horizontal


class RemoveItemMessage(Message):
    def __init__(self, item, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._item = item

    @property
    def item(self):
        return self._item


class AddDataMessage(Message):
    def __init__(self, data, viewer, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._data = data
        self._viewer = viewer

    @property
    def data(self):
        return self._data

    @property
    def viewer(self):
        return self._viewer


class SnackbarMessage(Message):
    def __init__(self, text, timeout=5000, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._text = text
        self._timeout = timeout

    @property
    def text(self):
        return self._text

    @property
    def timeout(self):
        return self._timeout
