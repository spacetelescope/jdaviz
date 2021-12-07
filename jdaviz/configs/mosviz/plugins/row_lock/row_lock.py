from traitlets import Bool

from jdaviz.core.registries import tool_registry
from jdaviz.core.template_mixin import TemplateMixin
from jdaviz.core.events import RowLockMessage

__all__ = ['RowLock']


@tool_registry('g-row-lock')
class RowLock(TemplateMixin):
    template_file = __file__, "row_lock.vue"
    is_locked = Bool(False).tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Watch for messages from Specviz helper redshift functions
        self.session.hub.subscribe(self, RowLockMessage,
                                   handler=self._row_lock_changed)

    def _row_lock_changed(self, msg):
        self.is_locked = msg.is_locked

    def vue_toggle_lock(self, event):
        # Send the RowLockMessage which will update is_locked in _row_lock_changed
        # but will also set the application state in the Mosviz helper
        msg = RowLockMessage(not self.is_locked, sender=self)
        self.app.hub.broadcast(msg)
