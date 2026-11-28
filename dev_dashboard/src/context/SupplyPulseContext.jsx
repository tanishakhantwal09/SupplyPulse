import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import sampleScenarios from '../data/sample_scenarios.json';
import portsData from '../data/ports.json';
import commoditiesData from '../data/commodities.json';
import routesData from '../data/routes.json';

// Honesty rules (BUILD_PLAN 4a): no client-side fallback result, no hard-coded
// confidence. Pages show "No run yet" until the API returns a real run.

import { API_BASE } from '../lib/format';

const SupplyPulseContext = createContext(null);

// A real development-set event from /api/events, shaped for the event lists.
function fromDevEvent(ev) {
  return {
    scenario_id: `EVT_${ev.event_id}`,
    data_source: ev.data_source || 'GDELT',
    origin: 'development',
    runnable: true,
    disruption_type: 'GDELT news event',
    affected_port: ev.nearest_port_name,
    country_code: ev.nearest_port_country,
    severity: ev.severity,
    duration_hours: ev.duration_hours,
    goldstein_scale: ev.goldstein_scale,
    avg_tone: ev.avg_tone,
    num_mentions: ev.num_mentions,
    freight_impact_pct: ev.freight_impact_pct,
    event_date: ev.event_date,
    raw: ev,
  };
}

// A synthetic benchmark scenario (offline display only; it lacks the fields the pipeline needs).
function fromSynthetic(sc) {
  return { ...sc, origin: 'synthetic', runnable: false, raw: null };
}

// The event object shown on pages. Missing values stay missing (shown as "—").
function toSelectedEvent(item) {
  if (!item) return null;
  const base = item.raw || {};
  return {
    ...base,
    scenario_id: item.scenario_id,
    origin: item.origin,
    runnable: item.runnable,
    data_source: item.data_source,
    disruption_type: item.disruption_type?.replace(/_/g, ' '),
    nearest_port_name: base.nearest_port_name ?? item.affected_port,
    nearest_port_country: base.nearest_port_country ?? item.country_code,
    severity: item.severity,
    duration_hours: item.duration_hours,
    freight_impact_pct: item.freight_impact_pct,
    goldstein_scale: item.goldstein_scale,
    avg_tone: item.avg_tone,
    num_mentions: item.num_mentions,
  };
}

const SYNTHETIC = (sampleScenarios || []).map(fromSynthetic);

// Last run, kept for this browser tab only (sessionStorage), so a page refresh shows it again.
// Every access is wrapped in try/catch: storage can be blocked (private mode, browser settings).
const LAST_RUN_KEY = 'supplypulse:lastRun';

function loadLastRun() {
  try {
    const raw = window.sessionStorage.getItem(LAST_RUN_KEY);
    const saved = raw ? JSON.parse(raw) : null;
    return saved?.result && saved?.eventKey ? saved : null;
  } catch {
    return null;
  }
}

function saveLastRun(result, eventKey) {
  try {
    window.sessionStorage.setItem(LAST_RUN_KEY, JSON.stringify({ result, eventKey, savedAt: new Date().toISOString() }));
  } catch {
    // storage unavailable: the run still shows until the page is refreshed
  }
}

function clearLastRun() {
  try {
    window.sessionStorage.removeItem(LAST_RUN_KEY);
  } catch {
    // ignore
  }
}

