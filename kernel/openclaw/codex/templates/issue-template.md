# [Gap ID] [Short Title]

## Summary

- **Gap Type:** `feature | test | performance | stability | tooling`
- **Subsystem:** `<virt/kvm | arch/riscv | mm | sched | ...>`
- **Compared Against:** `arm64`, `x86`
- **Priority:** `P0 | P1 | P2`
- **Suggested Owner:** `@login or team`

## Problem Statement

Describe the RISC-V gap in one paragraph:

- What exists on `arm64` and/or `x86`
- What is missing or materially worse on `riscv`
- Why this matters now

## Parity Evidence

### Code Evidence

- `arm64/x86` reference:
- `riscv` reference:
- Key files or symbols:

### Mailing List Evidence

- Thread URL:
- Message-ID:
- Current status: `discussion | RFC | patch posted | stalled | merged elsewhere`
- Key takeaway:

### Test / Benchmark Evidence

- Repro script or command:
- Benchmark or selftest result:
- Environment summary:

## Current Behavior

State what happens today on RISC-V:

1. `<step>`
2. `<step>`
3. `<observed result>`

## Expected Behavior

State the expected parity or performance target:

1. `<expected capability>`
2. `<expected test outcome>`
3. `<target performance or latency threshold>`

## Impact

- **User-visible impact:** `<yes/no + short note>`
- **Maintainer impact:** `<review burden / missing coverage / regressions>`
- **Risk if ignored:** `<performance loss / missing feature / unstable behavior>`

## Acceptance Criteria

- [ ] Root cause is understood and documented
- [ ] Required kernel code path is implemented or corrected
- [ ] Relevant `kselftest` / regression coverage exists
- [ ] `ARCH=riscv` build and targeted tests pass
- [ ] No blocker-level `checkpatch` findings remain
- [ ] Patch is ready for mailing-list submission

## Related Items

- Related issue(s):
- Related patch series:
- Related lore threads:
- Notes for Claude Planner:

