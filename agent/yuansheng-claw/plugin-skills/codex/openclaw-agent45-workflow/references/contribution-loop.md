# Contribution Loop Reference

Use this reference only when the task includes PRs, patches, maintainer feedback, or CI breakage.

## Normalize feedback

Turn raw signals into one of these buckets:
- failing test / build
- reviewer requested code change
- reviewer requested explanation
- submission formatting or process issue
- environment-specific failure
- unclear or conflicting feedback

## Attribution checklist

For each feedback item, identify:
- exact evidence
- probable root cause
- whether code must change
- whether only metadata/text must change
- what validation proves closure

## Response artifacts

Typical outputs:
- code patch refresh
- focused explanation for reviewer
- updated commit message / PR description
- rerun or additional regression evidence
- explicit note about assumptions or environment limits

## Closure rule

A feedback item is not closed merely because a patch was written.
It is closed only when evidence shows the issue is addressed or when a blocking ambiguity is surfaced clearly to the user/community.
