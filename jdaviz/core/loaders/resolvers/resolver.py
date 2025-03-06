import warnings
from traitlets import Bool, List, Unicode, observe

from jdaviz.core.template_mixin import PluginTemplateMixin, SelectPluginComponent, with_spinner
from jdaviz.core.registries import (loader_resolver_registry,
                                    loader_parser_registry,
                                    loader_importer_registry)
from jdaviz.core.user_api import LoaderUserApi

__all__ = ['BaseResolver', 'find_matching_resolver']


class FormatSelect(SelectPluginComponent):
    """
    Select component for the format field of a resolver.

    Parameters
    ----------
    plugin
        the parent plugin object
    items : str
        the name of the items traitlet defined in ``plugin``
    selected : str
        the name of the selected traitlet defined in ``plugin``
    default_mode : str, optional
        What mode to use when making the default selection.  Valid options: first, default_text,
        empty.
    """
    def __init__(self, plugin, items, selected, default_mode='first'):
        self._importers = {}
        super().__init__(plugin,
                         items=items,
                         selected=selected,
                         default_mode=default_mode)

    def _is_valid_item(self, item):
        return super()._is_valid_item(item, locals())

    @observe('filters')
    def _update_items(self, msg={}):
        if not self.plugin.is_valid:
            self.items = []
            self._apply_default_selection()
            return

        # check for valid parser > importer combinations given the current filters
        # and resolver inputs
        try:
            parser_input = self.plugin()
        except Exception:
            self.items = []
            self._apply_default_selection()
            return

        all_resolvers = []
        self._importers = {}
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            for parser_name, Parser in loader_parser_registry.members.items():
                this_parser = Parser(self.plugin.app, parser_input)
                try:
                    if this_parser.is_valid:
                        importer_input = this_parser()
                    else:
                        importer_input = None
                except Exception:
                    importer_input = None

                if importer_input is None:
                    continue
                for importer_name, Importer in loader_importer_registry.members.items():
                    this_importer = Importer(app=self.plugin.app, input=importer_input)
                    if this_importer.is_valid:
                        if self._is_valid_item(this_importer):
                            all_resolvers.append({'label': importer_name,
                                                  'parser': parser_name,
                                                  'importer': importer_name,
                                                  'target': this_importer.target})
                        # we'll store the importer even if it isn't valid according to the filters
                        # so that they can be used when compiling the list of target filters
                        self._importers[importer_name] = this_importer

        self.items = all_resolvers
        self._apply_default_selection()


class TargetSelect(SelectPluginComponent):
    """
    Select component for the target (filter on format) of a resolver.

    Parameters
    ----------
    plugin
        the parent plugin object
    items : str
        the name of the items traitlet defined in ``plugin``
    selected : str
        the name of the selected traitlet defined in ``plugin``
    default_mode : str, optional
        What mode to use when making the default selection.  Valid options: first, default_text,
        empty.
    """
    def __init__(self, plugin, items, selected, default_mode='first'):
        self._importers = {}
        super().__init__(plugin,
                         items=items,
                         selected=selected,
                         default_mode=default_mode)

    def _is_valid_item(self, item):
        return super()._is_valid_item(item, locals())

    def set_filter_target_in(self, targets):
        def filter_factory(targets):
            def filter_target(item):
                return item['label'] in targets
            return filter_target
        self.filters = [filter_factory(targets)]

    @observe('filters')
    def _update_items(self, msg={}):
        if not self.plugin.is_valid:
            self.items = []
            self._apply_default_selection()
            return

        # loop through choices on format and compile list of targets
        # note that the selection of a target may affect the available formats
        # so we want to store all importers in the target select even if they are not valid there
        # and use that list when compiling list of valid targets
        all_targets = list(set([importer.target for importer
                                in self.plugin.format._importers.values()]))

        all_items = [{'label': 'Any'}]+[{'label': target} for target in all_targets]
        self.items = [item for item in all_items if self._is_valid_item(item)]
        self._apply_default_selection()


