"""Utility function for working with asyncio and widgets."""
import asyncio
import time
import logging
import threading

from jupyter_ui_poll import ui_events

from typing import Callable
import ipywidgets
from asyncio import Queue
import queue
import solara
import solara.lab

logger = logging.getLogger(__name__)

# instead of a single global variable, this makes it kernel
# scoped in solara
_serial_task_queue = solara.lab.computed(Queue)


# analogous to asyncio.create_task, except, they will be called in sequence
def create_serial_task(coro):
    serial_task_run_task.get()  # ensure task runner is running
    _serial_task_queue.value.put_nowait(coro)


async def serial_task_run():
    logger.debug("serial_task_run: starting")
    while True:
        try:
            logger.debug("serial_task_run: getting task from queue")
            task = await _serial_task_queue.value.get()
            logger.debug("serial_task_run: got task from queue, running it")
            await task
        except Exception:
            logger.exception("Task failed")
        finally:
            _serial_task_queue.value.task_done()


@solara.lab.computed
def serial_task_run_task():
    event_loop_queue = queue.Queue()

    def runner():
        try:
            event_loop = asyncio.new_event_loop()
            event_loop_queue.put(event_loop)

            async def tick():
                while True:
                    await asyncio.sleep(0.1)

            # not sure why we need this
            event_loop.run_until_complete(tick())
            # event_loop.run_until_complete(serial_task_run())
            # but this doesn't work?
            # event_loop.run_forever() doesn't work?
        except Exception:
            logger.exception("Task running thread failed")

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    event_loop = event_loop_queue.get()
    event_loop.create_task(serial_task_run())
    logger.debug(f"serial_task_run_task: created event loop: {event_loop}")
    return event_loop


def wait_for_change(widget: ipywidgets.Widget, trait_name: str):
    # based on https://ipywidgets.readthedocs.io/en/latest/examples/Widget%20Asynchronous.html
    future = asyncio.Future()

    def getvalue(change):
        logger.debug(
            f"got new value for {trait_name} for widget {widget} new value {change.new}"
        )
        future.set_result(change.new)
        widget.unobserve(getvalue, trait_name)

    logger.debug(f"observing {trait_name} for widget {type(widget)}")
    widget.observe(getvalue, trait_name)
    return future


async def queue_screenshot_async(widget, method, *args, **kwargs):
    logger.debug("queue_screenshot_async: starting")
    # queue with just 1 item, the callback data
    data_queue = Queue()

    def callback_wrapper(data):
        logger.debug(
            "queue_screenshot_async: callback_wrapper: putting result in queue"
        )
        try:
            data_queue.put_nowait(data)
        except Exception:
            logger.exception("Failed to put data in queue")

    # calls Figure.get_svg_data or something similar
    method(callback_wrapper, *args, **kwargs)
    return await data_queue.get()


def queue_screenshot_sync(
    widget, method, callback, on_timeout, timeout=5, *args, **kwargs
):
    # queue with just 1 item, the callback data
    data_queue = Queue()

    def callback_wrapper(data):
        data_queue.put_nowait(data)

    async def execute():
        # calls Figure.get_svg_data or something similar
        method(callback_wrapper, *args, **kwargs)
        try:
            data = await asyncio.wait_for(data_queue.get(), timeout=timeout)
        except TimeoutError:
            on_timeout()
        callback(data)

    create_serial_task(execute())


def run_kernel_events_blocking_until(
    condition: Callable[[], bool], timeout: float = 5, sleep: float = 0.1
):
    """Executes kernel events while the condition is true or the timeout is reached.

    Used to block in the notebook while we wait for a widget result.
    """
    start_time = time.time()
    with ui_events() as poll:
        while condition():
            poll(10)  # process up to 10 UI events per iteration
            time.sleep(sleep)
            if time.time() - start_time > timeout:
                raise TimeoutError(
                    f"Timeout waiting for condition to be true after {timeout} seconds"
                )
