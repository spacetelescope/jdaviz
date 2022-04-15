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
        # track whether we're showing a loading message which won't clear by timeout,
        # but instead requires another message with msg.loading = False to clear
        self.loading = False
        # track whether this is the first message - we'll increase the timeout for that
        # to give time for the app to load.
        self.first = True

    def put(self, state, msg):
        if msg.loading:
            # immediately show the loading message indefinitely until cleared by a new message
            # with loading=False (or overwritten by a new indefinite message with loading=True)
            self.loading = True
            self._write_message(state, msg)
        elif self.loading:
            # clear the loading state, immediately show this message, then re-enter the queue
            self.loading = False
            self._write_message(state, msg)
        else:
            self.queue.append(msg)
            if len(self.queue) == 1:
                self._write_message(state, msg)

    def close_current_message(self, state):

        if self.loading:
            # then we've been interrupted, so keep this item in the queue to show after
            # loading is complete
            return

        # turn off snackbar iteself
        state.snackbar['show'] = False

        if len(self.queue) > 0:
            # determine if the closed entry came from the queue (not an interrupt)
            # in which case we should remove it from the queue.  We clear here instead
            # of when creating the snackbar so that items that are interrupted
            # (ie by a loading message) will reappear again at the top of the queue
            # so they are not missed
            msg = self.queue[0]
            if msg.text == state.snackbar['text']:
                _ = self.queue.popleft()

        # in case there are messages in the queue still,
        # display the next.
        if len(self.queue) > 0:
            msg = self.queue[0]
            self._write_message(state, msg)

    def _write_message(self, state, msg):

        state.snackbar['show'] = False
        state.snackbar['text'] = msg.text
        state.snackbar['color'] = msg.color
        # TODO: in vuetify >2.3, timeout should be set to -1 to keep open
        #  indefinitely
        state.snackbar['timeout'] = 0  # timeout controlled by thread
        state.snackbar['loading'] = msg.loading
        state.snackbar['show'] = True

        if msg.loading:
            # do not create timeout - the message will be indefinite until
            # cleared by another message
            return

        # timeout of the first message needs to be increased by a
        # few seconds to account for the time spent in page rendering.
        # A more elegant way to address this should be via a callback
        # from a vue hook such as  mounted(). It doesn't work though.
        # Since this entire queue effort is temporary anyway (pending
        # the implementation of VSnackbarQueue in ipyvuetify, it's
        # better to keep the solution contained all in one place here.
        timeout = msg.timeout
        if timeout < 500:
            # half-second minimum timeout
            timeout = 500
        if self.first:
            timeout += 5000
            self.first = False

        # create the timeout function which will close this message and
        # show the next message if one has been added to the queue since
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
