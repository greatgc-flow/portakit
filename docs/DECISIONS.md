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
