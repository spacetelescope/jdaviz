"""
Pytest plugin for skipping tests that fail due to remote network issues.

This module provides a pytest plugin that can optionally convert test
failures caused by network-related exceptions into skipped tests. This is
useful for CI environments where transient network issues shouldn't cause
test failures.

When enabled with --skip-remote-failures, the plugin:
1. Catches specific network-related exceptions (HTTPError, Timeout, etc.)
2. Converts test failures to skipped tests
3. Logs the failures to a JSON file for CI review

Usage
-----
Run pytest with the --skip-remote-failures option:

    pytest --skip-remote-failures

This will catch network exceptions and skip tests instead of failing them.
The failures are logged to .ci_artifacts/remote_failures.json for review.
"""
import json
import os

from _pytest.warning_types import PytestUnraisableExceptionWarning
from requests.exceptions import (RequestException,
                                 Timeout,
                                 ConnectionError,
                                 HTTPError)
from astropy.io.votable.exceptions import E19


# Module-level flag to track if remote skip is enabled
_remote_skip_enabled = False

# Remote exceptions to catch
REMOTE_EXCEPTIONS = (RequestException,
                     Timeout,
                     ConnectionError,
                     TimeoutError,
                     HTTPError,
                     E19,
                     PytestUnraisableExceptionWarning,
                     ExceptionGroup)


def _get_remote_failure_log_path():
    """
    Get the path to the remote failure log file.

    Writes to .ci_artifacts/ directory at repository root for access
    by GitHub Actions. This directory is gitignored and ephemeral.

    In GitHub Actions CI, uses GITHUB_WORKSPACE environment variable.
    Outside CI, searches for repository root by looking for pyproject.toml.

    Returns
    -------
    str
        Path to the remote failures JSON log file.
    """
    repo_root = None

    # In GitHub Actions, GITHUB_WORKSPACE points to repository root
    if 'GITHUB_WORKSPACE' in os.environ:
        repo_root = os.environ['GITHUB_WORKSPACE']
    else:
        # Search for repo root by looking for pyproject.toml
        current = os.path.abspath(os.getcwd())
        while current != os.path.dirname(current):  # stops at filesystem root
            if os.path.exists(os.path.join(current, 'pyproject.toml')):
                repo_root = current
                break
            current = os.path.dirname(current)

    # Fallback: use current directory
    if repo_root is None:
        repo_root = os.getcwd()

    ci_artifacts_dir = os.path.join(repo_root, '.ci_artifacts')
    # Create directory if it doesn't exist
    os.makedirs(ci_artifacts_dir, exist_ok=True)
    return os.path.join(ci_artifacts_dir, 'remote_failures.json')


def _log_remote_failure(test_name, exc_type_name, exc_message):
    """
    Log a test failure due to remote exception to a JSON file.

    The log file is written to the ignored directory .ci_artifacts so that
    GitHub Actions can read it and post a PR comment.

    Parameters
    ----------
    test_name : str
        The test node ID (full test path).
    exc_type_name : str
        The name of the exception type.
    exc_message : str
        The exception message.
    """
    log_path = _get_remote_failure_log_path()

    failures = []
    if os.path.exists(log_path):
        try:
            with open(log_path, 'r') as f:
                failures = json.load(f)
        except (json.JSONDecodeError, IOError):
            failures = []

    failures.append({'test': test_name, 'exception': exc_type_name, 'message': str(exc_message)})

    with open(log_path, 'w') as f:
        json.dump(failures, f, indent=2)


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


def remote_skip_configure(config):
    """
    Configure remote skip plugin based on command-line options.

    This function initializes the plugin settings. It should be called
    from conftest.py's pytest_configure hook.

    Parameters
    ----------
    config : pytest.Config
        The pytest configuration object.
    """
    global _remote_skip_enabled

    if config.getoption('skip_remote_failures', default=False):
        _remote_skip_enabled = True
        config._remote_skip_enabled = True


def remote_skip_runtest_makereport(item, call, report):
    """
    Handle remote data test failures.

    If --skip-remote-failures is passed, catch specific remote
    exceptions (HTTPError, Timeout, ConnectionError, etc.) and
    skip the test instead of failing. Also logs these failures to
    a JSON file for PR commenting.

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
                # Log the failure
                _log_remote_failure(item.nodeid, exc_type.__name__, str(call.excinfo.value))
                # Convert failure to skip
                msg = (f'Skipped due to remote exception: '
                       f'{exc_type.__name__}: {call.excinfo.value}')
                report.outcome = 'skipped'
                report.skip_reason = msg
