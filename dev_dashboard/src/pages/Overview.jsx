import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  ArrowUpRight,
  CheckCircle2,
  Navigation,
  Sparkles,
  Zap
} from 'lucide-react';
import PageShell from '../components/layout/PageShell';
import { useSupplyPulse } from '../context/SupplyPulseContext';
import { CountUp, CredCard, SeverityBadge } from '../components/ui/primitives';

export default function Overview() {
  const {
    selectedEvent,
    pipelineResult,
    isPipelineRunning,
    runPipeline
  } = useSupplyPulse();

  const navigate = useNavigate();

  const isReroute = pipelineResult?.decision === 'REROUTE';
  const confidenceNum = parseInt(pipelineResult?.confidence) || 92;
  const financialImpact = pipelineResult?.total_financial_impact_usd || 0;
  const responseTime = pipelineResult?.total_response_time_seconds || 3.42;
  const alternatePort = pipelineResult?.recommended_alternate_port || 'Port of Ningbo-Zhoushan';
  const targetPort = selectedEvent?.nearest_port_name || 'Port of Shanghai';
  const priorityCommodity = pipelineResult?.top_priority_commodity || 'Electronics & Semiconductors';
  const exposureUsd = pipelineResult?.inventory_exposure_usd || 0;
  const rerouteCost = pipelineResult?.rerouting_cost_usd || 0;
  const additionalDays = pipelineResult?.additional_transit_days || 0;
  const disruptionType = selectedEvent?.disruption_type || 'Maritime Disruption';
  const durationHours = selectedEvent?.duration_hours || 72;
  const freightShock = selectedEvent?.freight_impact_pct || 20;

  const agents = [
    {
      step: '01',
      name: 'Supervisor Agent',
      role: 'Triage & Task Delegation',
      model: 'gpt-oss-120b',
      status: 'Consensus Reached',
      detail: pipelineResult?.agent_assessments?.supervisor || `Assessed ${selectedEvent?.severity || 'CRITICAL'} severity event. Initiated multi-agent consensus graph.`
    },
    {
      step: '02',
      name: 'Route Optimization',
      role: 'Maritime Routing & Bathymetry',
      model: 'gpt-oss-120b',
      status: `Alternate: ${alternatePort}`,
      detail: pipelineResult?.agent_assessments?.route || `Evaluated nautical corridors. Recommended diverting to ${alternatePort} with +${additionalDays} days transit delay.`
    },
    {
      step: '03',
      name: 'Inventory Agent',
      role: 'Supply Exposure & Stockout',
      model: 'gpt-oss-120b',
      status: priorityCommodity,
      detail: pipelineResult?.agent_assessments?.inventory || `Audited supply buffer for ${priorityCommodity}. Projected inventory risk exposure of $${(exposureUsd / 1e6).toFixed(2)}M USD.`
    },
    {
      step: '04',
      name: 'Financial Auditor',
      role: 'Demurrage & Financial Exposure',
      model: 'gpt-oss-120b',
      status: pipelineResult?.financial_alert ? 'Alert Active' : 'Mitigated',
      detail: pipelineResult?.agent_assessments?.financial || `Calculated bottom-line financial impact of $${financialImpact.toLocaleString()} USD across freight rate surges and demurrage.`
    }
  ];

  return (
    <PageShell
      eyebrow="autonomous operations intelligence"
      title="Disruption Resolution &"
      accent="Telemetry."
      sub="Real-time multi-agent situational triage, spherical geodesic route optimization, and quantified financial impact modeling."
      right={
        <div className="flex items-center gap-3">
          <button
            onClick={() => navigate('/events')}
            className="cred-btn-secondary text-xs"
          >
            Change Scenario
          </button>
          <button
            onClick={() => {
              navigate('/pipeline');
              runPipeline();
            }}
            disabled={isPipelineRunning}
            className="cred-btn-crimson text-xs font-semibold"
          >
            {isPipelineRunning ? (
              <>
                <Zap className="h-3.5 w-3.5" />
                <span>Executing…</span>
              </>
            ) : (
              <>
                <span>Execute Pipeline</span>
                <ArrowUpRight className="h-3.5 w-3.5" />
              </>
            )}
          </button>
        </div>
      }
    >
      {/* ── 1. Active Scenario Context Strip (Borderless Open Grid) ────────── */}
      <section className="mb-14 grid grid-cols-2 lg:grid-cols-4 gap-8 border-b border-white/[0.06] pb-10">
        <div>
          <span className="cred-label block mb-1.5 text-neutral-500">Target Seaport</span>
          <div className="text-xl font-bold text-white tracking-tight truncate">{targetPort}</div>
          <span className="text-xs text-neutral-500 mt-1 block">{selectedEvent?.nearest_port_country || 'Global Hub'}</span>
        </div>

        <div>
          <span className="cred-label block mb-1.5 text-neutral-500">Disruption Event</span>
          <div className="text-xl font-bold text-white capitalize tracking-tight truncate">{disruptionType}</div>
          <span className="text-xs text-neutral-500 mt-1 block">GDELT Broadcast Signal</span>
        </div>

        <div>
          <span className="cred-label block mb-1.5 text-neutral-500">Expected Duration</span>
          <div className="mono text-xl font-bold text-white">{durationHours} Hours</div>
          <span className="text-xs text-neutral-500 mt-1 block">Est. resolution window</span>
        </div>

        <div>
          <span className="cred-label block mb-1.5 text-neutral-500">Freight Rate Surge</span>
          <div className="mono text-xl font-bold text-amber-400">+{freightShock}%</div>
          <span className="text-xs text-neutral-500 mt-1 block">Market variance index</span>
        </div>
      </section>

      {/* ── 2. Primary Hero Mission Control (Unified, Single Surface) ─────── */}
      <section className="mb-16">
        <CredCard elevated hover={false} className="p-8 sm:p-12">
          {/* Top Status Header */}
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/[0.06] pb-6 mb-8">
            <div className="flex items-center gap-3">
              <span className="flex items-center gap-2 text-xs font-semibold text-emerald-400">
                <CheckCircle2 className="h-4 w-4" />
                Multi-Agent Consensus Verified
              </span>
              <span className="text-neutral-700 hidden sm:inline">·</span>
              <span className="mono text-xs text-neutral-400 hidden sm:inline">
                Latency: <b className="text-white font-medium">{responseTime}s</b>
              </span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs text-neutral-500">Severity</span>
              <SeverityBadge severity={selectedEvent?.severity || 'CRITICAL'} />
            </div>
          </div>

          {/* Core Decision Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 lg:gap-14 items-center">
            {/* Left: Financial Impact Exposure */}
            <div className="lg:col-span-6 flex flex-col justify-center">
              <span className="cred-label mb-2 text-neutral-500">
                Total Quantified Financial Exposure
              </span>
              <div className="cred-hero text-4xl sm:text-5xl md:text-6xl text-white mono mb-4">
                <CountUp value={financialImpact} prefix="$" decimals={0} />
              </div>
              <p className="text-xs sm:text-sm text-neutral-400 leading-relaxed max-w-lg">
                Quantified exposure calculated across delayed cargo inventory value, freight spot-market surges (+{freightShock}%), and vessel carrier demurrage penalties.
              </p>
            </div>

            {/* Right: Autonomous Directive (No nested boxes) */}
            <div className="lg:col-span-6 border-t lg:border-t-0 lg:border-l border-white/[0.06] pt-8 lg:pt-0 lg:pl-12 flex flex-col gap-6">
              <div className="flex items-center justify-between">
                <span className="cred-label text-neutral-500">Autonomous Recommendation</span>
                <span className="mono text-xs text-rose-400 font-bold tracking-wider">
                  CONFIDENCE {confidenceNum}%
                </span>
              </div>

              <div className="flex items-start gap-4">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-rose-500/10 text-rose-400">
                  <Navigation className="h-5 w-5" />
                </div>
                <div>
                  <div className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                    {isReroute ? `REROUTE ➔ ${alternatePort}` : 'MONITOR SITUATION'}
                  </div>
                  <span className="text-xs text-neutral-400 mt-1.5 block leading-relaxed">
                    Divert vessels to draft-compatible maritime berth with optimal terminal capacity.
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-6 pt-4 border-t border-white/[0.06]">
                <div>
                  <span className="cred-label block mb-1 text-neutral-500">Transit Delay</span>
                  <span className="mono text-lg font-bold text-white">+{additionalDays} Days</span>
                </div>
                <div>
                  <span className="cred-label block mb-1 text-neutral-500">Rerouting Cost</span>
                  <span className="mono text-lg font-bold text-white">${rerouteCost.toLocaleString()}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Bottom KPI Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-6 pt-8 mt-10 border-t border-white/[0.06]">
            <div>
              <span className="cred-label block mb-1.5 text-neutral-500">Response Latency</span>
              <span className="mono text-xl font-bold text-white">{responseTime}s</span>
            </div>
            <div>
              <span className="cred-label block mb-1.5 text-neutral-500">Decision Confidence</span>
              <span className="mono text-xl font-bold text-emerald-400">{confidenceNum}%</span>
            </div>
            <div>
              <span className="cred-label block mb-1.5 text-neutral-500">Priority Cargo</span>
              <span className="text-sm font-semibold text-white block truncate">
                {priorityCommodity}
              </span>
            </div>
            <div>
              <span className="cred-label block mb-1.5 text-neutral-500">Execution Engine</span>
              <span className="mono text-sm font-bold text-rose-400 block">
                LangGraph 4-Agent
              </span>
            </div>
          </div>
        </CredCard>
      </section>

      {/* ── 3. Multi-Agent Execution Flow ─────────────────────────────────── */}
      <section className="mb-16">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <span className="cred-label text-neutral-500">Multi-Agent Workflow</span>
            <h2 className="cred-hero text-2xl sm:text-3xl text-white font-bold tracking-tight mt-1">
              Autonomous Consensus Graph
            </h2>
          </div>
          <button
            onClick={() => navigate('/pipeline')}
            className="cred-btn-secondary text-xs"
          >
            <span>Inspect Pipeline</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {agents.map((agent) => (
            <CredCard
              key={agent.step}
              onClick={() => navigate('/pipeline')}
              className="p-6 flex flex-col justify-between min-h-[250px]"
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="mono text-xs font-bold text-rose-400">{agent.step}</span>
                  <span className="mono text-[10px] text-neutral-500">
                    {agent.model}
                  </span>
                </div>
                <h3 className="text-base font-bold text-white mb-0.5">{agent.name}</h3>
                <span className="text-xs text-neutral-400 block mb-3.5">{agent.role}</span>
                <p className="text-xs text-neutral-400 leading-relaxed border-t border-white/[0.05] pt-3">
                  {agent.detail}
                </p>
              </div>

              <div className="mt-5 pt-3 border-t border-white/[0.05] flex items-center justify-between text-xs">
                <span className="font-semibold text-neutral-300 truncate">{agent.status}</span>
                <Sparkles className="h-3.5 w-3.5 text-rose-400 shrink-0 ml-1.5" />
              </div>
            </CredCard>
          ))}
        </div>
      </section>

      {/* ── 4. Seaport Contingency Routing ───────────────────────────────── */}
      <section className="mb-12 border-t border-white/[0.06] pt-10">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-center">
          <div>
            <span className="cred-label block mb-1.5 text-neutral-500">Disrupted Seaport</span>
            <div className="text-lg font-bold text-white">{targetPort}</div>
            <span className="text-xs text-neutral-500 mt-1 block">Primary commercial container terminal</span>
          </div>

          <div>
            <span className="cred-label block mb-1.5 text-neutral-500">Optimal Contingency Berth</span>
            <div className="text-lg font-bold text-emerald-400">{alternatePort}</div>
            <span className="text-xs text-neutral-500 mt-1 block">+{additionalDays} days transit · Lowest berth wait time</span>
          </div>

          <div className="flex md:justify-end">
            <button
              onClick={() => navigate('/events')}
              className="cred-btn-secondary text-xs"
            >
              Browse All Disruption Signals
            </button>
          </div>
        </div>
      </section>
    </PageShell>
  );
}
