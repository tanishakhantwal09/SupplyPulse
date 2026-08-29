import React, { useState } from 'react';
import { Activity, Filter, CheckCircle2, AlertTriangle, ShieldCheck, Terminal } from 'lucide-react';

export default function EventStream({ selectedEvent, pipelineResult }) {
  const [filter, setFilter] = useState('ALL');

  const events = [
    { time: '16:42:01.034', category: 'SYSTEM', agent: 'TELEMETRY', msg: `Disruption telemetry event received for ${selectedEvent?.nearest_port_name || 'Port of Shanghai'}` },
    { time: '16:42:01.201', category: 'AGENTS', agent: 'SUPERVISOR', msg: 'Supervisor Agent invoked — situation assessment in progress' },
    { time: '16:42:01.874', category: 'AGENTS', agent: 'ROUTER', msg: `Route Optimization Agent calculated alternate port ${pipelineResult?.recommended_alternate_port || 'pending'} (+${pipelineResult?.additional_transit_days ?? '—'} days)` },
    { time: '16:42:02.104', category: 'STATE', agent: 'INVENTORY', msg: `State updated — priority commodity exposure $${(pipelineResult?.inventory_exposure_usd || 0).toLocaleString()} USD` },
    { time: '16:42:02.441', category: 'AGENTS', agent: 'AUDITOR', msg: `Financial audit completed — total impact $${(pipelineResult?.total_financial_impact_usd || 0).toLocaleString()} USD (Alert: ${pipelineResult?.financial_alert ? 'TRIGGERED' : 'CLEAR'})` },
    { time: '16:42:03.021', category: 'DECISION', agent: 'SUPERVISOR', msg: `Unified Decision Node issued ${pipelineResult?.decision || 'PENDING'} command in ${pipelineResult?.total_response_time_seconds ?? '—'}s (Confidence: ${pipelineResult?.confidence || '—'})` }
  ];

  const filteredEvents = events.filter(e => {
    if (filter === 'ALL') return true;
    if (filter === 'AGENTS') return e.category === 'AGENTS';
    if (filter === 'STATE') return e.category === 'STATE';
    if (filter === 'ERRORS') return e.category === 'ERRORS';
    return true;
  });

  return (
    <div className="panel-dark p-6 font-mono space-y-4">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3 border-b border-white/5">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-cyan-400" />
          <h3 className="text-sm font-bold text-white uppercase">LIVE OBSERVABILITY EVENT STREAM</h3>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-1.5 text-xs bg-[#080B10] p-1 rounded border border-white/5">
          {['ALL', 'AGENTS', 'STATE', 'ERRORS'].map((cat) => (
            <button
              key={cat}
              onClick={() => setFilter(cat)}
              className={`px-2.5 py-1 rounded transition-all ${
                filter === cat
                  ? 'bg-cyan-500 text-slate-950 font-bold'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      <div className="space-y-2 text-xs">
        {filteredEvents.map((evt, idx) => (
          <div key={idx} className="p-3 rounded bg-[#080B10] border border-white/5 flex items-center justify-between gap-3 hover:border-white/10 transition-all">
            <div className="flex items-center gap-3">
              <span className="text-slate-500 text-[11px] font-mono shrink-0">{evt.time}</span>
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded font-mono ${
                evt.category === 'AGENTS' ? 'badge-cyan' :
                evt.category === 'STATE' ? 'badge-purple' :
                evt.category === 'DECISION' ? 'badge-emerald' : 'badge-amber'
              }`}>
                {evt.agent}
              </span>
              <span className="text-slate-200 font-mono">{evt.msg}</span>
            </div>
            <span className="text-emerald-400 text-[10px] shrink-0 font-bold">● LOGGED</span>
          </div>
        ))}
      </div>
    </div>
  );
}
