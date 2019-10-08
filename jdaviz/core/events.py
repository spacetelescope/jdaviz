from glue.core.message import Message


class NewViewerMessage(Message):
    def __init__(self, cls, data, x_attr, *args, **kwargs):
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
