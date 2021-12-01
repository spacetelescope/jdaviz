import time
import threading
from collections import deque
import os
from ipyvue import watch


__all__ = []


class SnackbarQueue:
    '''
    Class that performs the role of VSnackbarQueue, which is not
    implemented in ipyvuetify.
    '''
    def __init__(self):
        self.queue = deque()
        self.first = True

    def put(self, state, msg):
        if len(self.queue) == 0:
            self._write_message(state, msg)

        if not msg.loading:
            self.queue.appendleft(msg)

    def close_current_message(self, state):

        # turn off snackbar and remove corresponding
        # message from  queue.
        state.snackbar['show'] = False
        if len(self.queue) > 0:
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
        state.snackbar['timeout'] = 0  # timeout controlled by thread
        state.snackbar['loading'] = msg.loading
        state.snackbar['show'] = True

        if msg.loading:
            return

        # timeout of the first message needs to be increased by a
        # few seconds to account for the time spent in page rendering.
        # A more elegant way to address this should be via a callback
        # from a vue hook such as  mounted(). It doesn't work though.
        # Since this entire queue effort is temporary anyway (pending
        # the implementation of VSnackbarQueue in ipyvuetify, it's
        # better to keep the solution contained all in one place here.
        timeout = msg.timeout
        if self.first:
            timeout += 5000
            self.first = False

        def sleep_function(timeout):
            timeout_ = float(timeout) / 1000
            time.sleep(timeout_)
            self.close_current_message(state)

        x = threading.Thread(target=sleep_function,
                             args=(timeout,),
                             daemon=True)
        x.start()


def enable_hot_reloading():
    try:
        watch(os.path.dirname(__file__))
    except ModuleNotFoundError:
        print((
            'Watchdog module, needed for hot reloading, not found.'
            ' Please install with `pip install watchdog`'))
