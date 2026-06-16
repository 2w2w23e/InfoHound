# Writeback Protocol

## Purpose

Writeback turns useful work from temporary chat into durable repository state.
It protects the project from losing decisions, handoff status, role changes, and
reusable lessons when a GPT window is closed.

## Core Rules

- Temporary chat conclusions do not automatically become long-term memory.
- A role may recommend writeback.
- The Project Governor / Main Brain evaluates the recommendation.
- The user approves long-term writeback when it changes project direction,
  durable decisions, role authority, or shared memory.
- Write the smallest durable update that preserves the useful state.
- Durable governance writeback requires draft first, approval second, write
  third.

## Writeback Types

- `NO_WRITEBACK`: no repository update is needed.
- `HANDOFF_UPDATE`: update current work status or next steps.
- `MEMORY_UPDATE`: add reusable project or role learning.
- `DECISION_LOG_UPDATE`: record an approved decision.
- `PROJECT_STATE_UPDATE`: update verified current project state.
- `PROJECT_INTAKE_UPDATE`: update approved project intake facts.
- `ROLE_UPDATE`: update an approved role file.
- `CONTEXT_INDEX_UPDATE`: update routing rules.
- `ANTI_PATTERN_UPDATE`: record recurring failure modes or traps.
- `USER_PREFERENCE_UPDATE`: update durable user preferences.

## Writeback Targets

- `handoff/CURRENT.md`: current status, next steps, blockers, and open questions.
- `memory/*.md`: reusable lessons for a role or project area.
- `decisions/YYYY-MM.md`: approved decisions grouped by month.
- `PROJECT_STATE.md`: verified current project state and confirmed direction.
- `PROJECT_INTAKE.md`: approved project intake, constraints, and setup facts.
- `roles/*.md`: approved role instructions.
- `CONTEXT_INDEX.md`: task-to-context routing.
- `memory/ANTI_PATTERNS.md`: recurring mistakes, traps, and prevention rules.
- `user_preferences/GLOBAL.md`: cross-project user preferences.
- `user_preferences/role_overrides/<ROLE>.md`: role-specific user preferences.

## Information That Should Be Written Back

- Approved decisions that affect future work.
- Verified project state that future windows need.
- Current handoff status needed by the next window.
- Reusable lessons that should guide repeated work.
- Role changes approved by the user.
- Context routing changes that reduce future confusion.
- Recurring risks or failure modes.
- User preferences confirmed for future tasks, roles, or projects.

## Information That Must Not Be Written Back

- secrets, tokens, API keys, passwords, or credentials;
- raw private chat transcripts;
- unnecessary personal information;
- unverified claims presented as truth;
- temporary speculation;
- copied third-party content when a short summary is enough;
- implementation details that are already clear from source files unless they
  affect governance or future coordination.
- user preferences that were not confirmed or were only task-local.

## Approval Rules

User approval is required for:

- project direction or scope updates;
- durable decisions;
- role creation, role authority changes, merges, splits, or deprecation;
- sensitive security or privacy guidance;
- memory entries that could change future behavior across tasks;
- user preference updates, unless the user explicitly requested future reuse,
  such as "always do this" or "use this in future projects".

Explicit write approval is not required for:

- preparing a non-durable draft;
- recommending writeback without writing it;
- marking `NO_WRITEBACK`.

A narrow handoff update or stale route correction still requires explicit write
approval if it writes a long-term governance file.

## Approval Gate

For long-term governance files, approval is a hard gate. The role or window must
first show the draft, list the target files, separate repository evidence from
user-confirmed facts and inference, and ask the user for permission to write.

Only explicit approval counts, such as "approve writeback", "approved to write",
"you may write", "write this", "agree to write", or equivalent clear permission.
A user answering questions, continuing the discussion, or accepting a
recommendation does not by itself approve durable writeback.

During first-window bootstrap, durable state writeback is disabled by default.
The first window may draft `PROJECT_STATE.md`, `PROJECT_INTAKE.md`,
`handoff/CURRENT.md`, `memory/*`, `decisions/*`, `roles/*`, or other governance
updates, but it must not write them until the Bootstrap Completion Gate and this
approval gate are both satisfied.

## Writeback Workflow

1. Classify the result into one or more writeback types.
2. Identify target files.
3. Prepare the draft content.
4. Remove forbidden content.
5. Separate verified evidence from user confirmation and inference.
6. If the result is a user preference, classify it with
   `PREFERENCE_PROTOCOL.md`.
7. Ask for explicit user approval when required.
8. Write only after approval is granted.
9. Prepare a Writeback Packet for Codex or the user when another actor will
   perform the write.
10. Validate that only target files changed.

Use `prompts/writeback_packet.md` and `checklists/writeback.md`.
