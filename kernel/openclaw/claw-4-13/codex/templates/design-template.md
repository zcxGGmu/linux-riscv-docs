# [Issue ID] Design And Test Plan

## 1. Problem Definition

- **Issue URL:**
- **Subsystem:**
- **Gap Type:** `feature | test | performance | stability | tooling`
- **Primary Symptom:**
- **Non-goals:**

## 2. Architecture Parity Snapshot

| Area | `riscv` | `arm64` | `x86` | Notes |
| --- | --- | --- | --- | --- |
| Capability / hook |  |  |  |  |
| Selftest coverage |  |  |  |  |
| Performance signal |  |  |  |  |

## 3. Root Cause Hypothesis

Explain the likely reason for the gap. Separate hard evidence from inference.

- Confirmed evidence:
- Open questions:
- Assumptions requiring verification:

## 4. Design Options

### Option A

- Approach:
- Pros:
- Cons:

### Option B

- Approach:
- Pros:
- Cons:

### Recommended Option

- Chosen option:
- Why this is the best tradeoff:

## 5. Files And Surfaces To Touch

- **Code paths:**
- **Tests:**
- **Docs / scripts:**
- **Out-of-scope files:**

## 6. Implementation Plan

1. `<small, concrete step>`
2. `<small, concrete step>`
3. `<small, concrete step>`

## 7. Test Matrix

| Layer | Command / Environment | Expected Result |
| --- | --- | --- |
| Build |  |  |
| Unit / selftest |  |  |
| QEMU |  |  |
| Hardware |  |  |
| Performance |  |  |

## 8. Risks And Compatibility

- ABI / UAPI risk:
- KVM userspace compatibility risk:
- Regression risk:
- Review sensitivity:

## 9. Rollback Strategy

- Revert scope:
- Safe fallback behavior:
- How to detect bad rollout quickly:

## 10. Definition Of Done

- [ ] Code path implemented as designed
- [ ] Required tests added or updated
- [ ] Planned validation commands pass
- [ ] Performance delta is within threshold
- [ ] Patch narrative and cover letter inputs are ready