class BaseResolver(PluginTemplateMixin):
    default_input = None
    requires_api_support = False

    importer_widget = Unicode().tag(sync=True)

    import_spinner = Bool(False).tag(sync=True)

    format_items_spinner = Bool(False).tag(sync=True)
    format_items = List().tag(sync=True)
    format_selected = Unicode().tag(sync=True)

    target_items = List().tag(sync=True)
    target_selected = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        self.set_active_loader_callback = kwargs.pop('set_active_loader_callback', None)
        self.open_callback = kwargs.pop('open_callback', None)
        self.close_callback = kwargs.pop('close_callback', None)
        super().__init__(*args, **kwargs)

        # subclasses should call self._update_format_items on any change
        # to user-inputs that might affect the available formats
        self.format = FormatSelect(self,
                                   items='format_items',
                                   selected='format_selected')

        self.target = TargetSelect(self,
                                   items='target_items',
                                   selected='target_selected')

    @classmethod
    def from_input(cls, app, inp, **kwargs):
        self = cls(app=app)
        if self.default_input is None:
            raise NotImplementedError("Resolver subclass must implement default_input")  # noqa pragma: nocover
        setattr(self, self.default_input, inp)
        user_api = self.user_api
        for k, v in kwargs.items():
            if hasattr(user_api, k):
                setattr(user_api, k, v)
        return self

    @property
    def is_valid(self):
        # override by subclass
        return False  # pragma: nocover

    @property
    def input(self):
        if self.default_input is None:
            raise NotImplementedError("Resolver subclass must implement default_input")
        return getattr(self, self.default_input)

    def __call__(self):
        # override by subclass - must convert any inputs into something
        # that can be interpretted by at least one parser
        # (generally a filepath, file object, or python object)
        raise NotImplementedError("Resolver subclass must implement __call__")  # pragma: nocover

    @property
    def user_api(self):
        return LoaderUserApi(self)

    @with_spinner('format_items_spinner')
    def _update_format_items(self):
        self.format._update_items()
        self.target._update_items()  # assumes format._importers is updated from above

    @property
    def importer(self):
        # give access to the importer defined by the user-selection on format
        if not self.format.selected:
            raise ValueError("must select a format before accessing importer")
        return self.format._importers[self.format.selected]

    @observe('target_selected')
    def _on_target_selected_changed(self, change={}):
        def matches_target_factory(target):
            def matches_target(importer):
                return importer.target == target
            return matches_target

        if self.target_selected == 'Any':
            self.format.filters = []
        else:
            self.format.filters = [matches_target_factory(self.target_selected)]

    @observe('format_selected')
    def _on_format_selected_changed(self, change):
        if self.format_selected == '':
            self.importer_widget = ''
        else:
            self.importer_widget = "IPY_MODEL_" + self.importer.model_id

    def close_in_tray(self, close_sidebar=False):
        """
        Close the loader in the sidebar/tray.

        Parameters
        ----------
        close_sidebar : bool
            Whether to also close the sidebar itself.
        """
        if self.close_callback is not None:
            self.close_callback()
        if close_sidebar:
            self.app.state.drawer_content = ''

    def open_in_tray(self):
        """
        Show this resolver in the sidebar tray.
        """
        if self.set_active_loader_callback is None:
            raise NotImplementedError("set_active_loader_callback must be set to open dialog to specific tab")  # noqa
        self.set_active_loader_callback(self._registry_label)
        if self.open_callback is not None:
            self.open_callback()

    @with_spinner('import_spinner')
    def vue_import_clicked(self, *args, **kwargs):
        self.importer()


def find_matching_resolver(app, inp=None, resolver=None, format=None, target=None, **kwargs):
    valid_resolvers = []
    for resolver_name, Resolver in loader_resolver_registry.members.items():
        if resolver is not None and resolver != resolver_name:
            continue
        try:
            this_resolver = Resolver.from_input(app, inp, **kwargs)
        except Exception:
            this_resolver = None
        if this_resolver is None:
            continue
        try:
            is_valid = this_resolver.is_valid
        except Exception:
            is_valid = False
        if not is_valid:
            continue

        if target is not None:
            if target not in this_resolver.target.choices:
                continue
            this_resolver.target = target
        for fmt in this_resolver.format.choices:
            if format is not None and fmt != format:
                continue
            this_resolver.format.selected = fmt
            valid_resolvers.append((this_resolver, resolver_name, fmt))

    if len(valid_resolvers) == 0:
        raise ValueError("no valid resolvers found for input")
    elif len(valid_resolvers) > 1:
        vrs = [f"resolver={vr[1]} > format={vr[2]}" for vr in valid_resolvers]
        raise ValueError(f"multiple valid resolvers found for input: {vrs}")
    else:
        return valid_resolvers[0][0].user_api
