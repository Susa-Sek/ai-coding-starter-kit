# Design: Google Business Agent Consolidation

**Date:** 2026-03-02
**Status:** Approved
**Feature:** PROJ-1 Google Business Agent Optimization
**Designer:** Claude Code
**Approver:** User

## Executive Summary

This design consolidates multiple overlapping Google Business agent implementations into a unified, modular architecture based on the existing `new_ai_agent.py`. The consolidation addresses fragmentation, improves maintainability, and creates a single source of truth for Google Business automation while preserving the best functionality from all existing agents.

## Current State Analysis

### Existing Agent Landscape
1. **`new_ai_agent.py`** (Modern, modular)
   - KI-driven browser automation without hardcoded selectors
   - Modular architecture with clear separation: State Analyzer, Decision Engine, Action Executor, Memory Manager
   - Configuration management and structured logging
   - Memory system for learning behavior

2. **`smart_agent.py`** (Rule-based)
   - Rule-based decision making with URL/text pattern matching
   - Human delay simulation and state tracking
   - Handles 2FA challenges with user interaction
   - Business data integration from configuration

3. **`agent_profile_creator.py`** (AI-assisted)
   - Screenshot-based AI analysis (Anthropic/DeepSeek)
   - Goal-oriented task execution
   - Base64 screenshot encoding for AI processing

4. **`ai_profile_creator.py`** (Hybrid AI)
   - Combines rule-based and AI-driven approaches
   - Fallback strategies for different scenarios

### Key Problems Identified
- **Fragmentation**: Multiple implementations with overlapping functionality
- **Maintenance Overhead**: Changes need to be applied across multiple files
- **Inconsistent Interfaces**: Different approaches to configuration, logging, and error handling
- **Code Duplication**: Similar logic repeated across agents
- **Mixed Strategies**: Some agents use hardcoded selectors while others are AI-driven

## Target Architecture

### Core Principle: Modular Plugin Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    Unified Agent (new_ai_agent.py)          │
├─────────────────────────────────────────────────────────────┤
│  Task Parser │ State Analyzer │ Decision Engine │ Executor  │
└─────────────────────────────────────────────────────────────┘
         │             │              │              │
         ▼             ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Plugin System                            │
├─────────────┬─────────────┬──────────────┬─────────────────┤
│  Rule-Based │  AI-Driven  │  Hybrid      │  Specialized    │
│  Strategies │  Strategies │  Strategies  │  Handlers       │
└─────────────┴─────────────┴──────────────┴─────────────────┘
```

### Component Responsibilities

#### 1. **Task Parser** (`agents/task_parser.py`)
- **Purpose**: Convert natural language task descriptions into structured goals
- **Input**: "Create Google Business profile for SE Handwerk with address..."
- **Output**: Structured task with parameters, constraints, and validation rules
- **Migration**: Enhance existing parser with business data integration

#### 2. **State Analyzer** (`core/state_analyzer.py`)
- **Purpose**: Analyze current browser state and extract actionable information
- **Capabilities**:
  - DOM analysis and interactive element detection
  - Text content extraction and semantic analysis
  - Screenshot capture and visual analysis (from `agent_profile_creator.py`)
  - URL and page title monitoring
- **Migration**: Integrate screenshot-based analysis from older agents

#### 3. **Decision Engine** (`agents/decision_engine.py`)
- **Purpose**: Determine next action based on current state and task goals
- **Strategies**:
  - **Rule-Based**: Pattern matching from `smart_agent.py` (URL, text, buttons)
  - **AI-Driven**: LLM-based decision making from `agent_profile_creator.py`
  - **Hybrid**: Combine both approaches with confidence scoring
  - **Fallback**: Progressive escalation when primary strategy fails
- **Migration**: Create strategy plugins for each approach

#### 4. **Action Executor** (`core/action_executor.py`)
- **Purpose**: Execute browser actions with error handling and retry logic
- **Actions**:
  - Navigation, clicking, form filling, file uploads
  - Human-like delays and interaction patterns
  - Error recovery and fallback execution
- **Migration**: Consolidate action execution logic from all agents

#### 5. **Memory Manager** (`core/memory_manager.py`)
- **Purpose**: Track state history, learn from successes/failures, avoid loops
- **Features**:
  - Action history storage and analysis
  - Learning from past experiences
  - Loop detection and prevention
- **Migration**: Enhance with state tracking from `smart_agent.py`

#### 6. **Configuration Manager** (`core/config.py`)
- **Purpose**: Centralized configuration with environment variable support
- **Security**: No hardcoded credentials, all secrets from env vars
- **Validation**: Schema-based validation with default values
- **Migration**: Already exists and used by most agents

## Migration Strategy

### Phase 1: Analysis and Plugin Identification (Week 1)
1. **Inventory existing functionality**
   - Map all unique features from each agent
   - Identify dependencies and integration points
   - Document business logic and edge cases

2. **Design plugin interfaces**
   - Define abstract base classes for strategies
   - Create plugin registration system
   - Design configuration schema for plugins

### Phase 2: Core Enhancement (Week 2)
1. **Enhance `new_ai_agent.py` core**
   - Add plugin loading mechanism
   - Implement strategy selection and fallback
   - Enhance error handling and retry logic

2. **Create plugin implementations**
   - **Rule-Based Plugin**: Migrate logic from `smart_agent.py`
   - **AI-Driven Plugin**: Migrate screenshot analysis from `agent_profile_creator.py`
   - **Hybrid Plugin**: Combine approaches from `ai_profile_creator.py`
   - **2FA Handler**: Specialized 2FA challenge handling

### Phase 3: Integration and Testing (Week 3)
1. **Integration testing**
   - Test each plugin independently
   - Verify strategy selection and fallback
   - Validate business logic preservation

2. **Performance optimization**
   - Benchmark different strategies
   - Optimize memory usage and execution speed
   - Implement caching where appropriate

### Phase 4: Deprecation and Cleanup (Week 4)
1. **Gradual deprecation**
   - Mark old agents as deprecated
   - Redirect calls to unified agent
   - Update documentation and examples

2. **Final validation**
   - End-to-end testing with real scenarios
   - Performance comparison with original agents
   - Security audit and credential verification

## CLI Design

### Unified Command Structure
```bash
# Basic usage
./scripts/agents/new_ai_agent.py "Create Google Business profile"

