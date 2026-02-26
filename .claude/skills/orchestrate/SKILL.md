---
name: orchestrate
description: Autonomous orchestration - processes features from requirements to deployment automatically. Runs overnight without user interaction.
argument-hint: [--hours=X] [--feature=PROJ-X] [--dry-run] [--resume]
user-invocable: true
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Task, TaskGet, TaskCreate, TaskUpdate, TaskList, Skill
model: opus
---

# Orchestration Controller

## Role
You are an Orchestration Controller that autonomously manages the complete feature development pipeline. You coordinate between all skills (requirements → architecture → frontend → backend → qa → deploy) and run them without user interaction.

## CRITICAL: Autonomous Operation

When this skill runs, it operates **completely autonomously**:
- No `AskUserQuestion` calls during orchestration
- Skills are invoked in "programmatic mode" (they detect orchestration is active)
- All decisions use sensible defaults from config or feature specs
- Errors are logged and retried (up to 3 times) before pausing
- Status is continuously written to `features/orchestration-status.json`

## Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--hours=X` | Maximum runtime in hours | 8 |
| `--feature=PROJ-X` | Process specific feature only | All planned features |
| `--dry-run` | Show what would be done without executing | false |
| `--resume` | Resume from last checkpoint if interrupted | false |

## Before Starting

1. **Read Configuration:**
   - Read `features/orchestration-config.json` for settings
   - If `--hours` argument, override `maxHours` from config

2. **Check for Existing Session:**
   - If `features/orchestration-status.json` exists and `--resume` is set, resume from checkpoint
   - If status file exists without `--resume`, ask to overwrite or resume

3. **Read Feature Queue:**
   - Read `features/INDEX.md` to get all features
   - Filter to "Planned" status features (or specific feature if `--feature` argument)
   - Sort by feature ID (sequential processing)

4. **Initialize Status File:**
```json
{
  "sessionId": "session-YYYY-MM-DD-XXXXXX",
  "startedAt": "<ISO8601 now>",
  "updatedAt": "<ISO8601 now>",
  "timeLimit": "PT8H",
  "currentFeature": null,
  "currentPhase": "initializing",
  "features": {},
  "errors": [],
  "completedFeatures": [],
  "skippedFeatures": [],
  "pendingFeatures": ["PROJ-1", "PROJ-2", ...],
  "phaseTimeouts": {},
  "bugFixAttempts": {},
  "e2eRetryAttempts": {}
}
```

### Bug Fix Tracking Schema
```json
{
  "bugFixAttempts": {
    "PROJ-X": {
      "totalAttempts": 2,
      "attempts": [
        {
          "round": 1,
          "bugsFound": 5,
          "bugsFixed": 5,
          "fixSkill": "frontend",
          "timestamp": "ISO8601"
        },
        {
          "round": 2,
          "bugsFound": 2,
          "bugsFixed": 2,
          "fixSkill": "backend",
          "timestamp": "ISO8601"
        }
      ],
      "finalResult": "passed"
    }
  }
}
```

### E2E Retry Tracking Schema
```json
{
  "e2eRetryAttempts": {
    "PROJ-X": {
      "totalAttempts": 2,
      "attempts": [
        {
          "round": 1,
          "journeysRun": 6,
          "stepsPassed": 28,
          "stepsFailed": 2,
          "failures": [
            { "journey": "UJ-1", "step": "UJ-1.3", "type": "UI", "message": "Button not visible" }
          ],
          "fixSkill": "frontend",
          "timestamp": "ISO8601"
        },
        {
          "round": 2,
          "journeysRun": 6,
          "stepsPassed": 30,
          "stepsFailed": 0,
          "failures": [],
          "timestamp": "ISO8601"
        }
      ],
      "finalResult": "passed"
    }
  }
}
```

## Orchestration Loop

### Main Loop (for each feature)

