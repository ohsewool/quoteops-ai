# Release Checklist

Use this checklist after PR-34 is merged and before PR-35 creates the actual tag and GitHub Release.

- [ ] main branch is clean
- [ ] PR-00 through PR-34 are merged
- [ ] backend compile passes
- [ ] pytest passes
- [ ] frontend build passes
- [ ] security check passes
- [ ] final regression check passes
- [ ] render deployed QA script safely skips without URLs or passes with URLs
- [ ] demo flow check passes
- [ ] release package check passes
- [ ] VERSION is 0.1.0
- [ ] CHANGELOG.md has v0.1.0 section
- [ ] docs/release/v0.1.0.md exists
- [ ] README describes current MVP accurately
- [ ] no .env file is tracked
- [ ] no database file is tracked
- [ ] no frontend/dist is tracked
- [ ] no node_modules is tracked
- [ ] no real secrets are committed
- [ ] no git tag has been created yet
- [ ] no GitHub Release has been created yet

PR-35 will handle the actual git tag and GitHub Release after these checks pass.
