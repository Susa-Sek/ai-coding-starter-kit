# General Project Rules

## Feature Tracking
- All features are tracked in `features/INDEX.md` - read it before starting any work
- Feature specs live in `features/PROJ-X-feature-name.md`
- Feature IDs are sequential: check INDEX.md for the next available number
- One feature per spec file (Single Responsibility)
- Never combine multiple independent functionalities in one spec

## Git Conventions
- Commit format: `type(PROJ-X): description`
- Types: feat, fix, refactor, test, docs, deploy, chore
- Check existing features before creating new ones: `ls features/ | grep PROJ-`
- Check existing components before building: `git ls-files src/components/`
- Check existing APIs before building: `git ls-files src/app/api/`

## Human-in-the-Loop
- Always ask for user approval before finalizing deliverables
- Present options using clear choices rather than open-ended questions
- Never proceed to the next workflow phase without user confirmation

## Status Updates
- Update `features/INDEX.md` when feature status changes
- Update the feature spec header status field
- Valid statuses: Planned, In Progress, In Review, Deployed

## File Handling
- ALWAYS read a file before modifying it - never assume contents from memory
- After context compaction, re-read files before continuing work
- When unsure about current project state, read `features/INDEX.md` first
- Run `git diff` to verify what has already been changed in this session
- Never guess at import paths, component names, or API routes - verify by reading

## Handoffs Between Skills
- After completing a skill, suggest the next skill to the user
- Format: "Next step: Run `/skillname` to [action]"
- Handoffs are always user-initiated, never automatic

## Autonomous Orchestration

When `features/orchestration-status.json` exists, the system is running in **Programmatic Mode**:

### Detection
Skills detect programmatic mode by checking for the orchestration status file:
```
if (fs.existsSync('features/orchestration-status.json')) {
  // Running in programmatic mode
}
```

### Behavior Changes
When in programmatic mode:
- **Skip `AskUserQuestion` calls** - Use defaults instead
- **Skip user review steps** - Proceed without confirmation
- **Write completion signals** - Update status file with phase progress
- **Auto-commit changes** - Create commits automatically after each phase

### Status File Format
The orchestrator maintains state in `features/orchestration-status.json`:
```json
{
  "sessionId": "session-2026-02-24-abc123",
  "currentFeature": "PROJ-X",
  "currentPhase": "frontend",
  "features": {
    "PROJ-X": {
      "status": "in_progress",
      "phases": {
        "requirements": "completed",
        "architecture": "completed",
        "frontend": "in_progress"
      }
    }
  }
}
```

### Phase Flow
1. Orchestrator reads `features/INDEX.md` for queued features
2. For each "Planned" feature, executes: requirements → architecture → frontend → backend → qa → deploy
3. Each skill updates the status file upon completion
4. Orchestrator handles git commits between phases

### Error Handling
- Skills log errors to the status file's `errors` array
- Orchestrator retries failed phases (up to 3 times)
- After 3 failures, orchestrator pauses and generates a morning report

### Morning Review
At session end (completion, time limit, or error), `features/orchestration-report.md` is generated with:
- Processed features
- Errors encountered
- Pending work for next session

### Resume Support
Run `/orchestrate --resume` to continue from where the last session stopped.
