import React, { useState, useEffect, useRef } from 'react';
import { Terminal as TerminalIcon, Play, Trash2, Copy, Check } from 'lucide-react';

export default function TerminalLogs({ logs = [] }) {
  const [copied, setCopied] = useState(false);
  const terminalEndRef = useRef(null);

  const defaultLogs = [
    `[INFO  14:41:29] SupplyPulse Observability Engine Initialized.`,
    `[INFO  14:41:29] Connected to Python API Backend (http://localhost:5001).`,
    `[INFO  14:41:30] LLM Provider: Groq Cloud (Model: openai/gpt-oss-120b).`,
    `[INFO  14:41:31] Reference Databases Loaded: 40 Ports, 15 Routes, 25 Commodities.`,
    `[EVENT 14:41:32] Disruption Event Received: Shanghai Container Terminal Congestion (Severity: CRITICAL).`,
    `[AGENT 14:41:33] Step 1 — Supervisor Agent assessing situation...`,
    `[AGENT 14:41:34] Step 2 — Route Optimization Agent computing alternate draft-compatible ports...`,
    `[MATH  14:41:34] Haversine calculation: Port of Shanghai -> Ningbo-Zhoushan = 114.5 NM (+2.1 transit days).`,
    `[AGENT 14:41:35] Step 3 — Inventory Agent auditing component buffers... Priority: Semiconductors ($1,250,000 USD).`,
    `[AGENT 14:41:35] Step 4 — Financial Auditor Agent calculating demurrage penalties... Total: $382,000 USD (Alert: TRIGGERED).`,
    `[FINAL 14:41:36] Step 5 — LangGraph Unified Decision Node generated REROUTE action in 3.42s (Confidence: 91%).`
  ];

  const activeLogs = logs.length > 0 ? logs : defaultLogs;

  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activeLogs]);

  const handleCopy = () => {
    navigator.clipboard.writeText(activeLogs.join('\n'));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="glass-panel p-6 font-mono space-y-4">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <TerminalIcon className="w-5 h-5 text-cyan-400" />
          <h2 className="text-sm font-bold text-white">REAL-TIME AGENT EXECUTION TERMINAL LOGS</h2>
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className="px-3 py-1 bg-slate-900 hover:bg-slate-800 text-slate-300 rounded border border-slate-800 text-xs flex items-center gap-1"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            {copied ? 'COPIED' : 'COPY LOGS'}
          </button>
        </div>
      </div>

      <div className="bg-slate-950 p-4 rounded-xl border border-slate-900 text-xs leading-relaxed max-h-96 overflow-y-auto space-y-1.5">
        {activeLogs.map((log, idx) => {
          let colorClass = 'text-slate-300';
          if (log.includes('[INFO')) colorClass = 'text-cyan-400';
          if (log.includes('[EVENT')) colorClass = 'text-amber-400 font-bold';
          if (log.includes('[AGENT')) colorClass = 'text-purple-400';
          if (log.includes('[MATH')) colorClass = 'text-indigo-400';
          if (log.includes('[FINAL')) colorClass = 'text-emerald-400 font-bold';
          if (log.includes('[ERROR')) colorClass = 'text-rose-400 font-bold';

          return (
            <div key={idx} className={colorClass}>
              {log}
            </div>
          );
        })}
        <div ref={terminalEndRef} />
      </div>
    </div>
  );
}
