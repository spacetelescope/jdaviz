"""
Pytest memlog plugin - log per-test memory usage.

This module provides a pytest plugin for tracking memory usage during test
execution. It supports pytest-xdist for distributed testing and provides
various sorting and filtering options for the memory report.

Usage
-----
Run pytest with the --memlog option to enable memory logging:

    pytest --memlog                       # Show default 20 tests by memory diff
    pytest --memlog 10                    # Show top 10 tests by memory diff
    pytest --memlog 10 --memlog-sort peak # Sort by peak memory
    pytest --memlog 10 --memlog-max-worker # Show worker with the highest memory
"""
import re

import numpy as np
import psutil
import pytest


# ============================================================================
# Module-level storage and dtype
# ============================================================================
_memlog_dtype = np.dtype([('worker_id', 'U20'),
                          ('nodeid', 'U256'),
                          ('uss_before', 'u8'),
                          ('uss_after', 'u8'),
                          ('uss_diff', 'i8'),
                          ('rss_before', 'u8'),
                          ('rss_after', 'u8'),
                          ('rss_diff', 'i8'),
                          ('swap_before', 'u8'),
                          ('swap_after', 'u8'),
                          ('swap_diff', 'i8')])

_header = f'{"uss_diff":>10}  {"rss_diff":>10}  {"swap_diff":>10}  '
_header_no_worker = _header + 'test'
_header_with_worker = _header + f'{"worker":>8}  test'

_memlog_records = np.array([], dtype=_memlog_dtype)
_memlog_enabled_flag = False
_default_top_n = 20


# ============================================================================
# Helper functions
# ============================================================================
def _get_memory_bytes():
    """
    Get current process memory usage.

    Returns
    -------
    numpy.void
        A structured array record with rss, swap, and uss fields in bytes.
    """
    p = psutil.Process()
    rss = p.memory_info().rss
    swap = psutil.swap_memory().used
    uss = p.memory_full_info().uss

    mem_array = np.array([(rss, swap, uss)],
                         dtype=[('rss', 'u8'), ('swap', 'u8'), ('uss', 'u8')])
    return mem_array[0]


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
    record : numpy.void
        A structured array record with memory values and worker_id.
    include_worker : bool
        If True, include the worker ID in the output.

    Returns
    -------
    str
        Formatted line for display showing uss_diff, rss_diff, swap_diff.
    """
    uss_diff = int(record['uss_diff'])
    rss_diff = int(record['rss_diff'])
    swap_diff = int(record['swap_diff'])

    result_str = (f'{_format_bytes(uss_diff):>10}  '
                  f'{_format_bytes(rss_diff):>10}  '
                  f'{_format_bytes(swap_diff):>10}  ')

    if include_worker:
        worker = record['worker_id']
        return result_str + f'{worker:>8}  {record["nodeid"]}'
    else:
        return result_str + f'{record["nodeid"]}'


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
    Extract memory properties from user_properties list into a dict.

    Parameters
    ----------
    props : list
        List of (name, value) tuples from report.user_properties.

    Returns
    -------
    dict
        Dictionary mapping property names to integer values (or string for
        worker_id). Returns empty dict if no memory data found.
    """
    values = {'worker_id': 'master',
              'uss_before': 0,
              'uss_after': 0,
              'uss_diff': 0,
              'rss_before': 0,
              'rss_after': 0,
              'rss_diff': 0,
              'swap_before': 0,
              'swap_after': 0,
              'swap_diff': 0}

    for name, value in props:
        if name in values:
            if name == 'worker_id':
                values[name] = value
            else:
                values[name] = int(value)

    # Check if we have any memory data
    has_memory_data = any(
        values[k] != 0 for k in ['uss_before', 'uss_after', 'uss_diff',
                                 'rss_before', 'rss_after', 'rss_diff',
                                 'swap_before', 'swap_after', 'swap_diff'])

    return values if has_memory_data else {}


def _apply_memlog_sort(records, sort_method, top_n):
    """
    Apply sorting to memlog records based on sort_method.

    Parameters
    ----------
    records : numpy.ndarray
        Array of memlog records.
    sort_method : str
        Sorting method: 'diff', 'before', 'after', 'peak', or 'seq'.
    top_n : int
        Number of top records to return.

    Returns
    -------
    numpy.ndarray
        Sorted records, limited to top_n items.
    """
    if len(records) == 0:
        return records

    if sort_method == 'diff':
        sort_idx = np.argsort(-records['uss_diff'])

    elif sort_method == 'before':
        sort_idx = np.argsort(-records['uss_before'])

    elif sort_method == 'after':
        sort_idx = np.argsort(-records['uss_after'])

    elif sort_method == 'peak':
        peaks = np.maximum(records['uss_before'], records['uss_after'])
        sort_idx = np.argsort(-peaks)

    elif sort_method == 'seq':
        sort_idx = np.arange(len(records) - 1, -1, -1)

    else:
        sort_idx = np.arange(len(records))

    sorted_records = records[sort_idx]
    return sorted_records[:top_n]


