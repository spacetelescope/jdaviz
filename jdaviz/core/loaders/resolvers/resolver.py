import warnings
from contextlib import contextmanager
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
    debug = Bool(False).tag(sync=True)

    def __init__(self, plugin, items, selected, default_mode='first'):
        self._invalid_importers = {}
        self._importers = {}
        super().__init__(plugin,
                         items=items,
                         selected=selected,
                         default_mode=default_mode)

    def _is_valid_item(self, item):
        return super()._is_valid_item(item, locals())

    @observe('filters', 'debug')
    def _update_items(self, msg={}):
        if not self.plugin.is_valid:
            self.items = []
            self._apply_default_selection()
            return

        all_resolvers = []
        self._dbg_parsers = {}
        self._dbg_importers = {}
        self._invalid_importers = {}
        self._importers = {}

        # check for valid parser > importer combinations given the current filters
        # and resolver inputs
        try:
            # NOTE: plugin is just because this inherits from SelectPluginComponent,
            # but is actually the resolver.  This calls the implemented __call__ method
            # on the parent resolver.
            parser_input = self.plugin()
        except Exception as e:
            self.items = []
            self._invalid_importers = f'resolver exception: {e}'
            self._apply_default_selection()
            return

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            for parser_name, Parser in loader_parser_registry.members.items():
                this_parser = Parser(self.plugin.app, parser_input)
                if self.debug:
                    self._dbg_parsers[parser_name] = this_parser
                try:
                    if this_parser.is_valid:
                        importer_input = this_parser()
                    else:
                        self._invalid_importers[parser_name] = 'not valid'
                        importer_input = None
                except Exception as e:
                    self._invalid_importers[parser_name] = f'parser exception: {e}'
                    importer_input = None

                if importer_input is None:
                    self._invalid_importers.setdefault(parser_name, 'importer_input is None')
                    continue
                for importer_name, Importer in loader_importer_registry.members.items():
                    label = f"{parser_name} > {importer_name}"
                    try:
                        this_importer = Importer(app=self.plugin.app,
                                                 resolver=self.plugin,
                                                 input=importer_input)
                    except Exception as e:  # nosec
                        self._invalid_importers[label] = f'importer exception: {e}'
                        continue
                    if self.debug:
                        self._dbg_importers[label] = this_importer
                    if (self.plugin._restrict_to_target is not None and
                            this_importer.target['label'] != self.plugin._restrict_to_target):
                        # skip importers that do not match the target
                        self._invalid_importers[label] = 'not matching target'
                        continue
                    if this_importer.is_valid:
                        if self._is_valid_item(this_importer):
                            item = {'label': importer_name,
                                    'parser': parser_name,
                                    'importer': importer_name,
                                    'target': this_importer.target}
                            parser_pref = this_importer.parser_preference
                            if importer_name not in self._importers:
                                all_resolvers.append(item)
                            elif not len(parser_pref) or parser_name not in parser_pref:
                                # default to the previous (or first) found match
                                continue
                            else:
                                # then there was already a match from an earlier parser.  Compare
                                # to see which has preference and replace if necessary.
                                item_importers = [i['importer'] for i in all_resolvers]
                                item_index = item_importers.index(importer_name)
                                prev_parser = all_resolvers[item_index]['parser']
                                parser_pref = this_importer.parser_preference
                                if (prev_parser not in parser_pref or
                                        parser_pref.index(prev_parser) > parser_pref.index(parser_name)):  # noqa
                                    # this parser has preference over the previous one
                                    all_resolvers[item_index] = item
                                else:
                                    # this previous parser has preference over this one
                                    continue

                        # we'll store the importer even if it isn't valid according to the filters
                        # so that they can be used when compiling the list of target filters
                        self._importers[importer_name] = this_importer
                    else:
                        self._invalid_importers[label] = 'not valid'

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
        all_targets = []
        for importer in self.plugin.format._importers.values():
            target = importer.target
            if target not in all_targets:
                all_targets.append(target)

        self.items = [{'label': 'Any'}] + [item for item in all_targets if self._is_valid_item(item)]  # noqa
        self._apply_default_selection()


