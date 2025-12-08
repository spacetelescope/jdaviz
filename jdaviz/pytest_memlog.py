"""
Pytest memlog plugin - log per-test memory usage.

This module provides a pytest plugin for tracking memory usage during test
execution. It supports pytest-xdist for distributed testing and provides
various sorting and filtering options for the memory report.

Usage
-----
Run pytest with the --memlog option to enable memory logging:

    pytest --memlog 10                    # Show top 10 tests by memory diff
    pytest --memlog 10 --memlog-sort peak # Sort by peak memory
    pytest --memlog 10 --memlog-max-worker # Show worker with highest memory

To use this plugin, import and register the hooks in your conftest.py:

    from jdaviz.pytest_memlog import (
        pytest_addoption as memlog_addoption,
        pytest_configure as memlog_configure,
        pytest_runtest_setup as memlog_runtest_setup,
        pytest_runtest_teardown as memlog_runtest_teardown,
        pytest_runtest_makereport as memlog_runtest_makereport,
        pytest_runtest_logreport as memlog_runtest_logreport,
        pytest_terminal_summary as memlog_terminal_summary,
    )
"""
import re
from itertools import groupby

import psutil
import pytest


# ============================================================================
# Module-level storage
# ============================================================================
_memlog_records = []
_memlog_enabled_flag = False


# ============================================================================
# Helper functions
# ============================================================================
def _get_memory_bytes():
    """
    Return the current process resident set size (RSS) in bytes.
    """
    return psutil.Process().memory_info().rss


def _format_bytes(b):
    """
    Format byte count as human-readable string with MiB unit.
    """
    mib = b / (1024.0 * 1024.0)
    return f'{mib:7.2f} MiB'


def _format_memlog_line(record, include_worker=False):
    """
    Format a memlog record as a display line.

    Parameters
    ----------
    record : dict
        A memlog record with 'mem_diff', 'mem_before', 'mem_after',
        'worker_id', and 'nodeid' keys.
    include_worker : bool
        If True, include the worker ID in the output.

    Returns
    -------
    str
        Formatted line for display.
    """
    diff = record['mem_diff'] or 0
    before = record['mem_before'] or 0
    after = record['mem_after'] or 0

    if include_worker:
        worker = record.get('worker_id') or 'master'
        return (f'{_format_bytes(diff):>10}  '
                f'{_format_bytes(before):>10}  '
                f'{_format_bytes(after):>10}  '
                f'{worker:>8}  {record["nodeid"]}')
    else:
        return (f'{_format_bytes(diff):>10}  '
                f'{_format_bytes(before):>10}  '
                f'{_format_bytes(after):>10}  {record["nodeid"]}')


def _parse_worker_id(worker_id):
    """
    Parse worker_id into a sortable tuple.

    For xdist worker IDs like 'gw0', 'gw1', etc., returns
    (prefix, number). For 'master', returns ('~', 0) to sort
    last. Ensures numerical ordering within each prefix.

    Parameters
    ----------
    worker_id : str
        The worker ID string to parse.

    Returns
    -------
    tuple
        A (prefix, number) tuple suitable for sorting.
    """
    if worker_id == 'master':
        return '~', 0
    match = re.match(r'([a-z]+)(\d+)', worker_id)
    if match:
        prefix, number = match.groups()
        return prefix, int(number)
    return worker_id, 0


def _extract_memlog_properties(props):
    """
    Extract memory properties from user_properties list.

    Parameters
    ----------
    props : list
        List of (name, value) tuples from report.user_properties.

    Returns
    -------
    dict or None
        Dictionary with 'mem_before', 'mem_after', 'mem_diff', and
        'worker_id' keys, or None if no memory data found.
    """
    mem_before = None
    mem_after = None
    mem_diff = None
    worker_id = None

    for name, value in props:
        if name == 'mem_before':
            mem_before = int(value)
        elif name == 'mem_after':
            mem_after = int(value)
        elif name == 'mem_diff':
            mem_diff = int(value)
        elif name == 'worker_id':
            worker_id = value

    # Return None if no memory data found
    if mem_before is None and mem_after is None and mem_diff is None:
        return None

    return {'mem_before': mem_before,
            'mem_after': mem_after,
            'mem_diff': mem_diff,
            'worker_id': worker_id}


