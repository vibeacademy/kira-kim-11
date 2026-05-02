# Upstream Template Feedback — `/work-ticket` and `/review-pr`

**Audience:** Claude Code session working on the upstream
`vibeacademy/agile-flow-gcp` template.
**Scope:** Issues encountered running `/work-ticket` and `/review-pr` on
the first ticket of a freshly-bootstrapped fork, plus follow-on issues
through merge.
**Companion doc:** [UPSTREAM-TEMPLATE-FEEDBACK.md](UPSTREAM-TEMPLATE-FEEDBACK.md)
covers `/bootstrap-product`, `/bootstrap-architecture`, `/bootstrap-agents`,
and `/bootstrap-workflow`. This doc starts from the point where bootstrap
finished and the first ticket was picked up. Where an issue here has the
same root cause as something in the companion doc, this doc cites the
existing item rather than re-litigating it.
**Date observed:** 2026-05-01.
**Source:** Fork at `vibeacademy/kira-kim-11`, ticket #6 picked up via
`/work-ticket`, implemented as
[PR #10](https://github.com/vibeacademy/kira-kim-11/pull/10), reviewed via
`/review-pr`, merged by `kira-kim-11` (solo mode).

**TL;DR:** `/work-ticket` and `/review-pr` work end-to-end and produced a
clean, mergeable PR in ~13 minutes. But the path is rougher than it should
be: the agent has to skip pre-flight checks the template itself prevents
from passing, can't update project-board status due to token scope, hits a
genuine SQLModel gotcha that nothing in the framework warns about, and at
merge time runs into GitHub's "no self-approval" rule that the framework's
branch-protection guidance doesn't account for in solo mode.

---

## Environment

| Item | Value |
|---|---|
| Fork | `vibeacademy/kira-kim-11` |
| Mode | Solo (`AGILE_FLOW_SOLO_MODE=true`) |
| `gh` auth | Codespaces-issued `GITHUB_TOKEN` as `kira-kim-11` |
| Ticket worked | #6 — Add User SQLModel and Alembic migration |
| PR opened | [#10](https://github.com/vibeacademy/kira-kim-11/pull/10) |
| End state | PR merged, issue auto-closed, all 19 CI checks green |

---

## Critical issues

### 1. `/work-ticket` cannot perform two of its required steps without `project` scope

**Where:** `.claude/commands/work-ticket.md`, "Workflow Steps":

> 4. **Setup** — Create branch, **move to In Progress**
> 9. **Monitor CI** — … **move to In Review** when green

**Observed:** Both board-status mutations require GraphQL `updateProjectV2ItemFieldValue`, which needs `project` scope. The Codespaces `GITHUB_TOKEN` doesn't have it. Same root cause as items 2-4 in [UPSTREAM-TEMPLATE-FEEDBACK.md](UPSTREAM-TEMPLATE-FEEDBACK.md), but a new, recurring surface: every single ticket run hits this twice.

The agent has to either silently skip the moves (violating the documented workflow) or stop and ask the human to drag the card. In this run I told the user explicitly each time. That's correct, but means the workflow is fundamentally human-in-the-loop where the doc implies it isn't.

**Suggested upstream fix:**

- Either the bootstrap provisions a token with `project` scope (per the punch-list item in the companion doc), or
- `/work-ticket` is rewritten to acknowledge the limitation and instruct the agent to STOP-and-prompt the human at exactly two pre-defined points ("please move ticket to In Progress" / "please move to In Review") rather than treating the move as something the agent does.
- Either path should be a deliberate decision, not an undocumented coping behavior the agent invents.

---

### 2. Branch-protection guidance forbids merging in solo mode

**Where:** `.claude/commands/bootstrap-workflow.md`, step 2:

> Verify or configure branch protection on `main`:
> - [ ] Require pull request reviews before merging

**Observed:** GitHub does not allow a PR's author to approve their own PR. In solo mode, the same account is author *and* reviewer *and* merger, so "Require pull request reviews" is **structurally unsatisfiable** — the user cannot approve and therefore cannot merge their own PR. The framework's solo-mode guarantees and the framework's branch-protection guidance contradict each other.

The user hit this on the very first PR. They had to either:

- Edit branch protection to set required approvals to 0 (still requires a PR, still requires green CI — a sane solo-mode posture), or
- Disable the "Do not allow bypassing" option and use admin-merge override.

Both are valid; neither is documented.

**Suggested upstream fix:** `bootstrap-workflow.md` step 2 should branch on `AGILE_FLOW_SOLO_MODE`:

| Mode | Required approvals | "Do not allow bypassing" |
|---|---|---|
| Solo | 0 | unchecked (admin can merge) |
| Multi-bot | 1+ | checked |

Document both configurations explicitly in the slash command and in `docs/GETTING-STARTED.md`. The framework's GO/NO-GO comment from the `pr-reviewer` agent is the actual review record in solo mode; the GitHub Approve button is a UI affordance that doesn't apply.

---

### 3. The `/work-ticket` pre-flight has the same broken MCP-GitHub check as `/bootstrap-workflow`

**Where:** `.claude/commands/work-ticket.md`, "Pre-Flight Verification (REQUIRED)" check #1:

> "MCP GitHub server is reachable — Attempt a GitHub MCP tool call. If the MCP server is not connected, STOP."

**Observed:** Same as item #1 in the companion doc — `.mcp.json` does not register a GitHub MCP server, so a literal reading STOPs the workflow on every ticket. This is the same defect appearing in two slash commands.

**Suggested upstream fix:** Whatever fix lands for the companion doc's item #1 should be applied to `work-ticket.md` too. Both commands have nearly identical pre-flight blocks; consider extracting them into a shared snippet that's referenced from each, so future fixes don't need to be applied twice.

---

## Implementation surprises

### 4. SQLModel `table=True` classes silently bypass Pydantic validators — no framework warning

**Where:** Implementing #6 (User SQLModel), the ticket's Guardrails specify "normalize to lowercase in a SQLModel validator and use TEXT NOT NULL UNIQUE." Following this guidance literally, I started with:

```python
@field_validator("email")
@classmethod
def _normalize_email(cls, v: str) -> str:
    return v.strip().lower()
```

Tests failed: the validator never ran. Switched to `@model_validator(mode="before")`. Tests still failed: it also never ran. Eventually fell back to overriding `__init__`, which works — but only because of a documented SQLModel quirk that the framework nowhere mentions.

**The actual rule** (worth landing somewhere durable):

- For SQLModel classes with `table=True`, neither `@field_validator` nor `@model_validator` fires during `Model(**kwargs)` instantiation. They run only on `Model.model_validate(...)`.
- The reliable hook for input normalization on instantiation is `__init__`.
- This is a recurring source of test failures in any project doing data normalization at the model level.

**Observed cost in this run:** ~10 minutes and two test-fix iterations to discover this. For a workshop attendee unfamiliar with the SQLModel internals, it's plausibly an hour.

**Suggested upstream fix:**

- Add a "SQLModel gotchas" section to `docs/PATTERN-LIBRARY.md` (the project's existing pattern reference) covering this, with the `__init__` workaround pattern as the recommended fix.
- The `quality-engineer` agent's "Critical Quality Concerns" or `system-architect` agent's project-specific block should also point at it, since it's a class of bug that surfaces at test time, not type-check time.
- Optionally, the ticket-format reference in `docs/TICKET-FORMAT.md` could note: "if your guardrail mentions a SQLModel validator, the implementer should follow the SQLModel gotchas section of the pattern library; field validators don't fire for table classes."

---

### 5. Tests use `SQLModel.metadata.create_all`, not the actual Alembic migration

**Where:** `tests/conftest.py`'s `session_fixture` calls `SQLModel.metadata.create_all(engine)` to set up each test's schema.

**Observed:** This means tests verify the *model definition*, not the *migration script*. If a contributor changes a model but writes a wrong/incomplete Alembic revision, the tests still pass — the bug surfaces only when CI runs `alembic upgrade head` against the preview Neon branch. In #6 the migration was correct, but I called it out in the review because the gap is real.

This is a pre-existing template pattern (the same is true for the seed `001_create_todo_table.py`), not introduced by this PR. But it gets worse with every model added.

**Suggested upstream fix:**

- Add a second test fixture (`migrated_session`) that runs `alembic upgrade head` against the test engine instead of `metadata.create_all`. Tests that specifically guard the migration use this fixture.
- Or: add a single CI check that runs the model's `metadata.create_all` against an empty SQLite DB and diffs the resulting schema against the result of running migrations end-to-end. Schema drift fails loudly.
- At minimum: document this in `docs/PATTERN-LIBRARY.md` so contributors know `pytest` green doesn't mean "the migration is right."

---

## Process issues

### 6. Bootstrap-phase changes contaminate the first feature branch

**Where:** Default new-fork sequence: `/bootstrap-product` → `/bootstrap-architecture` → `/bootstrap-agents` → `/bootstrap-workflow` → `/work-ticket`. Each bootstrap phase writes files (PRD, architecture doc, agent specializations, CLAUDE.md, project marker file) but **none of them commit**.

**Observed:** When `/work-ticket` runs `git checkout -b feature/issue-6-...`, every uncommitted bootstrap-phase file rides along to the feature branch. I had to selectively `git add` only the User-model files to keep PR #10 focused on the ticket. The bootstrap files are still uncommitted in the working tree post-merge — they need their own follow-up PR.

A workshop attendee following the slash commands literally has no obvious cue that they need to commit between bootstrap and feature work. They'll either:
- Bundle bootstrap content into the first feature PR (mixed concerns), or
- Lose the bootstrap content if the Codespace dies before they realize it's uncommitted.

**Suggested upstream fix:** Either:

- The last step of `/bootstrap-workflow` automatically branches + commits + opens a `chore(bootstrap): populate project setup` PR with all the bootstrap-generated files. The user merges it before running `/work-ticket`. Clean, scriptable, no manual decisions.
- Or: `/work-ticket` checks `git status -s` at the start and STOP-and-prompts if there are uncommitted changes that don't match the ticket's expected file list. ("You have uncommitted changes outside the ticket's scope. Commit them as a separate `chore` PR first, or `git stash` to set aside.")

The first option is the better default; the second is the defensive backstop.

---

### 7. PRs reference docs that haven't been committed yet

**Where:** Ticket #6's body references `docs/TECHNICAL-ARCHITECTURE.md` (ADR-004 for auth approach). The same is true for #7, #8, and #9 — they all cite the architecture doc. But that doc was generated by `/bootstrap-architecture` and never committed. Until the bootstrap-cleanup PR lands, every link in every ticket body 404s.

**Observed:** This wasn't a blocker for implementation — I had the architecture doc in my session context — but it's a degraded experience for a future reviewer or a fresh agent run that can only read what's on `main`.

**Suggested upstream fix:** Same fix as item #6 — automate the bootstrap commit. Once the bootstrap docs are on `main`, all the links resolve.

---

### 8. `gh run rerun` requires `actions:write` — token can't do it

**Where:** Hit when re-running the failed `Deploy PR Preview to Cloud Run` job after the user fixed the `NEON_PARENT_BRANCH` secret.

**Observed:**

```text
$ gh run rerun 25237699624 --failed --repo vibeacademy/kira-kim-11
run 25237699624 cannot be rerun; Resource not accessible by integration
```

Same root cause family as items 2-4 in the companion doc and item #1 here, but a new symptom: even though the agent created the PR and is monitoring CI, it cannot trigger a CI re-run after a secret-config fix. The user had to click "Re-run failed jobs" in the Actions UI manually, or the agent had to push an empty commit to trigger a fresh run.

**Suggested upstream fix:** Add `actions:write` to the punch-list item recommending a higher-scope token. Document the empty-commit fallback for the no-PAT path. The CI monitoring section of `work-ticket.md` should mention what to do when re-run fails.

---

### 9. Neon parent-branch default mismatch fails preview deploy on the first PR

**Where:** [.github/workflows/preview-deploy.yml#L87](https://github.com/vibeacademy/agile-flow-gcp/blob/main/.github/workflows/preview-deploy.yml#L87) — `parent: ${{ secrets.NEON_PARENT_BRANCH || 'main' }}`. The fallback is `'main'`, but Neon projects from certain templates (or projects created before Neon's 2024 default rename) have a default branch named `production`.

**Observed:** PR #10 failed `Create Neon branch` with `ERROR: Branch *** not found` on the first preview deploy. The fix was setting `NEON_PARENT_BRANCH=production` as a repo secret. The workflow's inline comments warn about this (see lines 79-87) but the bootstrap-workflow command doesn't call out the lookup-and-set step.

**Suggested upstream fix:** Make the Neon-secrets walkthrough part of `/bootstrap-workflow` (or a new `/setup-neon` slash command). The walkthrough should:

1. Tell the user which values to gather from the Neon UI: project ID, API key, **default branch name**, pooled connection string.
2. Identify the right secret name for each.
3. Document the UI URL for setting them (since the Codespaces token can't `gh secret set`).
4. Verify by triggering a no-op CI run.

Currently this is split across `docs/PLATFORM-GUIDE.md` (high-level), the workflow YAML's inline comments (the warning), and ad-hoc agent guidance (what I gave the user this session). A single canonical walkthrough would close the gap.

---

## Smaller issues

### 10. `/review-pr` has no solo-mode caveat

**Where:** `.claude/commands/review-pr.md`.

**Observed:** In solo mode the agent picks up its own freshly-created PR and reviews it. The slash command's instructions don't acknowledge this case at all. The agent has to invent the disclosure ("I authored this PR earlier in the same session…"). The framework's design accepts this — solo mode collapses author and reviewer — but the slash command should say so.

**Suggested upstream fix:** Add a one-paragraph caveat to `review-pr.md`:

> **Solo-mode note:** If `AGILE_FLOW_SOLO_MODE=true` and you are reviewing a PR you authored in the same session, lead the review comment with an explicit disclosure ("I authored this PR; treat this review as a self-check, not the framework's separation-of-duties review"). The actual independent review remains the human's job at merge time.

This keeps the agent's review honest and prevents future confusion about whether solo-mode self-review counts as "real" review.

---

### 11. Pre-push hook output is verbose but the success path is the same as failure for half a second

**Where:** [scripts/hooks/pre-push](https://github.com/vibeacademy/agile-flow-gcp/blob/main/scripts/hooks/pre-push).

**Observed:** During `git push`, the hook prints "Running pre-push checks…" then runs ruff and pytest, and only at the very end prints `All pre-push checks passed.` In a Codespace where output buffering is sometimes laggy, the user sees "Running…" stall for a few seconds with no progress. Not a bug, but a UX rough edge — easy to think the push hung.

**Suggested upstream fix:** Add per-step progress. The hook already has the structure (`ruff check` followed by status, etc.); just emit a brief progress line at the start of each step too. Cosmetic, low priority.

---

## Suggested upstream punch list

In rough priority order, scoped to this doc's findings:

1. **Resolve the project-board write-access issue** (item 1). The most-frequent rough edge: every ticket hits it twice. Either a higher-scope token in solo mode or a documented STOP-and-prompt protocol in the slash command.
2. **Branch-protection guidance must branch on solo vs multi-bot** (item 2). This blocks the first merge. Easy doc fix.
3. **Document the SQLModel `table=True` validator gotcha** (item 4). One-time discoverable; lasting cost. Belongs in `PATTERN-LIBRARY.md`.
4. **Auto-commit bootstrap-generated files at the end of `/bootstrap-workflow`** (items 6, 7). Single fix that closes two issues.
5. **Add `actions:write` to the recommended token scope and document the empty-commit fallback** (item 8).
6. **Build a canonical Neon-secrets walkthrough into `/bootstrap-workflow` or `/setup-neon`** (item 9).
7. **Apply the MCP-GitHub-server pre-flight fix to all slash commands that use it** (item 3) — once the fix lands for `/bootstrap-workflow`, propagate.
8. **Add a `migrated_session` test fixture or schema-drift CI check** (item 5). Improves testing rigor across the lifetime of any project.
9. **Add a solo-mode caveat to `/review-pr`** (item 10). Quick doc fix.
10. **Pre-push hook progress output** (item 11). Cosmetic.

---

## What works well (for context)

- `/work-ticket` produced a clean, conventional-commit, well-scoped PR with full Power Sections traceability. From `/work-ticket` invocation to merged PR took ~13 minutes.
- The pre-push hook caught nothing because everything was clean locally — but it ran reliably and gave clear pass output.
- CI rollup is comprehensive: 19 checks (lint, format, mypy, pytest, build, actionlint, agent-policy lint, preview deploy, etc.). Once the Neon parent-branch was fixed, all 19 ran green in ~1.5 minutes.
- The auto-close-on-merge wiring (`Closes #6` in PR body → issue closes → "Item closed → Status: Done" workflow) is the right pattern.
- `docs/TICKET-FORMAT.md` continues to pay off. The Power Sections gave the agent a precise contract: implementing #6 was almost mechanical because the DoD was concrete.
- `pr-reviewer.md`'s "post a written GO/NO-GO comment, not the GitHub Approve button" instruction was exactly right for solo mode (where the Approve button doesn't work anyway). The instruction's design is solo-mode-friendly even though the surrounding doc doesn't acknowledge solo mode.

---

## Reproduction notes

For the upstream Claude session, here is the literal sequence that produced each finding:

```text
# Item 1 — project move STOP
$ gh project item-edit ...   # would need project scope
# Skipped — agent told user to drag manually.

# Item 2 — self-approval blocked
$ gh pr review 10 --approve --repo vibeacademy/kira-kim-11
HTTP 422: Can not approve your own pull request

# Item 4 — SQLModel validators don't fire on table=True
$ uv run pytest tests/models/test_user.py
FAILED tests/models/test_user.py::test_email_normalized_to_lowercase_and_stripped
# (with @field_validator)
$ # switched to @model_validator(mode="before")
FAILED tests/models/test_user.py::test_email_normalized_to_lowercase_and_stripped
# (still)
$ # fell back to __init__ override
4 passed in 0.04s

# Item 6 — uncommitted bootstrap files came along to feature branch
$ git status -s | wc -l
12  # 5 of which are #6's, 7 of which are bootstrap leftovers

# Item 8 — gh run rerun denied
$ gh run rerun 25237699624 --failed --repo vibeacademy/kira-kim-11
run 25237699624 cannot be rerun; Resource not accessible by integration

# Item 9 — Neon parent-branch fail
Create Neon branch  ERROR: Branch *** not found
# After setting NEON_PARENT_BRANCH=production: passed in 1m24s
```

End of report.
