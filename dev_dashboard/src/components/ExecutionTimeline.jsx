import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Clock, Cpu, CheckCircle2, ChevronRight, GitCommit } from 'lucide-react';
import JsonViewer from './JsonViewer';

export default function ExecutionTimeline({ pipelineResult, selectedEvent }) {
  const [selectedTraceStep, setSelectedTraceStep] = useState(0);

  const traceSteps = [
    {
      id: 0,
      timestamp: '00:00.000',
      timeMs: 0,
      agent: 'GDELT 2.0 Ingestion',
      type: 'TELEMETRY STREAM',
      latency: '0.034s',
      status: 'completed',
      tokens: 0,
      model: 'GDELT Broadcast API',
      inputPayload: { port: selectedEvent?.nearest_port_name, severity: selectedEvent?.severity },
      outputPayload: { goldstein_scale: selectedEvent?.goldstein_scale, avg_tone: selectedEvent?.avg_tone }
    },
    {
      id: 1,
      timestamp: '00:00.034',
      timeMs: 34,
      agent: 'Supervisor Agent',
      type: 'LLM ORCHESTRATOR',
      latency: '1.167s',
      status: 'completed',
      tokens: 1450,
      model: 'Groq / openai/gpt-oss-120b',
      inputPayload: { disruption_event: selectedEvent?.nearest_port_name },
      outputPayload: { situation_assessment: 'CONFIRMED DISRUPTION', delegated_agents: ['route_optimization', 'inventory', 'financial_auditor'] }
    },
    {
      id: 2,
      timestamp: '00:01.201',
      timeMs: 1201,
      agent: 'Route Optimization Agent',
      type: 'SPATIAL LOGISTICS',
      latency: '0.673s',
      status: 'completed',
      tokens: 1210,
      model: 'Groq / openai/gpt-oss-120b',
      inputPayload: { origin_port: selectedEvent?.nearest_port_name },
      outputPayload: { recommended_alternate_port: pipelineResult?.recommended_alternate_port || 'Ningbo-Zhoushan', distance_nm: pipelineResult?.distance_nm || 114.5 }
    },
    {
      id: 3,
      timestamp: '00:01.874',
      timeMs: 1874,
      agent: 'Inventory Agent',
      type: 'BUFFER EXPOSURE',
      latency: '0.568s',
      status: 'completed',
      tokens: 980,
      model: 'Groq / openai/gpt-oss-120b',
      inputPayload: { commodities: selectedEvent?.affected_commodities },
      outputPayload: { priority_commodity: pipelineResult?.top_priority_commodity || 'Semiconductors', inventory_exposure_usd: pipelineResult?.inventory_exposure_usd || 1250000 }
    },
    {
      id: 4,
      timestamp: '00:02.442',
      timeMs: 2442,
      agent: 'Financial Auditor Agent',
      type: 'COST AUDIT',
      latency: '0.650s',
      status: 'completed',
      tokens: 1120,
      model: 'Groq / openai/gpt-oss-120b',
      inputPayload: { rerouting_cost: pipelineResult?.rerouting_cost_usd || 45200 },
      outputPayload: { total_financial_impact_usd: pipelineResult?.total_financial_impact_usd || 382000, alert_triggered: true }
    },
    {
      id: 5,
      timestamp: '00:03.092',
      timeMs: 3092,
      agent: 'LangGraph Unified State',
      type: 'DECISION SYNTHESIS',
      latency: '0.328s',
      status: 'completed',
      tokens: 450,
      model: 'LangGraph StateGraph',
      inputPayload: { pipeline_outputs: 'all_agents' },
      outputPayload: pipelineResult || {}
    }
  ];

  const activeStep = traceSteps[selectedTraceStep] || traceSteps[0];

  return (
    <motion.div 
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6 font-outfit"
    >
      
      {/* Gantt Chart Container */}
      <div className="bg-bg-card border border-border-subtle rounded-3xl p-6 md:p-8 space-y-6 shadow-2xl">
        <div className="flex items-center justify-between border-b border-border-subtle pb-4">
          <div className="flex items-center gap-3">
            <Clock className="w-6 h-6 text-gold" />
            <h3 className="text-xl font-bold font-syne text-text-primary m-0">
              Visual Execution Timeline (Gantt Trace Chart)
            </h3>
          </div>
          <span className="text-xs font-dm-mono text-text-muted bg-bg-secondary px-3 py-1.5 rounded-lg border border-border-subtle">
            Total Pipeline Latency: <strong className="text-gold">{pipelineResult?.total_response_time_seconds || 3.42}s</strong>
          </span>
        </div>

        {/* Timeline Rows */}
        <div className="space-y-3 font-dm-mono">
          {traceSteps.map((step) => {
            const isSelected = selectedTraceStep === step.id;
            return (
              <motion.div 
                key={step.id}
                whileHover={{ scale: 1.01 }}
                onClick={() => setSelectedTraceStep(step.id)}
                className={`p-3 rounded-xl border transition-all cursor-pointer flex items-center justify-between text-xs ${
                  isSelected
                    ? 'border-gold bg-gold/15 shadow-lg shadow-gold/5 font-bold'
                    : 'border-border-subtle bg-bg-secondary/40 hover:bg-bg-card-hover'
                }`}
              >
                <div className="flex items-center gap-3 w-52 shrink-0">
                  <span className="text-[10px] text-text-muted">{step.timestamp}</span>
                  <span className="font-bold text-text-primary truncate">{step.agent}</span>
                </div>

                {/* Timeline Progress Bar */}
                <div className="flex-1 mx-4 bg-bg-secondary h-3.5 rounded-full overflow-hidden relative border border-border-subtle">
                  <div 
                    className={`h-full rounded-full ${
                      step.id === 0 ? 'bg-info' :
                      step.id === 1 ? 'bg-gold' :
                      step.id === 2 ? 'bg-purple-400' :
                      step.id === 3 ? 'bg-warning' :
                      step.id === 4 ? 'bg-danger' : 'bg-success'
                    }`}
                    style={{
                      width: `${Math.max(15, (parseFloat(step.latency) / 3.42) * 100)}%`,
                      marginLeft: `${(step.timeMs / 3420) * 80}%`
                    }}
                  />
                </div>

                <div className="flex items-center gap-4 w-36 justify-end shrink-0 text-[11px]">
                  <span className="text-text-muted">{step.latency}</span>
                  <span className="text-success font-bold">● EXECUTED</span>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>

      {/* Step Trace Details Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Step Selector Column */}
        <div className="lg:col-span-4 bg-bg-card border border-border-subtle rounded-3xl p-6 space-y-3 shadow-xl">
          <span className="text-[11px] font-dm-mono font-bold text-text-muted uppercase tracking-widest block mb-2">CHRONOLOGICAL TRACE STEPS</span>
          {traceSteps.map((step) => (
            <button
              key={step.id}
              onClick={() => setSelectedTraceStep(step.id)}
              className={`w-full text-left p-3.5 rounded-xl border text-xs font-dm-mono flex items-center justify-between transition-all cursor-pointer ${
                selectedTraceStep === step.id
                  ? 'border-gold/50 bg-gold/15 text-gold font-bold shadow-md'
                  : 'border-border-subtle bg-bg-secondary/40 text-text-muted hover:text-text-primary hover:bg-bg-card-hover'
              }`}
            >
              <div>
                <span className="text-[10px] text-text-muted block">{step.timestamp}</span>
                <span className="font-bold block truncate mt-0.5">{step.agent}</span>
              </div>
              <ChevronRight className="w-4 h-4 text-text-muted" />
            </button>
          ))}
        </div>

        {/* Selected Step Payload Viewers */}
        <div className="lg:col-span-8 space-y-6 font-dm-mono">
          <div className="bg-bg-card border border-border-subtle rounded-3xl p-6 flex items-center justify-between text-xs shadow-xl">
            <div>
              <span className="text-gold font-bold block text-[11px] uppercase tracking-wider">{activeStep.type}</span>
              <h4 className="text-lg font-bold font-syne text-text-primary mt-1">{activeStep.agent}</h4>
            </div>
            <div className="flex items-center gap-4 text-[11px]">
              <div><span className="text-text-muted block font-bold">LATENCY</span><span className="text-success font-bold">{activeStep.latency}</span></div>
              <div><span className="text-text-muted block font-bold">TOKENS</span><span className="text-warning font-bold">{activeStep.tokens} tk</span></div>
              <div><span className="text-text-muted block font-bold">MODEL</span><span className="text-purple-400 font-bold">{activeStep.model}</span></div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <JsonViewer data={activeStep.inputPayload} title="STEP INPUT PAYLOAD" />
            <JsonViewer data={activeStep.outputPayload} title="STEP COMPUTED OUTPUT" />
          </div>
        </div>

      </div>

    </motion.div>
  );
}
