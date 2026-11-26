# Sample run (3 Nov 2026, Port of Mundra)

These two files are one example output of the pipeline, kept for reference only.

- Event: a CRITICAL held-out event at the Port of Mundra (event date 2026-02-18), run on 3 Nov 2026.
- Produced by the **old code** (before the Stage 1 fixes). It still contains the
  severity-fixed confidence ("91%"), the old BPR settings (alpha = 1.5) and the
  unsourced cost constants. **Do not quote any number in it as a result.**

The live pipeline now writes `agents/pipeline_result.json` and
`agents/pipeline_attribution.json`, which are ignored by git because they change on every run.
