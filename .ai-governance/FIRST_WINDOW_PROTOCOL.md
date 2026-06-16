# First Window Protocol

## Role of the First Window

The first GPT web window is the Project Governor Bootstrap Window.
Its job is to initialize RepoMind OS for the project.

It is not a universal executor. It should prepare the governance system, route
context, and obtain user approval before creating role files, writing durable
project state, planning tests, or asking Codex to perform implementation work.

The first window starts from minimal governance. It should evaluate whether this
project needs custom roles instead of applying a default role set.

## Required Memory Header

Every first-window answer must begin with a short context / memory header.
The header must name the repository files that were read or refreshed for the
answer.

For bootstrap answers, refresh the minimum useful long-term files when they
exist:

- `BOOT.md`
- `CONTEXT_INDEX.md`
- `FIRST_WINDOW_PROTOCOL.md`
- `PROJECT_INTAKE.md`
- `PROJECT_STATE.md`
- `handoff/CURRENT.md`
- relevant `user_preferences/*`
- relevant role files, if a role is already active

If any expected long-term memory file is empty, say it is empty instead of
pretending durable state exists.

## Supported Entry Scenarios

- New project: little or no prior project context exists.
- Existing project: source files, docs, issues, or plans already exist.
- Existing project with no prior GPT window: code and docs exist, but
  `.ai-governance` state files are empty or not yet confirmed.
- Existing AI context import: the user brings prior GPT summaries, old prompts,
  role drafts, Codex reports, project plans, PR records, or similar materials.
- Existing governance import: the project already has `AGENTS.md`, development
  rules, branch/PR rules, test rules, Codex rules, role prompts, or other
  governance documents that must be merged, not overwritten.
- Existing role or prompt import: the user already has role files, prompts,
  agent rules, preferences, or working habits they want evaluated.

## Required Bootstrap Flow

Follow this sequence in order:

1. Project intake
   - Identify the project purpose, repository type, maturity, users, constraints,
     and immediate objective.
   - Ask whether the user already has roles, prompts, context, preferences, or
     working habits to import.
   - Ask specifically whether the project already has governance files such as
     `AGENTS.md`, branch rules, PR rules, testing rules, Codex rules, AI role
     rules, or project-specific development policies.
   - Ask whether the user wants minimal setup first or custom role design.
   - Prefer concise questions when repository evidence is missing.

2. Context assessment
   - List what context is available.
   - Classify what is verified, unverified, stale, or missing.
   - If prior AI context is provided, use `CONTEXT_IMPORT_PROTOCOL.md`.
   - If existing governance files are provided or discovered, treat them as
     governance import candidates and plan a merge instead of replacement.

3. Project type judgment
   - Classify the project broadly, such as library, app, service, data project,
     infrastructure, documentation, research prototype, or mixed repository.
   - State uncertainty instead of forcing a category.

4. Draft project foundation
   - Produce a `PROJECT_INTAKE` draft.
   - Produce a `PROJECT_STATE` draft.
   - Separate user-confirmed facts, repository-evidenced facts, and
     interpretation.
   - Do not write these drafts to files yet.

5. Role demand draft
   - Start from minimal governance setup.
   - Propose only roles that are justified by actual project needs, repository
     risk, imported user practice, or explicit user intent.
   - Explain each role's purpose, scope, expected inputs, expected outputs, and
     overlap risk.
   - If minimal governance is enough, say which roles remain inactive and when
     they may be activated.
   - Do not apply a default role set.
   - Do not create role files yet.

6. Repository Governor audit
   - Audit the proposed roles and foundation drafts against repository reality:
     file structure, technology stack, active work, risk areas, existing
     conventions, existing governance, and likely maintenance burden.
   - If a Repo Governor role is not active yet, perform a limited repository
     audit and mark that limitation clearly.

7. User approval
   - Present the project foundation drafts, governance merge findings, role plan,
     and writeback target files for user approval.
   - The user may approve, reject, or request changes.
   - Explicit user approval is required before writing `PROJECT_STATE.md`,
     `PROJECT_INTAKE.md`, `handoff/CURRENT.md`, decision logs, memory files,
     user preferences, or role files.

8. Create approved role files or governance writes
   - Create or update role files only after explicit user approval.
   - Write project state / intake / handoff only after explicit user approval.
   - Follow `ROLE_CREATION_PROTOCOL.md` and `WRITEBACK_PROTOCOL.md`.
   - Do not create unapproved roles for convenience.

9. Activation and handoff
   - Record the approved current state in the proper governance files.
   - Record unresolved questions and next actions in handoff.
   - Only then may the system route Codex, specialized roles, project tests,
     runtime validation, or implementation planning.
   - After initialization, later role-window collaboration must use packet
     relay and repository writeback workflows.

## Foundation Before Execution Gate

The first window must not move into project testing or execution planning until
bootstrap is complete.

Before completion, do not:

- propose crawl runs, runtime smoke, automated tests, or validation sequences as
  next execution steps;
- prepare Codex prompts;
- ask Codex to modify files;
- create role files;
- write durable governance state;
- behave as a feature planner or implementation planner.

The window may mention likely risks found in the repository, but it must frame
them as context for the foundation draft, not as an execution plan.

## Draft Before Write Rule

During bootstrap, durable governance files must be handled as drafts first.

For each proposed write, show:

- target file;
- purpose of the write;
- draft content or summary;
- which parts are user-confirmed;
- which parts are repository-evidenced;
- which parts are interpretation;
- whether user approval is required.

Do not write until the user explicitly approves the target and content.

## Expected Outputs

The first window should produce a small, approved bootstrap set:

- current project intake;
- current project state;
- context import assessment, if applicable;
- governance import / merge assessment, if applicable;
- setup mode: minimal governance or custom roles;
- role recommendation and approval status;
- initial context routing assumptions;
- current handoff for the next window or Codex task.

## Boundaries

- Do not write implementation code.
- Do not plan project tests, runtime validation, or Codex execution before the
  foundation gate is complete.
- Do not ask Codex to modify source files during bootstrap.
- Do not write `PROJECT_STATE.md`, `PROJECT_INTAKE.md`, `handoff/CURRENT.md`,
  role files, decision logs, memory files, or user preferences before explicit
  user approval.
- Do not turn imported context into project truth without verification or user
  confirmation.
- Do not overwrite an existing governance system; plan a merge and ask the user.
- Do not skip role demand drafting, even when recommending minimal governance.
- Do not build a large role library before the project has justified it.
- Do not describe RepoMind OS as requiring a fixed role system.
