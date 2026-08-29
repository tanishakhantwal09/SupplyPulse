import React from 'react';
import { 
  Layers, Radio, Cpu, Database, ShieldAlert, Terminal, 
  GitCommit, Code2, LineChart, ChevronRight, Settings, Sliders 
} from 'lucide-react';

export default function Navbar({ activeTab, setActiveTab, dataMode, setDataMode }) {
  const primaryTabs = [
    { id: 'pipeline', label: 'Workflow & Pipeline', icon: Layers, color: 'text-gold' },
    { id: 'datainstream', label: 'Data & Telemetry', icon: Radio, color: 'text-info' },
    { id: 'trace', label: 'Trace Explorer', icon: GitCommit, color: 'text-purple-400' },
    { id: 'state', label: 'State Inspector', icon: Code2, color: 'text-success' },
    { id: 'explainability', label: 'Reroute Logic', icon: Cpu, color: 'text-gold' },
    { id: 'evaluation', label: 'Benchmark Hub', icon: ShieldAlert, color: 'text-danger' },
    { id: 'inspector', label: 'Reference DB', icon: Database, color: 'text-info' },
    { id: 'terminal', label: 'Terminal Logs', icon: Terminal, color: 'text-success' },
  ];

  return (
    <div className="space-y-4 font-outfit">
      
      {/* Primary Navigation Tabs */}
      <nav className="flex flex-wrap items-center gap-3 border-b border-border-subtle pb-4 overflow-x-auto">
        {primaryTabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2.5 px-5 py-3 rounded-xl font-bold text-xs transition-all cursor-pointer ${
                isActive
                  ? 'bg-bg-secondary text-text-primary shadow-lg border border-border-accent ring-1 ring-border-accent/40 font-extrabold'
                  : 'text-text-muted hover:text-text-secondary hover:bg-bg-card-hover border border-transparent'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? tab.color : 'text-text-muted'}`} />
              {tab.label}
            </button>
          );
        })}
      </nav>

      {/* Sub-Navigation & Telemetry Stream Control Drawer */}
      <div className="flex flex-wrap items-center justify-between gap-3 pl-2 py-1 text-xs font-dm-mono">
        <div className="flex items-center gap-2 text-text-muted">
          <ChevronRight className="w-4 h-4" />
          <span>Active View: <strong className="text-gold uppercase font-bold">{activeTab}</strong></span>
        </div>

        {/* Data Stream Mode Switcher Pill */}
        <div className="flex items-center gap-2 bg-bg-secondary p-1 rounded-lg border border-border-subtle text-xs">
          <button
            onClick={() => setDataMode('pre-fetched')}
            className={`px-3 py-1.5 rounded-md flex items-center gap-1.5 transition-all font-bold cursor-pointer ${
              dataMode === 'pre-fetched'
                ? 'bg-info/20 text-info border border-info/40 shadow-sm'
                : 'text-text-muted hover:text-text-primary'
            }`}
          >
            <Database className="w-3.5 h-3.5" />
            Pre-Fetched Set
          </button>

          <button
            onClick={() => setDataMode('live')}
            className={`px-3 py-1.5 rounded-md flex items-center gap-1.5 transition-all font-bold cursor-pointer ${
              dataMode === 'live'
                ? 'bg-gold/20 text-gold border border-gold/40 shadow-sm'
                : 'text-text-muted hover:text-text-primary'
            }`}
          >
            <Radio className="w-3.5 h-3.5 text-gold animate-pulse" />
            Live GDELT 2.0 Stream
          </button>
        </div>
      </div>

    </div>
  );
}