# With configuration
./scripts/agents/new_ai_agent.py --config config.json "Task description"

# Strategy selection
./scripts/agents/new_ai_agent.py --strategy hybrid "Task description"

# Verbose output
./scripts/agents/new_ai_agent.py --verbose "Task description"

# Save results
./scripts/agents/new_ai_agent.py --output result.json "Task description"
```

### Subcommands for Specific Operations
```bash
# Profile creation
google-business-agent create-profile --business-data business.json

# Login only
google-business-agent login --email user@example.com

# Status check
google-business-agent status

# Configuration management
google-business-agent config --validate
google-business-agent config --show
```

### Output Formats
- **JSON**: Machine-readable results for automation
- **Human**: Formatted console output with emojis and progress indicators
- **Log Files**: Structured logging for debugging and auditing
- **Screenshots**: Visual documentation of key steps

## Integration with Main Project

### Feature Tracking
- Update `features/INDEX.md` to reflect consolidation progress
- Create sub-tasks in PROJ-1 for each migration phase
- Update status from "In Progress" to appropriate phase

### Configuration Management
- Use existing `.env.local` pattern from main project
- Extend with Google-specific environment variables:
  ```
  GOOGLE_BUSINESS_EMAIL=...
  GOOGLE_BUSINESS_PASSWORD=...
  GOOGLE_BUSINESS_API_KEY=...
  GOOGLE_BUSINESS_STRATEGY=hybrid
  ```

### Error Handling and Monitoring
- Integrate with main project logging system
- Implement health checks and monitoring endpoints
- Create alerting for critical failures

### Security Considerations
- **Credentials**: No hardcoded credentials, only environment variables
- **Data Validation**: Validate all business data before submission
- **Access Control**: Implement proper authentication for CLI usage
- **Audit Logging**: Log all actions with timestamps and user context

## Success Criteria

### Technical Metrics
1. **Success Rate**: >90% successful profile creation/updates
2. **Error Recovery**: >80% of errors automatically recovered
3. **Performance**: <5 minutes per operation (maintain or improve)
4. **Code Quality**: 30% reduction in total lines of code
5. **Test Coverage**: >80% unit test coverage for core components

### Business Metrics
1. **Maintainability**: Single codebase for all Google Business operations
2. **Extensibility**: New strategies can be added as plugins
3. **Usability**: Consistent CLI interface for all operations
4. **Documentation**: Comprehensive docs for users and developers
5. **Integration**: Seamless integration with main project workflow

## Risks and Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Plugin compatibility issues | Medium | Medium | Thorough interface testing, version compatibility checks |
| Performance degradation | Medium | Low | Benchmarking, performance testing, optimization phases |
| Loss of existing functionality | High | Low | Comprehensive testing, feature parity validation |
| Configuration migration failures | Medium | Medium | Configuration validation tools, migration scripts |
| Security vulnerabilities | High | Low | Security audit, credential validation, penetration testing |

## Appendix: Existing Agent Analysis

### `new_ai_agent.py` Strengths
- Modern modular architecture
- KI-driven decision making
- Memory and learning system
- Good error handling structure

### `smart_agent.py` Unique Features
- Effective 2FA challenge handling
- Human delay simulation
- URL change detection
- Business data integration logic

### `agent_profile_creator.py` Unique Features
- Screenshot-based AI analysis
- Multi-AI provider support (Anthropic, DeepSeek)
- Base64 image encoding for API calls

### `ai_profile_creator.py` Unique Features
- Hybrid rule-based/AI approach
- Progressive fallback strategies
- Context-aware decision making

## Next Steps

1. **Immediate**: Create detailed implementation plan using `/writing-plans` skill
2. **Short-term**: Begin Phase 1 analysis and plugin interface design
3. **Medium-term**: Implement core enhancements and plugin system
4. **Long-term**: Complete migration and deprecate old agents

## Approval

This design has been reviewed and approved by the user on 2026-03-02. All sections have received explicit approval during the presentation phase.

**Next Action**: Invoke `writing-plans` skill to create detailed implementation plan.