export function SupplyPulseProvider({ children }) {
  const [serverStatus, setServerStatus] = useState('checking');
  const [eventsStatus, setEventsStatus] = useState('idle');
  const [eventsError, setEventsError] = useState(null);
  const [isPipelineRunning, setIsPipelineRunning] = useState(false);
  const [scenariosList, setScenariosList] = useState(SYNTHETIC);
  const [selectedScenarioIndex, setSelectedScenarioIndex] = useState(0);
  const [menuOpen, setMenuOpen] = useState(false);
  const [restored] = useState(loadLastRun);
  const [pipelineResult, setPipelineResult] = useState(() => restored?.result ?? null);
  const [lastError, setLastError] = useState(null);
  const [terminalLogs, setTerminalLogs] = useState([
    `[INFO] Dashboard loaded. Reference data: ${portsData.length} ports, ${commoditiesData.length} commodities.`,
    '[INFO] No run yet. Start the API server (python3 dev_dashboard/server.py) to run the real pipeline.'
  ]);

  const addLog = (msg) => {
    const time = new Date().toLocaleTimeString();
    setTerminalLogs(prev => [...prev, `[${time}] ${msg}`]);
  };

  const selectedEvent = toSelectedEvent(scenariosList[selectedScenarioIndex]);

  // ONE shared status check used by every page. Two separate questions:
  //   serverStatus: is the API reachable?            'checking' | 'online' | 'offline'
  //   eventsStatus: did the event list load?          'idle' | 'loaded' | 'empty' | 'failed'
  // A failed event list never marks the server offline (bug of 27 Nov 2026).
  const checkServer = useCallback(async () => {
    setServerStatus('checking');
    setEventsError(null);
    try {
      const res = await fetch(`${API_BASE}/api/status`);
      const data = await res.json();
      if (!res.ok || data.status !== 'online') throw new Error(`status endpoint returned HTTP ${res.status}`);
      setServerStatus('online');
      addLog(`[INFO] Connected to the SupplyPulse API (${data.llm_model}).`);
    } catch (err) {
      setServerStatus('offline');
      setEventsStatus('idle');
      if (restored) setPipelineResult(null); // its event is not listed offline; kept in storage for later
      addLog(`[INFO] API server offline (${err.message}): showing SYNTHETIC scenarios only. Runs are disabled.`);
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/api/events`);
      const d = JSON.parse(await res.text()); // strict JSON, same as the browser's res.json()
      if (!res.ok) throw new Error(d.error || `HTTP ${res.status}`);
      if (d.events?.length) {
        const list = d.events.map(fromDevEvent);
        setScenariosList(list);
        // Re-select the event of the restored run; drop the run if its event is no longer listed.
        const idx = restored ? list.findIndex(e => e.scenario_id === restored.eventKey) : -1;
        setSelectedScenarioIndex(idx >= 0 ? idx : 0);
        if (restored && idx >= 0) {
          addLog(`[INFO] Restored the last run for ${restored.eventKey} (saved ${restored.savedAt}).`);
        } else if (restored) {
          setPipelineResult(null);
          clearLastRun();
        }
        setEventsStatus('loaded');
        addLog(`[INFO] Loaded ${d.events.length} events from the ${d.source}.`);
      } else {
        setEventsStatus('empty');
        addLog('[ERROR] Server reachable but the event list is empty (is the development Parquet file present?).');
      }
    } catch (err) {
      setEventsStatus('failed');
      setEventsError(err.message);
      addLog(`[ERROR] Server reachable but event list failed: ${err.message}`);
    }
  }, [restored]);

  useEffect(() => { checkServer(); }, [checkServer]);

  const runPipeline = useCallback(async () => {
    setLastError(null);
    if (serverStatus !== 'online') {
      const msg = serverStatus === 'checking' ? 'Still checking the API server: no run was made.'
        : 'API server is offline: no run was made.';
      setLastError(msg);
      addLog(`[ERROR] ${msg}`);
      return null;
    }
    if (!selectedEvent?.runnable) {
      const msg = 'Synthetic scenarios cannot be run. Select a development-set event.';
      setLastError(msg);
      addLog(`[ERROR] ${msg}`);
      return null;
    }
    setIsPipelineRunning(true);
    addLog(`[PIPELINE] Running for ${selectedEvent.nearest_port_name}...`);
    try {
      const response = await fetch(`${API_BASE}/api/run-pipeline`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event: selectedEvent.raw ?? scenariosList[selectedScenarioIndex].raw })
      });
      const data = await response.json();
      if (!response.ok || !data.success) {
        const msg = data.error || `HTTP ${response.status}`;
        setLastError(msg);
        addLog(`[ERROR] Run failed: ${msg}`);
        return null;
      }
      setPipelineResult(data.result);
      saveLastRun(data.result, selectedEvent.scenario_id);
      addLog(`[SUCCESS] Run ${data.result.status} in ${data.result.total_response_time_seconds}s. Decision: ${data.result.decision}`);
      return data.result;
    } catch (err) {
      const msg = `Could not reach the API: ${err.message}`;
      setLastError(msg);
      addLog(`[ERROR] ${msg}`);
      return null;
    } finally {
      setIsPipelineRunning(false);
    }
  }, [serverStatus, selectedEvent, scenariosList, selectedScenarioIndex]);

  const selectScenario = (index) => {
    if (index >= 0 && index < scenariosList.length) {
      setSelectedScenarioIndex(index);
      setPipelineResult(null);
      clearLastRun();
      setLastError(null);
      addLog(`[EVENT] Selected ${scenariosList[index].scenario_id} (${scenariosList[index].affected_port})`);
    }
  };

  return (
    <SupplyPulseContext.Provider value={{
      serverStatus,
      eventsStatus,
      eventsError,
      checkServer,
      isPipelineRunning,
      selectedEvent,
      pipelineResult,
      setPipelineResult,
      lastError,
      terminalLogs,
      addLog,
      runPipeline,
      scenariosList,
      selectedScenarioIndex,
      selectScenario,
      portsData,
      commoditiesData,
      routesData,
      menuOpen,
      setMenuOpen
    }}>
      {children}
    </SupplyPulseContext.Provider>
  );
}

export function useSupplyPulse() {
  return useContext(SupplyPulseContext);
}