def _apply_memlog_sort(records, sort_method, top_n):
    """
    Apply sorting to memlog records based on sort_method.

    Parameters
    ----------
    records : list
        List of memlog record dictionaries.
    sort_method : str
        Sorting method: 'diff', 'before', 'after', 'peak', or 'seq'.
    top_n : int
        Number of top records to return.

    Returns
    -------
    list
        Sorted records, limited to top_n items.
    """
    if sort_method == 'diff':
        records.sort(key=lambda r: r['mem_diff'], reverse=True)

    elif sort_method == 'before':
        records.sort(key=lambda r: r['mem_before'], reverse=True)

    elif sort_method == 'after':
        records.sort(key=lambda r: r['mem_after'], reverse=True)

    elif sort_method == 'peak':
        records.sort(key=lambda r: max(r['mem_before'], r['mem_after']),
                     reverse=True)

    elif sort_method == 'seq':
        # Keep original order but reverse for display purposes
        records = records[::-1]

    return records[:top_n]


# ============================================================================
# Pytest hooks
# ============================================================================

def pytest_addoption(parser):
    """
    Register memlog command-line options.
    """
    group = parser.getgroup('memlog')
    group.addoption(
        '--memlog',
        action='store',
        dest='memlog',
        default='10',
        help='Enable per-test memory logging and summary. Default: 10')

    group.addoption(
        '--memlog-sort',
        action='store',
        dest='memlog_sort',
        default='diff',
        help=(
            'Sorting method for memory results. Default: diff\n'
            'diff   - Sort by memory allocation difference.\n'
            'before - Sort by highest memory before test.\n'
            'after  - Sort by highest memory after test.\n'
            'peak   - Sort by highest peak memory allocation.\n'
            'seq    - Sort by test output order '
            '(can help determine sustained memory allocation).\n'
            'worker - Group by worker ID, then sort by peak memory '
            '(xdist only).\n'))

    group.addoption(
        '--memlog-max-worker',
        action='store_true',
        dest='memlog_max_worker',
        default=False,
        help=('Show memory report for the worker with highest peak '
              'memory allocation (xdist only).'))


def pytest_configure(config):
    """
    Configure memlog based on command-line options.

    This function initializes the memlog plugin settings. It should be
    called from conftest.py's pytest_configure hook.

    Parameters
    ----------
    config : pytest.Config
        The pytest configuration object.
    """
    global _memlog_enabled_flag

    if len(config.getoption('memlog')) > 0:
        config._memlog_top = int(config.getoption('memlog'))
        config._memlog_sort = config.getoption('memlog_sort')
        config._memlog_max_worker = config.getoption('memlog_max_worker')
        _memlog_enabled_flag = True
        config._memlog_enabled = True


def pytest_runtest_setup(item):
    """
    Setup hook that records memory before test.
    """
    if not _memlog_enabled_flag:
        return
    mem = _get_memory_bytes()
    item._mem_before = mem


