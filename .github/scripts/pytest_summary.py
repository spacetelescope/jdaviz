"""Combine JUnit XML reports from several pytest runs into a single summary.

Used in CI after running pytest in multiple invocations (e.g. pytest-split
groups), so that all failures are listed in one place instead of at the end of
each invocation's log. The summary is printed to stdout and, when available,
appended to the GitHub Actions job summary ($GITHUB_STEP_SUMMARY).

Usage: python pytest_summary.py [--title TITLE] REPORT.xml [REPORT.xml ...]

A missing report means that pytest invocation never finished (e.g. it crashed
or was killed for running out of memory), which is reported as well. This
script always exits 0; the test step itself is responsible for failing the job.
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


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--title', default='Test summary')
    parser.add_argument('reports', nargs='+', type=Path)
    args = parser.parse_args()

    rows, problems, missing = [], [], []
    for path in args.reports:
        if not path.is_file():
            missing.append(path.stem)
            rows.append(f'| {path.stem} | no report | | | | |')
            continue
        counts, report_problems = summarize_report(path)
        problems.extend(f'[{path.stem}] {p}' for p in report_problems)
        rows.append(f"| {path.stem} | {counts['passed']} | {counts['failures']} "
                    f"| {counts['errors']} | {counts['skipped']} | {counts['tests']} |")

    lines = [f'### {args.title}', '',
             '| Run | Passed | Failed | Errors | Skipped | Total |',
             '|---|---|---|---|---|---|', *rows, '']
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
