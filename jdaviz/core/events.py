from glue.core.message import Message

__all__ = ['NewViewerMessage', 'ViewerAddedMessage', 'ViewerRemovedMessage', 'LoadDataMessage',
           'AddDataMessage', 'SnackbarMessage', 'RemoveDataMessage',
           'AddLineListMessage', 'RowLockMessage',
           'SliceSelectSliceMessage',
           'SliceToolStateMessage',
           'TableClickMessage', 'LinkUpdatedMessage', 'ExitBatchLoadMessage',
           'MarkersChangedMessage', 'CanvasRotationChangedMessage',
           'ChangeRefDataMessage']


class NewViewerMessage(Message):
    """Message to trigger viewer creation in the application."""
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


class ViewerAddedMessage(Message):
    """Unlike `NewViewerMessage`, this should be emitted after a viewer is created."""
    def __init__(self, viewer_id, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # NOT viewer reference, which is not unique and can be None
        self._viewer_id = viewer_id

    @property
    def viewer_id(self):
        return self._viewer_id


class ViewerRemovedMessage(Message):
    """Message emitted after a viewer is destroyed by the application."""
    def __init__(self, viewer_id, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # NOT viewer reference, which is not unique and can be None
        self._viewer_id = viewer_id

    @property
    def viewer_id(self):
        return self._viewer_id


class LoadDataMessage(Message):
    def __init__(self, path, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._path = path

    @property
    def path(self):
        return self._path


class AddDataMessage(Message):
    def __init__(self, data, viewer, viewer_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._data = data
        self._viewer = viewer
        self._viewer_id = viewer_id

    @property
    def data(self):
        return self._data

    @property
    def viewer(self):
        return self._viewer

    @property
    def viewer_id(self):
        return self._viewer_id


class RemoveDataMessage(Message):
    def __init__(self, data, viewer, viewer_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._data = data
        self._viewer = viewer
        self._viewer_id = viewer_id

    @property
    def data(self):
        return self._data

    @property
    def viewer(self):
        return self._viewer

    @property
    def viewer_id(self):
        return self._viewer_id


class ChangeRefDataMessage(Message):
    def __init__(self, data, viewer, viewer_id=None, old=None, new=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._data = data
        self._viewer = viewer
        self._viewer_id = viewer_id
        self._old = old
        self._new = new

    @property
    def data(self):
        return self._data

    @property
    def viewer(self):
        return self._viewer

    @property
    def viewer_id(self):
        return self._viewer_id

    @property
    def old(self):
        return self._old

    @property
    def new(self):
        return self._new


class SnackbarMessage(Message):
    def __init__(self, text, color=None, timeout=5000, loading=False,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._text = text
        self._color = color
        self._timeout = timeout
        self._loading = loading

    @property
    def text(self):
        return self._text

    @property
    def color(self):
        return self._color

    @property
    def timeout(self):
        return self._timeout

    @property
    def loading(self):
        return self._loading


class ConfigurationLoadedMessage(Message):
    def __init__(self, config, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._config = config

    @property
    def config(self):
        return self._config


class AddDataToViewerMessage(Message):
    def __init__(self, viewer_reference, data_label, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._viewer_reference = viewer_reference
        self._data_label = data_label

    @property
    def viewer_reference(self):
        return self._viewer_reference

    @property
    def data_label(self):
        return self._data_label


class RemoveDataFromViewerMessage(Message):
    def __init__(self, viewer_reference, data_label, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._viewer_reference = viewer_reference
        self._data_label = data_label

    @property
    def viewer_reference(self):
        return self._viewer_reference

    @property
    def data_label(self):
        return self._data_label


class AddLineListMessage(Message):
    def __init__(self, table, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._table = table

    @property
    def table(self):
        return self._table


class LineIdentifyMessage(Message):
    def __init__(self, name_rest, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._name_rest = name_rest

    @property
    def name_rest(self):
        return self._name_rest


class SpectralMarksChangedMessage(Message):
    def __init__(self, marks, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._marks = marks

    @property
    def names_rest(self):
        return [m.name_rest for m in self.marks]

    @property
    def marks(self):
        return self._marks


class RedshiftMessage(Message):
    '''Messages related to Specviz redshift slider'''
    def __init__(self, param, value, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._param = param
        self._value = value

    @property
    def param(self):
        return self._param

    @property
    def value(self):
        return self._value


class RowLockMessage(Message):
    def __init__(self, is_locked, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._is_locked = is_locked

    @property
    def is_locked(self):
        return self._is_locked


class TableClickMessage(Message):
    '''Message generated by Mosviz table to zoom to object on image'''
    def __init__(self, selected_index, shared_image=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._selected_index = selected_index
        self._shared_image = shared_image

    @property
    def selected_index(self):
        return self._selected_index

    @property
    def shared_image(self):
        return self._shared_image


class SliceSelectSliceMessage(Message):
    '''Message generated by the cubeviz helper and processed by the slice plugin to sync
    slice selection across all viewers'''
    def __init__(self, slice=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._slice = slice

    @property
    def slice(self):
        return self._slice


class SliceToolStateMessage(Message):
    '''Message generated by the select slice plot plugin when activated/deactivated'''
    def __init__(self, change, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._change = change

    @property
    def change(self):
        return self._change


class LinkUpdatedMessage(Message):
    '''Message generated when the WCS/pixel linking is changed'''
    def __init__(self, link_type, wcs_use_fallback, wcs_use_affine, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._link_type = link_type
        self._wcs_use_fallback = wcs_use_fallback
        self._wcs_use_affine = wcs_use_affine

    @property
    def link_type(self):
        return self._link_type

    @property
    def wcs_use_fallback(self):
        return self._wcs_use_fallback

    @property
    def wcs_use_affine(self):
        return self._wcs_use_affine


class ExitBatchLoadMessage(Message):
    '''Message generated when exiting the outermost batch_load context manager'''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class MarkersChangedMessage(Message):
    '''Message generated when markers are added/removed from an image viewer'''
    def __init__(self, has_markers, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._has_markers = has_markers

    @property
    def has_markers(self):
        return self._has_markers


class CanvasRotationChangedMessage(Message):
    '''Message generated by canvas rotation plugin'''
    def __init__(self, viewer_id, angle, flip_horizontal, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._viewer_id = viewer_id
        self._angle = angle
        self._flip_horizontal = flip_horizontal

    @property
    def viewer_id(self):
        return self._viewer_id

    @property
    def angle(self):
        return self._angle

    @property
    def flip_horizontal(self):
        return self._flip_horizontal
