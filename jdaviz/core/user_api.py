import astropy.units as u

__all__ = ['UserApiWrapper', 'PluginUserApi', 'ViewerUserApi']

_internal_attrs = ('_obj', '_expose', '_readonly', '__doc__')


class UserApiWrapper:
    """
    This is an API wrapper around an internal object.  For a full list of attributes/methods,
    call dir(object).
    """
    def __init__(self, obj, expose=[], readonly=[]):
        self._obj = obj
        self._expose = list(expose) + list(readonly)
        self._readonly = readonly
        if obj.__doc__ is not None:
            self.__doc__ = self.__doc__ + "\n\n\n" + obj.__doc__

    def __dir__(self):
        return self._expose

    def __repr__(self):
        return self._obj.__repr__()

    def __eq__(self, other):
        return self._obj.__eq__(other)

    def __getattr__(self, attr):
        if attr in _internal_attrs or attr not in self._expose:
            return super().__getattribute__(attr)

        exp_obj = getattr(self._obj, attr)
        return getattr(exp_obj, 'user_api', exp_obj)

    def __setattr__(self, attr, value):
        if attr in _internal_attrs:
            return super().__setattr__(attr, value)
        if attr not in self._expose:
            raise ValueError(f"{attr} is not a valid attribute and cannot be set")

        if attr in self._readonly:
            raise AttributeError("cannot set read-only item")

        exp_obj = getattr(self._obj, attr)
        if hasattr(exp_obj, '__call__'):
            raise AttributeError(f"{attr} is a callable, cannot set to a value.  See help({attr}) for input arguments.")  # noqa
        from jdaviz.core.template_mixin import (SelectPluginComponent,
                                                UnitSelectPluginComponent,
                                                PlotOptionsSyncState,
                                                AddResults,
                                                AutoTextField)
        if isinstance(exp_obj, SelectPluginComponent):
            # this allows setting the selection directly without needing to access the underlying
            # .selected traitlet
            if isinstance(exp_obj, UnitSelectPluginComponent) and isinstance(value, u.Unit):
                value = value.to_string()
            exp_obj.selected = value
            return
        elif isinstance(exp_obj, AddResults):
            exp_obj.auto_label.value = value
            return
        elif isinstance(exp_obj, AutoTextField):
            exp_obj.value = value
            return
        elif isinstance(exp_obj, PlotOptionsSyncState):
            if not len(exp_obj.linked_states):
                raise ValueError("there are currently no synced glue states to set")

            # this allows setting the value immediately, and unmixing state, if appropriate,
            # even if the value matches the current value
            if value == exp_obj.value:
                exp_obj.unmix_state()
            else:
                # if there are choices, allow either passing the text or value
                text_to_value = {choice['text']: choice['value']
                                 for choice in exp_obj.sync.get('choices', [])}
                exp_obj.value = text_to_value.get(value, value)
            return

        return setattr(self._obj, attr, value)


class PluginUserApi(UserApiWrapper):
    """
    This is an API wrapper around an internal plugin.  For a full list of attributes/methods,
    call dir(plugin_object) and for help on any of those methods,
    call help(plugin_object.attribute).

    For example::
      help(plugin_object.show)
    """
    def __init__(self, plugin, expose=[], readonly=[]):
        expose = list(set(list(expose) + ['open_in_tray', 'close_in_tray', 'show']))
        if plugin.uses_active_status:
            expose += ['keep_active', 'as_active']
        super().__init__(plugin, expose, readonly)

    def __repr__(self):
        return f'<{self._obj._registry_label} API>'


class ViewerUserApi(UserApiWrapper):
    """
    This is an API wrapper around a viewer.  For a full list of attributes/methods,
    call dir(viewer_object) and for help on any of those methods,
    call help(viewer_object.attribute).

    For example::
      help(viewer_object.show)
    """
    def __init__(self, viewer, expose=[], readonly=[]):
        expose = list(set(list(expose) + []))
        super().__init__(viewer, expose, readonly)

    def __repr__(self):
        return f'<{self._obj._ref_or_id} API>'
