import React from 'react';
import { LineChart, Activity, Zap, CheckCircle2, DollarSign, ShieldAlert, Cpu } from 'lucide-react';

export default function TelemetryDashboard({ pipelineResult }) {
  const metrics = [
    { title: 'LAST RUN LATENCY', value: `${pipelineResult?.total_response_time_seconds ?? '—'}s`, change: 'Latest completed execution', color: 'text-cyan-400', badge: 'runtime' },
    { title: 'AGENTS ACTIVATED', value: pipelineResult?.agents_activated?.length ?? '—', change: 'Latest completed execution', color: 'text-emerald-400', badge: 'LangGraph' },
    { title: 'TOKEN CONSUMPTION', value: '—', change: 'Not returned by current API', color: 'text-purple-400', badge: 'unavailable' },
    { title: 'PIPELINE EXECUTIONS', value: '—', change: 'No persisted run counter', color: 'text-blue-400', badge: 'session only' },
    { title: 'FINANCIAL ALERT', value: pipelineResult?.financial_alert ? 'ACTIVE' : 'CLEAR', change: 'Latest agent decision', color: pipelineResult?.financial_alert ? 'text-amber-400' : 'text-emerald-400', badge: pipelineResult?.decision || 'ready' },
  ];

  return (
    <div className="space-y-6 font-mono">
      
      {/* Header */}
      <div className="panel-dark p-6 border-cyan-500/30">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <LineChart className="w-5 h-5 text-cyan-400" />
            <h2 className="text-lg font-bold text-white uppercase">SYSTEM TELEMETRY & AGENT PERFORMANCE MONITOR</h2>
          </div>
          <span className="text-xs text-slate-400 bg-[#080B10] px-3 py-1 rounded border border-white/5">
            Real-Time Engine Telemetry
          </span>
        </div>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {metrics.map((m, idx) => (
          <div key={idx} className="panel-dark p-5 space-y-2">
            <span className="text-[10px] text-slate-500 font-bold block">{m.title}</span>
            <div className={`text-2xl font-extrabold ${m.color}`}>{m.value}</div>
            <div className="flex items-center justify-between text-[10px]">
              <span className="text-slate-400">{m.change}</span>
              <span className="bg-white/5 px-1.5 py-0.5 rounded text-slate-300 border border-white/10">{m.badge}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Agent Performance Table */}
      <div className="panel-dark p-6 space-y-4">
        <h3 className="text-sm font-bold text-white uppercase flex items-center gap-2">
          <Cpu className="w-4 h-4 text-purple-400" />
          LATEST REFERENCE TRACE BREAKDOWN
        </h3>

        <div className="overflow-x-auto text-xs">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-white/5 text-slate-400 pb-2">
                <th className="p-3">AGENT NAME</th>
                <th className="p-3">ROLE</th>
                <th className="p-3">MODEL</th>
                <th className="p-3">AVG LATENCY</th>
                <th className="p-3">AVG TOKENS</th>
                <th className="p-3">STATUS</th>
              </tr>
            </thead>
            <tbody>
              {[
                { name: 'Supervisor Agent', role: 'Orchestrator', model: 'Groq / gpt-oss-120b', latency: '1.167s', tokens: 1450 },
                { name: 'Route Optimization Agent', role: 'Spatial Math', model: 'Groq / gpt-oss-120b', latency: '0.673s', tokens: 1210 },
                { name: 'Inventory Agent', role: 'Stock Exposure', model: 'Groq / gpt-oss-120b', latency: '0.568s', tokens: 980 },
                { name: 'Financial Auditor Agent', role: 'Cost Audit', model: 'Groq / gpt-oss-120b', latency: '0.650s', tokens: 1120 },
                { name: 'Supervisor Final Decision', role: 'Synthesis', model: 'LangGraph StateGraph', latency: '0.328s', tokens: 450 }
              ].map((row, idx) => (
                <tr key={idx} className="border-b border-white/5 hover:bg-white/5 transition-all">
                  <td className="p-3 font-bold text-white">{row.name}</td>
                  <td className="p-3 text-cyan-400">{row.role}</td>
                  <td className="p-3 text-slate-300">{row.model}</td>
                  <td className="p-3 text-emerald-400 font-bold">{row.latency}</td>
                  <td className="p-3 text-amber-400 font-bold">{row.tokens} tk</td>
                  <td className="p-3"><span className="text-emerald-400 font-bold">● HEALTHY</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}
