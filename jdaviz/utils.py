import os
from queue import Queue

from traitlets import Unicode

from echo import DictCallbackProperty


__all__ = ['load_template']


def load_template(file_name, path=None, traitlet=True):
    """
    Load a vue template file and instantiate the appropriate traitlet object.

    Parameters
    ----------
    file_name : str
        The name of the template file.
    path : str
        The path to where the template file is stored. If none is given,
        assumes the directory where the python file calling this function
        resides.

    Returns
    -------
    `Unicode`
        The traitlet object used to hold the vue code.
    """
    path = os.path.dirname(path)

    with open(os.path.join(path, file_name)) as f:
        TEMPLATE = f.read()

    if traitlet:
        return Unicode(TEMPLATE)

    return TEMPLATE


class SnackbarQueue:

    def __init__(self):
        self.queue = Queue()

    def put(self, state, msg):

        if self.queue.empty():
            state.snackbar['show'] = False
            state.snackbar['text'] = msg.text
            state.snackbar['color'] = msg.color
            state.snackbar['timeout'] = msg.timeout
            state.snackbar['loading'] = msg.loading
            state.snackbar['show'] = True

        self.queue.put(msg)