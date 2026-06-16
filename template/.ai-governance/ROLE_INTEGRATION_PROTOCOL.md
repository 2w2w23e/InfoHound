# Role Integration Protocol

## Purpose

This protocol defines Existing Role Integration Mode.

Use it to onboard a project that already has role files, old prompts, agent
rules, role-specific user preferences, working habits, or another AI governance
system.

Core rule:

```text
Existing roles are project assets, not obstacles.
```

RepoMind OS must discover, classify, and evaluate existing roles before it
creates or activates RepoMind default roles.

## When This Protocol Applies

Use this protocol before project testing, stability validation, Codex execution,
code-change recommendations, or role creation when any of these are present:

- existing role files;
- old GPT or AI prompts;
- `AGENTS.md` or agent instructions;
- AI rules, workflow rules, or governance notes;
- role-specific user preferences or working habits that define role behavior,
  authority, file access, or execution style;
- Codex reports that describe role behavior;
- imported project governance summaries.

Do not trigger this protocol only because a project has generic user preference
files about language, tone, formatting, or answer style. Route those to
`PREFERENCE_PROTOCOL.md` unless they materially affect role authority, role
responsibilities, repository reads, writeback, or Codex boundaries.

If imported context contains role or prompt behavior, route it here from
`CONTEXT_IMPORT_PROTOCOL.md`.

If no existing role material is found, record that finding in the bootstrap
draft and continue with minimal role foundation.

## Existing Role Discovery

Discover first. Do not rewrite first.

Check user-provided materials, repository governance files, existing role
folders, prompts, `AGENTS.md`, role-specific user preference notes, handoff
files, memory, decisions, and anti-pattern files when available.

For each discovered role-like source, record:

- source path or source description;
- source type;
- apparent owner or intended user;
- freshness, if known;
- responsibilities;
- authority limits;
- inputs and outputs;
- safety boundaries;
- overlap with RepoMind OS roles;
- uncertainty and missing evidence.

Do not treat raw private chat as repository-ready material. Summarize only the
rules, experience, decisions, or anti-patterns that the user approves.

## Role Source Classification

Classify by behavior, not by name.

For each source, evaluate:

- responsibilities;
- authority;
- allowed writes;
- required inputs;
- expected outputs;
- approval requirements;
- memory or context dependencies;
- handoff rules;
- risks from stale, broad, or unsafe instructions.

Do not merge roles only because their names look similar.

## Role Compatibility Actions

Only four compatibility actions are allowed:

- `preserve`: keep the role as an active project asset.
- `wrap`: keep the original role text and add a RepoMind OS adapter layer.
- `merge`: combine overlapping or conflicting responsibilities into an approved
  target role.
- `deprecate / suspend`: keep the source readable but mark it inactive unless
  the user approves deletion.

Prefer `preserve` or `wrap` when the old role has useful project knowledge.

Use `merge` only when responsibilities, authority, inputs, outputs, or risk
boundaries overlap enough to justify it.

Use `deprecate / suspend` for stale, duplicate, unsafe, or rejected roles.

Mark a source as `unsafe legacy role` if it permits unbounded modification,
automatic commits, bypassing user approval, broad secret handling, or authority
that conflicts with RepoMind OS boundaries. Ask the user before using it.

The original text of a valuable old role should be preserved when possible.
Do not overwrite it just to fit the RepoMind OS template.

## Role Adapter Layer

When an existing role is preserved or wrapped, add or draft an adapter layer
with at least these fields:

```text
Role Identity
Original Source
Owns
Does Not Own
Required Read Order
Long-term Memory Lookup
Experience / Anti-pattern Lookup
Answer Header Requirement
Writeback Rules
Codex Boundary
Stop Conditions
```

The adapter layer supplies missing RepoMind OS boundaries without deleting the
old role's useful content.

If the old role lacks safety boundaries, add boundaries through the adapter
layer. Do not delete the role only because it lacks the new fields.

## Required Read Order Upgrade

Each active role must know which repository files to read before each
substantive answer.

At minimum, an active role needs:

- its own role file or adapter;
- `BOOT.md`;
- `CONTEXT_INDEX.md`;
- current project state and intake files when relevant;
- `handoff/CURRENT.md` when current status matters;
- task-specific decisions, memory, anti-patterns, or user preferences.

The read order must be explicit before the role is activated.

## Long-term Memory and Experience Lookup Upgrade

Each active role must know where to look before answering repeated or risky
questions.

The lookup rules must cover:

- `PROJECT_STATE.md`;
- `PROJECT_INTAKE.md`;
- `handoff/CURRENT.md`;
- relevant `memory/*`;
- relevant `decisions/*`;
- relevant `anti_patterns/*`;
- relevant `user_preferences/*`.

If no memory file is read for an answer, the role must say so in the Context
Refresh Header.

If the memory path was checked and empty, the role must say it was checked but
empty.

Useful experience from an old role should become a role adapter, memory draft,
decision draft, or anti-pattern draft. It must not be silently lost.

## Conflict Detection

Detect conflicts before recommending execution.

Conflicts include:

- two roles claiming the same decision authority;
- a role allowing writes that RepoMind OS requires user approval for;
- stale instructions contradicting current project state;
- prompts that bypass context refresh;
- prompts that allow automatic commit, push, release, or broad file edits;
- instructions that treat private chat as durable repository truth;
- missing stop conditions or Codex boundaries.

Do not resolve conflicts silently. Produce a draft recommendation and ask the
user to approve the compatibility action.

## Role Registry Draft

Before writeback, produce a role registry draft.

The draft should include:

- source;
- proposed active role name;
- compatibility action: `preserve`, `wrap`, `merge`, or `deprecate / suspend`;
- owns;
- does not own;
- required read order;
- long-term memory lookup;
- Codex boundary;
- risks;
- user decision needed.

This registry is a draft until the user approves durable writeback.

## User Approval Gate

Before explicit user approval, RepoMind OS must not:

- create role files;
- delete role files;
- rewrite role files;
- merge role files;
- rename role files;
- replace old roles with RepoMind default roles;
- mark a role active or inactive in durable state.

Before approval, only drafts are allowed.

If the user says "continue" while integration is incomplete, continue the role
integration work. Do not route to implementation, testing, stability validation,
or Codex execution.

## Stop Conditions

Stop and ask the user before proceeding when:

- an existing role or prompt has not been classified;
- a compatibility action would change, merge, suspend, or delete a role;
- a role appears unsafe or conflicts with user approval requirements;
- the original source is private chat or unclear imported material;
- Required Read Order or Long-term Memory Lookup is missing for an active role;
- the user asks for execution before Foundation Complete is reached;
- durable writeback is needed but not approved.
