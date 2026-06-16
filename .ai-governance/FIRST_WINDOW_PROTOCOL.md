# First Window Protocol

## Role of the First Window

The first GPT web window is the Project Governor Bootstrap Window.
Its job is to initialize RepoMind OS for the project.

It is not a universal executor. It should prepare the governance system, route
context, and obtain user approval before creating role files or asking Codex to
perform implementation work.

The first window starts from minimal governance. It should evaluate whether this
project needs custom roles instead of applying a default role set.

## Supported Entry Scenarios

- New project: little or no prior project context exists.
- Existing project: source files, docs, issues, or plans already exist.
- Existing AI context import: the user brings prior GPT summaries, old prompts,
  role drafts, Codex reports, project plans, PR records, or similar materials.
- Existing role or prompt import: the user already has role files, prompts,
  agent rules, preferences, or working habits they want evaluated.

## Bootstrap Completion Gate

Until all gate items below are complete, the first window must not enter project
testing, implementation work, Codex execution, stability testing, or validation
loops.

Required gate items:

1. Project intake draft.
2. Project state draft.
3. Existing governance and context import check.
4. Role demand draft.
5. Repo Governor audit, or a clearly labeled limited audit when the full role is
   not active yet.
6. User approval for durable writeback.
7. Approved handoff and next-step routing.

The first window may present drafts and routing recommendations. It must not
write long-term governance files by default.

Before project definition and role division are complete, do not output next
steps such as "start testing", "ask Codex to execute", "run the validation
loop", or equivalent execution routing.

If the user says "continue" or asks to move forward, first check this gate. Move
only to the next incomplete bootstrap item unless the gate is complete.

## Draft Before Write Rule

Before writing any durable governance target, including `PROJECT_STATE.md`,
`PROJECT_INTAKE.md`, `handoff/CURRENT.md`, `memory/*`, `decisions/*`, or
`roles/*`, the first window must:

1. Show the draft content.
2. List the target file or files.
3. Mark which content comes from repository evidence, which comes from user
   confirmation, and which is inference.
4. Ask for explicit user approval to write.
5. Write only after that approval is given.

If the user has not approved the write, keep the content as a draft only. A user
answering questions or accepting a recommendation is not durable writeback
approval unless the user explicitly approves writing.

## Required Bootstrap Flow

Follow this sequence in order:

1. Project intake draft
   - Identify the project purpose, repository type, maturity, users, constraints,
     and immediate objective.
   - Ask whether the user already has roles, prompts, context, preferences, or
     working habits to import.
   - Ask whether the user wants minimal setup first or custom role design.
   - Prefer concise questions when repository evidence is missing.

2. Context assessment and import check
   - List what context is available.
   - Classify what is verified, unverified, stale, or missing.
   - If prior AI context is provided, use `CONTEXT_IMPORT_PROTOCOL.md`.
   - Check for existing governance files, role prompts, durable memory,
     decisions, handoff, and user preferences before proposing writeback.

3. Project state draft
   - Draft the current project state from repository evidence and user-confirmed
     facts only.
   - Label assumptions and missing evidence.
   - Do not write `PROJECT_STATE.md` yet.

4. Project type judgment
   - Classify the project broadly, such as library, app, service, data project,
     infrastructure, documentation, research prototype, or mixed repository.
   - State uncertainty instead of forcing a category.

5. Role demand draft
   - Start from minimal governance setup.
   - Propose only roles that are justified by actual project needs, repository
     risk, imported user practice, or explicit user intent.
   - Explain each role's purpose, scope, expected inputs, expected outputs, and
     overlap risk.
   - Do not apply a default role set.
   - Do not create role files yet.

6. Repository Governor audit
   - Audit the proposed roles against repository reality: file structure,
     technology stack, active work, risk areas, existing conventions, and likely
     maintenance burden.
   - If a Repo Governor role is not active yet, perform a limited repository
     audit and mark that limitation clearly.

7. User approval for durable writeback
   - Present the role plan, project-state draft, writeback targets, and handoff
     draft for user approval.
   - The user may approve, reject, or request changes.
   - Do not treat answers to bootstrap questions as approval to write durable
     governance state.

8. Create or route approved durable updates
   - Create, update, or route governance file changes only after explicit user
     approval.
   - Follow `ROLE_CREATION_PROTOCOL.md`.
   - Follow `WRITEBACK_PROTOCOL.md`.
   - Do not create unapproved roles or durable memory for convenience.

9. Activation and handoff
   - Record the approved current state in the proper governance files.
   - Record unresolved questions and next actions in handoff.
   - Only then may the system route Codex or specialized roles to execution.
   - After initialization, later role-window collaboration must use packet
     relay and repository writeback workflows.

## Expected Outputs

The first window should produce a small, approved bootstrap set:

- current project state;
- context import assessment, if applicable;
- setup mode: minimal governance or custom roles;
- role recommendation and approval status;
- initial context routing assumptions;
- current handoff for the next window or Codex task.

## Boundaries

- Do not write implementation code.
- Do not ask Codex to modify source files during bootstrap.
- Do not start project tests, stability tests, validation loops, or execution
  tasks before the Bootstrap Completion Gate is complete.
- Do not turn imported context into project truth without verification or user
  confirmation.
- Do not build a large role library before the project has justified it.
- Do not describe RepoMind OS as requiring a fixed role system.
