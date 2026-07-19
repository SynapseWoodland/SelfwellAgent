# Harness V2 migration note

> Status: draft for review
> Target cutover: W4, 2026-08-14
> Source: V1.6 `harness/workflow.yaml`
> Target: V2 `harness/workflow-v2.yaml`

## 1. Six major changes

1. **Sixteen-phase graph** — the ten V1.6 delivery phases remain, with six explicit V2 phases added.
2. **Independent security gate** — `SECURITY_TEST` runs after `VERIFY` and before `DEPLOY`; it is no longer only a Pre-Mortem concern.
3. **Feedback-driven intake** — `DATA_REPLAY` replays telemetry and customer feedback before the next `PRD` cycle and carries `replay_session_id`.
4. **Post-deploy control loop** — `INCIDENT_RESPONSE` and `OPS_LOOP` make incident handling, rollout, A/B decisions, and feedback linkage explicit.
5. **Harness evolution** — `SKILL_UPDATE` records lesson → pattern → instinct promotion decisions instead of treating autolearn as an informal SIGN_OFF afterthought.
6. **Interrupt engineering** — the five-question budget is enforced per run; `INTERRUPT_REVIEW` records continue/defer decisions and escalates over-budget questions to `AskUser`.

## 2. Migration checklist and order

1. Freeze new V1.6 runs and record their `run_id` and current phase.
2. Add `workflow-v2.yaml` as the machine-readable source; keep `workflow.yaml` read-only during the transition.
3. Rewrite the complete decision table and terminal-state rules in `agents/harness/DISPATCHER.md` for all 16 phases.
4. Update `.cursor/skills/harness-dispatcher/SKILL.md` to read V2 and route interruption/replay transitions.
5. Extend `harness/evidence/README.md` and evidence checks with `interrupt_budget` and `replay_session_id`; accept old six-field evidence with defaults.
6. Add phase context and evidence templates for security, incidents, operations, skill updates, interrupts, and replay.
7. Update `agents/harness/ORCHESTRATOR.md` and `REVIEWERS.md` so PRE_MORTEM always serially calls all five reviewers, then synthesizes.
8. Extend state schema/examples with interruption stack, remaining budget, and replay session metadata.
9. Run one pilot FR through all 16 phases, then run existing V1.6 evidence compatibility checks and regression gates.
10. After the pilot is green, switch the dispatcher alias from `workflow.yaml` to V2 and mark V1.6 runs read-only.

## 3. Cutover window

Use W1–W2 for protocol and schema changes, W3 for a complete pilot and rollback rehearsal, and W4 for the alias switch. V2 replaces V1.6 at the end of W4; retain V1.6 evidence and the deprecated file as read-only audit history until the next planned Harness release.
