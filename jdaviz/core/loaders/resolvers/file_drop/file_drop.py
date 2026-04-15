import io
import os
import sys

import IPython
import ipyvuetify.extra.file_input as _ipyvuetify_file_input
import reacton
from astropy.table import Table as astropyTable
from ipywidgets import widget_serialization
from solara import FileDropMultiple
from traitlets import Any, Int

from jdaviz.core.loaders.resolvers import BaseResolver
from jdaviz.core.registries import loader_resolver_registry
from jdaviz.core.user_api import LoaderUserApi


def _patch_process_messages():
    """Patch ipyvuetify's ``process_messages`` for compatibility with ipykernel >= 7.

    When a file is dropped, ipyvuetify reads file data by sending chunk requests
    to the browser and waiting for the replies to arrive as comm messages.
    ``process_messages`` is called in that wait loop to manually pump pending
    kernel messages so the chunk replies are delivered.

    ipykernel >= 7 removed ``msg_queue`` and ``do_one_iteration`` (the APIs used
    to pump messages), and made ``_parent_header`` a read-only property.  The
    upstream implementation in ipyvuetify references all three, causing file drop
    to fail silently on the first drop and raise ``AttributeError`` on any
    subsequent drop.

    In ipykernel >= 7, comm messages are delivered automatically on a dedicated
    shell-channel thread, so manual pumping is unnecessary.  The replacement
    detects which kernel generation is present and either returns immediately
    (>= 7) or preserves the original drain-the-queue behaviour (< 7).
    """
    async def _process_messages():
        ipython = IPython.get_ipython()
        if ipython is None or not hasattr(ipython, 'kernel'):
            return

        kernel = ipython.kernel

        # ipykernel >= 7: comm messages arrive on a dedicated shell-channel
        # thread, so no manual pumping is needed.
        if not hasattr(kernel, 'msg_queue'):
            return

        # ipykernel < 7: manually drain pending messages, restoring the kernel's
        # execution context afterwards so that output (print, display, execution
        # count) is attributed to the correct cell.
        original_parent_ident = kernel._parent_ident
        original_parent_header = kernel._parent_header
        original_set_parent = ipython.set_parent

        def _set_parent_sink(*args):
            pass

        try:
            ipython.set_parent = _set_parent_sink
            while not kernel.msg_queue.empty():
                await kernel.do_one_iteration()
        finally:
            kernel.set_parent(original_parent_ident, original_parent_header)
            sys.stdout.parent_header = original_parent_header
            sys.stderr.parent_header = original_parent_header
            ipython.display_pub.parent_header = original_parent_header
            ipython.set_parent = original_set_parent

    _ipyvuetify_file_input.process_messages = _process_messages


_patch_process_messages()


@loader_resolver_registry('file drop')
class FileDropResolver(BaseResolver):
    template_file = __file__, "file_drop.vue"

    progress = Int(100).tag(sync=True)
    nfiles = Int(0).tag(sync=True)
    file_drop_widget = Any().tag(sync=True, **widget_serialization)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._file_info = None

        self.file_drop_widget_el = FileDropMultiple(label="Drop file here",
                                                    on_total_progress=self._on_total_progress,
                                                    on_file=self._on_file_updated,
                                                    lazy=False)
        self.file_drop_widget, rc = reacton.render(self.file_drop_widget_el)

    @property
    def user_api(self):
        return LoaderUserApi(self, expose=[])

    @property
    def is_valid(self):
        return True

    @property
    def default_label(self):
        # Use the first file name as the default label, if available.
        # Otherwise, return None.
        if self._file_info and 'name' in self._file_info:
            return os.path.splitext(self._file_info['name'])[0]
        return None

    def _parsed_input_to_table(self, parsed_input):
        # support loading in from file drop resolver
        for format in ('csv', 'ascii', 'fits', 'votable'):
            try:
                parsed_input = astropyTable.read(parsed_input, format=format)
                return parsed_input
            except Exception:  # nosec
                pass
        return None

    def _on_total_progress(self, progress):
        self.progress = progress

    def _on_file_updated(self, file_infos):
        self.nfiles = len(file_infos)
        self._file_info = file_infos[0]
        self._resolver_input_updated()
        self._update_format_items()
        self.progress = 100

    @property
    def output(self):
        result = self.parsed_input
        if hasattr(result, 'seek'):
            result.seek(0)
        return result

    def parse_input(self):
        # this will return a bytes object of the file contents
        return io.BytesIO(self._file_info.get('data'))
