import React, { useState } from 'react';
import { Code2, ArrowUpRight, CheckCircle2, FileCode2, Layers } from 'lucide-react';

export default function StateInspector({ pipelineResult, selectedEvent }) {
  const [activeSection, setActiveSection] = useState('all');

  const stateSchema = {
    input_event: {
      nearest_port_name: selectedEvent?.nearest_port_name || 'Port of Shanghai',
      severity: selectedEvent?.severity || 'critical',
      goldstein_scale: selectedEvent?.goldstein_scale || -8.5,
      avg_tone: selectedEvent?.avg_tone || -6.2,
      affected_routes: selectedEvent?.affected_routes || '["R01", "R05"]',
      affected_commodities: selectedEvent?.affected_commodities || '["Semiconductors"]',
      mutated: false
    },
    routing_state: {
      recommended_alternate_port: pipelineResult?.recommended_alternate_port || 'Ningbo-Zhoushan',
      alternate_port_country: pipelineResult?.alternate_port_country || 'China',
      distance_nm: pipelineResult?.distance_nm || 114.5,
      additional_transit_days: pipelineResult?.additional_transit_days || 2.1,
      rerouting_cost_usd: pipelineResult?.rerouting_cost_usd || 45200,
      mutated: true
    },
    inventory_state: {
      top_priority_commodity: pipelineResult?.top_priority_commodity || 'Semiconductors & Component Parts',
      inventory_exposure_usd: pipelineResult?.inventory_exposure_usd || 1250000,
      safety_buffer_days: 4.5,
      stockout_risk: 'CRITICAL',
      mutated: true
    },
    financial_state: {
      total_financial_impact_usd: pipelineResult?.total_financial_impact_usd || 382000,
      financial_alert: pipelineResult?.financial_alert ?? true,
      demurrage_usd: 85000,
      fuel_surcharges_usd: 24500,
      mutated: true
    },
    decision_state: {
      decision: pipelineResult?.decision || 'REROUTE',
      confidence: pipelineResult?.confidence || '91%',
      agents_activated: pipelineResult?.agents_activated || ['supervisor', 'route_optimization', 'inventory', 'financial_auditor', 'supervisor_final'],
      total_response_time_seconds: pipelineResult?.total_response_time_seconds || 3.42,
      mutated: true
    }
  };

  return (
    <div className="space-y-6 font-mono">
      
      {/* Header */}
      <div className="panel-dark p-6 border-cyan-500/30">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Code2 className="w-5 h-5 text-cyan-400" />
              <h2 className="text-lg font-bold text-white uppercase">LANGGRAPH APPLICATION STATE INSPECTOR</h2>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Inspect live DAG state graph dictionary mutations and execution context parameters.
            </p>
          </div>

          <div className="flex items-center gap-2 bg-[#080B10] p-1.5 rounded-lg border border-white/5 text-xs">
            {['all', 'input_event', 'routing_state', 'inventory_state', 'financial_state', 'decision_state'].map((sec) => (
              <button
                key={sec}
                onClick={() => setActiveSection(sec)}
                className={`px-3 py-1 rounded capitalize transition-all ${
                  activeSection === sec
                    ? 'bg-cyan-500 text-slate-950 font-bold'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {sec.replace('_state', '').replace('_', ' ')}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* State Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {Object.entries(stateSchema).map(([key, val]) => {
          if (activeSection !== 'all' && activeSection !== key) return null;
          const isMutated = val.mutated;
          const fields = { ...val };
          delete fields.mutated;

          return (
            <div key={key} className="panel-dark p-5 space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-white/5">
                <span className="text-xs font-bold text-cyan-400 uppercase tracking-wider">
                  {key.replace('_', ' ')}
                </span>
                {isMutated && (
                  <span className="text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded font-bold flex items-center gap-1">
                    <ArrowUpRight className="w-3 h-3" />
                    MUTATED BY AGENT
                  </span>
                )}
              </div>

              <div className="space-y-2 text-xs">
                {Object.entries(fields).map(([fKey, fVal]) => (
                  <div key={fKey} className="bg-[#080B10] p-2.5 rounded border border-white/5 flex items-center justify-between">
                    <span className="text-slate-400 font-mono">{fKey}:</span>
                    <span className="text-white font-bold font-mono">
                      {typeof fVal === 'object' ? JSON.stringify(fVal) : String(fVal)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

    </div>
  );
}