# ============================================================================
# Pytest hooks
# ============================================================================

def memlog_addoption(parser):
    """
    Register memlog command-line options.
    """
    group = parser.getgroup('memlog')
    group.addoption(
        '--memlog',
        action='store',
        nargs='?',
        const=str(_default_top_n),
        dest='memlog',
        default='',
        help='Enable per-test memory logging and summary.\n'
             'Usage: --memlog [N], where N is the number of top entries to display.\n'
             f'Default: {_default_top_n}')

    group.addoption(
        '--memlog-sort',
        action='store',
        dest='memlog_sort',
        default='diff',
        help=('Sorting method for memory results. Default: diff\n'
              'diff   - Sort by memory allocation difference.\n'
              'before - Sort by highest memory before test.\n'
              'after  - Sort by highest memory after test.\n'
              'peak   - Sort by highest peak memory allocation.\n'
              'seq    - Sort by test output order '
              '(can help determine sustained memory allocation).\n'
              'worker - Group by worker ID, then sort by peak memory '
              '(xdist only).'))

    group.addoption(
        '--memlog-max-worker',
        action='store_true',
        dest='memlog_max_worker',
        default=False,
        help=('Show memory report for the worker with highest peak '
              'memory allocation (xdist only).'))


def memlog_configure(config):
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

    if config.getoption('memlog') or config.getoption('memlog_max_worker'):
        config._memlog_top = config.getoption('memlog')
        config._memlog_sort = config.getoption('memlog_sort')
        config._memlog_max_worker = config.getoption('memlog_max_worker')
        _memlog_enabled_flag = True
        config._memlog_enabled = True


def memlog_runtest_setup(item):
    """
    Setup hook that records memory before test.
    """
    if not _memlog_enabled_flag:
        return
    item._mem_before = _get_memory_bytes()


def memlog_runtest_teardown(item, _):
    """
    Teardown hook that records memory after test.
    """
    if not _memlog_enabled_flag:
        return
    item._mem_after = _get_memory_bytes()


@pytest.hookimpl(hookwrapper=True)
def memlog_runtest_makereport(item, call):
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

    # Attach to user_properties - these get serialized to master in xdist
    for prefix in ('uss', 'rss', 'swap'):
        before = int(mem_before[prefix])
        after = int(mem_after[prefix])
        diff = after - before

        report.user_properties.append((f'{prefix}_before', before))
        report.user_properties.append((f'{prefix}_after', after))
        report.user_properties.append((f'{prefix}_diff', diff))

    # Get worker_id from config (xdist sets this)
    worker_id = getattr(item.config, 'workerinput', {}).get('workerid', 'master')
    report.user_properties.append(('worker_id', worker_id))


def memlog_runtest_logreport(report):
    """
    Log report hook that collects memory measurements from user_properties.

    This runs on both workers and master. On master (xdist), it receives
    the serialized user_properties from workers.
    """
    global _memlog_records

    if report.when != 'teardown':
        return

    props = getattr(report, 'user_properties', [])

    if not props:
        return

    mem_props = _extract_memlog_properties(props)
    if not mem_props:
        return

    # Build record tuple in dtype field order
    record_values = (mem_props['worker_id'],
                     getattr(report, 'nodeid', '<unknown>'),
                     mem_props['uss_before'],
                     mem_props['uss_after'],
                     mem_props['uss_diff'],
                     mem_props['rss_before'],
                     mem_props['rss_after'],
                     mem_props['rss_diff'],
                     mem_props['swap_before'],
                     mem_props['swap_after'],
                     mem_props['swap_diff'])

    record = np.array([record_values], dtype=_memlog_dtype)
    _memlog_records = np.append(_memlog_records, record)


def memlog_terminal_summary(terminalreporter, config=None):
    """
    Terminal summary hook that prints memlog summary.
    """
    if config is None:
        config = terminalreporter.config

    if not getattr(config, '_memlog_enabled', False):
        return

    if len(_memlog_records) == 0:
        terminalreporter.write_line('memlog: no records collected.')
        return

    top_n = getattr(config, '_memlog_top', '20')
    if isinstance(top_n, str):
        if top_n.isdigit():
            top_n = int(top_n)
        else:
            top_n = 20
    elif not isinstance(top_n, int):
        top_n = 20

    # Filter records with valid uss_diff (no null/nan checks needed with arrays)
    records = _memlog_records[_memlog_records['uss_diff'] != 0]

    if len(records) == 0:
        terminalreporter.write_line('memlog: no records collected.')
        return

    sort_method = getattr(config, '_memlog_sort', 'diff')

    # If max worker is requested, find and report on the worker with
    # the highest peak memory allocation
    if getattr(config, '_memlog_max_worker', False):
        _display_max_worker_report(terminalreporter, records, top_n)
        return

    # Group by worker_id if sorting by worker
    if sort_method == 'worker':
        _display_worker_grouped_report(terminalreporter, records, top_n)
    else:
        _display_standard_report(terminalreporter, records, sort_method, top_n)

    # Display peak memory usage across all tests
    _display_peak_usage(terminalreporter, records)

    terminalreporter.write_sep('-', 'end of memlog summary')


