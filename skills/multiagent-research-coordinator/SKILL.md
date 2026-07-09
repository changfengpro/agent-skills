---
name: multiagent-research-coordinator
description: Decide whether to use, then design and run, coordinator-worker research workflows where a strong model plans, arbitrates, and synthesizes while cheaper or narrower workers perform token-heavy reading, search, verification, or codebase/document sweeps. Use when the user asks for multi-agent research, plan-big-execute-small delegation, high-rigor source verification, parallel fact gathering, worker/coordinator prompt design, submodel-vs-frontier quality/cost evaluation, or cost/latency comparison between solo and delegated research.
---

# Multiagent Research Coordinator

## Purpose

Use this skill to decide whether a research task should be split into a coordinator-worker team, then design the delegation, evidence contract, synthesis process, and evaluation plan. Do not use this pattern just because multiple agents are available; use it when independent workers can safely process large raw inputs and return compact, auditable findings.

## Suitability Check

Proceed with a coordinator-worker plan when most of these are true:

- The task is coverage-shaped: many facts, files, logs, documents, pages, repositories, or sources must be checked.
- Subtasks are mostly independent and can run in parallel.
- The expensive part is reading, fetching, scanning, or extracting evidence rather than subtle final judgment on the raw material.
- Worker outputs can be constrained to short findings with URLs, paths, quotes, line numbers, or other evidence.
- The user needs high rigor, provenance, broad coverage, or an explicit cost/latency/quality comparison.

Prefer a single strong agent when the question is narrow, the raw material requires frontier-level interpretation, subtasks strongly depend on one another, or delegation overhead would exceed the reading cost.

## Delegation Gate

Before spawning workers, make a hard gate decision. Default to `do not delegate` when any of these are true, unless the user explicitly asks to benchmark or force a multi-agent run:

- Fewer than 4 independent units exist, and each unit is small enough for one strong agent to handle directly.
- The main conversation context is already long, so worker prompts, skill text, or repeated setup would duplicate more context than the workers would save.
- The plan requires frequent `wait` or follow-up cycles instead of one mostly parallel fan-out.
- Subtasks share write state, shared mutable data, or sequencing constraints that make parallel patches likely to conflict.
- The task needs one unified architecture judgment, product decision, or cross-cutting design rather than independent extraction or execution.
- Worker outputs would be shorter than the worker setup brief, or the expected evidence can be checked locally faster than delegating.

If the gate says `do not delegate`, keep the work local with a strong model and state the reason briefly. If the user requested evaluation, record the gate result as the baseline decision rather than forcing an uneconomic worker run.

## Temporary Code-Task Probe

For user code tasks, generate a lightweight probe report every time this skill is used. This probe is temporary and should remain until the user asks to remove it.

- Write the report under `/home/rmer/文档/测试报告/多agent调度/`.
- Use a timestamped Markdown filename: `YYYYMMDD-HHMMSS-<short-task-slug>.md`.
- Create the directory if it does not exist.
- Generate the report whether the gate decision is `delegate` or `do not delegate`; a solo decision is valuable probe data.
- Keep the report concise and auditable. Do not paste long source files, secrets, credentials, or large logs.
- If token, model, latency, or cost data is unavailable, write `unavailable`; do not invent values. If quoting cost, use measured tokens and current verified pricing.

Include these fields:

```text
# Multiagent Dispatch Probe

Task: <brief user goal>
Timestamp: <local time and timezone>
Skill path: /home/rmer/.codex/skills/multiagent-research-coordinator/SKILL.md

## Gate Decision
- Decision: delegate / do not delegate
- Gate result: passed / failed / user-forced benchmark
- Triggered gate conditions: <list>
- Rationale: <why this was or was not a good multi-agent fit>

## Dispatch Plan
- Units: <independent slices, or why none>
- Worker count: <number and reason>
- Model plan: <coordinator and worker model tiers if known>
- Local critical path: <what stayed with the main agent>

## Execution Trace
- Agents spawned: <id/nickname/model/role, or none>
- Wait/follow-up cycles: <count>
- Files changed: <paths or none>
- Verification commands: <commands and pass/fail>

## Efficiency Data
- Main/coordinator tokens: <input/output/total/cost or unavailable>
- Worker tokens: <input/output/total/cost or unavailable>
- Wall-clock time: <available timings or unavailable>
- Subscription/quota proxy: <token volume, rate-limit info, or unavailable>

## Quality Notes
- Worker output quality: <if applicable>
- Main-agent validation quality: <what was independently checked>
- Rework/conflicts: <none or details>
- Skill tuning observation: <one sentence>
```

## Model Tier Decision

- Use cheaper workers for retrieval, extraction, enumeration, log/file scanning, and first-pass evidence capture.
- Use stronger workers only for ambiguous interpretation, adversarial source conflicts, subtle domain judgment, or tasks where a bad summary would destroy important nuance.
- Do not delegate when repeated prompts, skill text, or setup overhead dominate the raw material being read.
- Keep final synthesis, conflict resolution, and quality arbitration with the strongest available coordinator unless the final answer is purely mechanical.

Default fan-out: start with 4-12 workers for broad independent work; batch adjacent tiny units until each worker has enough raw material to amortize setup; split further only when a worker would become serial or context-heavy.

## Coordinator Discipline

- First decide what must stay local on the critical path; delegate only independent sidecar reading or extraction.
- Do not spawn workers until the research contract, source policy, and output schema are explicit.
- Give each worker one bounded slice and tell it not to answer the broader user question.
- Wait for worker results before synthesizing claims that depend on them.
- Close completed workers when no further follow-up is needed.

