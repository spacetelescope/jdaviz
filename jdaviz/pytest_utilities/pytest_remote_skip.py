"""
Pytest plugin for skipping tests that fail due to remote network issues.

This module provides a pytest plugin that can optionally convert test
failures caused by network-related exceptions into skipped tests. This is
useful for CI environments where transient network issues shouldn't cause
test failures.

When enabled with --skip-remote-failures, the plugin:
1. Catches specific network-related exceptions/warnings (HTTPError, Timeout, etc.)
2. Converts test failures to skipped tests

Usage
-----
Run pytest with the --skip-remote-failures option:

    pytest --skip-remote-failures

This will catch network exceptions and skip tests instead of failing them.
"""
from _pytest.warning_types import PytestUnraisableExceptionWarning
from requests.exceptions import (RequestException,
                                 Timeout,
                                 ConnectionError,
                                 HTTPError)
from astropy.io.votable.exceptions import E19

# Remote exceptions to catch
REMOTE_EXCEPTIONS = (RequestException,
                     Timeout,
                     ConnectionError,
                     TimeoutError,
                     HTTPError,
                     E19,
                     PytestUnraisableExceptionWarning,
                     ExceptionGroup)


def remote_skip_addoption(parser):
    """
    Register command-line option for remote failure skipping.

    Parameters
    ----------
    parser : pytest.Parser
        The pytest argument parser.
    """
    parser.addoption(
        '--skip-remote-failures',
        action='store_true',
        default=False,
        help='Skip remote failures due to network issues.')


def remote_skip_runtest_makereport(item, call, report):
    """
    Handle remote data test failures.

    If --skip-remote-failures is passed, catch specific remote
    exceptions (HTTPError, Timeout, ConnectionError, etc.) and
    skip the test instead of failing.

    Parameters
    ----------
    item : pytest.Item
        The test item.
    call : pytest.CallInfo
        The call information.
    report : pytest.TestReport
        The test report object.
    """
    # Only process call phase (not setup/teardown) failures
    if report.when == 'call' and report.failed and item.config.getoption(
            'skip_remote_failures', default=False):
        # Check if failure is due to a remote exception
        if call.excinfo is not None:
            exc_type = call.excinfo.type
            if issubclass(exc_type, REMOTE_EXCEPTIONS):
                # Convert failure to skip
                msg = (f'Skipped due to remote exception: '
                       f'{exc_type.__name__}: {call.excinfo.value}')
                report.outcome = 'skipped'
                report.skip_reason = msg
