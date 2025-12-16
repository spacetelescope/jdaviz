"""
Pytest memlog plugin - log per-test memory usage.

This module provides a pytest plugin for tracking memory usage during test
execution. It supports pytest-xdist for distributed testing and provides
various sorting and filtering options for the memory report.

Memory metrics tracked:
- USS (Unique Set Size): Private memory used by the process
- RSS (Resident Set Size): All physical memory used by the process
- Swap: Swap memory used by the system during test execution

The primary focus is on combined USS + Swap as the key metric for memory
allocation during tests.

Usage
-----
Run pytest with the --memlog option to enable memory logging:

    pytest --memlog                         # Show default 20 tests by USS+Swap diff
    pytest --memlog 10                      # Show top 10 tests by USS+Swap diff
    pytest --memlog 10 --memlog-sort peak   # Sort by peak USS+Swap memory
    pytest --memlog 10 --memlog-max-worker  # Show worker with highest peak memory
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

_full_header = (f'{"uss_before":>12}  {"uss_after":>12}  {"uss_diff":>10}  '
                f'{"rss_before":>12}  {"rss_after":>12}  {"rss_diff":>10}  '
                f'{"swap_before":>12}  {"swap_after":>12}  {"swap_diff":>10}  ')
_after_header = (f'{"uss_after":>12}  '
                 f'{"rss_after":>12}  '
                 f'{"swap_after":>12}  ')
_diff_header = f'{"uss_diff":>10}  {"rss_diff":>10}  {"swap_diff":>10}  '
_full_header_no_worker = _full_header + 'test'
_full_header_with_worker = _full_header + f'{"worker":>8}  test'
_after_header_no_worker = _after_header + 'test'
_after_header_with_worker = _after_header + f'{"worker":>8}  test'

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
    mf = p.memory_full_info()
    swap = getattr(mf, 'swap', 0) or 0
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


def _format_memlog_line(record, header='full', include_worker=False):
    """
    Format a memlog record as a display line matching header templates.

    Parameters
    ----------
    record : numpy.void
        A structured array record with memory values and worker_id.
    full_header : bool, optional
        If True (default), display all before/after/diff values.
        If False, display only diff values (uss_diff, rss_diff, swap_diff).
    include_worker : bool, optional
        If True, include the worker ID in the output. Default is False.
    after_only : bool, optional
        If True, display only after values. Default is False.

    Returns
    -------
    str
        Formatted line for display showing memory values aligned with headers.
    """
    # Extract values from record
    uss_before = int(record['uss_before'])
    uss_after = int(record['uss_after'])
    uss_diff = int(record['uss_diff'])
    rss_before = int(record['rss_before'])
    rss_after = int(record['rss_after'])
    rss_diff = int(record['rss_diff'])
    swap_before = int(record['swap_before'])
    swap_after = int(record['swap_after'])
    swap_diff = int(record['swap_diff'])

    # Format all columns matching _full_header layout
    result_str = (f'{_format_bytes(uss_before):>10}  ',
                  f'{_format_bytes(uss_after):>10}  ',
                  f'{_format_bytes(uss_diff):>10}  ',
                  f'{_format_bytes(rss_before):>10}  ',
                  f'{_format_bytes(rss_after):>10}  ',
                  f'{_format_bytes(rss_diff):>10}  ',
                  f'{_format_bytes(swap_before):>10}  ',
                  f'{_format_bytes(swap_after):>10}  ',
                  f'{_format_bytes(swap_diff):>10}  ')

    if header == 'full':
        result_str = ''.join(result_str)
    elif header == 'after':
        # After only
        result_str = result_str[1] + result_str[4] + result_str[7]
    elif header == 'diff':
        # Diffs only
        result_str = result_str[2] + result_str[5] + result_str[8]

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

    All methods that reference USS implicitly include the combined USS + Swap
    metric as the primary indicator of memory allocation.

    Parameters
    ----------
    records : numpy.ndarray
        Array of memlog records.
    sort_method : str
        Sorting method:
        - 'diff': Sort by USS + Swap difference (memory allocated during test)
        - 'before': Sort by highest USS before test
        - 'after': Sort by highest USS after test
        - 'peak': Sort by highest peak combined USS + Swap
        - 'seq': Reverse chronological order (test execution order)
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
        combined_diffs = records['uss_diff'] + records['swap_diff']
        sort_idx = np.argsort(-combined_diffs)

    elif sort_method == 'before':
        sort_idx = np.argsort(-records['uss_before'])

    elif sort_method == 'after':
        sort_idx = np.argsort(-records['uss_after'])

    elif sort_method == 'peak':
        uss_peaks = np.maximum(records['uss_before'], records['uss_after'])
        swap_peaks = np.maximum(records['swap_before'], records['swap_after'])
        combined_peaks = uss_peaks + swap_peaks
        sort_idx = np.argsort(-combined_peaks)

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
        help=('Sorting method for memory (USS + Swap) results. Default: diff\n'
              'diff   - Sort by USS + Swap difference (memory allocated during test).\n'
              'before - Sort by highest USS before test.\n'
              'after  - Sort by highest USS after test.\n'
              'peak   - Sort by highest peak combined USS + Swap.\n'
              'seq    - Sort by test execution order (helps identify sustained memory).\n'
              'worker - Group by worker ID (xdist only), then sort by peak USS + Swap.'))

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
    The user_properties are serialized and sent to master in xdist. We track
    USS, RSS, and Swap for each test, though the analysis focuses on
    USS + Swap as the primary memory allocation metric.
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


def _display_max_worker_report(terminalreporter, records, top_n):
    """
    Display memory report for the worker with the highest peak memory.

    Identifies the worker that had the highest peak combined USS + Swap memory
    allocation across all tests, then displays all that worker's tests in
    execution order.

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

    # Find the worker with the highest peak USS + Swap memory across all tests
    # using vectorized operations
    uss_peaks = np.maximum(records['uss_before'], records['uss_after'])
    swap_peaks = np.maximum(records['swap_before'], records['swap_after'])
    combined_peaks = uss_peaks + swap_peaks
    max_idx = np.argmax(combined_peaks)
    max_peak = int(combined_peaks[max_idx])
    max_worker = records[max_idx]['worker_id']

    # Filter to only this worker's records
    worker_records = records[records['worker_id'] == max_worker]

    # Sort by execution order (seq) to see memory allocation pattern
    worker_records = _apply_memlog_sort(worker_records, 'seq', top_n)

    title = (f'Top {top_n} tests for worker {max_worker}, in sequence order '
             f'(highest peak USS + Swap: {_format_bytes(max_peak)})')
    terminalreporter.write_sep('-', title)

    terminalreporter.write_line(_full_header_no_worker)

    for r in worker_records:
        terminalreporter.write_line(_format_memlog_line(r))

    # Display peak memory usage across all tests
    _display_peak_usage(terminalreporter, records)

    terminalreporter.write_sep('-', 'end of memlog summary')


