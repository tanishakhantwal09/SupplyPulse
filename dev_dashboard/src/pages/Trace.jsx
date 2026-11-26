import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { ChevronRight, Clock } from 'lucide-react';
import PageShell from '../components/layout/PageShell';
import { useSupplyPulse } from '../context/SupplyPulseContext';
import { NA, hasPlan } from '../lib/format';
import { JsonBlock, CredCard } from '../components/ui/primitives';

const BAR_SHADES = [
  'bg-rose-500/40',
  'bg-rose-500/60',
  'bg-rose-500/80',
  'bg-rose-600',
  'bg-blood',
  'bg-amber-400'
];

export default function Trace() {
  const { pipelineResult, selectedEvent } = useSupplyPulse();
  const [selectedTraceStep, setSelectedTraceStep] = useState(0);

  // Built only from the last real run: measured per-agent seconds and token counts.
  const r = pipelineResult;
  const plan = hasPlan(r);
  const timings = r?.agent_timings_seconds || {};
  const usage = r?.llm_usage?.per_agent || {};
  const model = r?.llm_model || 'openai/gpt-oss-20b';
  const total = r?.total_response_time_seconds || 0;
  const defs = [
    ['supervisor', 'Supervisor Agent', 'LLM ORCHESTRATOR', { assessment: r?.agent_assessments?.supervisor }],
    ['route_optimization', 'Route Optimization Agent', 'PORT SCORING',
      plan ? { recommended_alternate_port: r.recommended_alternate_port, ship_allocation: r.ship_allocation } : {}],
    ['inventory', 'Inventory Agent', 'COMMODITY EXPOSURE',
      plan ? { top_priority_commodity: r.top_priority_commodity, inventory_exposure_usd: r.inventory_exposure_usd } : {}],
    ['financial_auditor', 'Financial Auditor Agent', 'COST AUDIT',
      plan ? { total_financial_impact_usd: r.total_financial_impact_usd, cost_breakdown_usd: r.cost_breakdown_usd } : {}],
    ['final_decision', 'Final Decision', 'RESULT', r || {}],
  ];
  let elapsed = 0;
  const traceSteps = defs.filter(([key]) => timings[key] !== undefined).map(([key, agent, type, out], id) => {
    const start = elapsed;
    elapsed += timings[key];
    const tok = usage[key];
    return {
      id, agent, type, status: 'completed',
      timestamp: `${start.toFixed(3)}s`, timeSec: start, latencySec: timings[key],
      latency: `${timings[key].toFixed(3)}s`,
      tokens: tok ? tok.input_tokens + tok.output_tokens : 0,
      model: key === 'final_decision' ? 'LangGraph StateGraph' : model,
      inputPayload: { port: selectedEvent?.nearest_port_name ?? NA, severity: selectedEvent?.severity ?? NA },
      outputPayload: out,
    };
  });
  if (traceSteps.length === 0) {
    traceSteps.push({ id: 0, agent: r ? `No agents ran (${r.status})` : 'No run yet', type: 'NO TRACE',
      status: 'none', timestamp: NA, timeSec: 0, latencySec: 0, latency: NA, tokens: 0, model: NA,
      inputPayload: {}, outputPayload: r?.signal_gate || {} });
  }
  const scale = total || 1;

  const activeStep = traceSteps[selectedTraceStep] || traceSteps[0];

  return (
    <PageShell
      eyebrow="chronological execution trace"
      title="Every Step,"
      accent="Accounted For."
      sub="Timeline of the last real run: measured seconds and LLM tokens per agent."
      right={
        <div className="flex items-center gap-2 text-xs">
          <span className="cred-label text-[10px] text-neutral-500">Total Latency</span>
          <span className="mono text-base font-bold text-rose-400">
            {r ? `${r.total_response_time_seconds}s` : NA}
          </span>
        </div>
      }
    >
      {/* ── 1. Gantt Timeline Bar ───────────────────────────────────────── */}
      <section className="mb-12">
        <CredCard elevated hover={false} className="p-8 sm:p-10">
          <div className="mb-8 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Clock className="h-5 w-5 text-rose-400" />
              <h2 className="cred-hero text-xl sm:text-2xl text-white font-bold tracking-tight">
                Execution Timeline & Offsets
              </h2>
            </div>
            <span className="text-xs text-neutral-500">Click any step to inspect</span>
          </div>

          <div className="space-y-3">
            {traceSteps.map((step, idx) => {
              const isSelected = selectedTraceStep === step.id;
              return (
                <button
                  key={step.id}
                  onClick={() => setSelectedTraceStep(step.id)}
                  data-cursor-label="Inspect"
                  className={`w-full flex items-center justify-between gap-4 p-4 text-left transition-all duration-150 cursor-pointer border ${
                    isSelected
                      ? 'bg-[rgba(225,29,72,0.12)] border-[rgba(225,29,72,0.5)] text-white'
                      : 'bg-transparent border-transparent hover:bg-white/[0.03] hover:border-[rgba(225,29,72,0.25)]'
                  }`}
                >
                  <div className="flex w-52 shrink-0 items-center gap-3">
                    <span className="mono text-xs text-neutral-500">{step.timestamp}</span>
                    <span className="text-xs sm:text-sm font-bold text-white truncate">{step.agent}</span>
                  </div>

                  <div className="relative mx-3 h-2 flex-1 overflow-hidden bg-black/40">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${Math.max(4, (step.latencySec / scale) * 100)}%` }}
                      transition={{ delay: 0.1 + idx * 0.05, duration: 0.6 }}
                      className={`h-full ${BAR_SHADES[idx]}`}
                      style={{ marginLeft: `${(step.timeSec / scale) * 96}%` }}
                    />
                  </div>

                  <div className="flex w-36 shrink-0 items-center justify-end gap-3">
                    <span className="mono text-xs text-neutral-300 font-semibold">{step.latency}</span>
                    <span className="mono text-[10px] font-bold text-emerald-400">
                      DONE
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </CredCard>
      </section>

      {/* ── 2. Detailed Step Inspector ──────────────────────────────────── */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-8 mb-16">
        {/* Step Selector List */}
        <div className="lg:col-span-4">
          <CredCard hover={false} className="p-6 space-y-2">
            <div className="cred-label mb-4 text-neutral-400">Chronological Steps</div>
            {traceSteps.map((step) => (
              <button
                key={step.id}
                onClick={() => setSelectedTraceStep(step.id)}
                className={`w-full flex items-center justify-between p-3.5 text-left transition-all cursor-pointer border ${
                  selectedTraceStep === step.id
                    ? 'bg-[rgba(225,29,72,0.12)] border-[rgba(225,29,72,0.5)] text-white font-semibold'
                    : 'text-neutral-400 border-transparent hover:bg-white/[0.04] hover:text-white'
                }`}
              >
                <div>
                  <span className="mono text-[10px] text-neutral-500 block">{step.timestamp}</span>
                  <span className="text-xs font-semibold truncate block mt-0.5">{step.agent}</span>
                </div>
                <ChevronRight className={`h-4 w-4 ${selectedTraceStep === step.id ? 'text-rose-400' : 'text-neutral-600'}`} />
              </button>
            ))}
          </CredCard>
        </div>

        {/* Active Step Details & Payloads */}
        <div className="lg:col-span-8 space-y-6">
          <CredCard hover={false} className="p-8 flex flex-wrap items-center justify-between gap-6">
            <div>
              <span className="cred-label text-rose-400">{activeStep.type}</span>
              <h3 className="cred-hero text-2xl font-bold text-white mt-1">{activeStep.agent}</h3>
            </div>
            <div className="mono flex items-center gap-6 text-xs">
              <div>
                <span className="cred-label block text-[10px] text-neutral-500">Latency</span>
                <span className="font-bold text-emerald-400 mt-1 block">{activeStep.latency}</span>
              </div>
              <div>
                <span className="cred-label block text-[10px] text-neutral-500">Tokens</span>
                <span className="font-bold text-amber-400 mt-1 block">{activeStep.tokens} tk</span>
              </div>
              <div>
                <span className="cred-label block text-[10px] text-neutral-500">Engine</span>
                <span className="font-bold text-neutral-300 mt-1 block max-w-[150px] truncate">{activeStep.model}</span>
              </div>
            </div>
          </CredCard>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <JsonBlock data={activeStep.inputPayload} title="Step Input State" />
            <JsonBlock data={activeStep.outputPayload} title="Step Output State" />
          </div>
        </div>
      </section>
    </PageShell>
  );
}