def _display_max_worker_report(terminalreporter, records, top_n):
    """
    Display memory report for the worker with the highest peak memory.

    Parameters
    ----------
    terminalreporter : TerminalReporter
        The pytest terminal reporter.
    records : numpy.ndarray
        Array of memlog records.
    top_n : int
        Number of top records to display.
    """
    if len(records) == 0:
        terminalreporter.write_line('memlog: no worker found with memory data.')
        return

    # Find the worker with the highest peak uss memory across all tests
    # using vectorized operations
    peaks = np.maximum(records['uss_before'], records['uss_after'])
    max_idx = np.argmax(peaks)
    max_peak = int(peaks[max_idx])
    max_worker = records[max_idx]['worker_id']

    # Filter to only this worker's records
    worker_records = records[records['worker_id'] == max_worker]

    # Apply the selected sort method to worker records
    worker_records = _apply_memlog_sort(worker_records, 'seq', top_n)

    title = (f'Top {top_n} tests for worker {max_worker} '
             f'(highest peak uss: {_format_bytes(max_peak)})')
    terminalreporter.write_sep('-', title)

    terminalreporter.write_line(_header_no_worker)

    for r in worker_records:
        terminalreporter.write_line(_format_memlog_line(r))

    # Display peak memory usage across all tests
    _display_peak_usage(terminalreporter, records)

    terminalreporter.write_sep('-', 'end of memlog summary')


def _display_worker_grouped_report(terminalreporter, records, top_n):
    """
    Display memory report grouped by worker ID.

    Parameters
    ----------
    terminalreporter : TerminalReporter
        The pytest terminal reporter.
    records : numpy.ndarray
        Array of memlog records.
    top_n : int
        Number of top records to display per worker.
    """
    if len(records) == 0:
        return

    # Get unique worker IDs and sort them numerically
    unique_workers = np.unique(records['worker_id'])
    sorted_workers = sorted(unique_workers, key=_parse_worker_id)

    # Display results grouped by worker
    title = f'Top {top_n} tests by worker, sorted by peak memory'
    terminalreporter.write_sep('-', title)

    for worker_id in sorted_workers:
        # Filter records for this worker
        worker_records = records[records['worker_id'] == worker_id]
        # Sort within worker group
        worker_records = _apply_memlog_sort(worker_records, 'seq', top_n)

        terminalreporter.write_line(f'\nWorker: {worker_id}')
        terminalreporter.write_line(_header_with_worker)

        for r in worker_records[:top_n]:
            terminalreporter.write_line(_format_memlog_line(r, include_worker=True))


def _display_standard_report(terminalreporter, records, sort_method, top_n):
    """
    Display standard memory report with selected sorting.

    Parameters
    ----------
    terminalreporter : TerminalReporter
        The pytest terminal reporter.
    records : numpy.ndarray
        Array of memlog records.
    sort_method : str
        Sorting method: 'diff', 'before', 'after', 'peak', or 'seq'.
    top_n : int
        Number of top records to display.
    """
    # Apply the selected sort method to all records
    records = _apply_memlog_sort(records, sort_method, top_n)

    title = f'Top {top_n} tests by memory difference'
    terminalreporter.write_sep('-', title)

    terminalreporter.write_line(_header_with_worker)

    for r in records:
        terminalreporter.write_line(_format_memlog_line(r, include_worker=True))


def _calculate_peak_usage(records):
    """
    Calculate peak memory usage across all records using vectorized operations.

    Parameters
    ----------
    records : numpy.ndarray
        Array of memlog records.

    Returns
    -------
    dict
        Dictionary with 'uss', 'rss', 'swap' peak values.
    """
    if len(records) == 0:
        return {'uss': 0, 'rss': 0, 'swap': 0}

    # Use vectorized operations to find max peaks for each memory type
    peaks = {}
    for prefix in ('uss', 'rss', 'swap'):
        before = records[f'{prefix}_before']
        after = records[f'{prefix}_after']
        peaks[prefix] = int(np.maximum(before, after).max())

    return peaks


def _display_peak_usage(terminalreporter, records):
    """
    Display peak memory usage summary.

    Parameters
    ----------
    terminalreporter : TerminalReporter
        The pytest terminal reporter.
    records : numpy.ndarray
        Array of memlog records.
    """
    peak = _calculate_peak_usage(records)

    terminalreporter.write_line('')
    terminalreporter.write_line('Peak memory usage across all tests:')
    terminalreporter.write_line(f'  USS:  {_format_bytes(peak["uss"])}')
    terminalreporter.write_line(f'  RSS:  {_format_bytes(peak["rss"])}')
    terminalreporter.write_line(f'  Swap: {_format_bytes(peak["swap"])}')
