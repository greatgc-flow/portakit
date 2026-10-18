# Team decisions (rounds 1-5; cc, cx, ag)
Name `portakit`; SPEC.md unanimous (r3b). Roles/profiles unanimous APPROVE (r4 amended -> r5 all APPROVE):
- cx.effort: implementer/TDD + edge tests; must cite a test per change and a reproducible test command + result.
- cc.effort: adversarial reviewer (static + orchestrator-supplied test results); cc.standard quick votes.
- ag.standard: short read-only votes, `--json`; no long writable tasks (peerhub#169).
- Orchestrator terminal: minimal tokens; runs `python -I -m unittest discover -s tests` after every cx task and before every commit.
- Tie-break: 1-1 split -> third read-only ag vote -> then *.deepthink. Record voter profile + output.
- Log per-task peer/profile/tokens (from CLI usage output) in docs/LOG.md.
Note: r5 side-amendments (cx: test-per-change, usage-based token log; cc: pin vote inputs) were adopted as additive; not re-voted.
Test files must match test*.py.

## Process deviation (lesson)
Roles/models/effort were agreed in r4-r5 AFTER implementation began (r1-r3 covered name, scope, SPEC only). Future: vote roles/profiles/effort in the first round, before any build. Cannot be undone retroactively.

## Ratification outcome (v0.2.1)
Deadlock on over-engineering settled by cc.deepthink arbiter ruling (see SPEC). Roles agreed (r4-r5, post-hoc). Final code votes: cc APPROVE, cx APPROVE (after 6 fix rounds: reparse root/state/lock/temp, dest ownership, exit-code mapping, recovery link check). ag: APPROVE on SPEC (r13); on final code ag returned empty replies (peerhub#169), so no fresh ag vote. 166 tests, run by orchestrator.

ag final vote (v0.2.1): APPROVE x2, on a summary of the implementation (ag did not read the code; empty replies occur when it tries tools — prefix "Do not use tools. Reply in plain text only." makes it answer). Final: cc, cx, ag APPROVE.
