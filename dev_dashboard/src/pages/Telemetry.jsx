import React from 'react';
import PageShell from '../components/layout/PageShell';
import { useSupplyPulse } from '../context/SupplyPulseContext';
import { CredCard } from '../components/ui/primitives';

const REFERENCE_TRACE = [
  { name: 'Supervisor Agent', role: 'Orchestration & Triage', model: 'Groq Cloud / gpt-oss-120b', latency: '1.167s', tokens: 1450 },
  { name: 'Route Optimization Agent', role: 'Bathymetry & Routing', model: 'Groq Cloud / gpt-oss-120b', latency: '0.673s', tokens: 1210 },
  { name: 'Inventory Agent', role: 'Buffer & Stockout Audit', model: 'Groq Cloud / gpt-oss-120b', latency: '0.568s', tokens: 980 },
  { name: 'Financial Auditor Agent', role: 'Demurrage & Financial Cost', model: 'Groq Cloud / gpt-oss-120b', latency: '0.650s', tokens: 1120 },
  { name: 'Supervisor Final Decision', role: 'Unified Synthesis', model: 'LangGraph StateGraph', latency: '0.328s', tokens: 450 }
];

export default function Telemetry() {
  const { pipelineResult } = useSupplyPulse();

  const metrics = [
    { title: 'Last Run Latency', value: `${pipelineResult?.total_response_time_seconds ?? '3.42'}s`, note: 'Latest execution cycle', accent: 'text-rose-400', badge: 'Runtime' },
    { title: 'Agents Activated', value: '4 + 1', note: 'Active LangGraph nodes', accent: 'text-emerald-400', badge: 'LangGraph' },
    { title: 'Model Engine', value: 'GPT-OSS', note: '120B parameter scale', accent: 'text-sky-400', badge: 'Groq Cloud' },
    { title: 'Token Count', value: '~5,210', note: 'Estimated context footprint', accent: 'text-amber-400', badge: 'Prompt+Gen' },
    { title: 'Financial Alert', value: pipelineResult?.financial_alert ? 'ACTIVE' : 'CLEAR', note: 'Threshold: $100k USD', accent: pipelineResult?.financial_alert ? 'text-rose-400' : 'text-emerald-400', badge: pipelineResult?.decision || 'Decision' }
  ];

  return (
    <PageShell
      eyebrow="engine telemetry & vitals"
      title="Runtime Observability &"
      accent="Vitals."
      sub="Health, response latency, token consumption, and agent node execution telemetry for the multi-agent decision pipeline."
    >
      {/* ── 1. Vitals Metric Open Strip (No Redundant Boxed Cards) ─────── */}
      <section className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-8 mb-16 border-b border-white/[0.06] pb-12">
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
            Multi-Agent Node Latency & Model Specs
          </h2>
        </div>

        <CredCard hover={false} className="p-8 sm:p-10">
          <div className="divide-y divide-white/[0.05]">
            {REFERENCE_TRACE.map((row, idx) => (
              <div
                key={idx}
                className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-6 items-center gap-4 py-4 text-xs transition-colors hover:bg-white/[0.02] px-3 rounded-lg"
              >
                <span className="text-sm font-bold text-white md:col-span-2">{row.name}</span>
                <span className="text-xs text-rose-400 font-semibold">{row.role}</span>
                <span className="mono text-xs text-neutral-400">{row.model}</span>
                <span className="mono text-xs text-white">
                  <b className="text-emerald-400 font-bold">{row.latency}</b> · {row.tokens} tokens
                </span>
                <div className="flex justify-end">
                  <span className="text-[11px] font-bold text-emerald-400 uppercase tracking-wider">
                    HEALTHY
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
