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
import { NA, fmtUsd, hasPlan } from '../lib/format';
import { JsonBlock, CredCard, RunStatusBanner, SeverityBadge } from '../components/ui/primitives';

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

  // Every value comes from the selected event or the last real API run (missing = "—").
  // "description" text describes what the code does; it is not the LLM prompt itself.
  const r = pipelineResult;
  const plan = hasPlan(r);
  const t = r?.agent_timings_seconds || {};
  const u = r?.llm_usage?.per_agent || {};
  const model = r?.llm_model || 'openai/gpt-oss-20b';
  const llmParams = (agent, maxTokens) => ({
    model, max_tokens: maxTokens,
    seconds: t[agent] ?? NA,
    tokens_in_out: u[agent] ? `${u[agent].input_tokens} / ${u[agent].output_tokens}` : NA,
  });

  const nodes = [
    {
      id: 'telemetry',
      name: 'Signal Gate',
      index: '01',
      type: 'Input + Gate',
      agentName: 'agents/confidence.py',
      icon: MapPin,
      summary: r?.signal_gate ? `${r.signal_gate.action} (score ${r.signal_gate.score})` : 'No run yet',
      systemPrompt: 'Scores the news signal (mention volume 40%, |Goldstein| 35%, |tone| 25%). The gate is enforced for live GDELT events only (agents run on PROCEED, score >= 0.60); manual scenarios always run and show the score. Weights and thresholds are assumptions; it is not a conformal method.',
      userPayload: selectedEvent?.raw || selectedEvent || {},
      llmParams: { llm: 'none (deterministic)', reject_below: 0.35, proceed_from: 0.60 },
      output: r?.signal_gate || {}
    },
    {
      id: 'supervisor',
      name: 'Supervisor Agent',
      index: '02',
      type: 'LLM Orchestrator',
      agentName: 'agents/supervisor_agent.py',
      icon: Cpu,
      summary: plan ? 'Situation assessment and delegation written' : 'No plan',
      systemPrompt: 'Writes the situation assessment, immediate actions and delegation. It is told not to choose a port, a risk rating or any number.',
      userPayload: { nearest_port: selectedEvent?.nearest_port_name ?? NA, severity: selectedEvent?.severity ?? NA },
      llmParams: llmParams('supervisor', 700),
      output: { assessment: r?.agent_assessments?.supervisor ?? NA }
    },
    {
      id: 'route_optimization',
      name: 'Route Optimization',
      index: '03',
      type: 'Port Scoring',
      agentName: 'agents/route_optimization_agent.py',
      icon: Compass,
      summary: plan ? `Most ships to ${r.recommended_alternate_port}; equilibrium travel time ${r.equilibrium_time_days} d` : 'No plan',
      systemPrompt: 'Code allocates ships per day by a Wardrop (1952) user equilibrium: travel time = sailing + BPR port time (alpha 0.15, beta 4; U.S. Bureau of Public Roads 1964), equal at every port used. The 0.40 risk + 0.35 time + 0.25 cost score is for comparison only. The LLM only explains.',
      userPayload: { disrupted_port: selectedEvent?.nearest_port_name ?? NA, vessels_affected: selectedEvent?.vessels_affected ?? NA, duration_hours: selectedEvent?.duration_hours ?? NA },
      llmParams: llmParams('route_optimization', 400),
      output: plan ? { recommended_port: r.recommended_alternate_port, ship_allocation: r.ship_allocation, explanation: r.agent_assessments?.route } : {}
    },
    {
      id: 'inventory',
      name: 'Inventory Agent',
      index: '04',
      type: 'Commodity Exposure',
      agentName: 'agents/inventory_agent.py',
      icon: Package,
      summary: plan ? `Priority: ${r.top_priority_commodity} (${fmtUsd(r.inventory_exposure_usd)})` : 'No plan',
      systemPrompt: 'Code matches commodity words to commodities.json (whole words) and computes exposed containers and value. Containers per vessel is an assumption. The LLM only explains.',
      userPayload: { affected_commodities: selectedEvent?.affected_commodities ?? NA },
      llmParams: llmParams('inventory', 700),
      output: plan ? { inventory_analysis: r.inventory_analysis, unmatched_commodities: r.unmatched_commodities, explanation: r.agent_assessments?.inventory } : {}
    },
    {
      id: 'financial_auditor',
      name: 'Financial Auditor',
      index: '05',
      type: 'Cost Audit',
      agentName: 'agents/financial_auditor_agent.py',
      icon: DollarSign,
      summary: plan ? `Total: ${fmtUsd(r.total_financial_impact_usd)} (alert ${r.financial_alert ? 'TRIGGERED' : 'not triggered'}, threshold ${fmtUsd(r.alert_threshold_usd)})` : 'No plan',
      systemPrompt: 'Code prices each receiving port: rerouting + ship-weighted travel time + freight + inventory at risk + operating cost + EU ETS carbon (Directive (EU) 2023/959). Several constants are assumptions. The LLM only explains.',
      userPayload: plan ? { ship_allocation: r.ship_allocation } : {},
      llmParams: llmParams('financial_auditor', 400),
      output: plan ? { cost_breakdown_usd: r.cost_breakdown_usd, cost_per_port: r.cost_per_port, carbon: r.carbon_details, single_port_options: r.single_port_options, explanation: r.agent_assessments?.financial } : {}
    },
    {
      id: 'final_decision',
      name: 'Final Decision Node',
      index: '06',
      type: 'Result',
      agentName: 'agents/langgraph_orchestrator.py',
      icon: ShieldCheck,
      summary: r ? `${r.decision} (${r.status})` : 'No run yet',
      systemPrompt: 'Combines the agent outputs. The decision itself is a severity rule (REROUTE if critical or high), recorded as an assumption.',
      userPayload: {},
      llmParams: { framework: 'LangGraph StateGraph', response_time_s: r?.total_response_time_seconds ?? NA },
      output: r || {}
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
      sub="Six stages, one directed state graph. Click a node to see what it does and its real inputs and outputs from the last run. The step animation while running is cosmetic; real per-agent times are shown after the run."
      right={
        <div className="flex items-center gap-4">
          <div className="hidden sm:flex items-center gap-2 text-xs text-neutral-400">
            <span className="mono text-neutral-300 font-semibold">{isPipelineRunning ? 'Executing…' : 'Graph Ready'}</span>
            <span className="text-neutral-700">·</span>
            <span className="mono text-neutral-400">{pipelineResult ? `${pipelineResult.total_response_time_seconds}s` : NA}</span>
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
      <RunStatusBanner />
      {/* ── 1. Decision banner (from the last real run) ────────────────── */}
      <section className="mb-12">
        <CredCard elevated hover={false} className="p-8 sm:p-10">
          <div className="flex flex-wrap items-center justify-between gap-6">
            <div className="flex items-center gap-6">
              <div className="text-xl sm:text-2xl font-black tracking-tight text-rose-500">
                {r?.decision ?? 'NO RUN YET'}
              </div>
              <div className="border-l border-[rgba(225,29,72,0.3)] pl-6">
                <div className="text-base sm:text-lg font-bold text-white tracking-tight">
                  {plan ? `${r.disrupted_port} ➔ ${r.recommended_alternate_port}` : (selectedEvent?.nearest_port_name ?? NA)}
                </div>
                <div className="mono text-xs text-neutral-400 mt-1 flex items-center gap-3">
                  <span>{plan ? `${r.additional_transit_days} d travel time` : NA}</span>
                  <span>·</span>
                  <span>{plan ? `${fmtUsd(r.rerouting_cost_usd)} rerouting` : NA}</span>
                  <span>·</span>
                  <span>{plan ? `${r.distance_nm} nm` : NA}</span>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-6">
              {r?.severity && <SeverityBadge severity={r.severity} />}
              <div className="text-xs text-neutral-400">
                Signal gate <b className="mono text-emerald-400 font-bold text-sm ml-1">{r?.signal_gate ? `${r.signal_gate.action} ${r.signal_gate.score ?? ''}` : NA}</b>
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
            // While running, the step highlight is cosmetic. DONE only after a real run that ran this node.
            const executing = isPipelineRunning && runStep === idx;
            const ranKey = node.id === 'final_decision' ? 'supervisor_final' : node.id;
            const done = !isPipelineRunning && !!r &&
              (node.id === 'telemetry' || (r.agents_activated || []).includes(ranKey));
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
                    {executing ? 'RUNNING' : done ? 'DONE' : 'NOT RUN'}
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
                  <span>What this stage does (description, not the prompt)</span>
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
