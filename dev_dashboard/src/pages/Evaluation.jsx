import React, { useEffect, useState } from 'react';
import PageShell from '../components/layout/PageShell';
import { API_BASE, NA, fmtNum } from '../lib/format';
import { CredCard } from '../components/ui/primitives';

// Values are read from experiments/results/*.json through /api/evaluation.
// Nothing on this page is typed in by hand. These results are RETIRED
// (see docs/RETIRED.md) and are shown only so they are not hidden.
export default function Evaluation() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/evaluation`)
      .then(r => r.json())
      .then(setData)
      .catch(e => setError(e.message));
  }, []);

  const sp = data?.supplypulse?.metrics;
  const bl = data?.brintrup_baseline?.metrics;
  const rows = [
    ['Rerouting F1', sp?.f1_rerouting, bl?.f1_score, 3],
    ['Precision', sp?.precision, bl?.precision, 3],
    ['Recall', sp?.recall, bl?.recall, 3],
    ['Accuracy', sp?.accuracy, bl?.accuracy, 3],
    ['Plan correctness', sp?.plan_correctness, null, 3],
    ['Avg response time (s)', sp?.avg_response_time_seconds, bl?.avg_response_time_seconds, 2],
    ['Cost per analysis (USD, ASSUMPTION)', sp?.cost_per_analysis_usd, bl?.cost_per_analysis_usd, 4],
  ];

  return (
    <PageShell
      eyebrow="evaluation results"
      title="Evaluation"
      accent="(Retired)."
      sub="Old results read from experiments/results. They are retired and must not be reported. New results come from the Stage 2-3 experiments."
    >
      <div className="mb-10 border border-rose-500/50 bg-rose-500/10 px-5 py-4 text-sm text-rose-200 leading-relaxed">
        <b>RETIRED.</b> The F1 scores below are circular: the "ground truth" labels and the pipeline's
        decision both come from the same severity rule. The cost per analysis is an ASSUMPTION
        (1,500 tokens × 4 calls × $0.15 per million), not a measurement. The Brintrup et al. comparison uses a
        preprint, which may only be cited as a disclosed reference. See docs/RETIRED.md.
        {data?.retired_note && <span className="block mt-2 text-rose-300/80">{data.retired_note}</span>}
      </div>

      {error && <div className="mb-8 text-sm text-neutral-400">API server offline: no results shown ({error}).</div>}

      <section className="mb-16">
        <CredCard hover={false} className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-[rgba(225,29,72,0.3)] bg-white/[0.02]">
                  <th className="py-5 px-8 text-xs font-bold uppercase tracking-wider text-neutral-400">Metric</th>
                  <th className="py-5 px-8 text-xs font-bold uppercase tracking-wider text-neutral-300">SupplyPulse (formal_evaluation.json)</th>
                  <th className="py-5 px-8 text-xs font-bold uppercase tracking-wider text-neutral-400">Rule baseline (brintrup_baseline.json)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[rgba(225,29,72,0.22)]">
                {rows.map(([name, a, b, d]) => (
                  <tr key={name}>
                    <td className="py-5 px-8 text-sm font-semibold text-white">{name}</td>
                    <td className="py-5 px-8 mono text-sm text-neutral-300">{a == null ? NA : fmtNum(a, d)}</td>
                    <td className="py-5 px-8 mono text-sm text-neutral-400">{b == null ? NA : fmtNum(b, d)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CredCard>
      </section>
    </PageShell>
  );
}
