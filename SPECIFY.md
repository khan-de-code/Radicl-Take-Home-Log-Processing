# Specify Spec-Driven Development Workflow

This document serves as a reference guide for running Specify commands inside the **Antigravity (agy)** agent context, covering both the base Specify lifecycle and the newly installed extensions: `spec-kit-doctor`, `spec-kit-checkpoint`, and `spec-kit-memory-hub` (`memory-md`).

---

## 1. Initial One-Time Repository Setup

Before starting any feature, perform the following one-time setup steps in the repository:

1. **Establish Core Principles (Constitution)**:
   - **Command**: `/speckit-constitution`
   - **Purpose**: Creates or updates the core coding principles, tech stack constraints, quality gates, and governance policies in [.specify/memory/constitution.md](file:///home/dbatz/projects/Backend-Engineering-Excercise/.specify/memory/constitution.md) and propagates updates to templates.

2. **Initialize Markdown Memory**:
   - **Command**: `/speckit-memory-md-init`
   - **Purpose**: Creates the durable memory index and folders (`docs/memory/INDEX.md`, etc.) for capturing decisions, architectural constraints, and historical bug patterns.

---

## 2. Feature Lifecycle Workflow

When developing a new feature, follow this chronological order of commands:

### Phase 2A: Specification & Scope
1. **Start Specification**:
   - **Command**: `/speckit-specify <feature description>`
   - **Purpose**: Generates the feature directory (e.g., `specs/001-feature-name/`), copies the spec template, and initializes `spec.md`.
2. **Clarification** (If [NEEDS CLARIFICATION] markers are present in `spec.md`):
   - **Command**: `/speckit-clarify`
   - **Purpose**: Interactively prompts for answers to clarify requirements and updates `spec.md` directly.
3. **Generate Checklist**:
   - **Command**: `/speckit-checklist`
   - **Purpose**: Creates the spec quality checklist in `specs/<feature>/checklists/requirements.md`.

### Phase 2B: Context Synthesis & Planning
4. **Synthesize Memory**:
   - **Command**: `/speckit-memory-md-plan-with-memory` (or triggered automatically via hook `before_plan`)
   - **Purpose**: Evaluates project memory and the project [constitution.md](file:///home/dbatz/projects/Backend-Engineering-Excercise/.specify/memory/constitution.md) to generate `specs/<feature>/memory-synthesis.md`, flagging architectural/security conflicts.
5. **Create Plan**:
   - **Command**: `/speckit-plan`
   - **Purpose**: Generates the detailed technical design and logs it in `plan.md`.

### Phase 2C: Task Setup & Validation
6. **Generate Tasks**:
   - **Command**: `/speckit-tasks`
   - **Purpose**: Creates the actionable task breakdown in `tasks.md` with dependency ordering.
7. **Cross-Artifact Consistency Check**:
   - **Command**: `/speckit-analyze`
   - **Purpose**: Runs a sanity check verifying that `spec.md`, `plan.md`, and `tasks.md` align without gaps.

### Phase 2D: Implementation & Checkpoints
8. **Execute Tasks**:
   - **Command**: `/speckit-implement`
   - **Purpose**: Begins executing tasks from `tasks.md` in order.
9. **Checkpoint Progress (Mid-implementation)**:
   - **Command**: `/speckit-checkpoint-commit` (from the `checkpoint` extension)
   - **Purpose**: Automatically makes intermediate git commits for changes during implementation to avoid huge end-of-feature commits.

### Phase 2E: Quality & Memory Capture
10. **Analyze Diff & Capture Lessons**:
    - **Command**: `/speckit-memory-md-capture-from-diff` (or triggered automatically via hook `after_implement`)
    - **Purpose**: Scans code changes and guides you to record durable lessons, patterns, or decisions back into the repository memory index.
11. **Propose Lessons from Completed Work**:
    - **Command**: `/speckit-memory-md-capture`
    - **Purpose**: Proposes human-approved durable lessons and updates the memory index from completed work.

---

## 3. Maintenance & Diagnostics Commands

Run these utility commands at any time to verify system health:

- **Check Project Health**:
  - `/speckit-doctor-check` (or `/speckit-doctor`): Runs full project diagnostics on structures, features, scripts, and git state.
- **Audit Memory Structure**:
  - `/speckit-memory-md-audit`: Evaluates long-term memory quality, index alignment, and synthesis hygiene.
- **Node/Token Efficiency Check**:
  - `/speckit-memory-md-token-report`: Compares estimated token costs between full-memory scanning vs. optimized synthesis.
- **Update Agent Context**:
  - `/speckit-agent-context-update`: Refreshes the managed Spec Kit section in the coding agent context/instruction files.
- **Log Audit Findings**:
  - `/speckit-memory-md-log-finding`: Turns a high-signal audit finding into a tracker-ready follow-up issue for external systems (GitHub, GitLab, Jira, etc.).

---

## Configuration Reference

- **Extension Configurations**: [.specify/extensions/](file:///home/dbatz/projects/Backend-Engineering-Excercise/.specify/extensions/)
- **Hooks Configuration**: [extensions.yml](file:///home/dbatz/projects/Backend-Engineering-Excercise/.specify/extensions.yml)
- **Active Feature Status**: `.specify/feature.json`
