import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  CheckCircle2, AlertTriangle, ShieldCheck, MapPin, 
  DollarSign, Package, Compass, Cpu, FileCode2, ChevronRight, Sparkles, Activity, ArrowRight 
} from 'lucide-react';
import JsonViewer from './JsonViewer';

const PIPELINE_NODE_IDS = ['telemetry', 'supervisor', 'route_optimization', 'inventory', 'financial_auditor', 'final_decision'];

export default function PipelineVisualizer({ pipelineResult, selectedEvent, isRunning }) {
  const [activeNode, setActiveNode] = useState('supervisor');
  const [runStep, setRunStep] = useState(5);

  const nodes = [
    {
      id: 'telemetry',
      name: '0. GDELT Telemetry',
      type: 'Input Stream',
      agentName: 'fetch_gdelt.py / enrich_gdelt.py',
      icon: MapPin,
      color: 'border-info text-info bg-info/10',
      summary: `${selectedEvent?.nearest_port_name || 'Port of Shanghai'} (${selectedEvent?.severity || 'critical'})`,
      systemPrompt: 'Ingests GDELT news event telemetry, computes Goldstein Instability index, average tone, and maps coordinates to nearest seaport using Haversine NM distance.',
      userPayload: selectedEvent || {},
      llmParams: { provider: 'GDELT 2.0 Broadcast Stream', polling: '15 mins', distance_formula: 'Haversine NM' },
      output: {
        nearest_port_name: selectedEvent?.nearest_port_name || 'Port of Shanghai',
        severity: selectedEvent?.severity || 'critical',
        goldstein_scale: selectedEvent?.goldstein_scale || -8.5,
        avg_tone: selectedEvent?.avg_tone || -6.2,
        affected_routes: selectedEvent?.affected_routes || '["R01", "R05"]',
        freight_impact_pct: selectedEvent?.freight_impact_pct || 48.5,
      }
    },
    {
      id: 'supervisor',
      name: '1. Supervisor Agent',
      type: 'LLM Orchestrator',
      agentName: 'agents/supervisor_agent.py',
      icon: Cpu,
      color: 'border-gold text-gold bg-gold/10',
      summary: 'Performs initial situation assessment & delegates tasks to downstream agents',
      systemPrompt: `You are the Supervisor Agent of SupplyPulse.
You coordinate EXACTLY these 4 agents:
1. Route Optimization Agent
2. Inventory Agent
3. Financial Auditor Agent
4. Supervisor Agent (yourself)

Provide:
1. SITUATION ASSESSMENT
2. IMMEDIATE ACTIONS
3. AGENT DELEGATION
4. REROUTING RECOMMENDATION
5. RISK LEVEL`,
      userPayload: {
        nearest_port: selectedEvent?.nearest_port_name,
        severity: selectedEvent?.severity,
        affected_routes: selectedEvent?.affected_routes,
        at_risk_commodities: selectedEvent?.affected_commodities
      },
      llmParams: { provider: 'Groq Cloud', model: 'openai/gpt-oss-120b', temperature: 0.1, max_tokens: 1500 },
      output: {
        assessment: `DISRUPTION CONFIRMED: High severity event at ${selectedEvent?.nearest_port_name || 'Port of Shanghai'}. Operational bottleneck detected across major shipping lanes.`,
        delegation: ['Route Optimization Agent', 'Inventory Agent', 'Financial Auditor Agent'],
        preliminary_action: 'Prepare immediate vessel rerouting protocols and calculate alternate draft-compatible ports.'
      }
    },
    {
      id: 'route_optimization',
      name: '2. Route Optimization',
      type: 'Spatial Logistics',
      agentName: 'agents/route_optimization_agent.py',
      icon: Compass,
      color: 'border-purple-400 text-purple-400 bg-purple-500/10',
      summary: `Recommends alternate port: ${pipelineResult?.recommended_alternate_port || 'Ningbo-Zhoushan'} (+${pipelineResult?.additional_transit_days || 2.1} days)`,
      systemPrompt: `You are the Route Optimization Agent.
Calculate alternate port options based on nautical distance (NM), vessel draft compatibility, port capacity, transit delay days, and rerouting costs (USD).`,
      userPayload: {
        disrupted_port: selectedEvent?.nearest_port_name,
        vessel_draft_m: 14.5,
        available_alternate_ports: ['Ningbo-Zhoushan', 'Qingdao', 'Busan']
      },
      llmParams: { provider: 'Groq Cloud', model: 'openai/gpt-oss-120b', temperature: 0.1 },
      output: {
        recommended_port: pipelineResult?.recommended_alternate_port || 'Ningbo-Zhoushan',
        country: pipelineResult?.alternate_port_country || 'China',
        distance_nm: pipelineResult?.distance_nm || 114.5,
        estimated_delay_days: pipelineResult?.additional_transit_days || 2.1,
        estimated_cost_usd: pipelineResult?.rerouting_cost_usd || 45200
      }
    },
    {
      id: 'inventory',
      name: '3. Inventory Agent',
      type: 'Buffer Exposure',
      agentName: 'agents/inventory_agent.py',
      icon: Package,
      color: 'border-warning text-warning bg-warning/10',
      summary: `Priority Commodity: ${pipelineResult?.top_priority_commodity || 'Semiconductors'} ($${(pipelineResult?.inventory_exposure_usd || 1250000).toLocaleString()} USD)`,
      systemPrompt: `You are the Inventory Agent.
Assess commodity inventory exposures, safety stock depletion rates, critical component lead-time impacts, and stockout timelines.`,
      userPayload: {
        affected_commodities: selectedEvent?.affected_commodities,
        estimated_delay_days: pipelineResult?.additional_transit_days || 2.1
      },
      llmParams: { provider: 'Groq Cloud', model: 'openai/gpt-oss-120b', temperature: 0.1 },
      output: {
        top_priority_commodity: pipelineResult?.top_priority_commodity || 'Semiconductors',
        inventory_exposure_usd: pipelineResult?.inventory_exposure_usd || 1250000,
        buffer_days_remaining: 4.5,
        stockout_risk: 'HIGH'
      }
    },
    {
      id: 'financial_auditor',
      name: '4. Financial Auditor',
      type: 'Cost Audit',
      agentName: 'agents/financial_auditor_agent.py',
      icon: DollarSign,
      color: 'border-danger text-danger bg-danger/10',
      summary: `Total Impact: $${(pipelineResult?.total_financial_impact_usd || 382000).toLocaleString()} USD (Alert: ${pipelineResult?.financial_alert ? 'TRIGGERED' : 'CLEAR'})`,
      systemPrompt: `You are the Financial Auditor Agent.
Audit complete financial exposure: demurrage charges, fuel surcharges, alternative port handling fees, lost customer revenue, and total USD impact. Trigger alert if > $100,000 USD.`,
      userPayload: {
        rerouting_cost_usd: pipelineResult?.rerouting_cost_usd || 45200,
        inventory_exposure_usd: pipelineResult?.inventory_exposure_usd || 1250000,
        delay_days: pipelineResult?.additional_transit_days || 2.1
      },
      llmParams: { provider: 'Groq Cloud', model: 'openai/gpt-oss-120b', temperature: 0.1 },
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
      name: '5. Final Decision Node',
      type: 'Decision Synthesis',
      agentName: 'agents/langgraph_orchestrator.py',
      icon: ShieldCheck,
      color: 'border-success text-success bg-success/10',
      summary: `UNIFIED DECISION: ${pipelineResult?.decision || 'REROUTE'} (Confidence: ${pipelineResult?.confidence || '91%'})`,
      systemPrompt: 'Synthesizes all 4 specialized agent outputs into a unified, actionable supply chain response plan.',
      userPayload: pipelineResult || {},
      llmParams: { framework: 'LangGraph StateGraph', execution_time_sec: pipelineResult?.total_response_time_seconds || 3.42 },
      output: pipelineResult || {}
    }
  ];

  const currentNode = nodes.find(n => n.id === activeNode) || nodes[1];

  useEffect(() => {
    if (!isRunning) return undefined;
    const startTimer = window.setTimeout(() => {
      setRunStep(0);
      setActiveNode(PIPELINE_NODE_IDS[0]);
    }, 0);
    const timer = window.setInterval(() => {
      setRunStep(step => {
        const next = Math.min(step + 1, PIPELINE_NODE_IDS.length - 1);
        setActiveNode(PIPELINE_NODE_IDS[next]);
        return next;
      });
    }, 540);
    return () => {
      window.clearTimeout(startTimer);
      window.clearInterval(timer);
    };
  }, [isRunning]);

  return (
    <motion.div 
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6 font-outfit"
    >
      
      {/* Top Status Overview Panel */}
      <div className="bg-bg-card border border-border-subtle rounded-2xl p-5 shadow-xl grid grid-cols-2 md:grid-cols-6 gap-4 font-dm-mono text-xs">
        <div>
          <span className="text-text-muted text-[10px] block font-bold uppercase tracking-wider">PIPELINE STATUS</span>
          <span className="text-success font-bold flex items-center gap-1.5 mt-0.5">
            <span className={`w-2 h-2 rounded-full ${isRunning ? 'bg-gold animate-ping' : 'bg-success'}`}></span>
            {isRunning ? 'EXECUTING' : 'READY / COMPLETED'}
          </span>
        </div>
        <div>
          <span className="text-text-muted text-[10px] block font-bold uppercase tracking-wider">CURRENT AGENT</span>
          <span className="text-gold font-bold mt-0.5 block">{currentNode.name.split('. ')[1]}</span>
        </div>
        <div>
          <span className="text-text-muted text-[10px] block font-bold uppercase tracking-wider">ELAPSED LATENCY</span>
          <span className="text-text-primary font-bold mt-0.5 block">{pipelineResult?.total_response_time_seconds || 3.42}s</span>
        </div>
        <div>
          <span className="text-text-muted text-[10px] block font-bold uppercase tracking-wider">AGENTS COMPLETED</span>
          <span className="text-purple-400 font-bold mt-0.5 block">{isRunning ? `${runStep} / 5 Nodes` : '5 / 5 Nodes'}</span>
        </div>
        <div>
          <span className="text-text-muted text-[10px] block font-bold uppercase tracking-wider">SYSTEM CONFIDENCE</span>
          <span className="text-success font-bold mt-0.5 block">{pipelineResult?.confidence || '91%'}</span>
        </div>
        <div>
          <span className="text-text-muted text-[10px] block font-bold uppercase tracking-wider">DECISION ACTION</span>
          <span className={`font-extrabold px-2 py-0.5 rounded text-[11px] inline-block mt-0.5 ${pipelineResult?.decision === 'REROUTE' ? 'badge-reroute' : 'badge-monitor'}`}>
            {pipelineResult?.decision || 'REROUTE'}
          </span>
        </div>
      </div>

      {/* Visual Connected DAG Workflow Graph */}
      <div className="bg-bg-card border border-border-subtle rounded-3xl p-6 md:p-8 space-y-6 shadow-2xl">
        <div className="flex items-center justify-between border-b border-border-subtle pb-4">
          <div className="flex items-center gap-3">
            <Activity className="w-6 h-6 text-gold" />
            <h2 className="text-xl font-bold font-syne text-text-primary m-0">
              Interactive Multi-Agent Graph (LangGraph DAG)
            </h2>
          </div>
          <span className="text-xs font-dm-mono text-text-muted bg-bg-secondary px-3 py-1 rounded-lg border border-border-subtle">
            Click any node to inspect agent specs
          </span>
        </div>

        {/* Nodes Grid with Framer Motion Spring Animations */}
        <div className="workflow-grid grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {nodes.map((node, idx) => {
            const Icon = node.icon;
            const isSelected = activeNode === node.id;
            const isComplete = !isRunning || idx < runStep;
            const isExecuting = isRunning && idx === runStep;

            return (
              <motion.div
                key={node.id}
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => setActiveNode(node.id)}
                className={`workflow-node p-4 rounded-2xl border text-left transition-all cursor-pointer relative ${isComplete ? 'is-complete' : ''} ${isExecuting ? 'is-executing' : ''} ${
                  isSelected
                    ? 'border-gold bg-gold/15 shadow-xl shadow-gold/10 active-node-glow ring-1 ring-gold'
                    : 'border-border-subtle bg-bg-secondary/40 hover:bg-bg-card-hover hover:border-border-accent'
                }`}
              >
                <div className="flex items-center justify-between mb-3">
                  <div className={`p-2 rounded-xl border ${node.color}`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <span className="node-status"><i />{isExecuting ? 'RUN' : isComplete ? 'DONE' : `0${idx}`}</span>
                </div>
                <div className="text-xs font-bold text-text-primary font-outfit truncate">{node.name.split('. ')[1]}</div>
                <div className="text-[11px] text-text-muted font-dm-mono mt-1 truncate">{node.type}</div>
              </motion.div>
            );
          })}
        </div>
      </div>

      {/* Selected Node Inspector Drawer */}
      <AnimatePresence mode="wait">
        <motion.div
          key={currentNode.id}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.2 }}
          className="grid grid-cols-1 lg:grid-cols-12 gap-6"
        >
          {/* Node Spec & System Prompt */}
          <div className="lg:col-span-7 space-y-6">
            <div className="bg-bg-card border border-border-subtle rounded-3xl p-6 md:p-8 space-y-5 shadow-2xl">
              <div className="flex items-center justify-between pb-4 border-b border-border-subtle">
                <div>
                  <span className="text-xs font-dm-mono text-gold font-bold uppercase tracking-wider">{currentNode.type}</span>
                  <h3 className="text-xl font-bold font-syne text-text-primary mt-1">{currentNode.name}</h3>
                  <p className="text-xs font-dm-mono text-text-muted mt-1">{currentNode.agentName}</p>
                </div>
                <span className="px-3 py-1 rounded-lg bg-success-dim text-success border border-success/30 font-dm-mono text-xs font-bold">
                  ● ACTIVE / READY
                </span>
              </div>

              {/* Parameter Badges */}
              <div className="bg-bg-secondary p-4 rounded-xl border border-border-subtle font-dm-mono text-xs grid grid-cols-2 sm:grid-cols-4 gap-4">
                <div><span className="text-text-muted text-[10px] block font-bold">PROVIDER</span><span className="text-gold font-bold">{currentNode.llmParams.provider}</span></div>
                <div><span className="text-text-muted text-[10px] block font-bold">MODEL</span><span className="text-text-primary font-bold">{currentNode.llmParams.model || 'Deterministic'}</span></div>
                <div><span className="text-text-muted text-[10px] block font-bold">TEMPERATURE</span><span className="text-warning font-bold">{currentNode.llmParams.temperature ?? 'N/A'}</span></div>
                <div><span className="text-text-muted text-[10px] block font-bold">LATENCY</span><span className="text-success font-bold">{currentNode.llmParams.execution_time_sec ? `${currentNode.llmParams.execution_time_sec}s` : '< 1.2s'}</span></div>
              </div>

              {/* System Prompt View */}
              <div className="space-y-2">
                <span className="text-xs font-bold text-text-primary font-dm-mono flex items-center gap-2">
                  <FileCode2 className="w-4 h-4 text-gold" />
                  SYSTEM PROMPT & AGENT SCHEMATIC
                </span>
                <pre className="bg-bg-secondary p-4 rounded-xl border border-border-subtle font-dm-mono text-xs text-text-secondary whitespace-pre-wrap leading-relaxed max-h-60 overflow-y-auto">
                  {currentNode.systemPrompt}
                </pre>
              </div>
            </div>
          </div>

          {/* Right Column: Code & JSON Payload Inspectors */}
          <div className="lg:col-span-5 space-y-6">
            <JsonViewer data={currentNode.userPayload} title="NODE INPUT STATE PAYLOAD" />
            <JsonViewer data={currentNode.output} title="AGENT COMPUTED OUTPUT JSON" />
          </div>

        </motion.div>
      </AnimatePresence>

    </motion.div>
  );
}
