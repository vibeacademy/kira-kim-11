# Upstream Template Feedback — `/bootstrap-workflow`

**Audience:** Claude Code session working on the upstream
`vibeacademy/agile-flow-gcp` template.
**Source:** Fork at `vibeacademy/kira-kim-11`, generated from
`vibeacademy/agile-flow-gcp` and run through `/bootstrap-product`,
`/bootstrap-architecture`, `/bootstrap-agents`, `/bootstrap-workflow`
in a GitHub Codespace.
**Date observed:** 2026-05-01.
**TL;DR:** The first three bootstrap phases work. Phase 4
(`/bootstrap-workflow`) is **not runnable in the default Codespaces
environment** because it requires permissions and infrastructure that
the template does not provision.

This report enumerates each problem, what was expected, what was
observed, and a suggested upstream fix. Phases 1-3 also surfaced
smaller issues that are listed at the end.

---

## Environment used to reproduce

| Item | Value |
|---|---|
| Fork | `vibeacademy/kira-kim-11` |
| Default branch | `main` (clean, two commits) |
| Container | `mcr.microsoft.com/devcontainers/base:noble` per `.devcontainer/devcontainer.json` |
| Solo mode | `AGILE_FLOW_SOLO_MODE=true` (set by devcontainer) |
| `gh` auth | `GITHUB_TOKEN` (Codespaces-issued, prefix `ghu_*`) as user `kira-kim-11` |
| MCP servers configured (`.mcp.json`) | `memory`, `sequential-thinking` |
| MCP servers connected at runtime | `memory`, `sequential-thinking` (no GitHub MCP) |

This is the *intended* default environment for a workshop attendee — a
Codespace launched from the upstream template. So issues below are
not "exotic environment" issues; they are "first-run" issues.

---

## Critical issues (block Phase 4 from completing)

### 1. Pre-flight requires a GitHub MCP server that the template does not ship

**Where:** `.claude/commands/bootstrap-workflow.md`, "Pre-Flight
Verification (REQUIRED)", check #1:

> "MCP GitHub server is reachable — Attempt a GitHub MCP tool call
> (e.g., list repos). If the MCP server is not connected, STOP. Do
> not fall back to CLI-only mode silently."

**Observed:** `.mcp.json` only registers `memory` and
`sequential-thinking`. There is no GitHub MCP server in the template,
so the agent is instructed to STOP on every fresh fork.