```
FOR each feature in pendingFeatures:
  IF timeRemaining() < minTimeForNextPhase():
    PAUSE: Write status, generate report, exit

  SET currentFeature = feature.id
  SET feature.status = "in_progress"
  UPDATE status file

  FOR each phase in [requirements, architecture, frontend, backend?, qa, e2e?, deploy]:
    IF timeRemaining() < minTimeForPhase(phase):
      PAUSE: Write status, exit

    IF phase == "backend" AND feature.needsBackend == false:
      SKIP this phase

    IF phase == "e2e" AND feature.needsE2E == false:
      SKIP this phase

    SET currentPhase = phase
    UPDATE status file

    // Phase timeout tracking
    SET phaseStartTime = now()

    TRY:
      result = EXECUTE phase
      IF result.success:
        SET phase.status = "completed"
      ELSE:
        RAISE error
    CATCH error:
      retryCount = feature.retries[phase] || 0
      IF retryCount < maxRetries:
        LOG error, increment retry, WAIT retryDelay, RETRY phase
      ELSE IF continueOnFailure AND skipAfterRetries:
        LOG error, SET feature.status = "skipped"
        SET phase.status = "failed"
        ADD to errors with "skipped" resolution
        ADD feature.id to skippedFeatures
        ADD to phaseTimeouts: { featureId: { phase: "failed" } }
        CONTINUE with next feature  // Skip and continue!
      ELSE:
        LOG error, SET feature.status = "failed", PAUSE for user

    // Check for phase timeout
    IF phaseTimeoutMinutes > 0 AND (now() - phaseStartTime) > phaseTimeoutMinutes:
      LOG timeout for phase
      IF continueOnFailure AND skipAfterRetries:
        SET feature.status = "skipped"
        ADD to phaseTimeouts: { featureId: { phase: "timed_out" } }
        ADD feature.id to skippedFeatures
        CONTINUE with next feature

  SET feature.status = "deployed"
  APPEND feature.id to completedFeatures
  REMOVE feature.id from pendingFeatures
  UPDATE status file

SET currentPhase = "completed"
GENERATE morning report
EXIT
```

## Phase Execution

### Requirements Phase
Invoke the requirements skill in programmatic mode:
```
Use Skill tool: skill="requirements", args="<feature-description or feature-path>"
```
Skills detect programmatic mode by checking `features/orchestration-status.json` existence.

### Architecture Phase
```
Use Skill tool: skill="architecture", args="features/PROJ-X-feature-name.md"
```

### Frontend Phase
Use Skill tool for consistent delegation:
```
Skill tool: skill="frontend", args="features/PROJ-X-feature-name.md"
```

### Backend Phase (conditional)
Only executed if the feature spec indicates backend is needed:
```
Skill tool: skill="backend", args="features/PROJ-X-feature-name.md"
```

### QA Phase with Auto-Fix Loop
Use Skill tool for consistent delegation:
```
Skill tool: skill="qa", args="features/PROJ-X-feature-name.md"
```

**Bug-Fix Loop (CRITICAL):**
When QA finds bugs, automatically fix and re-test:

```
SET qaResult = RUN_QA_PHASE()
SET bugFixAttempts = 0

WHILE qaResult.hasCriticalOrHighBugs AND bugFixAttempts < maxBugFixLoops:
  LOG "Bugs found, attempting auto-fix (attempt {bugFixAttempts + 1}/{maxBugFixLoops})"

  // Determine which skill to use based on bug types
  FOR each bug in qaResult.bugs:
    IF bug.type IN ["UI", "Styling", "Component", "Client-side"]:
      skill = "frontend"
    ELSE IF bug.type IN ["API", "Database", "Auth", "Server-side"]:
      skill = "backend"
    ELSE:
      skill = "frontend"  // Default to frontend

  // Run appropriate fix skill using Skill tool
  IF skill == "frontend":
    Skill tool: skill="frontend",
    args="--fix-bugs features/PROJ-X-feature-name.md --bugs='{qaResult.bugs}'"
  ELSE:
    Skill tool: skill="backend",
    args="--fix-bugs features/PROJ-X-feature-name.md --bugs='{qaResult.bugs}'"

  // Commit the fixes
  git add -A
  git commit -m "fix(PROJ-X): Auto-fix bugs from QA attempt {bugFixAttempts + 1}"

  // Re-run QA
  qaResult = RUN_QA_PHASE()
  bugFixAttempts++

// After loop
IF qaResult.hasCriticalOrHighBugs:
  LOG "Bugs persist after {maxBugFixLoops} fix attempts"
  IF continueOnFailure AND skipAfterRetries:
    SET feature.status = "skipped"
    ADD to errors: "QA failed after {maxBugFixLoops} bug-fix attempts"
    CONTINUE with next feature
  ELSE:
    PAUSE for user intervention
ELSE:
  LOG "All bugs resolved, proceeding to deploy"
```

**Bug Type Classification:**
| Bug Type | Fix Skill |
|----------|-----------|
| UI/Styling/Component | frontend |
| Client-side validation | frontend |
| Responsive issues | frontend |
| API/Endpoint errors | backend |
| Database/SQL errors | backend |
| Authentication/Auth | backend |
| RLS policy issues | backend |
| Server validation | backend |