class BaseResolver(PluginTemplateMixin):
    _defer_update_format_items = False  # only use via defer_update_format_items contex manager
    default_input = None
    default_input_cast = None
    requires_api_support = False

    importer_widget = Unicode().tag(sync=True)
    import_disabled = Bool(False).tag(sync=True)
    import_spinner = Bool(False).tag(sync=True)

    format_items_spinner = Bool(False).tag(sync=True)
    format_items = List().tag(sync=True)
    format_selected = Unicode().tag(sync=True)
    valid_import_formats = Unicode().tag(sync=True)

    target_items = List().tag(sync=True)
    target_selected = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        self.set_active_loader_callback = kwargs.pop('set_active_loader_callback', None)
        self.open_callback = kwargs.pop('open_callback', None)
        self.close_callback = kwargs.pop('close_callback', None)
        self._restrict_to_target = kwargs.pop('restrict_to_target', None)
        super().__init__(*args, **kwargs)

        # subclasses should call self._update_format_items on any change
        # to user-inputs that might affect the available formats
        self.format = FormatSelect(self,
                                   items='format_items',
                                   selected='format_selected')

        self.target = TargetSelect(self,
                                   items='target_items',
                                   selected='target_selected')

    @contextmanager
    def defer_update_format_items(self):
        """
        Context manager to delay updating format items until multiple traitlets have been set.
        """
        self._defer_update_format_items = True
        try:
            yield
        finally:
            self._defer_update_format_items = False
            self._update_format_items()

    @classmethod
    def from_input(cls, app, inp, **kwargs):
        self = cls(app=app)
        if self.default_input is None:
            raise NotImplementedError("Resolver subclass must implement default_input")  # noqa pragma: nocover
        with self.defer_update_format_items():
            setattr(self, self.default_input,
                    self.default_input_cast(inp) if self.default_input_cast else inp)
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

    @property
    def default_label(self):
        # override by subclass to provide a default label to the importer
        # importers can then decide whether to use this or not.
        return None

    @with_spinner('format_items_spinner')
    def _update_format_items(self):
        if self._defer_update_format_items:
            return
        # NOTE: this will result in a call to the implemented __call__ on the resolver
        self.format._update_items()
        self.target._update_items()  # assumes format._importers is updated from above
        # ensure the importer updates even if the format selection remains fixed
        self._on_format_selected_changed()

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
                return importer.target.get('label', '') == target
            return matches_target

        if self._restrict_to_target is not None:
            self.format.filters = [matches_target_factory(self._restrict_to_target)]
        elif self.target_selected == 'Any':
            self.format.filters = []
        else:
            self.format.filters = [matches_target_factory(self.target_selected)]

    def _get_valid_import_formats(self):
        if self._restrict_to_target is not None:
            # if the resolver was initialized with a list of valid import formats,
            # use that instead of the registry
            return [self._restrict_to_target]
        # fallback on all items available in the registry
        return loader_importer_registry.members.keys()

    @observe('format_selected')
    def _on_format_selected_changed(self, change={}):
        if self.format_selected == '':
            self.importer_widget = ''

            if (hasattr(self.format._invalid_importers, 'keys') and
               self.format._invalid_importers.keys()) and self.target_selected:
                # if no valid importer for format_selected, provide supported sources/formats
                # to user in a warning message
                self.valid_import_formats = ", ".join(self._get_valid_import_formats())
        else:
            self.importer_widget = "IPY_MODEL_" + self.importer.model_id
            self.valid_import_formats = ''

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
    formats = format if isinstance(format, list) else [format]
    invalid_resolvers = {}
    valid_resolvers = []
    for resolver_name, Resolver in loader_resolver_registry.members.items():
        if resolver_name == 'file drop':
            # no API input, so let's avoid always returning the confusing
            # message that default_input is undefined
            continue
        if resolver is not None and resolver != resolver_name:
            invalid_resolvers[resolver_name] = f'not {resolver}'
            continue
        try:
            this_resolver = Resolver.from_input(app, inp, **kwargs)
        except Exception as e:  # nosec
            invalid_resolvers[resolver_name] = f'resolver exception: {e}'
            if resolver_name == 'url' and 'timeout' in str(e):
                raise e
            continue
        try:
            is_valid = this_resolver.is_valid
        except Exception as e:  # nosec
            invalid_resolvers[resolver_name] = f'is_valid exception: {e}'
            is_valid = False
        if not is_valid:
            invalid_resolvers.setdefault(resolver_name, 'not valid')
            continue

        if target is not None:
            try:
                this_resolver.target = target
            except ValueError:
                invalid_resolvers[resolver_name] = this_resolver.format._invalid_importers
                continue
        if not len(this_resolver.format.items):
            invalid_resolvers[resolver_name] = this_resolver.format._invalid_importers
            continue
        for fmt_item in this_resolver.format.items:
            if (format is not None
                and not any([format in (fmt_item['label'],
                                        fmt_item['parser'],
                                        fmt_item['importer'])
                             for format in formats])):
                invalid_resolvers[resolver_name] = this_resolver.format._invalid_importers
                continue
            this_resolver.format.selected = fmt_item['label']
            valid_resolvers.append((this_resolver, resolver_name, fmt_item['label']))

    if len(valid_resolvers) == 0:
        raise ValueError("no valid loaders found for input, tried", invalid_resolvers)
    elif len(valid_resolvers) > 1:
        vrs = [f"resolver={vr[1]} > format={vr[2]}" for vr in valid_resolvers]
        raise ValueError(f"multiple valid loaders found for input: {vrs}")
    else:
        return valid_resolvers[0][0].user_api
