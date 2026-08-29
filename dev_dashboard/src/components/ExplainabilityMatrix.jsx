import React from 'react';
import { Compass, DollarSign, Package, ShieldCheck, AlertCircle, Calculator, Cpu, CheckCircle2 } from 'lucide-react';

export default function ExplainabilityMatrix({ pipelineResult, selectedEvent }) {
  const result = pipelineResult || {
    disrupted_port: selectedEvent?.nearest_port_name || 'Port of Shanghai',
    severity: (selectedEvent?.severity || 'critical').toUpperCase(),
    decision: 'REROUTE',
    recommended_alternate_port: 'Ningbo-Zhoushan',
    alternate_port_country: 'China',
    distance_nm: 114.5,
    additional_transit_days: 2.1,
    rerouting_cost_usd: 45200,
    total_financial_impact_usd: 382000,
    financial_alert: true,
    top_priority_commodity: 'Semiconductors & Electronics',
    inventory_exposure_usd: 1250000,
    confidence: '91%',
    total_response_time_seconds: 3.42
  };

  return (
    <div className="space-y-6">
      
      {/* Top Banner: Decision Overview */}
      <div className="glass-panel p-6 border-emerald-500/30">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-6 h-6 text-emerald-400" />
              <h2 className="text-xl font-bold text-white font-mono">EXPLAINABLE UNIFIED DECISION MATRIX</h2>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Deep mathematical & operational breakdown explaining why the multi-agent system arrived at this recommendation.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="bg-slate-900 px-4 py-2 rounded-xl border border-slate-800 font-mono text-xs">
              <span className="text-slate-500 block">SYSTEM CONFIDENCE</span>
              <span className="text-emerald-400 font-bold text-base">{result.confidence}</span>
            </div>
            <div className="bg-slate-900 px-4 py-2 rounded-xl border border-slate-800 font-mono text-xs">
              <span className="text-slate-500 block font-mono">FINAL DECISION</span>
              <span className={`font-extrabold text-base px-2 py-0.5 rounded badge-${result.decision === 'REROUTE' ? 'reroute' : 'monitor'}`}>
                {result.decision}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* 3 Explanatory Pillars */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Pillar 1: Spatial Rerouting Math */}
        <div className="glass-panel p-6 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <Compass className="w-5 h-5 text-indigo-400" />
              <h3 className="text-sm font-bold text-white font-mono">1. ROUTE OPTIMIZATION MATH</h3>
            </div>
            <span className="text-[10px] font-mono text-indigo-400 bg-indigo-950 px-2 py-0.5 rounded">HAVERSINE NM</span>
          </div>

          <div className="space-y-3 font-mono text-xs">
            <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
              <span className="text-slate-500 block">DISRUPTED PORT:</span>
              <span className="text-rose-400 font-bold">{result.disrupted_port}</span>
            </div>

            <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
              <span className="text-slate-500 block">RECOMMENDED ALTERNATE PORT:</span>
              <span className="text-emerald-400 font-bold">{result.recommended_alternate_port} ({result.alternate_port_country})</span>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                <span className="text-slate-500 block">DISTANCE:</span>
                <span className="text-white font-bold">{result.distance_nm} NM</span>
              </div>
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                <span className="text-slate-500 block">TRANSIT DELAY:</span>
                <span className="text-amber-400 font-bold">+{result.additional_transit_days} Days</span>
              </div>
            </div>

            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-[11px] text-slate-400 leading-relaxed">
              <strong className="text-slate-200 block mb-1">Formula & Logic:</strong>
              Uses <code>R = 3440.065 NM</code> Haversine spherical distance calculation between coordinates, validating vessel draft & port throughput capability.
            </div>
          </div>
        </div>

        {/* Pillar 2: Inventory & Stockout Exposure */}
        <div className="glass-panel p-6 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <Package className="w-5 h-5 text-purple-400" />
              <h3 className="text-sm font-bold text-white font-mono">2. INVENTORY RISK EXPOSURE</h3>
            </div>
            <span className="text-[10px] font-mono text-purple-400 bg-purple-950 px-2 py-0.5 rounded">BUFFER ANALYSIS</span>
          </div>

          <div className="space-y-3 font-mono text-xs">
            <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
              <span className="text-slate-500 block">TOP PRIORITY COMMODITY:</span>
              <span className="text-purple-400 font-bold">{result.top_priority_commodity}</span>
            </div>

            <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
              <span className="text-slate-500 block">TOTAL EXPOSURE VALUE:</span>
              <span className="text-rose-400 font-bold text-sm">${(result.inventory_exposure_usd || 0).toLocaleString()} USD</span>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                <span className="text-slate-500 block">SAFETY BUFFER:</span>
                <span className="text-amber-400 font-bold">4.5 Days</span>
              </div>
              <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
                <span className="text-slate-500 block">STOCKOUT RISK:</span>
                <span className="text-rose-400 font-bold">CRITICAL</span>
              </div>
            </div>

            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-[11px] text-slate-400 leading-relaxed">
              <strong className="text-slate-200 block mb-1">Stockout Equation:</strong>
              <code>Depletion Rate = Daily Consumption x Transit Delay</code>. Evaluates critical tier-1 component stockout windows against safety stock buffers.
            </div>
          </div>
        </div>

        {/* Pillar 3: Financial Impact Audit */}
        <div className="glass-panel p-6 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <DollarSign className="w-5 h-5 text-amber-400" />
              <h3 className="text-sm font-bold text-white font-mono">3. FINANCIAL AUDIT BREAKDOWN</h3>
            </div>
            <span className="text-[10px] font-mono text-amber-400 bg-amber-950 px-2 py-0.5 rounded">FINANCIAL AUDIT</span>
          </div>

          <div className="space-y-3 font-mono text-xs">
            <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
              <span className="text-slate-500 block">REROUTING COST (FUEL/PORT):</span>
              <span className="text-white font-bold">${(result.rerouting_cost_usd || 0).toLocaleString()} USD</span>
            </div>

            <div className="bg-slate-950 p-3 rounded-lg border border-slate-800">
              <span className="text-slate-500 block">TOTAL FINANCIAL IMPACT:</span>
              <span className="text-rose-400 font-bold text-sm">${(result.total_financial_impact_usd || 0).toLocaleString()} USD</span>
            </div>

            <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 flex items-center justify-between">
              <span className="text-slate-500">FINANCIAL ALERT STATUS:</span>
              <span className={`font-bold px-2 py-0.5 rounded ${result.financial_alert ? 'bg-rose-950 text-rose-400 border border-rose-800' : 'bg-emerald-950 text-emerald-400'}`}>
                {result.financial_alert ? 'TRIGGERED (> $100k)' : 'CLEAR'}
              </span>
            </div>

            <div className="p-3 bg-slate-950 rounded-lg border border-slate-800 text-[11px] text-slate-400 leading-relaxed">
              <strong className="text-slate-200 block mb-1">Financial Equation:</strong>
              <code>Total Impact = Demurrage + Fuel Surcharges + Alternate Port Handling + Customer SLA Penalties</code>.
            </div>
          </div>
        </div>

      </div>

    </div>
  );
}
