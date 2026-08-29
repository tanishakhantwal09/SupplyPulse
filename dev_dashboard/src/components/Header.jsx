import React from 'react';
import { Activity, MapPin, Pause, Play, RotateCcw, Square, Wifi, Zap } from 'lucide-react';

export default function Header({ selectedEvent, dataMode, serverStatus, isPipelineRunning, onRunPipeline }) {
  const apiOnline = serverStatus === 'online';
  return (
    <header className="global-header">
      <div className="brand-lockup">
        <div className="brand-mark"><Activity size={19} /></div>
        <div className="brand-copy"><strong>SUPPLY<span>PULSE</span></strong><small>AI SUPPLY CHAIN OPERATIONS</small></div>
        <div className="version-badge">v2.4</div>
      </div>

      <div className="header-center">
        <div className="target-brief">
          <MapPin size={15} />
          <div><small>ACTIVE SIGNAL</small><strong>{selectedEvent?.nearest_port_name || 'No target selected'}</strong></div>
          {selectedEvent?.severity && <b className={`severity ${selectedEvent.severity}`}>{selectedEvent.severity}</b>}
        </div>
        <div className="status-cluster">
          <span className={apiOnline ? 'ok' : 'warn'}><i />API {apiOnline ? 'CONNECTED' : 'LOCAL MODE'}</span>
          <span className="ok"><i />MODEL ONLINE</span>
          <span className={dataMode === 'live' ? 'live' : ''}><Wifi size={11} />{dataMode === 'live' ? 'STREAM ACTIVE' : 'DATASET READY'}</span>
        </div>
      </div>

      <div className="execution-controls">
        <button className="run-button" onClick={onRunPipeline} disabled={isPipelineRunning} title="Run pipeline">
          {isPipelineRunning ? <Zap size={15} /> : <Play size={15} fill="currentColor" />}
          <span>{isPipelineRunning ? 'EXECUTING' : 'RUN PIPELINE'}</span>
        </button>
        <button onClick={onRunPipeline} disabled={isPipelineRunning} title="Replay last execution"><RotateCcw size={15} /></button>
        <button disabled={!isPipelineRunning} title="Pause is unavailable while the request is atomic"><Pause size={15} /></button>
        <button disabled={!isPipelineRunning} title="Stop is unavailable while the request is atomic"><Square size={14} /></button>
      </div>
    </header>
  );
}