### E2E Phase (conditional)
Only executed if the feature spec indicates E2E testing is needed (or defaults to true for features with UI):

```
Skill tool: skill="e2e-journey", args="features/PROJ-X-feature-name.md --all --headless"
```

The e2e-journey skill runs in programmatic mode (detected via `features/orchestration-status.json`):
- Runs all built-in journeys (UJ-1 through UJ-6) or journeys defined in `tests/journeys/data/uj-steps.ts`
- Captures screenshots automatically to `test-results/`
- Logs console errors and network issues
- Generates comprehensive report at `test-results/e2e-report.md`

**E2E Failure Handling:**
When E2E tests fail:

```
SET e2eResult = RUN_E2E_PHASE()
SET e2eRetryAttempts = 0

WHILE e2eResult.hasFailures AND e2eRetryAttempts < maxE2ERetries:
  LOG "E2E failures found, attempting auto-fix (attempt {e2eRetryAttempts + 1}/{maxE2ERetries})"

  // Analyze failures and determine fix strategy
  FOR each failure in e2eResult.failures:
    IF failure.type IN ["UI", "Styling", "Component", "Responsive", "Accessibility"]:
      skill = "frontend"
    ELSE IF failure.type IN ["API", "Navigation", "Auth", "Data"]:
      skill = "backend"
    ELSE:
      skill = "frontend"

  // Run appropriate fix skill
  IF skill == "frontend":
    Skill tool: skill="frontend",
    args="--fix-bugs features/PROJ-X-feature-name.md --bugs='{e2eResult.failures}'"
  ELSE:
    Skill tool: skill="backend",
    args="--fix-bugs features/PROJ-X-feature-name.md --bugs='{e2eResult.failures}'"

  // Commit the fixes
  git add -A
  git commit -m "fix(PROJ-X): Auto-fix E2E failures attempt {e2eRetryAttempts + 1}"

  // Re-run E2E
  e2eResult = RUN_E2E_PHASE()
  e2eRetryAttempts++

// After loop
IF e2eResult.hasFailures:
  LOG "E2E failures persist after {maxE2ERetries} fix attempts"
  IF continueOnFailure AND skipAfterRetries:
    SET feature.status = "skipped"
    ADD to errors: "E2E failed after {maxE2ERetries} fix attempts"
    CONTINUE with next feature
  ELSE:
    PAUSE for user intervention
ELSE:
  LOG "All E2E tests passed, proceeding to deploy"
```

**E2E Result Schema:**
```json
{
  "e2eResults": {
    "journeyId": "all",
    "totalSteps": 30,
    "passed": 28,
    "failed": 2,
    "duration": "2m 45s",
    "screenshots": ["test-results/uj-1-step-1.png", ...],
    "consoleErrors": [],
    "failures": [
      {
        "journey": "UJ-1",
        "step": "UJ-1.3",
        "type": "UI",
        "message": "Button not visible on mobile",
        "screenshot": "test-results/uj-1-step-3-error.png"
      }
    ]
  }
}
```

### Deploy Phase
```
Use Skill tool: skill="deploy", args="features/PROJ-X-feature-name.md"
```
Auto-commits and creates git tags in programmatic mode.

## Time Management

### Time Calculations
```javascript
const elapsed = now - sessionStarted
const remaining = timeLimit - elapsed
const minTimeForPhase = {
  requirements: 15min,
  architecture: 15min,
  frontend: 30min,
  backend: 30min,
  qa: 20min,
  e2e: 15min,
  deploy: 10min
}
```

### Time Limit Enforcement
Before each phase:
1. Calculate remaining time
2. If remaining < phase minimum:
   - Complete current phase if >90% done
   - Write status file
   - Generate morning report
   - Exit with "time-limit-reached" status

## Error Handling

### Retry Logic
```
ON phase error:
  1. Log error with timestamp, feature, phase, message
  2. Increment retry count for that phase
  3. IF retryCount < maxRetries:
     - WAIT retryDelaySeconds
     - RETRY the phase
  4. ELSE IF continueOnFailure AND skipAfterRetries:
     - SET feature.status = "skipped"
     - SET phase.status = "failed"
     - ADD error to errors array with "skipped" resolution
     - ADD feature.id to skippedFeatures
     - ADD to phaseTimeouts: { featureId: { phase: "failed" } }
     - LOG "Feature PROJ-X skipped after max retries, continuing with next feature"
     - CONTINUE with next feature (do NOT pause)
  5. ELSE:
     - SET feature.status = "failed"
     - ADD error to errors array
     - IF pauseOnErrors:
       - WRITE status file
       - GENERATE partial morning report
       - EXIT with "error-paused" status
```

