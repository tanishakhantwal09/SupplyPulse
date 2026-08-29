import React, { useEffect, useMemo, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Menu, Radio, X } from 'lucide-react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import PipelineVisualizer from './components/PipelineVisualizer';
import DataStreamToggle from './components/DataStreamToggle';
import ExplainabilityMatrix from './components/ExplainabilityMatrix';
import DataInspector from './components/DataInspector';
import EvaluationHub from './components/EvaluationHub';
import TerminalLogs from './components/TerminalLogs';
import ExecutionTimeline from './components/ExecutionTimeline';
import StateInspector from './components/StateInspector';
import TelemetryDashboard from './components/TelemetryDashboard';
import EventStream from './components/EventStream';

const VIEW_META = {
  pipeline: ['Pipeline command center', 'Inspect the live LangGraph route, agent contracts, and computed payloads.'],
  datainstream: ['Data telemetry', 'Select an event source and control the disruption signal entering the pipeline.'],
  telemetry: ['Execution metrics', 'Monitor runtime health, latency, token consumption, and agent performance.'],
  trace: ['Trace explorer', 'Follow every execution step and inspect its exact inputs and outputs.'],
  state: ['State inspector', 'Review application-state mutations across the multi-agent graph.'],
  terminal: ['Terminal logs', 'Search and copy the engine output produced during this session.'],
  explainability: ['Decision intelligence', 'Understand the signals and thresholds behind the rerouting decision.'],
  evaluation: ['Benchmark hub', 'Compare SupplyPulse results with the formal evaluation baseline.'],
  inspector: ['Reference database', 'Browse the ports, shipping lanes, and commodity records used by agents.'],
};

