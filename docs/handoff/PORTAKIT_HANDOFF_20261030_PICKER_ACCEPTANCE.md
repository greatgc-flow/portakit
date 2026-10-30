# Picker human-acceptance helper — 2026-10-30 handoff

Repository: PUBLIC `greatgc-flow/portakit`. Work branched from main `0ad134e0c45c3257536283ba3c6975e3157dd98e`. Always verify latest main SHA and CI before claiming merge.

## Purpose and safety
Previous GUI picker/overview and keyboard code was validated only by headless unit tests and Windows CI. Live Tk/DPI/keyboard/Korean IME/screen-reader/enterprise policy remains **HUMAN_NOT_VERIFIED**. This helper provides an optional repeatable local operator checklist **without claiming** that CI or ChatGPT has seen a real desktop.

`scripts/PickerAcceptance.cmd` invokes `scripts/picker_acceptance.py`. Default run is source syntax/hash and interpreter/Tk module *static prerequisites only*; no Tk instance, no files, and an explicit NOT_VERIFIED statement. `--review --out LocalReview.json` prompts for fourteen independent P/F/S observations after an operator separately starts `scripts/MyToolkitGUI.cmd`; creates only new-only local JSON and exactly mirrored program-produced console log, never releases binaries or edits settings. Abort preserves partial log but not completed report. A self-reported full PASS is **not** independent accessibility, EDR, enterprise EULA, redistribution or release approval. Keep evidence off the public repository.

## Tests and continuation
- `tests/test_picker_acceptance.py` headless tests input normalization, independent DPI cases, invalid/short answers, PASS/FAIL/SKIP gating, existing output refusal, interrupted log, static no-Tk no-apply rule, exact console transcript.
- Windows Python 3.11 / 3.14 workflows include default static `NOT_VERIFIED` smoke and complete unittest discovery.
- Following PR full green: squash merge and re-check main CI. Keep #27, #36, #25 open until actual operator/legal evidence is independently reviewed. The next action is human-guided GUI acceptance on a sanitized permitted desktop, not publishing a product release.