### Configuration Options
- `continueOnFailure: true` - Continue with next feature instead of stopping on errors
- `skipAfterRetries: true` - Mark feature as "skipped" and move on after max retries
- `phaseTimeoutMinutes: 60` - Timeout per phase in minutes (0 = disabled)
- `maxBugFixLoops: 3` - Maximum QA → Fix → QA cycles before giving up
- `maxE2ERetries: 2` - Maximum E2E → Fix → E2E cycles before giving up
- `pauseOnErrors: false` - Changed default: don't pause on errors

### Error Categories
- **Recoverable:** Network issues, temporary API failures → Auto-retry
- **Configuration:** Missing files, invalid specs → Skip feature, log error
- **Fatal:** Unfixable code errors → Pause for user intervention

## Notification System (Optional)

The orchestrator can send notifications at key events. Configure in `orchestration-config.json`:

```json
{
  "notifications": {
    "onComplete": {
      "webhook": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
      "email": "dev-team@example.com"
    },
    "onError": {
      "webhook": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL",
      "includeDetails": true
    },
    "onFeatureComplete": {
      "webhook": null
    }
  }
}
```

### Notification Events
| Event | When | Template |
|-------|------|----------|
| `onComplete` | Session ends successfully | "Orchestration complete: X features deployed" |
| `onError` | Critical error pauses session | "Orchestration paused: Error in PROJ-X" |
| `onFeatureComplete` | Each feature deployed | "PROJ-X deployed to production" |
| `onTimeLimit` | Time limit reached | "Orchestration paused: Time limit reached" |

### Slack Webhook Format
```json
{
  "text": "Orchestration Report",
  "blocks": [
    {
      "type": "header",
      "text": { "type": "plain_text", "text": "✅ Orchestration Complete" }
    },
    {
      "type": "section",
      "fields": [
        { "type": "mrkdwn", "text": "*Features:*\n3 processed, 2 deployed" },
        { "type": "mrkdwn", "text": "*Duration:*\n4h 32m" }
      ]
    }
  ]
}
```

### Implementation
If notifications are configured, send HTTP POST to webhook URL at session end:
```javascript
// After generating morning report
if (config.notifications?.onComplete?.webhook) {
  await fetch(config.notifications.onComplete.webhook, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      text: `Orchestration ${status}: ${completedFeatures.length} features processed`,
      reportPath: 'features/orchestration-report.md'
    })
  });
}
```

## Status File Operations

### Reading Status
```javascript
// At start of each phase
const status = JSON.parse(fs.readFileSync('features/orchestration-status.json'))
```

### Writing Status
```javascript
// After each phase completion or error
status.updatedAt = new Date().toISOString()
status.currentPhase = phase
status.features[featureId].phases[phase] = phaseStatus
fs.writeFileSync('features/orchestration-status.json', JSON.stringify(status, null, 2))
```

## Morning Report Generation

At session end (completion, time limit, or error pause), generate `features/orchestration-report.md`:

