<!-- This comments are hidden when you submit the pull request,
so you do not need to remove them! -->

<!-- Please be sure to check out our code of conduct,
https://github.com/spacetelescope/jdaviz/blob/main/CODE_OF_CONDUCT.md . -->

### Description
<!-- Provide a general description of what your pull request does.
Complete the following sentence and add relevant details as you see fit. -->

<!-- In addition please ensure that the pull request title is descriptive
and allows maintainers to infer the applicable viz component(s). -->

This pull request is to address ...

<!-- If the pull request closes any open issues you can add this.
If you replace <Issue Number> with a number, GitHub will automatically link it.
If this pull request is unrelated to any issues, please remove
the following line. -->

Fixes #<Issue Number>

### Change log entry

- [ ] Is a change log needed? If yes, is it added to `CHANGES.rst`? If you want to avoid merge conflicts,
  list the proposed change log here for review and add to `CHANGES.rst` before merge. If no, maintainer
  should add a `no-changelog-entry-needed` label.

### Checklist for package maintainer(s)
<!-- This section is to be filled by package maintainer(s) who will
review this pull request. -->

This checklist is meant to remind the package maintainer(s) who will review this pull request of some common things to look for. This list is not exhaustive.

- [ ] Are two approvals required? Branch protection rule does not check for the second approval. If a second approval is not necessary, please apply the `trivial` label.
- [ ] Do the proposed changes actually accomplish desired goals? Also manually run the affected example notebooks, if necessary.
- [ ] Do the proposed changes follow the [STScI Style Guides](https://github.com/spacetelescope/style-guides)?
- [ ] Are tests added/updated as required? If so, do they follow the [STScI Style Guides](https://github.com/spacetelescope/style-guides)?
- [ ] Are docs added/updated as required? If so, do they follow the [STScI Style Guides](https://github.com/spacetelescope/style-guides)?
- [ ] Did the CI pass? If not, are the failures related?
- [ ] Is a milestone set? Set this to bugfix milestone if this is a bug fix and needs to be released ASAP; otherwise, set this to the next major release milestone.
- [ ] After merge, any internal documentations need updating (e.g., JIRA, Innerspace)?