**Expected:** Either the template ships a GitHub MCP server (and
`.mcp.json` registers it), or the pre-flight check is rewritten to
accept `gh` CLI as the primary method (which is consistent with
`CLAUDE.md`'s line "Agents use the `gh` CLI for all GitHub
operations").

**Suggested upstream fix:**
- Drop pre-flight check #1, OR
- Make the GitHub MCP server part of the template's `.mcp.json` and
  document the auth wiring, OR
- Reword check #1 as "MCP GitHub server OR `gh` CLI is reachable."
  The current wording forces a STOP that contradicts the rest of the
  framework.

---

### 2. Codespaces `GITHUB_TOKEN` lacks `project` scope

**Where:** Phase 4 expects to "Verify or create project board" and
list/manage `projectsV2` resources.

**Observed:**

```text
$ gh project list --owner vibeacademy
GraphQL: Resource not accessible by integration (organization.projectsV2.nodes.0), ...

$ gh api graphql -f query='{ repository(owner:"vibeacademy",name:"kira-kim-11") { projectsV2(first:5) { nodes { id title number } } } }'
{"data":{... "projectsV2":{"nodes":[]}}}    # repo-scope read works (returns empty)
                                             # but org-scope read is denied
```

The Codespaces-issued token has `repo` access but not `project`
scope. The pre-flight checklist text in the command does mention
"GitHub personal access token with repo, project, and workflow
permissions," but the devcontainer does not provision such a token —
it relies on the Codespaces default `GITHUB_TOKEN`. There is no
scripted path from "I just opened the Codespace" to "I have a token
that works for projectsV2."

**Expected:** Either Phase 4 detects the scope gap and prints a
single, clear remediation step, or the template documents how to mint
and inject a higher-scope PAT for Codespaces (and how to do it
without leaking secrets across cohorts).

**Suggested upstream fix:**

1. Add a pre-flight scope probe (e.g.
   `gh api graphql -f query='{ viewer { projectsV2(first:1) { totalCount } } }'`)
   and print a precise remediation message on failure, including the
   exact PAT scopes required.
2. Add a `scripts/setup-bootstrap-pat.sh` (or similar) that prompts
   the user, runs `gh auth login --scopes project,read:project`, and
   confirms the new scopes — analogous to `scripts/setup-solo-mode.sh`.
3. In `docs/GETTING-STARTED.md`, add a "Phase 4 prerequisites"
   subsection. Right now Phase 4's prerequisites are listed only
   inside the slash-command file, which is read late.

---

### 3. Branch protection cannot be configured by the bootstrap token

**Where:** Phase 4, step 2 ("Branch Protection Configuration"), says:

> Verify or configure branch protection on `main`.

**Observed:**

```text
$ gh api repos/vibeacademy/kira-kim-11/branches/main/protection
{"message":"Resource not accessible by integration", ...
 "status":"403"}
```

The default `GITHUB_TOKEN` cannot read or write branch protection on
the repo, even though the user has ADMIN
(`viewerPermission: "ADMIN"`).

**Expected:** Either the bootstrap pre-creates protection (via a
scripted workflow that runs once with elevated auth), or the command
explicitly tells the user this step requires the UI and gives them
the click-path.

**Suggested upstream fix:**

- Same as item 2 (a `setup-bootstrap-pat.sh` that requests
  `repo` + `admin:repo_hook` + `project` scopes), OR
- Add a documented "manual fallback" block to the command that links
  directly to
  `https://github.com/<owner>/<repo>/settings/branches` and provides
  a copy-pasteable Settings → Branches checklist. Currently the
  command says "Configure manually in GitHub settings" only in the
  Troubleshooting section, which is not where the agent looks
  first.

---

### 4. `projectV2` boards cannot be created via the API by this token

**Where:** Phase 4, step 1.

**Observed:** `repository.projectsV2` is empty. The
`createProjectV2` GraphQL mutation requires `project` scope, which
the Codespaces token lacks (item 2). The user must therefore create
the board in the GitHub UI before Phase 4 can attach issues to it.

The command does provide the correct UI workflow for the
"Item closed → Status: Done" toggle (and correctly notes that
`createProjectV2Workflow` does not exist in the API), but it does
**not** include the equivalent UI walkthrough for *creating* the
board itself.

**Suggested upstream fix:** Add a section in
`.claude/commands/bootstrap-workflow.md` titled
"Manual: create the project board" that mirrors the existing
"Manual UI toggle (recommended)" section and includes:

1. Direct URL to `https://github.com/users/<user>/projects` (solo) or
   `https://github.com/orgs/<org>/projects` (multi-bot).
2. Required column names exactly as expected by the framework
   (`Icebox`, `Backlog`, `Ready`, `In Progress`, `In Review`, `Done`)
   so the agent and human agree on column casing.
3. Instructions to attach the project to the repository so the agent
   can reach it via `repository.projectsV2`.

---

## Setup gaps (template ships partial state)

### 5. Pre-push hook is "REQUIRED" but never installed

**Where:** `CLAUDE.md` Critical Requirements:

> ### Pre-push Hook (REQUIRED)
> ```bash
> git config core.hooksPath scripts/hooks
> ```

**Observed:** Files exist at `scripts/hooks/pre-push`, but on a fresh
fork `git config core.hooksPath` returns empty. Nothing in the
devcontainer `postCreateCommand`, in `bootstrap.sh`, in
`scripts/setup-solo-mode.sh`, or in any of the four `/bootstrap-*`
slash commands runs the `git config` line.

The hook is therefore a "required" control that is not enforced by
default — `--no-verify` is forbidden, but the hook isn't running
unless the user manually configures it.

**Suggested upstream fix:**

- Add `git config core.hooksPath scripts/hooks` to
  `.devcontainer/devcontainer.json`'s `postCreateCommand`, AND
- Add the same line to `scripts/setup-solo-mode.sh`, AND
- Have `/bootstrap-workflow` verify it is set as a pre-flight check
  (warn-and-fix, not warn-only).

---

### 6. Standard labels (`P0`/`P1`/`P2`/`P3`/`epic`) do not exist on the repo

**Observed:**

```text
$ gh api graphql -f query='{ repository(owner:"vibeacademy",name:"kira-kim-11") { labels(first:30) { nodes { name } } } }'
labels: bug, documentation, duplicate, enhancement, good first issue,
        help wanted, invalid, question, wontfix
```

These are GitHub's defaults. None of the priority or workflow labels
that the framework references exist. `/bootstrap-workflow` says
"Add priority labels (P0/P1/P2/P3)" without specifying that they
must be created first, and `/groom-backlog` and the
`agile-backlog-prioritizer` agent assume those labels exist.

**Suggested upstream fix:** Either pre-create labels via a one-time
script (a `scripts/setup-labels.sh` invoked by
`scripts/setup-solo-mode.sh`), or have `/bootstrap-workflow` create
them with explicit color and description before any issues are
opened. The label set should be canonical and documented in one
place — currently the closest thing is informal mentions in agent
files.

---

### 7. CLAUDE.md placeholders are never filled by any bootstrap phase

**Where:** `CLAUDE.md`, "Project-Specific Configuration":

```markdown
- **Project Name**: [Your project name]
- **Repository**: [GitHub repo URL]
- **Project Board**: [GitHub project board URL]
- **Organization**: [GitHub org name]
```

**Observed:** All four still contain the bracketed placeholders after
Phases 1-3. Phase 2 says "This phase also updates CLAUDE.md with
project-specific configuration" and Phase 4 says
"CLAUDE.md Finalization", but neither command's body lists the
specific keys to update, and the agent has no deterministic way to
derive them from the PRD or the architecture doc (the org/repo
information must come from `git remote` or be supplied by the user).

Result: a real fork ships with `[Your project name]` in CLAUDE.md and
that string is then loaded into the system prompt of every subsequent
session.

**Suggested upstream fix:**

- Move repo/org/project-board placeholders into a single block
  named, e.g., `<!-- bootstrap:project-config -->`, and have a
  scripted step in `bootstrap.sh` (or a `postCreateCommand`) populate
  them from `git remote` + a one-line user prompt.
- Phase 4's command body should explicitly enumerate the CLAUDE.md
  keys it owns and either edit them or leave them blank if not yet
  available.

---

## Documentation / command consistency issues

### 8. Phase 1 command's output template diverges from the in-repo template file

**Where:** `.claude/commands/bootstrap-product.md` defines
"Output Templates" for `docs/PRODUCT-REQUIREMENTS.md` and
`docs/PRODUCT-ROADMAP.md`. The actual template files in `docs/` (which
ship with the fork) have a richer structure: Non-Functional
Requirements, Dependencies, Risks, Glossary, Revision History, etc.
None of those fields are present in the command's "Output Templates."

**Observed:** I had to merge the two — the command instructs the
agent to overwrite with a thinner structure, but the existing template
has fields a real PRD needs.

**Suggested upstream fix:** Pick one source of truth. Either:

- Treat the in-repo template as canonical and have the slash command
  reference it (`Read docs/PRODUCT-REQUIREMENTS.md, fill in the
  placeholders`), OR
- Treat the slash command's template as canonical and reduce the
  in-repo template to match.

Same comment applies to `docs/PRODUCT-ROADMAP.md`.

---

### 9. Phase 2 says "Launch the system-architect agent" but custom subagents may not be loadable

**Where:** `.claude/commands/bootstrap-architecture.md` opening line:
"Launch the system-architect agent…"

**Observed:** In this Codespace's Claude Code session, the available
`subagent_type` values for the `Agent` tool were
`claude-code-guide`, `Explore`, `general-purpose`, `Plan`, and
`statusline-setup`. The `.claude/agents/system-architect.md` file
defines a project agent, but it was not exposed as a launchable
subagent. Other people's CC environments may differ — but if the
template intends `/bootstrap-architecture` to dispatch to a custom
agent, that integration is not visibly working out-of-the-box.

(Notably, `/bootstrap-agents` later does the right thing by editing
the agent files directly, so the inconsistency is between
`/bootstrap-architecture` (delegates) and `/bootstrap-agents` (edits
inline).)

**Suggested upstream fix:** Either verify that all `.claude/agents/*`
files are loaded as subagents in the workshop default environment and
document how to confirm it (`claude --list-agents` or similar), or
rewrite Phase 2's command to act inline like Phase 3 does. The
mismatch confuses the agent driving the slash command.

---

### 10. `bootstrap.sh` vs `/bootstrap-*` slash commands — relationship undocumented

**Where:** Both `/bootstrap-architecture` and `/bootstrap-agents`
end with "When complete, run `bash bootstrap.sh` to continue to
Phase X." But there is also a sequence of slash commands
(`/bootstrap-product`, `/bootstrap-architecture`, `/bootstrap-agents`,
`/bootstrap-workflow`) that fully covers the same phases.

**Observed:** It's unclear whether `bootstrap.sh` is a wrapper, an
alternative path, or required glue. A user following the slash
commands literally never invokes `bootstrap.sh`, but it's referenced
as a continuation step.

**Suggested upstream fix:** Pick one path and remove the other from
prompts (or document them as alternatives with explicit "do A *or* B,
not both" guidance). The current text reads as "do both," which
isn't what's intended.

---

### 11. Pre-flight check #2 references a script that does not exist at the path implied

**Where:** `.claude/commands/bootstrap-workflow.md` pre-flight check
#2:

> "If only a personal account is active, STOP and instruct the user to
> run `scripts/ensure-github-account.sh`."

**Observed:** The actual file is at
`.claude/hooks/ensure-github-account.sh`, not
`scripts/ensure-github-account.sh`. (See `ls .claude/hooks/`.)

**Suggested upstream fix:** Update the path in the slash command, or
add a thin `scripts/ensure-github-account.sh` shim that calls the
hook so both paths work.

---

### 12. Solo mode pre-flight is misleading

**Where:** Pre-flight check #2 says to STOP if "only a personal
account is active." But solo mode is the default for new forks and is
explicitly the supported configuration in this template (see
`CLAUDE.md`: "Solo mode is the default" and
`AGILE_FLOW_SOLO_MODE=true` in the devcontainer).

**Observed:** A literal reading of pre-flight check #2 forces a STOP
on every solo-mode session because there *is* only a personal
account. The check needs to branch on `AGILE_FLOW_SOLO_MODE`.

**Suggested upstream fix:** Rewrite check #2 to read:

> "If `AGILE_FLOW_SOLO_MODE=true`, the user's personal account IS the
> expected account. Otherwise, verify the active account matches the
> configured worker bot."

(That logic already exists inside the agent files —
`.claude/agents/github-ticket-worker.md` and
`.claude/agents/pr-reviewer.md` both branch correctly on solo mode.
The pre-flight check should match.)

---

### 16. Workshop fork model creates a user-project-vs-org-repo mismatch

**Where:** `.claude/commands/bootstrap-workflow.md`, step 1
("GitHub Project Board Setup") and the manual UI-toggle guidance.

**Observed:** Workshop attendees fork `vibeacademy/agile-flow-gcp`
into the same org (`vibeacademy/<attendee-name>`), so the repo is
**org-owned**. But Phase 4 instructs the attendee to create the
project at `https://github.com/users/<attendee>/projects` — a
**user-scoped** project. User-scoped projects can only natively
discover repos that the project owner controls, so when the
attendee opens the project's "Add items from a repository"
dropdown or the auto-add workflow's repo filter, the fork does
**not appear**. Two consequences:

1. The "Add items from a repository" bulk-import flow is unusable.
   Workaround: paste each issue URL one at a time into the column
   input row (works because user projects accept items from any
   public issue by URL, even if the repo isn't in the dropdown).
2. The "Auto-add to project" workflow cannot be configured to
   target the org repo. Every new issue requires manual board-add
   for the lifetime of the project.

This breaks two of the bootstrap's promises at once: bulk seeding
and auto-add. The framework still functions (board kanban and
slash commands work once items are on the board), but every issue
created downstream needs a manual paste.

**Suggested upstream fix:**

- **Default to org-scoped projects when the repo is org-owned.** If
  Phase 4 detects `gh repo view --json owner --jq .owner.login` is
  an organization, instruct the attendee to create the project at
  `https://github.com/orgs/<org>/projects/new` instead of
  `https://github.com/users/<attendee>/projects/new`. Org projects
  see all org repos natively.
- If creating an org-scoped project requires permissions the
  attendee doesn't have (typical for forks into a
  workshop-organizer-owned org), Phase 4 must say so explicitly and
  document the URL-paste workaround for the user-project case.
- Update the "Manual UI toggle" sections to include both flows —
  one for the org-project case (auto-add works) and one for the
  user-project case (auto-add doesn't work; manual add only).

---

### 17. Codespaces `GITHUB_TOKEN` cannot manage Actions secrets either

**Where:** Hit when adding Neon secrets needed for the per-PR Neon
branching CI flow.

**Observed:**

```text
$ gh secret set NEON_API_KEY --repo vibeacademy/kira-kim-11
failed to fetch public key: HTTP 403: Resource not accessible by
integration
(https://api.github.com/repos/.../actions/secrets/public-key)
```

The Codespaces-issued `GITHUB_TOKEN` has `repo` access to
*content* but not to Actions `secrets` or `variables`. This is the
same root cause as items 2-4 — the token is scoped for code, not
ops — but it is a *new* surface: setting up CI secrets is a
prerequisite for any preview deploy, and the framework's preview
flow assumes Neon secrets are configured.

**Suggested upstream fix:** Add a section to `docs/SECRETS.md` (or
to `docs/PLATFORM-GUIDE.md`'s Neon section) titled "Setting CI
secrets in a Codespace fork" that explicitly tells attendees the
default token won't work and gives them two recipes:

1. UI fallback (direct URL to repo Actions Secrets page, list of
   names to add).
2. CLI fallback: `unset GITHUB_TOKEN && gh auth login --scopes
   repo,workflow` then `gh secret set …`.

Otherwise the first attendee to try `gh secret set` after
following the bootstrap flow hits a 403 with no documented next
step. (The error message is generic enough that they're unlikely
to figure out it's a scope issue, not a permission issue.)

---

### 18. Auto-add workflow does not backfill existing issues

**Where:** Phase 4, step 1.5
("Enable Auto-Move-to-Done Workflow") — and by extension the
"Auto-add to project" workflow that is enabled in the same UI
panel.

**Observed:** When attendees enable "Auto-add to project" *after*
issues have already been created (the natural order if Phase 4 is
run before the board exists, which is the default), the workflow
applies only to issues created from that moment on. None of the
9 issues created in this run landed on the board automatically
even though the workflow was correctly configured — they had to
be added manually by URL paste.

**Suggested upstream fix:**

- Phase 4's instructions should explicitly sequence as:
  (1) create the project board, (2) enable both auto-add and
  item-closed workflows, (3) *then* create issues. Any deviation
  from this order leaves issues stranded.
- Alternatively, after creating issues, add a closing step:
  "Bulk-add existing issues to the board by pasting their URLs
  into a column's add-item input row, since auto-add does not
  backfill."

Without one of these, the bootstrap creates issues that are
invisible to `/sprint-status` until manually rescued.

---

## Smaller issues from earlier phases

These didn't block, but came up while running Phases 1-3 and are worth
fixing alongside the above.

### 13. Phase 1 (`/bootstrap-product`) doesn't mention what to do if `docs/PRODUCT-REQUIREMENTS.md` already exists

The template ships with a populated-template version of both
PRD/roadmap files. The slash command's "After Collecting All Responses"
section only says "synthesize the responses into two documents" — it
doesn't tell the agent to first read the existing template files
(which contain richer scaffolding) and fill them in. See item 8.

### 14. Phase 3 (`/bootstrap-agents`) doesn't enumerate which agents need updates

The command lists 5 agents but the template ships 7
(`.claude/agents/`: agile-backlog-prioritizer, agile-product-manager,
devops-engineer, github-ticket-worker, pr-reviewer, quality-engineer,
system-architect). Specifically `agile-backlog-prioritizer` and
`devops-engineer` are not mentioned. They may legitimately not need
project-specific blocks, but the omission isn't called out, so the
agent has to decide on its own whether to skip them. (I skipped them
on the grounds that they had no `TEMPLATE:` markers and the command
didn't list them — that judgment should not be the agent's to make.)

**Suggested fix:** Phase 3's command should explicitly say "these N
agents have project-specific blocks; these M agents are
config-driven and don't need edits."

### 15. Phase 1 commits the user's MAU target without checking it's well-formed

The questionnaire accepts `100` as a free-form answer for "3-month
target" without confirming a unit (users? bids? listings?). I
inferred "100 active users" from context, but a stricter prompt
would prevent ambiguity downstream when the metric shows up in the
roadmap and in DoD wording.

**Suggested fix:** Reformulate Q5.2 as `"<NUMBER> <unit>"` with an
example matching the metric chosen in Q5.1.

---

## Suggested upstream punch list

In rough priority order:

1. **Fix the Phase 4 pre-flight to match what the template actually
   ships** (items 1, 11, 12). Without this, the phase STOPs on every
   fresh fork.
2. **Provide a one-shot path to a workable token** (items 2, 3, 4,
   17): either a `setup-bootstrap-pat.sh` that requests the
   necessary scopes (`repo`, `workflow`, `project`,
   `admin:repo_hook` for branch protection,
   plus secrets-write), or a documented manual sequence with
   explicit UI click-paths and a script that verifies the result.
   Item 17 is the same root cause but appears later in the
   workflow, when CI secrets need to be set.
3. **Detect org-vs-user repo ownership and route project-board
   creation accordingly** (item 16). Default to org-scoped projects
   when the repo is org-owned; document the user-project workaround
   when the attendee can't create org projects.
4. **Sequence Phase 4 so auto-add is enabled before issues are
   created, OR add a backfill step** (item 18). The current
   ordering creates orphaned issues.
5. **Auto-install the pre-push hook** (item 5).
6. **Pre-create canonical labels** (item 6).
7. **Make CLAUDE.md placeholder filling a scripted step** (item 7).
8. **Reconcile the two PRD/Roadmap templates** (items 8, 13).
9. **Decide whether `/bootstrap-architecture` dispatches to the
   `system-architect` subagent or acts inline, and align the command
   text** (item 9).
10. **Document or remove the `bootstrap.sh` continuation references**
    (item 10).
11. **Enumerate which agents Phase 3 should and should not touch**
    (item 14).
12. **Tighten Q5.2's input format** (item 15).

---

## What works well (for context)

- Phases 1-3 ran end-to-end without blocking.
- The agent files in `.claude/agents/` are well-structured and the
  `TEMPLATE:` markers made specialization mechanical.
- `docs/TICKET-FORMAT.md` is genuinely good: clear, opinionated, and
  the "where each section comes from" table makes generation
  deterministic.
- Solo-mode handling inside the worker/reviewer agent files is
  already correct; pre-flight just needs to match.
- The "Manual UI toggle (recommended)" section for the Item-closed
  workflow (with the explicit click path and the API-research
  pointer to issue #86) is the right pattern; replicating it for
  branch protection and project-board creation would close most of
  the Phase 4 gaps.

---

## Reproduction transcript (abridged)

For the upstream Claude session, here is the exact sequence that hit
each blocker:

```text
$ git remote -v
origin  https://github.com/vibeacademy/kira-kim-11 (fetch/push)

$ gh auth status
✓ Logged in to github.com account kira-kim-11 (GITHUB_TOKEN)
  - Active account: true

$ gh project list --owner vibeacademy
GraphQL: Resource not accessible by integration ...      # item 2

$ gh api repos/vibeacademy/kira-kim-11/branches/main/protection
{"message":"Resource not accessible by integration","status":"403"}   # item 3

$ gh api graphql -f query='... projectsV2(first:5) { nodes { id title } } ...'
projectsV2: nodes: []                                    # item 4 (no board)

$ git config core.hooksPath
(empty)                                                   # item 5

$ gh api graphql -f query='... labels(first:30) ...'
default GitHub labels only                                # item 6

$ grep -n "\[Your" CLAUDE.md
168:- **Project Name**: [Your project name]
169:- **Repository**: [GitHub repo URL]
170:- **Project Board**: [GitHub project board URL]
178:- **Organization**: [GitHub org name]              # item 7

$ cat .mcp.json
{ "mcpServers": { "memory": ..., "sequential-thinking": ... } }   # item 1
```

End of report.
