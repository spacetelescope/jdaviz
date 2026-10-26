"""Combine JUnit XML reports from several pytest runs into a single summary.

Used in CI where the test suite is split across several pytest invocations
via pytest-split, so that all results and failures are listed in one place
at the end of the log. The summary is printed to stdout and, when available,
appended to the GitHub Actions job summary ($GITHUB_STEP_SUMMARY).

Usage: python .github/scripts/pytest_summary.py [--title TITLE] REPORT.xml [REPORT.xml ...]
"""
import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

# Keep each failure on a single, reasonably short line in the summary
MAX_MESSAGE_LENGTH = 300
# Cap the failure list so a widespread breakage doesn't flood the log or the
# job summary (GitHub limits $GITHUB_STEP_SUMMARY to 1 MiB per step)
MAX_PROBLEMS = 100

# (column header, outcome key) pairs, in display order
COLUMNS = [('Passed', 'passed'), ('Failed', 'failed'), ('Errors', 'error'),
           ('Skipped', 'skipped'), ('Total', 'total')]
# Per-test outcomes, least to most severe
OUTCOME_SEVERITY = ['passed', 'skipped', 'error', 'failed']


def first_line(elem):
    """One-line, length-capped description of a failure or error element."""
    # The "message" attribute is the short reason. The element text holds the
    # full traceback and is only used as a fallback
    message = (elem.get('message') or elem.text or '').strip()
    message = message.splitlines()[0] if message else ''
    if len(message) > MAX_MESSAGE_LENGTH:
        message = message[:MAX_MESSAGE_LENGTH] + '...'
    return message


def summarize_report(path):
    """Read one JUnit XML report.

    Returns ``(counts, problems)``: ``counts`` is a Counter keyed by the outcome
    keys in ``COLUMNS``, and ``problems`` is a list of one-line
    ``FAILED``/``ERROR`` descriptions.
    """
    root = ET.parse(path).getroot()
    outcomes = {}
    problems = []
    for case in root.iter('testcase'):
        # classname is the dotted module (and class) path, e.g.
        # "jdaviz.core.tests.test_foo.TestBar", not a file path
        node = f"{case.get('classname', '')}::{case.get('name', '')}"
        # remove the leading junk from tox
        node = node.split('site-packages.')[-1]
        failure, error = case.find('failure'), case.find('error')
        if failure is not None:
            outcome = 'failed'
        elif error is not None:
            outcome = 'error'
        elif case.find('skipped') is not None:  # includes xfail
            outcome = 'skipped'
        else:
            outcome = 'passed'

        previous = outcomes.get(node, outcome)
        outcomes[node] = max(previous, outcome, key=OUTCOME_SEVERITY.index)

        # List every failure and error, including both for a double-reported test.
        for label, elem in (('FAILED', failure), ('ERROR', error)):
            if elem is not None:
                problems.append(f'{label} {node} - {first_line(elem)}')

    counts = Counter(outcomes.values())
    counts['total'] = len(outcomes)
    return counts, problems


def format_table(header, rows):
    """Markdown table padded so columns also line up in the plain-text log.
    """
    widths = [max(len(r[i]) for r in [header, *rows]) for i in range(len(header))]

    def fmt(row):
        cells = [row[0].ljust(widths[0])] + [c.rjust(w) for c, w in zip(row[1:], widths[1:])]
        return '| ' + ' | '.join(cells) + ' |'

    # A trailing ':' in the divider ("---:") right-aligns that column in Markdown
    divider = ['-' * widths[0]] + ['-' * (w - 1) + ':' for w in widths[1:]]
    return [fmt(header), '| ' + ' | '.join(divider) + ' |', *(fmt(r) for r in rows)]


def build_summary(title, paths):
    """Return the Markdown summary of the given reports as a single string."""
    header = ['Run'] + [label for label, _ in COLUMNS]
    rows, problems, unreadable = [], [], []
    n_problem_tests = 0
    for path in paths:
        name = path.stem
        try:
            counts, report_problems = summarize_report(path)
        # A missing or truncated report means that pytest process exited before
        # it could write the XML, e.g. a crash or the runner killing it for OOM
        except (OSError, ET.ParseError) as exc:
            reason = 'missing' if isinstance(exc, FileNotFoundError) else f'unreadable: {exc}'
            unreadable.append(f'{name} ({reason})')
            rows.append([name, 'no report'] + [''] * (len(COLUMNS) - 1))
            continue
        rows.append([name] + [str(counts[key]) for _, key in COLUMNS])
        n_problem_tests += counts['failed'] + counts['error']
        # Prefix each problem with its run name so it can be traced to its log section
        problems.extend(f'[{name}] {p}' for p in report_problems)

    lines = [f'### {title}', '', *format_table(header, rows), '']
    if unreadable:
        lines += [f":warning: No report for: {', '.join(unreadable)}. This means the "
                  "pytest run didn't finish (it may have crashed or run out of "
                  "memory); check its log.", '']
    if problems:
        lines += [f'**{n_problem_tests} failed/errored tests:**', '', '```',
                  *problems[:MAX_PROBLEMS]]
        if len(problems) > MAX_PROBLEMS:
            lines.append(f'... and {len(problems) - MAX_PROBLEMS} more, see the log above.')
        lines.append('```')
    elif not unreadable:
        lines.append(':white_check_mark: All tests passed.')
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--title', default='Test summary')
    parser.add_argument('reports', nargs='+', type=Path)
    args = parser.parse_args(argv)

    summary = build_summary(args.title, args.reports)

    # Failure messages can contain characters the console can't encode (e.g.
    # cp1252 on Windows runners), replace them rather than crash
    sys.stdout.reconfigure(errors='replace')
    print(summary, end='')
    # GitHub Actions sets this to a file whose Markdown is shown on the run's
    # summary page. Append rather than overwrite so other content is kept
    step_summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if step_summary:
        with open(step_summary, 'a', encoding='utf-8') as f:
            f.write(summary)


if __name__ == '__main__':
    main()
