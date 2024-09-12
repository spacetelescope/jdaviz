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

- [ ] Is a change log entry needed? If yes, write a fragment in `changes/`: `echo "changed something" > changes/<module>/<pr#>.<changetype>.rst` 
  or `echo "changed something" > changes/<pr#>.<changetype>.rst` (see below for change types). 
  If no, maintainer should add a `no-changelog-entry-needed` label.

  <details><summary>change log entry types...</summary>

  - `changes/<module>/<pr#>.feature.rst`: adds new feature
  - `changes/<module>/<pr#>.apichange.rst`: changes API
  - `changes/<module>/<pr#>.bugfix.rst`: resolves an issue
  - `changes/<module>/<pr#>.other.rst`: other changes and additions
  </details>

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
- [ ] Is a milestone set? Set this to bugfix milestone if this is a bug fix and needs to be released ASAP; otherwise, set this to the next major release milestone. Bugfix milestone also needs an accompanying backport label.
- [ ] After merge, any internal documentations need updating (e.g., JIRA, Innerspace)?