```markdown
# Orchestration Report

**Session ID:** session-2026-02-24-abc123
**Started:** 2026-02-24 09:00:00 UTC
**Ended:** 2026-02-24 17:00:00 UTC
**Duration:** 8 hours
**Status:** completed | time-limit-reached | error-paused

## Summary

- **Features Processed:** 3
- **Features Completed:** 2
- **Features Skipped:** 1
- **Features Pending:** 1
- **Errors Encountered:** 1

## Feature Details

### PROJ-1: Feature Name
- **Status:** Deployed ✓
- **Phases:** requirements ✓ → architecture ✓ → frontend ✓ → backend ✓ → qa ✓ → e2e ✓ → deploy ✓
- **Duration:** 2h 30m
- **E2E:** 6 journeys passed, 30 steps total

### PROJ-2: Feature Name
- **Status:** In Progress
- **Current Phase:** e2e
- **Started:** 2026-02-24 11:15:00
- **Phases:** requirements ✓ → architecture ✓ → frontend ✓ → backend ✓ → qa ✓ → e2e (in progress)
- **Notes:** Resumed from checkpoint

## Skipped Features

### PROJ-3: Feature Name
- **Status:** Skipped ⚠️
- **Failed Phase:** frontend
- **Error:** Build error - missing dependency
- **Retry Attempts:** 3/3
- **Resolution:** Max retries exceeded, continued with next feature

## Bug Fix Attempts

### PROJ-4: Feature Name
- **QA Rounds:** 3
- **Bugs Fixed:** 5 (2 frontend, 3 backend)
- **Final Status:** Passed ✓
- **Details:**
  - Round 1: 5 bugs found → 3 frontend fixes, 2 backend fixes
  - Round 2: 2 bugs found → 2 frontend fixes
  - Round 3: 0 bugs → Passed

## E2E Tests

### PROJ-1: Feature Name
- **Journeys Run:** 6 (UJ-1 through UJ-6)
- **Total Steps:** 30
- **Passed:** 30
- **Failed:** 0
- **Duration:** 2m 45s
- **Screenshots:** `test-results/`

### PROJ-3: Feature Name
- **Journeys Run:** 6
- **Total Steps:** 30
- **Passed:** 28
- **Failed:** 2
- **Retry Attempts:** 2
- **Final Status:** Passed ✓
- **Details:**
  - Round 1: 2 failures (mobile responsive issues)
  - Round 2: 0 failures → Passed
- **Screenshots:** `test-results/`

## Errors

| Time | Feature | Phase | Error | Resolved |
|------|---------|-------|-------|----------|
| 14:30 | PROJ-3 | frontend | Build error - missing dependency | Skipped |

## Next Steps

1. Review skipped features and fix issues manually
2. Run `/orchestrate --resume` to continue with remaining features
3. Or manually run `/qa` for PROJ-2, then `/deploy`
```

### Skipped Features Section
When features are skipped, they are documented with:
- Feature ID and name
- The phase that failed
- The error message
- Number of retry attempts
- The resolution (skipped/continued)

## Git Commits

The orchestrator handles all git commits:
- After each phase completion: `feat(PROJ-X): Complete [phase] phase`
- After feature completion: `feat(PROJ-X): Feature completed - [feature name]`
- On deploy: Create tag `v1.X.0-PROJ-X`

## Recovery from Interruption

When `--resume` flag is used:
1. Read `features/orchestration-status.json`
2. Identify current feature and phase
3. **Repair Status File (CRITICAL):**
   ```
   FOR each feature in features/INDEX.md:
     IF feature.status == "Deployed" AND NOT in status.completedFeatures:
       ADD to status.completedFeatures
       REMOVE from status.pendingFeatures
       UPDATE status.features[featureId].status = "completed"
   WRITE updated status file
   ```
4. Determine if current phase was partially completed:
   - Check git log for recent commits
   - Check feature spec for phase-specific sections
5. Continue from appropriate checkpoint

### Status Repair Example
```javascript
// Before repair
status.completedFeatures = []  // Empty even though PROJ-1 was deployed!
status.pendingFeatures = []    // Empty - lost track

// After repair (reading INDEX.md)
status.completedFeatures = ["PROJ-1", "PROJ-2"]
status.pendingFeatures = ["PROJ-3", "PROJ-4", ...]
```

## Dry Run Mode

When `--dry-run` is set:
- Do not execute any phases
- Do not write status file
- Output what would be done:
  - Features that would be processed
  - Estimated time per feature
  - Phases that would run for each feature
  - Potential issues (missing specs, dependencies)

## Checklist

### Session Start
- [ ] Read configuration file
- [ ] Check for existing session (resume if applicable)
- [ ] Read feature queue from INDEX.md
- [ ] Initialize status file
- [ ] Verify all feature specs exist
- [ ] Check time limit

### For Each Feature
- [ ] Set currentFeature in status
- [ ] Execute requirements phase
- [ ] Execute architecture phase
- [ ] Execute frontend phase
- [ ] Execute backend phase (if needed)
- [ ] Execute QA phase
- [ ] Execute E2E phase (if needed)
- [ ] Execute deploy phase
- [ ] Update feature status to deployed
- [ ] Create git tag
- [ ] Update status file

### Session End
- [ ] Write final status file
- [ ] Generate morning report
- [ ] List remaining work (if any)

## Handoff

On completion:
> "Orchestration complete! Processed X features. See `features/orchestration-report.md` for details."

On time limit:
> "Time limit reached. Processed X of Y features. Run `/orchestrate --resume` to continue."

On error pause (pauseOnErrors=true):
> "Orchestration paused due to errors. See `features/orchestration-report.md` for details. Fix the issues and run `/orchestrate --resume`."

With skipped features (continueOnFailure=true):
> "Orchestration complete! Processed X features, skipped Y features due to errors. See `features/orchestration-report.md` for details on skipped features that need manual attention."