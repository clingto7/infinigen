# Issue tracker: GitHub

Issues and specs for this repo live in GitHub Issues at
`clingto7/infinigen`. Use the `gh` CLI from this clone.

## Conventions

- Create: `gh issue create --title "..." --body-file <file>`
- Read: `gh issue view <number> --comments`, including labels
- List: `gh issue list --state open --json number,title,body,labels,comments`
- Comment: `gh issue comment <number> --body-file <file>`
- Label: `gh issue edit <number> --add-label "..."` or `--remove-label "..."`
- Close: `gh issue close <number> --comment "..."`

When a skill says “publish to the issue tracker,” create a GitHub issue.
When it says “fetch the relevant ticket,” read that issue and its comments.

## Pull requests as a triage surface

**PRs as a request surface: no.** Change this to `yes` if this repo
starts treating external PRs as feature requests.

## Wayfinding operations

A map is one issue labelled `wayfinder:map`; child tickets are linked as
GitHub sub-issues when available. Otherwise, list children in the map
body and put `Part of #<map>` in each child. Use `wayfinder:research`,
`wayfinder:prototype`, `wayfinder:grilling`, or `wayfinder:task` labels.

Use GitHub issue dependencies for blockers when available. Otherwise,
put `Blocked by: #<n>` at the top of the child issue. An unassigned
child with no open blockers is ready to claim; assign it to the driving
developer. On resolution, comment with the answer, close the child,
and update the map’s decisions.
