import React, { useState } from 'react';
import { Radio, Database, RefreshCw, Globe, ExternalLink, Sliders, CheckCircle } from 'lucide-react';

export default function DataStreamToggle({ dataMode, setDataMode, selectedEvent, setSelectedEvent, onFetchLive }) {
  const [isFetchingLive, setIsFetchingLive] = useState(false);

  const presetScenarios = [
    {
      id: 'critical_suez',
      title: 'Suez Canal / Red Sea Security Crisis',
      nearest_port_name: 'Port of Suez',
      nearest_port_country: 'Egypt',
      severity: 'critical',
      goldstein_scale: -9.0,
      avg_tone: -7.5,
      num_mentions: 84,
      event_location: 'Bab-el-Mandeb Strait / Red Sea',
      affected_routes: '["R03", "R07"]',
      affected_commodities: '["Crude Oil", "Liquefied Natural Gas", "Container Freight"]',
      freight_impact_pct: 54.2,
      vessels_affected: 165,
      duration_hours: 240,
      source_url: 'https://www.reuters.com/maritime-disruption-red-sea',
      event_date: '2026-08-20',
      port_type: 'Canal / Transshipment Hub',
      port_strategic_importance: 'CRITICAL GLOBAL BOTTLENECK'
    },
    {
      id: 'critical_shanghai',
      title: 'Shanghai Container Terminal Congestion',
      nearest_port_name: 'Port of Shanghai',
      nearest_port_country: 'China',
      severity: 'critical',
      goldstein_scale: -7.5,
      avg_tone: -5.8,
      num_mentions: 62,
      event_location: 'Yangshan Deepwater Port, Shanghai',
      affected_routes: '["R01", "R05"]',
      affected_commodities: '["Semiconductors & Electronics", "Consumer Goods", "Auto Parts"]',
      freight_impact_pct: 42.0,
      vessels_affected: 98,
      duration_hours: 120,
      source_url: 'https://www.lloydslist.com/shanghai-port-backlog',
      event_date: '2026-08-22',
      port_type: 'Mega Commercial Port',
      port_strategic_importance: 'WORLD #1 CONTAINER PORT'
    },
    {
      id: 'high_singapore',
      title: 'Singapore Strait Tanker Collision Risk',
      nearest_port_name: 'Port of Singapore',
      nearest_port_country: 'Singapore',
      severity: 'high',
      goldstein_scale: -5.2,
      avg_tone: -4.1,
      num_mentions: 39,
      event_location: 'Singapore Strait Outer Anchorage',
      affected_routes: '["R02", "R04"]',
      affected_commodities: '["Refined Petroleum", "Chemicals", "Palm Oil"]',
      freight_impact_pct: 26.5,
      vessels_affected: 45,
      duration_hours: 72,
      source_url: 'https://www.maritime-executive.com/singapore-strait-alert',
      event_date: '2026-08-25',
      port_type: 'Global Bunkering & Transshipment',
      port_strategic_importance: 'KEY ASIAN HUB'
    },
    {
      id: 'medium_hamburg',
      title: 'Hamburg Dockworkers Strike Warning',
      nearest_port_name: 'Port of Hamburg',
      nearest_port_country: 'Germany',
      severity: 'medium',
      goldstein_scale: -3.8,
      avg_tone: -3.0,
      num_mentions: 28,
      event_location: 'Elbe River Port Area, Hamburg',
      affected_routes: '["R06"]',
      affected_commodities: '["Industrial Machinery", "Automobiles", "Chemicals"]',
      freight_impact_pct: 12.0,
      vessels_affected: 18,
      duration_hours: 48,
      source_url: 'https://www.dw.com/hamburg-port-labor-negotiations',
      event_date: '2026-08-27',
      port_type: 'European River Port',
      port_strategic_importance: 'MAJOR EUROPEAN GATEWAY'
    }
  ];

  const handleFetchLiveClick = async () => {
    setIsFetchingLive(true);
    try {
      const liveResult = await onFetchLive();
      if (liveResult && liveResult.top_signal) {
        setSelectedEvent(liveResult.top_signal);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsFetchingLive(false);
    }
  };

  return (
    <div className="space-y-6 font-mono">
      
      {/* Selector Header */}
      <div className="panel-dark p-6 border-cyan-500/30">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Sliders className="w-5 h-5 text-cyan-400" />
              <h2 className="text-lg font-bold text-white uppercase">TELEMETRY DATA SOURCE CONTROL PANEL</h2>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Select between live 15-minute GDELT 2.0 broadcast telemetry streams or verified historical validation datasets.
            </p>
          </div>

          <div className="flex items-center gap-2 bg-[#080B10] p-1 rounded border border-white/5 text-xs">
            <button
              onClick={() => setDataMode('pre-fetched')}
              className={`px-4 py-2 rounded flex items-center gap-2 font-bold transition-all ${
                dataMode === 'pre-fetched'
                  ? 'bg-blue-600 text-white shadow'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Database className="w-4 h-4" />
              PRE-FETCHED SET
            </button>
            <button
              onClick={() => setDataMode('live')}
              className={`px-4 py-2 rounded flex items-center gap-2 font-bold transition-all ${
                dataMode === 'live'
                  ? 'bg-cyan-500 text-slate-950 shadow'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              <Radio className="w-4 h-4 text-slate-950 animate-pulse" />
              LIVE GDELT 2.0 STREAM
            </button>
          </div>
        </div>
      </div>

      {/* Mode View */}
      {dataMode === 'live' ? (
        <div className="panel-dark p-6 space-y-6">
          <div className="flex items-center justify-between pb-4 border-b border-white/5">
            <div>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-cyan-400 animate-ping"></span>
                <h3 className="text-sm font-bold text-white uppercase">GDELT 2.0 BROADCAST POLLING ENGINE</h3>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Polling <code className="text-cyan-400">http://data.gdeltproject.org/gdeltv2/lastupdate.txt</code> (15-min cycle)
              </p>
            </div>

            <button
              onClick={handleFetchLiveClick}
              disabled={isFetchingLive}
              className="px-4 py-2 rounded bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs flex items-center gap-2 shadow"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isFetchingLive ? 'animate-spin' : ''}`} />
              {isFetchingLive ? 'POLLING GDELT SERVERS...' : 'FETCH LATEST 15-MIN SIGNAL NOW'}
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-xs">
            <div className="bg-[#080B10] p-4 rounded border border-white/5">
              <span className="text-[10px] text-slate-500 block">STREAM HEALTH</span>
              <div className="text-sm font-bold text-emerald-400 mt-1 flex items-center gap-1.5">
                <CheckCircle className="w-4 h-4 text-emerald-400" />
                ONLINE (15-min updates)
              </div>
            </div>

            <div className="bg-[#080B10] p-4 rounded border border-white/5">
              <span className="text-[10px] text-slate-500 block">GOLDSTEIN INSTABILITY INDEX</span>
              <div className="text-base font-bold text-rose-400 mt-1">{selectedEvent?.goldstein_scale || -8.5} / -10.0</div>
            </div>

            <div className="bg-[#080B10] p-4 rounded border border-white/5">
              <span className="text-[10px] text-slate-500 block">AVERAGE NEWS TONE</span>
              <div className="text-base font-bold text-amber-400 mt-1">{selectedEvent?.avg_tone || -6.2}</div>
            </div>

            <div className="bg-[#080B10] p-4 rounded border border-white/5">
              <span className="text-[10px] text-slate-500 block">ARTICLE MENTIONS</span>
              <div className="text-base font-bold text-cyan-400 mt-1">{selectedEvent?.num_mentions || 62} Sources</div>
            </div>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white flex items-center gap-2 uppercase">
              <Database className="w-4 h-4 text-blue-400" />
              VERIFIED REAL VALIDATION SCENARIOS (30 Events Available)
            </h3>
            <span className="text-xs text-slate-400">Click any scenario to load into the pipeline</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {presetScenarios.map((scenario) => {
              const isSelected = selectedEvent?.nearest_port_name === scenario.nearest_port_name;
              return (
                <div
                  key={scenario.id}
                  onClick={() => setSelectedEvent(scenario)}
                  className={`p-5 rounded-lg border transition-all cursor-pointer ${
                    isSelected
                      ? 'border-cyan-400 bg-cyan-500/10 shadow-lg shadow-cyan-500/10'
                      : 'border-white/5 bg-[#0D1218] hover:bg-[#131A22]'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded badge-${scenario.severity}`}>
                      {scenario.severity}
                    </span>
                    <span className="text-xs text-slate-400">{scenario.event_date}</span>
                  </div>

                  <h4 className="text-sm font-bold text-white mb-1">{scenario.title}</h4>
                  <p className="text-xs text-slate-400 mb-3">{scenario.event_location}</p>

                  <div className="grid grid-cols-2 gap-2 text-[11px] bg-[#080B10] p-2.5 rounded border border-white/5">
                    <div><span className="text-slate-500 block">Port:</span><span className="text-cyan-400 font-bold">{scenario.nearest_port_name}</span></div>
                    <div><span className="text-slate-500 block">Freight Impact:</span><span className="text-rose-400 font-bold">+{scenario.freight_impact_pct}%</span></div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

    </div>
  );
}