## Workflow

1. Define the research contract before delegating.
   - State the exact claims or entities to verify.
   - Specify acceptable sources and evidence format, including retrieval date for time-sensitive sources.
   - Include the verification standard: one source, authoritative source, two independent fetches, conflict handling, freshness checks, or line-level citations.
   - Define what counts as `supported`, `not found`, `not applicable`, `conflicting`, and `needs follow-up` for this task.
   - If the premise matters, assign a worker to verify the premise instead of assuming the decomposition is correct.

2. Design the roles.
   - Coordinator: decompose, assign, wait for workers, inspect reports, request follow-ups, resolve conflicts, synthesize.
   - Workers: search/read/fetch/scan only the assigned slice, preserve evidence, report uncertainty, and avoid broad synthesis.
   - Scope worker tools to the minimum required for untrusted raw input.
   - Keep the coordinator prompt aligned with the actual worker prompt; do not assume the runtime exposes worker instructions to the coordinator.

3. Choose the delegation grain.
   - Split by independent unit: source, entity, time window, file group, subsystem, question, or claim cluster.
   - Avoid tiny tasks that create fixed overhead without reducing reading.
   - Avoid oversized tasks that force one worker to perform serial work.
   - Give each worker a complete brief with success criteria and evidence requirements.

4. Run fan-out and control the loop.
   - Spawn workers for independent subtasks.
   - Wait for all workers before drawing conclusions.
   - Send follow-ups for missing evidence, contradictions, or infrastructure failures.
   - Escalate only the ambiguous or high-risk slice to a stronger worker; do not rerun the whole workflow by default.
   - Preserve a trace of delegation: task brief, worker result, evidence, retrieval date, and unresolved uncertainty.

5. Synthesize with provenance.
   - Build a claim table or evidence matrix before writing prose.
   - Mark unsupported, stale, conflicting, or low-confidence findings.
   - Do not let a worker summary erase important raw-source nuance.
   - Explain any exclusions or unresolved gaps.

6. Evaluate honestly.
   - Compare against a solo-agent or all-strong baseline only when the user asks for a workflow evaluation or savings claim.
   - Measure wall-clock time, input/output tokens, total cost, coordinator overhead, worker share, supported-claim rate, conflict handling, and rework.
   - Treat pricing, model names, provider APIs, and tool availability as time-sensitive; verify current values before quoting cost or implementation details.
   - Report whether savings come from lower worker prices, lower token volume, lower latency, or improved evidence quality; do not collapse these into one score.

## Decision Brief

Before launching workers, write a compact brief:

```text
Decision: delegate / do not delegate.
Gate result: <passed, failed, or user-forced benchmark; include the specific gate condition>.
Reason: <coverage, independence, evidence, cost, or risk rationale>.
Units: <source/entity/time/file/question slices>.
Worker count: <number and why>.
Source policy: <allowed sources and freshness rule>.
Output schema: <row fields and status vocabulary>.
Escalation rule: <when to send follow-up or use a stronger worker>.
Synthesis plan: <claim table, conflict handling, final answer shape>.
```

## Worker Brief Template

```text
Research only this sub-question: <sub-question>.
Use only acceptable sources: <source policy>.
Verification standard: <number/type of sources, conflict policy, freshness requirement>.
Return:
1. Direct answer
2. Evidence with URLs/paths/line numbers/short quotes
3. What you checked
4. Retrieval date for time-sensitive evidence
5. Conflicts, uncertainty, and whether missing facts are "not found" or "not applicable"
Do not answer the broader user question.
```

## Worker Output Schema

Ask workers to return compact rows whenever possible:

```text
unit | claim | answer | evidence | source_or_path | retrieved_or_observed_at | status | confidence | notes
```

Use `status` values consistently: `supported`, `conflicting`, `not found`, `not applicable`, `stale`, or `needs follow-up`.

Reject or follow up on worker reports that lack source-level evidence, answer outside their slice, merge uncertainty into prose, omit retrieval dates for time-sensitive evidence, or hide conflicts.

## Common Failure Modes

- Delegating before defining the verification standard.
- Matching a rigorous team run against a low-rigor solo baseline.
- Comparing cheap workers to stronger baselines without using the same task and source policy.
- Assuming the task premise is true, then verifying only downstream facts.
- Giving workers broad tools when they only need search/read access.
- Splitting into too many tiny worker tasks.
- Ignoring the delegation gate on small tasks, long-context sessions, shared-state code work, frequent-wait workflows, or unified architecture decisions.
- Delegating the immediate critical-path question and then idling while workers run.
- Letting the coordinator answer from memory after no workers spawn.
- Treating worker summaries as evidence when the user needs source-level proof.
- Collapsing "not found" and "not applicable" into the same status.
- Claiming token or cost savings without measuring both input and output, model price, and coordinator overhead.

## Evaluation Rubric

When evaluating worker or baseline outputs, consider:

- Suitability: correct decision to delegate or not delegate.
- Gate discipline: explicitly applies the hard gate and respects `do not delegate` unless the user forced a benchmark.
- Contract quality: clear claims, source rules, evidence format, retrieval date, and conflict policy.
- Grain quality: split is independent, not too narrow, not too broad.
- Evidence discipline: avoids unsupported claims and preserves uncertainty.
- Synthesis readiness: returns compact rows or findings the coordinator can audit.
- Cost discipline: identifies token, latency, model price, and hidden overhead tradeoffs.