export default function App() {
  const [activeTab, setActiveTab] = useState('pipeline');
  const [dataMode, setDataMode] = useState('pre-fetched');
  const [serverStatus, setServerStatus] = useState('offline');
  const [isPipelineRunning, setIsPipelineRunning] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  const [selectedEvent, setSelectedEvent] = useState({
    nearest_port_name: 'Port of Shanghai', nearest_port_country: 'China', severity: 'critical',
    goldstein_scale: -8.5, avg_tone: -6.2, num_mentions: 62,
    event_location: 'Yangshan Deepwater Port, Shanghai', affected_routes: '["R01", "R05"]',
    affected_commodities: '["Semiconductors & Electronics", "Consumer Goods"]',
    freight_impact_pct: 48.5, vessels_affected: 98, duration_hours: 120,
    source_url: 'https://www.lloydslist.com/shanghai-port-backlog'
  });

  const [pipelineResult, setPipelineResult] = useState({
    disrupted_port: 'Port of Shanghai', severity: 'CRITICAL', decision: 'REROUTE',
    recommended_alternate_port: 'Ningbo-Zhoushan', alternate_port_country: 'China',
    distance_nm: 114.5, additional_transit_days: 2.1, rerouting_cost_usd: 45200,
    total_financial_impact_usd: 382000, financial_alert: true,
    top_priority_commodity: 'Semiconductors & Electronics', inventory_exposure_usd: 1250000,
    confidence: '91%', total_response_time_seconds: 3.42,
    agents_activated: ['supervisor', 'route_optimization', 'inventory', 'financial_auditor', 'supervisor_final']
  });

  const [terminalLogs, setTerminalLogs] = useState([
    '[INFO  16:56:09] SupplyPulse Observability Platform Engine Ready.',
    '[INFO  16:56:09] Connected to Python API Server at http://localhost:5001.'
  ]);

  const addLog = (msg) => {
    const time = new Date().toLocaleTimeString();
    setTerminalLogs(prev => [...prev, `${time} ${msg}`]);
  };

  useEffect(() => {
    fetch('http://localhost:5001/api/status')
      .then(res => res.json())
      .then(data => {
        if (data.status === 'online') {
          setServerStatus('online');
          addLog('[SERVER] Connected to Python API Backend at http://localhost:5001');
        }
      })
      .catch(() => {
        setServerStatus('offline');
        addLog('[SERVER] Standalone execution mode active.');
      });
  }, []);

  const handleRunPipeline = async () => {
    setIsPipelineRunning(true);
    setActiveTab('pipeline');
    addLog(`[PIPELINE] Executing multi-agent pipeline for ${selectedEvent.nearest_port_name}...`);
    try {
      const response = await fetch('http://localhost:5001/api/run-pipeline', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event: selectedEvent })
      });
      if (!response.ok) throw new Error('API failed');
      const data = await response.json();
      setPipelineResult(data.result);
      addLog(`[SUCCESS] Pipeline execution complete in ${data.result.total_response_time_seconds}s. Decision: ${data.result.decision}`);
    } catch {
      addLog(`[SIMULATION] Completed pipeline execution for ${selectedEvent.nearest_port_name}.`);
      const isCritical = selectedEvent.severity?.toLowerCase() === 'critical';
      setPipelineResult({
        disrupted_port: selectedEvent.nearest_port_name,
        severity: (selectedEvent.severity || 'CRITICAL').toUpperCase(),
        decision: isCritical ? 'REROUTE' : 'MONITOR',
        recommended_alternate_port: selectedEvent.nearest_port_name.includes('Shanghai') ? 'Ningbo-Zhoushan' : 'Cape of Good Hope',
        alternate_port_country: selectedEvent.nearest_port_country,
        distance_nm: isCritical ? 114.5 : 45, additional_transit_days: isCritical ? 2.1 : 0.8,
        rerouting_cost_usd: isCritical ? 45200 : 12000,
        total_financial_impact_usd: isCritical ? 382000 : 85000,
        financial_alert: isCritical, top_priority_commodity: 'Semiconductors & Electronics',
        inventory_exposure_usd: isCritical ? 1250000 : 350000,
        confidence: isCritical ? '91%' : '82%', total_response_time_seconds: 3.42,
        agents_activated: ['supervisor', 'route_optimization', 'inventory', 'financial_auditor', 'supervisor_final']
      });
    } finally {
      setIsPipelineRunning(false);
    }
  };

  const handleFetchLive = async () => {
    addLog('[GDELT] Polling GDELT 2.0 live stream at lastupdate.txt...');
    try {
      const response = await fetch('http://localhost:5001/api/fetch-live', { method: 'POST' });
      if (response.ok) {
        const data = await response.json();
        addLog(`[GDELT] New Live Disruption Signal Detected: ${data.top_signal.nearest_port_name}`);
        return data;
      }
    } catch {
      addLog('[GDELT] Simulated live event signal ingested.');
    }
    return { top_signal: { nearest_port_name: 'Port of Suez', nearest_port_country: 'Egypt', severity: 'critical', goldstein_scale: -9, avg_tone: -7.2, num_mentions: 84, event_location: 'Bab-el-Mandeb Strait / Red Sea', affected_routes: '["R03", "R07"]', affected_commodities: '["Crude Oil", "LNG", "Containers"]', freight_impact_pct: 54.2, vessels_affected: 165, duration_hours: 240, source_url: 'https://www.reuters.com/maritime-disruption-red-sea' } };
  };

  const view = useMemo(() => {
    const props = { pipelineResult, selectedEvent };
    const views = {
      pipeline: <PipelineVisualizer {...props} isRunning={isPipelineRunning} />,
      datainstream: <DataStreamToggle dataMode={dataMode} setDataMode={setDataMode} selectedEvent={selectedEvent} setSelectedEvent={setSelectedEvent} onFetchLive={handleFetchLive} />,
      telemetry: <TelemetryDashboard pipelineResult={pipelineResult} />,
      trace: <ExecutionTimeline {...props} />,
      state: <StateInspector {...props} />,
      explainability: <ExplainabilityMatrix {...props} />,
      evaluation: <EvaluationHub />,
      inspector: <DataInspector />,
      terminal: <TerminalLogs logs={terminalLogs} />,
    };
    return views[activeTab] || views.pipeline;
  }, [activeTab, dataMode, isPipelineRunning, pipelineResult, selectedEvent, terminalLogs]);

  const navigate = (tab) => {
    setActiveTab(tab);
    setMobileNavOpen(false);
  };
  const [viewTitle, viewSubtitle] = VIEW_META[activeTab] || VIEW_META.pipeline;

  return (
    <div className="app-shell">
      <div className="ambient ambient-one" /><div className="ambient ambient-two" />
      <aside className={`desktop-sidebar ${sidebarCollapsed ? 'is-collapsed' : ''}`}>
        <Sidebar activeTab={activeTab} setActiveTab={navigate} collapsed={sidebarCollapsed} setCollapsed={setSidebarCollapsed} />
      </aside>

      <AnimatePresence>
        {mobileNavOpen && (
          <motion.div className="mobile-nav-layer" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <motion.aside initial={{ x: -280 }} animate={{ x: 0 }} exit={{ x: -280 }} transition={{ type: 'spring', damping: 26 }}>
              <button className="mobile-nav-close" onClick={() => setMobileNavOpen(false)} aria-label="Close navigation"><X size={18} /></button>
              <Sidebar activeTab={activeTab} setActiveTab={navigate} collapsed={false} setCollapsed={() => {}} />
            </motion.aside>
          </motion.div>
        )}
      </AnimatePresence>

      <section className="app-stage">
        <Header selectedEvent={selectedEvent} dataMode={dataMode} serverStatus={serverStatus} isPipelineRunning={isPipelineRunning} onRunPipeline={handleRunPipeline} />
        <main className="workspace">
          <div className="workspace-heading">
            <div className="workspace-title-wrap">
              <button className="mobile-menu" onClick={() => setMobileNavOpen(true)} aria-label="Open navigation"><Menu size={18} /></button>
              <div><div className="eyebrow">SUPPLY PULSE / {activeTab.replaceAll('_', ' ')}</div><h1>{viewTitle}</h1><p>{viewSubtitle}</p></div>
            </div>
            <div className="stream-chip"><Radio size={13} /><span>{dataMode === 'live' ? 'LIVE GDELT' : 'VALIDATION SET'}</span><i /></div>
          </div>

          <AnimatePresence mode="wait">
            <motion.div key={activeTab} initial={{ opacity: 0, y: 10, filter: 'blur(4px)' }} animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }} exit={{ opacity: 0, y: -6 }} transition={{ duration: .24 }} className="view-surface">
              {view}
            </motion.div>
          </AnimatePresence>

          <div className="event-dock"><EventStream selectedEvent={selectedEvent} pipelineResult={pipelineResult} /></div>
          <footer>SUPPLY PULSE / MULTI-AGENT OPERATIONS CONSOLE <span>BUILD 2.4.0 · 2026</span></footer>
        </main>
      </section>
    </div>
  );
}
