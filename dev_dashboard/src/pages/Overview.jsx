import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, ArrowUpRight, Navigation, Sparkles, Zap } from 'lucide-react';
import PageShell from '../components/layout/PageShell';
import { useSupplyPulse } from '../context/SupplyPulseContext';
import { NA, fmtUsd, hasPlan } from '../lib/format';
import { CountUp, CredCard, RunStatusBanner, SeverityBadge } from '../components/ui/primitives';

// Every number on this page comes from the last real API run (pipelineResult).
// When there is no run, values show "—".
export default function Overview() {
  const { selectedEvent, pipelineResult, isPipelineRunning, runPipeline } = useSupplyPulse();
  const navigate = useNavigate();

  const r = pipelineResult;
  const plan = hasPlan(r);
  const isReroute = r?.decision === 'REROUTE';
  const gate = r?.signal_gate;
  const model = r?.llm_model?.replace('openai/', '') || 'gpt-oss-20b';
  const alternatePort = plan ? r.recommended_alternate_port : NA;
  const targetPort = selectedEvent?.nearest_port_name ?? NA;
  const travelDays = plan ? r.travel_time_days : null;

  const agents = [
    { step: '01', name: 'Supervisor Agent', role: 'Assessment and delegation',
      status: plan ? 'Assessment written' : NA, detail: r?.agent_assessments?.supervisor },
    { step: '02', name: 'Route Optimization', role: 'Wardrop equilibrium ship allocation',
      status: plan ? `Alternate: ${alternatePort}` : NA, detail: r?.agent_assessments?.route },
    { step: '03', name: 'Inventory Agent', role: 'Commodity exposure',
      status: plan ? r.top_priority_commodity : NA, detail: r?.agent_assessments?.inventory },
    { step: '04', name: 'Financial Auditor', role: 'Six-part cost incl. EU ETS',
      status: plan ? (r.financial_alert ? 'Alert triggered' : 'Within threshold') : NA,
      detail: r?.agent_assessments?.financial },
  ];

  return (
    <PageShell
      eyebrow="operations overview"
      title="Disruption Resolution &"
      accent="Telemetry."
      sub="Multi-agent assessment, ship allocation by Wardrop user equilibrium (BPR port congestion) and a six-part cost estimate. All figures come from the last pipeline run."
      right={
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/events')} className="cred-btn-secondary text-xs">Change Event</button>
          <button
            onClick={() => { navigate('/pipeline'); runPipeline(); }}
            disabled={isPipelineRunning}
            className="cred-btn-crimson text-xs font-semibold"
          >
            {isPipelineRunning
              ? (<><Zap className="h-3.5 w-3.5" /><span>Running…</span></>)
              : (<><span>Run Pipeline</span><ArrowUpRight className="h-3.5 w-3.5" /></>)}
          </button>
        </div>
      }
    >
      <RunStatusBanner />

      {/* ── 1. Selected event ─────────────────────────────────────────────── */}
      <section className="mb-14 grid grid-cols-2 lg:grid-cols-4 gap-8 border-b border-[rgba(225,29,72,0.25)] pb-10">
        <div>
          <span className="cred-label block mb-1.5 text-neutral-500">Target Seaport</span>
          <div className="text-xl font-bold text-white tracking-tight truncate">{targetPort}</div>
          <span className="text-xs text-neutral-500 mt-1 block">{selectedEvent?.nearest_port_country ?? NA}</span>
        </div>
        <div>
          <span className="cred-label block mb-1.5 text-neutral-500">Event</span>
          <div className="text-xl font-bold text-white capitalize tracking-tight truncate">{selectedEvent?.disruption_type ?? NA}</div>
          <span className="text-xs text-neutral-500 mt-1 block">
            {selectedEvent?.origin === 'synthetic' ? 'SYNTHETIC SCENARIO' : 'Development-set event'}
          </span>
        </div>
        <div>
          <span className="cred-label block mb-1.5 text-neutral-500">Duration (rule-based estimate)</span>
          <div className="mono text-xl font-bold text-white">{selectedEvent?.duration_hours ?? NA} h</div>
        </div>
        <div>
          <span className="cred-label block mb-1.5 text-neutral-500">Freight-rate impact (rule-based estimate)</span>
          <div className="mono text-xl font-bold text-amber-400">
            {selectedEvent?.freight_impact_pct != null ? `+${selectedEvent.freight_impact_pct}%` : NA}
          </div>
        </div>
      </section>

      {/* ── 2. Decision ───────────────────────────────────────────────────── */}
      <section className="mb-16">
        <CredCard elevated hover={false} className="p-8 sm:p-12">
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[rgba(225,29,72,0.25)] pb-6 mb-8">
            <span className="mono text-xs text-neutral-400">
              Run status: <b className="text-white font-medium">{r?.status ?? 'no run yet'}</b>
              {r && <> · Response time: <b className="text-white font-medium">{r.total_response_time_seconds}s</b></>}
            </span>
            <div className="flex items-center gap-3">
              <span className="text-xs text-neutral-500">Severity (rule-based)</span>
              {selectedEvent?.severity ? <SeverityBadge severity={selectedEvent.severity} /> : NA}
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-14 items-center">
            <div className="lg:col-span-6 flex flex-col justify-center">
              <span className="cred-label mb-2 text-neutral-500">Total Estimated Financial Impact</span>
              <div className="cred-hero text-4xl sm:text-5xl md:text-6xl text-white mono mb-4">
                {plan ? <CountUp value={r.total_financial_impact_usd} prefix="$" decimals={0} /> : NA}
              </div>
              <p className="text-xs sm:text-sm text-neutral-400 leading-relaxed max-w-lg">
                Sum of rerouting, trade delay, freight increase, inventory at risk, operating cost and EU ETS carbon.
                Several of these constants are assumptions without a source yet.
              </p>
            </div>

            <div className="lg:col-span-6 border-t lg:border-t-0 lg:border-l border-[rgba(225,29,72,0.25)] pt-8 lg:pt-0 lg:pl-12 flex flex-col gap-6">
              <div className="flex items-center justify-between">
                <span className="cred-label text-neutral-500">Recommendation</span>
                <span className="mono text-xs text-rose-400 font-bold tracking-wider">
                  SIGNAL GATE {gate ? `${gate.action}${gate.score != null ? ` (${gate.score})` : ''}${gate.enforced === false ? ' · not enforced (manual)' : ''}` : NA}
                </span>
              </div>
              <div className="flex items-start gap-4">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center border border-[rgba(225,29,72,0.4)] bg-[rgba(225,29,72,0.1)] text-[#E11D48]">
                  <Navigation className="h-5 w-5" />
                </div>
                <div>
                  <div className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                    {!r ? 'No run yet' : !plan ? r.decision : isReroute ? `REROUTE ➔ ${alternatePort}` : 'MONITOR'}
                  </div>
                  <span className="text-xs text-neutral-400 mt-1.5 block leading-relaxed">{r?.decision_basis ?? ''}</span>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-6 pt-4 border-t border-[rgba(225,29,72,0.25)]">
                <div>
                  <span className="cred-label block mb-1 text-neutral-500">Travel time at that port (sailing + port)</span>
                  <span className="mono text-lg font-bold text-white">{travelDays != null ? `${travelDays} days` : NA}</span>
                </div>
                <div>
                  <span className="cred-label block mb-1 text-neutral-500">Rerouting cost (all ports)</span>
                  <span className="mono text-lg font-bold text-white">{plan ? fmtUsd(r.rerouting_cost_usd) : NA}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-6 pt-8 mt-10 border-t border-[rgba(225,29,72,0.25)]">
            <div>
              <span className="cred-label block mb-1.5 text-neutral-500">Response time</span>
              <span className="mono text-xl font-bold text-white">{r ? `${r.total_response_time_seconds}s` : NA}</span>
            </div>
            <div>
              <span className="cred-label block mb-1.5 text-neutral-500">Signal gate score</span>
              <span className="mono text-xl font-bold text-emerald-400">{gate?.score ?? NA}</span>
            </div>
            <div>
              <span className="cred-label block mb-1.5 text-neutral-500">Priority cargo</span>
              <span className="text-sm font-semibold text-white block truncate">{plan ? r.top_priority_commodity : NA}</span>
            </div>
            <div>
              <span className="cred-label block mb-1.5 text-neutral-500">LLM tokens (in / out)</span>
              <span className="mono text-sm font-bold text-rose-400 block">
                {r?.llm_usage ? `${r.llm_usage.input_tokens} / ${r.llm_usage.output_tokens}` : NA}
              </span>
            </div>
          </div>
        </CredCard>
      </section>

      {/* ── 3. Agents ─────────────────────────────────────────────────────── */}
      <section className="mb-16">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <span className="cred-label text-neutral-500">Multi-Agent Workflow</span>
            <h2 className="cred-hero text-2xl sm:text-3xl text-white font-bold tracking-tight mt-1">Agent Outputs</h2>
          </div>
          <button onClick={() => navigate('/pipeline')} className="cred-btn-secondary text-xs">
            <span>Inspect Pipeline</span><ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {agents.map((agent) => (
            <CredCard key={agent.step} onClick={() => navigate('/pipeline')} cursorLabel="Inspect"
              className="p-6 flex flex-col justify-between min-h-[250px]">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="mono text-xs font-bold text-rose-400">{agent.step}</span>
                  <span className="mono text-[10px] text-neutral-500">{model}</span>
                </div>
                <h3 className="text-base font-bold text-white mb-0.5">{agent.name}</h3>
                <span className="text-xs text-neutral-400 block mb-3.5">{agent.role}</span>
                <p className="text-xs text-neutral-400 leading-relaxed border-t border-[rgba(225,29,72,0.22)] pt-3 whitespace-pre-line">
                  {agent.detail ?? 'No run yet.'}
                </p>
              </div>
              <div className="mt-5 pt-3 border-t border-[rgba(225,29,72,0.22)] flex items-center justify-between text-xs">
                <span className="font-semibold text-neutral-300 truncate">{agent.status}</span>
                <Sparkles className="h-3.5 w-3.5 text-rose-400 shrink-0 ml-1.5" />
              </div>
            </CredCard>
          ))}
        </div>
      </section>

      {/* ── 4. Ports ──────────────────────────────────────────────────────── */}
      <section className="mb-12 border-t border-[rgba(225,29,72,0.25)] pt-10">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-center">
          <div>
            <span className="cred-label block mb-1.5 text-neutral-500">Disrupted Seaport</span>
            <div className="text-lg font-bold text-white">{targetPort}</div>
          </div>
          <div>
            <span className="cred-label block mb-1.5 text-neutral-500">Code-selected alternate</span>
            <div className="text-lg font-bold text-emerald-400">{alternatePort}</div>
            <span className="text-xs text-neutral-500 mt-1 block">
              {travelDays != null ? `${travelDays} days travel time (sailing + port); port with the most ships` : NA}
            </span>
          </div>
          <div className="flex md:justify-end">
            <button onClick={() => navigate('/events')} className="cred-btn-secondary text-xs">Browse Events</button>
          </div>
        </div>
      </section>
    </PageShell>
  );
}