def pytest_runtest_teardown(item, nextitem):
    """
    Teardown hook that records memory after test.
    """
    if not _memlog_enabled_flag:
        return
    mem = _get_memory_bytes()
    item._mem_after = mem


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Hook wrapper to attach memory measurements to report user_properties.

    This runs during report creation when we still have access to the item.
    The user_properties are serialized and sent to master in xdist.
    """
    outcome = yield
    report = outcome.get_result()

    if call.when != 'teardown':
        return

    if not _memlog_enabled_flag:
        return

    mem_before = getattr(item, '_mem_before', None)
    mem_after = getattr(item, '_mem_after', None)

    if mem_before is None or mem_after is None:
        return

    diff = int(mem_after) - int(mem_before)

    # Get worker_id from config (xdist sets this)
    worker_id = getattr(item.config, 'workerinput', {}).get('workerid', 'master')

    # Attach to user_properties - these get serialized to master in xdist
    report.user_properties.append(('mem_before', int(mem_before)))
    report.user_properties.append(('mem_after', int(mem_after)))
    report.user_properties.append(('mem_diff', int(diff)))
    report.user_properties.append(('worker_id', worker_id))


def pytest_runtest_logreport(report):
    """
    Log report hook that collects memory measurements from user_properties.

    This runs on both workers and master. On master (xdist), it receives
    the serialized user_properties from workers.
    """
    if report.when != 'teardown':
        return

    props = getattr(report, 'user_properties', [])

    if not props:
        return

    mem_props = _extract_memlog_properties(props)
    if mem_props is None:
        return

    _memlog_records.append({'nodeid': getattr(report, 'nodeid', '<unknown>'),
                            'worker_id': mem_props['worker_id'],
                            'when': report.when,
                            'mem_before': mem_props['mem_before'],
                            'mem_after': mem_props['mem_after'],
                            'mem_diff': mem_props['mem_diff']})


def pytest_terminal_summary(terminalreporter, config=None):
    """
    Terminal summary hook that prints memlog summary.
    """
    if config is None:
        config = terminalreporter.config

    if not getattr(config, '_memlog_enabled', False):
        return

    if not _memlog_records:
        terminalreporter.write_line('memlog: no records collected.')
        return

    top_n = getattr(config, '_memlog_top', 10)
    records = [r for r in _memlog_records if r.get('mem_diff') is not None]

    sort_method = getattr(config, '_memlog_sort', 'diff')

    # If max worker is requested, find and report on the worker with
    # highest peak memory allocation
    if getattr(config, '_memlog_max_worker', False):
        _display_max_worker_report(terminalreporter, records, sort_method, top_n)
        return

    # Group by worker_id if sorting by worker
    if sort_method == 'worker':
        _display_worker_grouped_report(terminalreporter, records, top_n)
    else:
        _display_standard_report(terminalreporter, records, sort_method, top_n)

    terminalreporter.write_sep('-', 'end of memlog summary')


def _display_max_worker_report(terminalreporter, records, top_n):
    """
    Display memory report for the worker with highest peak memory.

    Parameters
    ----------
    terminalreporter : TerminalReporter
        The pytest terminal reporter.
    records : list
        List of memlog record dictionaries.
    sort_method : str
        Sorting method for the worker's records.
    top_n : int
        Number of top records to display.
    """
    # Find the worker with the highest peak memory across all tests
    max_worker = None
    max_peak = -1

    for r in records:
        worker_id = r.get('worker_id') or 'master'
        peak = max(r['mem_before'], r['mem_after'])
        if peak > max_peak:
            max_peak = peak
            max_worker = worker_id

    if max_worker is None:
        terminalreporter.write_line('memlog: no worker found with memory data.')
        return

    # Filter to only this worker's records
    worker_records = [r for r in records if (r.get('worker_id') or 'master') == max_worker]

    # Apply the selected sort method to worker records
    worker_records = _apply_memlog_sort(worker_records, 'seq', top_n)

    title = (f'Top {top_n} tests for worker {max_worker} '
             f'(highest peak memory: {_format_bytes(max_peak)})')
    terminalreporter.write_sep('-', title)

    header = f'{"mem diff":>10}  {"before":>10}  {"after":>10}  test'
    terminalreporter.write_line(header)

    for r in worker_records:
        terminalreporter.write_line(_format_memlog_line(r))

    terminalreporter.write_sep('-', 'end of memlog summary')


def _display_worker_grouped_report(terminalreporter, records, top_n):
    """
    Display memory report grouped by worker ID.

    Parameters
    ----------
    terminalreporter : TerminalReporter
        The pytest terminal reporter.
    records : list
        List of memlog record dictionaries.
    top_n : int
        Number of top records to display per worker.
    """
    # Sort records by worker_id first (with numerical sorting)
    records.sort(key=lambda r: _parse_worker_id(r.get('worker_id') or 'master'))

    # Group by worker_id
    grouped = {}
    for worker_id, group_records in (
            groupby(records, key=lambda r: r.get('worker_id') or 'master')):
        # Within each worker, sort by sequential order
        grouped[worker_id] = _apply_memlog_sort(list(group_records), 'seq', top_n)

    # Display results grouped by worker
    title = f'Top {top_n} tests by worker, sorted by peak memory'
    terminalreporter.write_sep('-', title)

    header = (f'{"mem diff":>10}  {"before":>10}  {"after":>10}  '
              f'{"worker":>8}  test')

    # Sort worker_ids numerically for display
    sorted_worker_ids = sorted(grouped.keys(), key=_parse_worker_id)

    for worker_id in sorted_worker_ids:
        terminalreporter.write_line(f'\nWorker: {worker_id}')
        terminalreporter.write_line(header)

        for r in grouped[worker_id][:top_n]:
            terminalreporter.write_line(_format_memlog_line(r, include_worker=True))


def _display_standard_report(terminalreporter, records, sort_method, top_n):
    """
    Display standard memory report with selected sorting.

    Parameters
    ----------
    terminalreporter : TerminalReporter
        The pytest terminal reporter.
    records : list
        List of memlog record dictionaries.
    sort_method : str
        Sorting method: 'diff', 'before', 'after', 'peak', or 'seq'.
    top_n : int
        Number of top records to display.
    """
    # Apply the selected sort method to all records
    records = _apply_memlog_sort(records, sort_method, top_n)

    title = f'Top {top_n} tests by memory difference'
    terminalreporter.write_sep('-', title)

    header = (f'{"mem diff":>10}  {"before":>10}  {"after":>10}  '
              f'{"worker":>8}  test')
    terminalreporter.write_line(header)

    for r in records:
        terminalreporter.write_line(_format_memlog_line(r, include_worker=True))
