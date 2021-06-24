import os
import time
import threading
from collections import deque

from traitlets import Unicode


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
        self.queue = deque()

    def put(self, state, msg):

        if len(self.queue) == 0:
            self._write_message(state, msg)

        self.queue.appendleft(msg)

    def close_current_message(self, state):

        # turn off snackbar and remove corresponding
        # message from  queue.
        state.snackbar['show'] = False
        _ = self.queue.pop()

        # in case there are messages in the queue still,
        # display the next.
        if len(self.queue) > 0:
            msg = self.queue.pop()
            self.queue.append(msg)
            self._write_message(state, msg)

    def _write_message(self, state, msg):
        state.snackbar['show'] = False
        state.snackbar['text'] = msg.text
        state.snackbar['color'] = msg.color
        state.snackbar['timeout'] = 0
        state.snackbar['loading'] = msg.loading
        state.snackbar['show'] = True

        def sleep_function(timeout):
            timeout_ = float(timeout) / 1000
            time.sleep(timeout_)
            self.close_current_message(state)

        x = threading.Thread(target=sleep_function,
                             args=(msg.timeout,),
                             daemon=True)
        x.start()

