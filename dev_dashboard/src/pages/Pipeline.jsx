import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Cpu,
  DollarSign,
  FileCode2,
  MapPin,
  Package,
  Compass,
  ShieldCheck,
  Zap,
  Play
} from 'lucide-react';
import PageShell from '../components/layout/PageShell';
import { useSupplyPulse } from '../context/SupplyPulseContext';
import { JsonBlock, CredCard, SeverityBadge } from '../components/ui/primitives';

const PIPELINE_NODE_IDS = [
  'telemetry',
  'supervisor',
  'route_optimization',
  'inventory',
  'financial_auditor',
  'final_decision'
];

export default function PipelinePage() {
  const { pipelineResult, selectedEvent, isPipelineRunning, runPipeline } = useSupplyPulse();
  const [activeNode, setActiveNode] = useState('supervisor');
  const [runStep, setRunStep] = useState(6);

  const nodes = [
    {
      id: 'telemetry',
      name: 'GDELT Telemetry',
      index: '01',
      type: 'Input Stream',
      agentName: 'fetch_gdelt.py / enrich_gdelt.py',
      icon: MapPin,
      summary: `${selectedEvent?.nearest_port_name || 'Port of Shanghai'} (${selectedEvent?.severity || 'critical'})`,
      systemPrompt: 'Ingests GDELT news event telemetry, computes Goldstein Instability index, average tone, and maps coordinates to nearest seaport using spherical Haversine trigonometric distance.',
      userPayload: selectedEvent || {},
      llmParams: { provider: 'GDELT 2.0 Broadcast', polling: '15 mins', distance_formula: 'Haversine NM', tone: selectedEvent?.avg_tone || -4.5 },
      output: {
        nearest_port_name: selectedEvent?.nearest_port_name || 'Port of Shanghai',
        severity: selectedEvent?.severity || 'critical',
        goldstein_scale: selectedEvent?.goldstein_scale || -6.2,
        avg_tone: selectedEvent?.avg_tone || -4.5,
        affected_routes: selectedEvent?.alternative_routes || ['R01', 'R05'],
        freight_impact_pct: selectedEvent?.freight_impact_pct || 24.5
      }
    },
    {
      id: 'supervisor',
      name: 'Supervisor Agent',
      index: '02',
      type: 'LLM Orchestrator',
      agentName: 'agents/supervisor_agent.py',
      icon: Cpu,
      summary: 'Initial situational triage and task delegation to downstream specialized agents',
      systemPrompt: `You are the Supervisor Agent of SupplyPulse.\nYou coordinate EXACTLY these 4 agents:\n1. Route Optimization Agent\n2. Inventory Agent\n3. Financial Auditor Agent\n4. Supervisor Agent (yourself)\n\nProvide:\n1. SITUATION ASSESSMENT\n2. IMMEDIATE ACTIONS\n3. AGENT DELEGATION\n4. REROUTING RECOMMENDATION\n5. RISK LEVEL`,
      userPayload: {
        nearest_port: selectedEvent?.nearest_port_name,
        severity: selectedEvent?.severity,
        affected_routes: selectedEvent?.alternative_routes,
        at_risk_commodities: selectedEvent?.affected_commodities
      },
      llmParams: { provider: 'Groq Cloud', model: 'openai/gpt-oss-120b', temperature: 0.1, max_tokens: 1500 },
      output: {
        assessment: `DISRUPTION CONFIRMED: High severity event at ${selectedEvent?.nearest_port_name || 'Port of Shanghai'}. Operational bottleneck detected across major shipping corridors.`,
        delegation: ['Route Optimization Agent', 'Inventory Agent', 'Financial Auditor Agent'],
        preliminary_action: 'Prepare immediate vessel rerouting protocols and calculate draft-compatible alternate berths.'
      }
    },
    {
      id: 'route_optimization',
      name: 'Route Optimization',
      index: '03',
      type: 'Spatial Logistics',
      agentName: 'agents/route_optimization_agent.py',
      icon: Compass,
      summary: `Alternate port: ${pipelineResult?.recommended_alternate_port || 'Ningbo-Zhoushan'} (+${pipelineResult?.additional_transit_days || 2.1} days)`,
      systemPrompt: 'You are the Route Optimization Agent.\nCalculate alternate port options based on nautical distance (NM), vessel draft compatibility, port throughput capacity, transit delay days, and rerouting costs (USD).',
      userPayload: {
        disrupted_port: selectedEvent?.nearest_port_name,
        vessel_draft_m: 14.5,
        available_alternate_ports: selectedEvent?.alternative_routes || ['Port of Ningbo-Zhoushan', 'Port of Busan', 'Port of Tokyo']
      },
      llmParams: { provider: 'Groq Cloud', model: 'openai/gpt-oss-120b', temperature: 0.1, distance_metric: 'Great Circle NM' },
      output: {
        recommended_port: pipelineResult?.recommended_alternate_port || 'Port of Ningbo-Zhoushan',
        country: pipelineResult?.alternate_port_country || 'China',
        distance_nm: pipelineResult?.distance_nm || 114.5,
        estimated_delay_days: pipelineResult?.additional_transit_days || 2.1,
        estimated_cost_usd: pipelineResult?.rerouting_cost_usd || 45200
      }
    },
    {
      id: 'inventory',
      name: 'Inventory Agent',
      index: '04',
      type: 'Buffer Exposure',
      agentName: 'agents/inventory_agent.py',
      icon: Package,
      summary: `Priority: ${pipelineResult?.top_priority_commodity || 'Semiconductors'} ($${(pipelineResult?.inventory_exposure_usd || 1250000).toLocaleString()})`,
      systemPrompt: 'You are the Inventory Agent.\nAssess commodity inventory exposures, safety stock depletion rates, critical component lead-time impacts, and factory stockout timelines.',
      userPayload: {
        affected_commodities: selectedEvent?.affected_commodities,
        estimated_delay_days: pipelineResult?.additional_transit_days || 2.1
      },
      llmParams: { provider: 'Groq Cloud', model: 'openai/gpt-oss-120b', temperature: 0.1, buffer_horizon_days: 14 },
      output: {
        top_priority_commodity: pipelineResult?.top_priority_commodity || 'Semiconductors',
        inventory_exposure_usd: pipelineResult?.inventory_exposure_usd || 1250000,
        buffer_days_remaining: 4.5,
        stockout_risk: 'CRITICAL'
      }
    },
    {
      id: 'financial_auditor',
      name: 'Financial Auditor',
      index: '05',
      type: 'Cost Audit',
      agentName: 'agents/financial_auditor_agent.py',
      icon: DollarSign,
      summary: `Total Impact: $${(pipelineResult?.total_financial_impact_usd || 382000).toLocaleString()} (Alert: ${pipelineResult?.financial_alert ? 'TRIGGERED' : 'CLEAR'})`,
      systemPrompt: 'You are the Financial Auditor Agent.\nAudit complete financial exposure: demurrage charges, fuel surcharges, alternative port handling fees, lost customer revenue, and total USD impact. Trigger alert if > $100,000 USD.',
      userPayload: {
        rerouting_cost_usd: pipelineResult?.rerouting_cost_usd || 45200,
        inventory_exposure_usd: pipelineResult?.inventory_exposure_usd || 1250000,
        delay_days: pipelineResult?.additional_transit_days || 2.1
      },
      llmParams: { provider: 'Groq Cloud', model: 'openai/gpt-oss-120b', temperature: 0.1, threshold_usd: 100000 },
      output: {
        total_financial_impact_usd: pipelineResult?.total_financial_impact_usd || 382000,
        financial_alert: pipelineResult?.financial_alert ?? true,
        demurrage_usd: 85000,
        fuel_surcharge_usd: 24500,
        port_handling_usd: 20700
      }
    },
    {
      id: 'final_decision',
      name: 'Final Decision Node',
      index: '06',
      type: 'Consensus Synthesis',
      agentName: 'agents/langgraph_orchestrator.py',
      icon: ShieldCheck,
      summary: `UNIFIED: ${pipelineResult?.decision || 'REROUTE'} (Confidence: ${pipelineResult?.confidence || '92%'})`,
      systemPrompt: 'Synthesizes all specialized agent outputs into a unified, actionable supply chain response plan with state convergence.',
      userPayload: pipelineResult || {},
      llmParams: { framework: 'LangGraph StateGraph', execution_time_sec: pipelineResult?.total_response_time_seconds || 3.42 },
      output: pipelineResult || {}
    }
  ];

  const currentNode = nodes.find(n => n.id === activeNode) || nodes[1];

  useEffect(() => {
    if (!isPipelineRunning) {
      setRunStep(6);
      return undefined;
    }
    setRunStep(0);
    setActiveNode(PIPELINE_NODE_IDS[0]);
    const timer = window.setInterval(() => {
      setRunStep(step => {
        const next = Math.min(step + 1, PIPELINE_NODE_IDS.length);
        if (next < PIPELINE_NODE_IDS.length) setActiveNode(PIPELINE_NODE_IDS[next]);
        return next;
      });
    }, 550);
    return () => window.clearInterval(timer);
  }, [isPipelineRunning]);

  return (
    <PageShell
      eyebrow="autonomous multi-agent orchestrator"
      title="The LangGraph"
      accent="Pipeline."
      sub="Six stages, one directed state graph. Click any node to inspect its execution parameters, system prompt, and state payloads."
      right={
        <div className="flex items-center gap-4">
          <div className="hidden sm:flex items-center gap-2 text-xs text-neutral-400">
            <span className="mono text-neutral-300 font-semibold">{isPipelineRunning ? 'Executing…' : 'Graph Ready'}</span>
            <span className="text-neutral-700">·</span>
            <span className="mono text-neutral-400">{pipelineResult?.total_response_time_seconds || 3.42}s</span>
          </div>

          <button
            onClick={runPipeline}
            disabled={isPipelineRunning}
            className="cred-btn-primary text-xs"
          >
            {isPipelineRunning ? (
              <>
                <Zap className="h-3.5 w-3.5 text-rose-600" />
                <span>Running…</span>
              </>
            ) : (
              <>
                <Play className="h-3.5 w-3.5 fill-black" />
                <span>Re-run Graph</span>
              </>
            )}
          </button>
        </div>
      }
    >
      {/* ── 1. Unified Decision Banner ─────────────────────────────────── */}
      <section className="mb-12">
        <CredCard elevated hover={false} className="p-8 sm:p-10">
          <div className="flex flex-wrap items-center justify-between gap-6">
            <div className="flex items-center gap-6">
              <div className="text-xl sm:text-2xl font-black tracking-tight text-rose-500">
                {pipelineResult?.decision || 'REROUTE'}
              </div>
              <div className="border-l border-[rgba(225,29,72,0.3)] pl-6">
                <div className="text-base sm:text-lg font-bold text-white tracking-tight">
                  {pipelineResult?.disrupted_port} ➔ {pipelineResult?.recommended_alternate_port}
                </div>
                <div className="mono text-xs text-neutral-400 mt-1 flex items-center gap-3">
                  <span>+{pipelineResult?.additional_transit_days} Transit Days</span>
                  <span>·</span>
                  <span>${(pipelineResult?.rerouting_cost_usd || 0).toLocaleString()} Reroute Cost</span>
                  <span>·</span>
                  <span>{pipelineResult?.distance_nm} NM</span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-6">
              <SeverityBadge severity={pipelineResult?.severity} />
              <div className="text-xs text-neutral-400">
                Confidence <b className="mono text-emerald-400 font-bold text-sm ml-1">{pipelineResult?.confidence}</b>
              </div>
            </div>
          </div>
        </CredCard>
      </section>

      {/* ── 2. Interactive Directed Graph DAG ────────────────────────────── */}
      <section className="mb-16">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <span className="cred-label">Execution Graph</span>
            <h2 className="cred-hero text-2xl sm:text-3xl text-white font-bold tracking-tight mt-1">
              Topological DAG Nodes
            </h2>
          </div>
          <span className="text-xs text-neutral-500">Click node to inspect memory & prompts</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          {nodes.map((node, idx) => {
            const isSelected = activeNode === node.id;
            const executing = isPipelineRunning && runStep === idx;
            const done = !isPipelineRunning || runStep > idx;
            const Icon = node.icon;

            return (
              <button
                key={node.id}
                onClick={() => setActiveNode(node.id)}
                data-cursor-label="Inspect"
                className={`relative flex flex-col justify-between p-5 text-left transition-all duration-200 cursor-pointer min-h-[140px] ${
                  executing
                    ? 'bg-[rgba(225,29,72,0.14)] border border-[rgba(225,29,72,0.7)]'
                    : isSelected
                    ? 'bg-[#0C0C11] border border-[rgba(225,29,72,0.55)]'
                    : 'bg-[#0A0A0D] border border-[rgba(225,29,72,0.25)] hover:border-[rgba(225,29,72,0.55)]'
                }`}
              >
                <div className="flex items-center justify-between mb-4">
                  <div className={`flex h-9 w-9 items-center justify-center transition-colors ${
                    isSelected || executing
                      ? 'bg-[#E11D48] text-white'
                      : 'bg-white/[0.06] text-neutral-400'
                  }`}>
                    <Icon className="h-4 w-4" />
                  </div>
                  <span className={`mono text-[10px] font-bold ${
                    executing ? 'text-rose-400' : done ? 'text-emerald-400' : 'text-neutral-500'
                  }`}>
                    {executing ? 'RUN' : done ? 'DONE' : node.index}
                  </span>
                </div>

                <div className="text-xs sm:text-sm font-bold text-white tracking-tight truncate">
                  {node.name}
                </div>
                <div className="cred-label mt-1 text-[10px] text-neutral-500 truncate">
                  {node.type}
                </div>
              </button>
            );
          })}
        </div>
      </section>

      {/* ── 3. Deep Node Inspector ───────────────────────────────────────── */}
      <AnimatePresence mode="wait">
        <motion.section
          key={currentNode.id}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.25 }}
          className="grid grid-cols-1 lg:grid-cols-12 gap-8"
        >
          {/* Left Column: Node Schematic & System Prompt */}
          <div className="lg:col-span-7 flex flex-col gap-6">
            <CredCard elevated hover={false} className="p-8 sm:p-10">
              <div className="flex items-start justify-between border-b border-[rgba(225,29,72,0.25)] pb-6 mb-6">
                <div>
                  <span className="cred-label text-rose-400">{currentNode.type}</span>
                  <h3 className="cred-hero text-2xl font-bold text-white mt-1">
                    {currentNode.name}
                  </h3>
                  <p className="mono text-xs text-neutral-400 mt-1">{currentNode.agentName}</p>
                </div>
                <span className="mono border border-emerald-500/30 bg-emerald-500/[0.07] px-3 py-1 text-[10px] font-bold text-emerald-400 uppercase tracking-wider">
                  ● ACTIVE NODE
                </span>
              </div>

              {/* Parameters Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
                {Object.entries(currentNode.llmParams).map(([k, v]) => (
                  <div key={k} className="cred-inset p-4">
                    <span className="cred-label block text-[10px] text-neutral-500">
                      {k.replace('_', ' ')}
                    </span>
                    <span className="mono text-xs font-bold text-white mt-1 block truncate">
                      {String(v)}
                    </span>
                  </div>
                ))}
              </div>

              {/* System Prompt View */}
              <div className="mb-6">
                <div className="cred-label mb-3 flex items-center gap-2 text-neutral-300">
                  <FileCode2 className="h-4 w-4 text-rose-400" />
                  <span>System Prompt & Role Definition</span>
                </div>
                <pre className="mono max-h-60 overflow-y-auto whitespace-pre-wrap rounded-2xl bg-[#08080C] border border-[rgba(225,29,72,0.25)] p-5 text-xs leading-relaxed text-neutral-300">
                  {currentNode.systemPrompt}
                </pre>
              </div>

              {/* Summary Callout */}
              <div className="border border-[rgba(225,29,72,0.3)] bg-[rgba(225,29,72,0.07)] px-6 py-4 text-xs text-neutral-300 leading-relaxed">
                <b className="text-[#E11D48] font-bold uppercase tracking-wider">Node Output Summary: </b>
                <span>{currentNode.summary}</span>
              </div>
            </CredCard>
          </div>

          {/* Right Column: Payloads & State JSON */}
          <div className="lg:col-span-5 flex flex-col gap-6">
            <JsonBlock data={currentNode.userPayload} title="Stage Input State" maxH="max-h-[280px]" />
            <JsonBlock data={currentNode.output} title="Stage Computed Output" maxH="max-h-[340px]" />
          </div>
        </motion.section>
      </AnimatePresence>
    </PageShell>
  );
}
