from traitlets import List, Unicode, observe

from jdaviz.core.template_mixin import PluginTemplateMixin, SelectPluginComponent
from jdaviz.core.registries import loader_parser_registry, loader_importer_registry

__all__ = ['BaseResolver']


class FormatSelect(SelectPluginComponent):
    def __init__(self, plugin, items, selected, default_mode='first'):
        """
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
        super().__init__(plugin,
                         items=items,
                         selected=selected,
                         default_mode=default_mode)

    def _is_valid_item(self, item):
        return super()._is_valid_item(item, locals())

    @observe('filters')
    def _update_items(self, msg={}):
        # print("*** Format._update_items")
        if not self.plugin.is_valid:
            self.items = []
            self._apply_default_selection()
            return

        # check for valid parser > importer combinations given the current filters
        # and resolver inputs
        parser_input = self.plugin()

        all_resolvers = []
        for parser_name, Parser in loader_parser_registry.members.items():
            this_parser = Parser(parser_input)
            # print("*** parser name: ", parser_name, this_parser.is_valid)
            if this_parser.is_valid:
                importer_input = this_parser()
                for importer_name, Importer in loader_importer_registry.members.items():
                    this_importer = Importer(app=self.plugin.app, input=importer_input)
                    # print("*** importer name: ", importer_name, this_importer.is_valid)
                    if this_importer.is_valid and self._is_valid_item(this_importer):
                        all_resolvers.append({'label': importer_name,
                                              'parser': parser_name,
                                              'importer': importer_name})
        self.items = all_resolvers
        self._apply_default_selection()


class BaseResolver(PluginTemplateMixin):
    format_items = List().tag(sync=True)
    format_selected = Unicode().tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # subclasses should call self.format._update_items on any change
        # to user-inputs that might affect the available formats
        self.format = FormatSelect(self,
                                   items='format_items',
                                   selected='format_selected')
        #self.target

    @property
    def is_valid(self):
        # override by subclass
        return False

    def __call__(self):
        # override by subclass - must convert any inputs into something
        # that can be interpretted by at least one parser
        # (generally a filepath, file object, or python object)
        raise NotImplementedError("Resolver subclass must implement __call__")

    @property
    def importer(self):
        # give access to the importer defined by the user-selection on format
        if not self.format.selected:
            raise ValueError("must select a format before accessing importer")
        return loader_importer_registry.members.get(self.format.selected)