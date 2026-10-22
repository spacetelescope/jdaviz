"""Combine JUnit XML reports from several pytest runs into a single summary.

Used in CI after running pytest in multiple invocations via pytest-split,
so that all failures are listed in one place at the end of
each invocation's log. The summary is printed to stdout and, when available,
appended to the GitHub Actions job summary ($GITHUB_STEP_SUMMARY).

Usage: python jdaviz/pytest_utilities/pytest_summary.py [--title TITLE] REPORT.xml [REPORT.xml ...]
"""
import argparse
import os
import xml.etree.ElementTree as ET
from pathlib import Path

MAX_MESSAGE_LENGTH = 300


def summarize_report(path):
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == 'testsuite' else root.iter('testsuite')
    counts = dict(tests=0, failures=0, errors=0, skipped=0)
    problems = []
    for suite in suites:
        for key in counts:
            counts[key] += int(suite.get(key, 0))
        for case in suite.iter('testcase'):
            for outcome in ('failure', 'error'):
                elem = case.find(outcome)
                if elem is None:
                    continue
                message = (elem.get('message') or elem.text or '').strip()
                message = message.splitlines()[0] if message else ''
                if len(message) > MAX_MESSAGE_LENGTH:
                    message = message[:MAX_MESSAGE_LENGTH] + '...'
                node = f"{case.get('classname', '')}::{case.get('name', '')}"
                label = 'FAILED' if outcome == 'failure' else 'ERROR'
                problems.append(f'{label} {node} - {message}')
    counts['passed'] = (counts['tests'] - counts['failures']
                        - counts['errors'] - counts['skipped'])
    return counts, problems


def format_table(header, rows):
    """Markdown table padded so columns also line up in the plain-text log.

    The first column is left-aligned and the numeric columns right-aligned.
    """
    widths = [max(len(r[i]) for r in [header, *rows]) for i in range(len(header))]

    def fmt(row):
        cells = [row[0].ljust(widths[0])] + [c.rjust(w) for c, w in zip(row[1:], widths[1:])]
        return '| ' + ' | '.join(cells) + ' |'

    divider = ['-' * widths[0]] + ['-' * (w - 1) + ':' for w in widths[1:]]
    return [fmt(header), '| ' + ' | '.join(divider) + ' |', *(fmt(r) for r in rows)]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--title', default='Test summary')
    parser.add_argument('reports', nargs='+', type=Path)
    args = parser.parse_args()

    header = ['Run', 'Passed', 'Failed', 'Errors', 'Skipped', 'Total']
    rows, problems, missing = [], [], []
    for path in args.reports:
        try:
            counts, report_problems = summarize_report(path)
        except (OSError, ET.ParseError):
            missing.append(path.stem)
            rows.append([path.stem, 'no report', '', '', '', ''])
            continue
        problems.extend(f'[{path.stem}] {p}' for p in report_problems)
        rows.append([path.stem] + [str(counts[k]) for k in
                                   ('passed', 'failures', 'errors', 'skipped', 'tests')])

    lines = [f'### {args.title}', '', *format_table(header, rows), '']
    if missing:
        lines += [f":warning: No report for: {', '.join(missing)}. That pytest run did "
                  "not finish (it may have crashed or run out of memory); check its log.",
                  '']
    if problems:
        lines += [f'**{len(problems)} failed/errored tests:**', '', '```',
                  *problems, '```']
    elif not missing:
        lines.append(':white_check_mark: All tests passed.')
    summary = '\n'.join(lines) + '\n'

    print(summary)
    step_summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if step_summary:
        with open(step_summary, 'a', encoding='utf-8') as f:
            f.write(summary)


if __name__ == '__main__':
    main()
