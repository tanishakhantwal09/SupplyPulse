import React from 'react';
import PageShell from '../components/layout/PageShell';
import { useSupplyPulse } from '../context/SupplyPulseContext';
import { NA, fmtUsd, hasPlan } from '../lib/format';
import { CredCard, ServerStatusBadge } from '../components/ui/primitives';

const AGENT_ROWS = [
  ['supervisor', 'Supervisor Agent', 'Assessment & delegation'],
  ['route_optimization', 'Route Optimization Agent', 'Port scoring (BPR)'],
  ['inventory', 'Inventory Agent', 'Commodity exposure'],
  ['financial_auditor', 'Financial Auditor Agent', 'Six-part cost incl. EU ETS'],
  ['final_decision', 'Final Decision', 'Result assembly (no LLM)'],
];

// Every value comes from the last real run (measured), or shows "—".
export default function Telemetry() {
  const { pipelineResult: r } = useSupplyPulse();
  const model = r?.llm_model || 'openai/gpt-oss-20b';
  const usage = r?.llm_usage;
  const timings = r?.agent_timings_seconds || {};

  const metrics = [
    { title: 'Last Run Time', value: r ? `${r.total_response_time_seconds}s` : NA, note: 'Measured, whole pipeline', accent: 'text-rose-400', badge: 'Runtime' },
    { title: 'Agents Run', value: r ? String(r.agents_activated?.length ?? 0) : NA, note: 'Counted from the run', accent: 'text-emerald-400', badge: 'LangGraph' },
    { title: 'Model', value: 'gpt-oss-20b', note: model, accent: 'text-sky-400', badge: 'Groq' },
    { title: 'LLM Tokens', value: usage ? (usage.input_tokens + usage.output_tokens).toLocaleString() : NA, note: usage ? `${usage.input_tokens} in / ${usage.output_tokens} out (measured)` : 'No run yet', accent: 'text-amber-400', badge: 'Prompt+Gen' },
    { title: 'Financial Alert', value: hasPlan(r) ? (r.financial_alert ? 'ACTIVE' : 'CLEAR') : NA, note: hasPlan(r) ? `Threshold: ${fmtUsd(r.alert_threshold_usd)}` : 'No plan', accent: r?.financial_alert ? 'text-rose-400' : 'text-emerald-400', badge: r?.decision || 'Decision' }
  ];
  const rows = AGENT_ROWS.map(([key, name, role]) => {
    const u = usage?.per_agent?.[key];
    return { name, role, model: key === 'final_decision' ? 'LangGraph StateGraph' : model,
      latency: timings[key] !== undefined ? `${timings[key].toFixed(3)}s` : NA,
      tokens: u ? u.input_tokens + u.output_tokens : NA, ran: timings[key] !== undefined };
  });

  return (
    <PageShell
      eyebrow="engine telemetry & vitals"
      title="Runtime Observability &"
      accent="Vitals."
      sub="Health, response latency, token consumption, and agent node execution telemetry for the multi-agent decision pipeline."
      right={
        <div className="flex items-center gap-2.5">
          <span className="mono text-[11px] font-semibold text-neutral-400 uppercase tracking-wider">
            API Backend
          </span>
          <ServerStatusBadge />
        </div>
      }
    >
      {/* ── 1. Vitals Metric Open Strip (No Redundant Boxed Cards) ─────── */}
      <section className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-8 mb-16 border-b border-[rgba(225,29,72,0.25)] pb-12">
        {metrics.map((m) => (
          <div key={m.title} className="flex flex-col justify-between">
            <div className="flex items-center justify-between gap-2">
              <span className="cred-label text-[10px] text-neutral-500">{m.title}</span>
              <span className="mono text-[10px] text-neutral-600 font-medium">
                {m.badge}
              </span>
            </div>
            <div className={`mono my-2 text-3xl sm:text-4xl font-bold tracking-tight ${m.accent}`}>
              {m.value}
            </div>
            <span className="text-xs text-neutral-500">
              {m.note}
            </span>
          </div>
        ))}
      </section>

      {/* ── 2. Reference Trace Breakdown (Clean Table, No Inset Boxes) ─────── */}
      <section className="mb-16">
        <div className="mb-8">
          <span className="cred-label text-neutral-500">Execution Breakdown</span>
          <h2 className="cred-hero text-2xl sm:text-3xl text-white font-bold tracking-tight mt-1">
            Measured Time and Tokens per Agent
          </h2>
        </div>

        <CredCard hover={false} className="p-8 sm:p-10">
          <div className="divide-y divide-[rgba(225,29,72,0.22)]">
            {rows.map((row, idx) => (
              <div
                key={idx}
                className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-6 items-center gap-4 py-4 text-xs transition-colors hover:bg-white/[0.02] px-3"
              >
                <span className="text-sm font-bold text-white md:col-span-2">{row.name}</span>
                <span className="text-xs text-rose-400 font-semibold">{row.role}</span>
                <span className="mono text-xs text-neutral-400">{row.model}</span>
                <span className="mono text-xs text-white">
                  <b className="text-emerald-400 font-bold">{row.latency}</b> · {row.tokens} tokens
                </span>
                <div className="flex justify-end">
                  <span className={`text-[11px] font-bold uppercase tracking-wider ${row.ran ? 'text-emerald-400' : 'text-neutral-500'}`}>
                    {row.ran ? 'RAN' : 'NOT RUN'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </CredCard>
      </section>
    </PageShell>
  );
}