def _display_worker_grouped_report(terminalreporter, records, top_n):
    """
    Display memory report grouped by worker ID and sorted by test execution.

    This report shows the top N tests for each worker in the order they were
    executed, making it easier to identify memory leaks or accumulated memory
    allocation over the test sequence for each worker.

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

    # Display results grouped by worker in execution order
    title = f'Top {top_n} tests by worker, in test execution order'
    terminalreporter.write_sep('-', title)

    for worker_id in sorted_workers:
        # Filter records for this worker and sort by execution order (seq)
        worker_records = records[records['worker_id'] == worker_id]
        worker_records = _apply_memlog_sort(worker_records, 'seq', top_n)

        terminalreporter.write_line(f'\nWorker: {worker_id}')
        terminalreporter.write_line(_full_header_with_worker)

        for r in worker_records[:top_n]:
            terminalreporter.write_line(_format_memlog_line(r, include_worker=True))


def _display_standard_report(terminalreporter, records, sort_method, top_n):
    """
    Display standard memory report with selected sorting.

    Displays all memory before/after/diff values aligned with the full header
    template. Sorting is based on the USS + Swap combined metric.

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

    # Create descriptive title based on sort method
    sort_titles = {
        'diff': 'by USS + Swap difference',
        'before': 'by USS before test',
        'after': 'by USS after test',
        'peak': 'by peak USS + Swap',
        'seq': 'by test execution order'
    }
    sort_desc = sort_titles.get(sort_method, 'by memory difference')
    title = f'Top {top_n} tests {sort_desc}'
    terminalreporter.write_sep('-', title)

    terminalreporter.write_line(_diff_header)

    for r in records:
        terminalreporter.write_line(_format_memlog_line(r, header='diff', include_worker=True))


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
    Display peak memory usage summary across all workers.

    Identifies and displays the test(s) that reached the highest combined USS +
    Swap memory allocation (peak value) in each worker. Shows the test with
    maximum memory usage for each worker separately.

    Parameters
    ----------
    terminalreporter : TerminalReporter
        The pytest terminal reporter.
    records : numpy.ndarray
        Array of memlog records.
    """
    if len(records) == 0:
        return

    terminalreporter.write_line('')
    terminalreporter.write_line('Peak memory usage (maximum USS + Swap per worker):')

    # Get unique worker IDs and sort them numerically
    unique_workers = np.unique(records['worker_id'])
    sorted_workers = sorted(unique_workers, key=_parse_worker_id)

    terminalreporter.write_line(_full_header_with_worker)

    # For each worker, find the test with the maximum combined peak
    for worker_id in sorted_workers:
        worker_records = records[records['worker_id'] == worker_id]

        # Calculate peak values for this worker's tests
        uss_swap_before = worker_records['uss_before'] + worker_records['swap_before']
        uss_swap_after = worker_records['uss_after'] + worker_records['swap_after']
        combined_peaks = np.maximum(uss_swap_before, uss_swap_after)

        # Find the test with the maximum combined peak in this worker
        max_idx = np.argmax(combined_peaks)
        peak_record = worker_records[max_idx]

        terminalreporter.write_line(_format_memlog_line(peak_record,
                                                        include_worker=True))


def _display_final_usage(terminalreporter, records):
    """
    Display final memory usage summary of final tests in all workers.

    Shows the memory state (after the test, before teardown) of the last test
    executed in each worker, helping identify final memory footprint across
    distributed workers.

    Parameters
    ----------
    terminalreporter : TerminalReporter
        The pytest terminal reporter.
    records : numpy.ndarray
        Array of memlog records.
    """
    if len(records) == 0:
        return

    terminalreporter.write_line('')
    terminalreporter.write_line('Final memory usage '
                                '(last test in each worker, after test execution):')

    # Get unique worker IDs and sort them numerically
    unique_workers = np.unique(records['worker_id'])
    sorted_workers = sorted(unique_workers, key=_parse_worker_id)

    terminalreporter.write_line(_after_header_with_worker)

    # For each worker, get the last test executed (highest index in execution order)
    for worker_id in sorted_workers:
        worker_records = records[records['worker_id'] == worker_id]
        # The last record for this worker is the one with the highest index
        last_record = worker_records[-1]
        terminalreporter.write_line(_format_memlog_line(last_record,
                                                        header='after',
                                                        include_worker=True))


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

    if len(_memlog_records) == 0:
        terminalreporter.write_line('memlog: no records collected.')
        return

    sort_method = getattr(config, '_memlog_sort', 'diff')

    # If max worker is requested, find and report on the worker with
    # the highest peak memory allocation
    if getattr(config, '_memlog_max_worker', False):
        _display_max_worker_report(terminalreporter, _memlog_records, top_n)

    else:
        # Group by worker_id if sorting by worker
        if sort_method == 'worker':
            _display_worker_grouped_report(terminalreporter, _memlog_records, top_n)
        else:
            _display_standard_report(terminalreporter, _memlog_records, sort_method, top_n)

    # Display peak memory usage across all tests
    _display_peak_usage(terminalreporter, _memlog_records)

    # Display final memory usage of last test in each worker
    _display_final_usage(terminalreporter, _memlog_records)

    terminalreporter.write_sep('-', 'end of memlog summary')
