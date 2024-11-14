import astropy.units as u
from glue.core.message import Message

__all__ = ['NewViewerMessage', 'ViewerAddedMessage', 'ViewerRemovedMessage', 'LoadDataMessage',
           'AddDataMessage', 'SnackbarMessage', 'RemoveDataMessage',
           'AddLineListMessage', 'RowLockMessage',
           'SliceSelectSliceMessage', 'SliceValueUpdatedMessage',
           'SliceToolStateMessage',
           'TableClickMessage', 'LinkUpdatedMessage', 'ExitBatchLoadMessage',
           'AstrowidgetMarkersChangedMessage', 'MarkersPluginUpdate',
           'GlobalDisplayUnitChanged', 'ChangeRefDataMessage',
           'PluginTableAddedMessage', 'PluginTableModifiedMessage',
           'PluginPlotAddedMessage', 'PluginPlotModifiedMessage',
           'IconsUpdatedMessage']


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


class ViewerRenamedMessage(Message):
    """Message emitted after a viewer is destroyed by the application."""
    def __init__(self, old_viewer_ref, new_viewer_ref, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._old_viewer_ref = old_viewer_ref
        self._new_viewer_ref = new_viewer_ref

    @property
    def old_viewer_ref(self):
        return self._old_viewer_ref

    @property
    def new_viewer_ref(self):
        return self._new_viewer_ref


class LoadDataMessage(Message):
    def __init__(self, path, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._path = path

    @property
    def path(self):
        return self._path


class AddDataMessage(Message):
    """
    Emitted AFTER data is added to a viewer
    """
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
    def __init__(self, data, viewer, viewer_id=None, old=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._data = data
        self._viewer = viewer
        self._viewer_id = viewer_id
        self._old = old

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
    """
    Emitted to request data is added to a viewer (BEFORE the data is actually added)
    """
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
    def __init__(self, value, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._value = value

    @property
    def value(self):
        return self._value


class SliceValueUpdatedMessage(Message):
    '''Message generated by the slice plugin when the selected slice is updated'''
    def __init__(self, value, value_unit, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.value = value
        self.value_unit = value_unit


class SliceToolStateMessage(Message):
    '''Message generated by the select slice plot plugin when activated/deactivated'''
    def __init__(self, change, viewer, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._change = change
        self._viewer = viewer

    @property
    def change(self):
        return self._change

    @property
    def viewer(self):
        return self._viewer


class LinkUpdatedMessage(Message):
    '''Message generated when the WCS/pixel linking is changed'''
    def __init__(self, link_type, wcs_use_fallback, wcs_fast_approximation, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._link_type = link_type
        self._wcs_use_fallback = wcs_use_fallback
        self._wcs_fast_approximation = wcs_fast_approximation

    @property
    def link_type(self):
        return self._link_type

    @property
    def wcs_use_fallback(self):
        return self._wcs_use_fallback

    @property
    def wcs_fast_approximation(self):
        return self._wcs_fast_approximation


class ExitBatchLoadMessage(Message):
    '''Message generated when exiting the outermost batch_load context manager'''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class AstrowidgetMarkersChangedMessage(Message):
    '''Message generated when markers are added/removed from an image viewer via astrowidgets API'''
    def __init__(self, has_markers, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._has_markers = has_markers

    @property
    def has_markers(self):
        return self._has_markers


class MarkersPluginUpdate(Message):
    '''Message when the length of the markers plugin table changes'''
    def __init__(self, table_length, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.table_length = table_length


class GlobalDisplayUnitChanged(Message):
    '''Message generated when the (x or y axis) unit of the spectrum viewer is
    changed, which is used app-wide to inform display units that depend on the
    unit choice and flux<>sb toggle of the spectrum viewer.'''

    def __init__(self, axis, unit, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._axis = axis
        self._unit = unit

    @property
    def axis(self):
        return self._axis

    @property
    def unit(self):
        return u.Unit(self._unit)


class PluginTableAddedMessage(Message):
    '''Message generated when a plugin table is initialized'''
    def __init__(self, sender):
        super().__init__(sender)

    @property
    def table(self):
        return self.sender

    @property
    def plugin(self):
        return self.sender._plugin


class PluginTableModifiedMessage(PluginTableAddedMessage):
    '''Message generated when the items in a plugin table are changed'''
    def __init__(self, sender):
        super().__init__(sender)


class PluginPlotAddedMessage(Message):
    '''Message generated when a plugin plot is initialized'''
    def __init__(self, sender):
        super().__init__(sender)

    @property
    def plot(self):
        return self.sender

    @property
    def plugin(self):
        return self.sender._plugin


class PluginPlotModifiedMessage(PluginPlotAddedMessage):
    '''Message generated when the items in a plugin plot are changed'''
    def __init__(self, sender):
        super().__init__(sender)


class IconsUpdatedMessage(Message):
    '''Message generated when the viewer or layer icons are updated'''
    def __init__(self, icon_type, icons, **kwargs):
        # icon_type = 'layer' or 'viewer'
        super().__init__(**kwargs)
        self.icon_type = icon_type
        # icons might be a CallbackDict, cast to ensure its a dictionary
        self.icons = dict(icons)
