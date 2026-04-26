# Agent5: RISC-V Contribution Workflow

Use this reference when the task is primarily "observe community/system feedback, attribute, fix, re-verify, resubmit" for RISC-V open-source contributions.

## Overview

Agent5 is a contribution-closure loop, not just code editing.
It continuously monitors external feedback events and drives them to resolution.

## Inputs

- repository state: current branch, patch series, PR status
- submission norms: project commit message style, patch format, PR template
- project knowledge: from Agent4 knowledge base or project-specific skills
- external feedback events: CI failures, review comments, maintainer requests, new issues

## Execution resources

- project skills and tools
- action modules for common operations
- build environment and test platform
- internet access for CI logs, issue trackers, mailing lists
- MCP servers, web APIs, CLI tools

## Outputs

- regression test results
- commit generation or refresh
- PR / patch update
- review feedback monitoring report
- resubmission package

## Core loop

### 1. Normalize incoming signals

Turn raw feedback into one of these buckets:
- failing test / build
- reviewer requested code change
- reviewer requested explanation
- submission formatting or process issue
- environment-specific failure
- unclear or conflicting feedback

### 2. Attribute the issue

For each feedback item, identify:
- exact evidence (log excerpt, comment quote, CI link)
- probable root cause
- whether code must change
- whether only metadata / text must change
- what validation proves closure

Attribution categories:
- regression: the change broke existing functionality
- environment issue: failure is specific to CI environment, not a real bug
- flaky test: non-deterministic failure unrelated to the change
- style / compliance gap: formatting, naming, or process violation
- missing rationale: the change needs better explanation or documentation
- real bug: the change itself is incorrect

### 3. Choose the next action

Based on attribution, select one:
- fix code and rerun tests
- refresh commit message or PR description
- update patch / PR text with explanation
- rerun validation with additional checks
- request clarification from reviewer or maintainer

### 4. Produce the response artifact

Typical outputs:
- code patch refresh
- focused explanation for reviewer
- updated commit message / PR description
- rerun or additional regression evidence
- explicit note about assumptions or environment limits

### 5. Monitor for the next feedback event

After producing the artifact:
- wait for CI results
- wait for review comments
- watch for new external events (new issues, dependent changes)
- continue until the contribution is merged or explicitly paused

## Closure rule

A feedback item is not closed merely because a patch was written.
It is closed only when evidence shows the issue is addressed, or when a blocking ambiguity is surfaced clearly to the user or community.

## Shared resources with Agent4

Agent5 reuses:
- Common Skills
- Knowledge Base (from Agent4 knowledge intake)
- MCP Servers, Web API, CLI Tools
- GitHub, GitLab, Mail
- Build ENV, Test Platform, Internet, LLM

When Agent4 has already produced a patch, Agent5 starts from that patch state and handles the community-facing follow-up.
