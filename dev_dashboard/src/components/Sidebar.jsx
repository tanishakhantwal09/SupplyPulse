import React from 'react';
import { 
  Layers, Radio, Cpu, Database, ShieldAlert, Terminal, 
  ChevronLeft, ChevronRight, Activity, GitCommit, Sliders, 
  Code2, LineChart
} from 'lucide-react';

export default function Sidebar({ activeTab, setActiveTab, collapsed, setCollapsed }) {
  const navSections = [
    {
      title: 'OVERVIEW',
      items: [
        { id: 'pipeline', label: 'Pipeline DAG', icon: Layers },
        { id: 'datainstream', label: 'Data Telemetry', icon: Radio },
        { id: 'telemetry', label: 'Execution Metrics', icon: LineChart },
      ]
    },
    {
      title: 'DEBUG & TRACE',
      items: [
        { id: 'trace', label: 'Trace Explorer', icon: GitCommit },
        { id: 'state', label: 'State Inspector', icon: Code2 },
        { id: 'terminal', label: 'Terminal Logs', icon: Terminal },
      ]
    },
    {
      title: 'ANALYSIS',
      items: [
        { id: 'explainability', label: 'Reroute Logic', icon: Cpu },
        { id: 'evaluation', label: 'Benchmark Hub', icon: ShieldAlert },
      ]
    },
    {
      title: 'SYSTEM',
      items: [
        { id: 'inspector', label: 'Reference DB', icon: Database },
      ]
    }
  ];

  return (
    <aside className={`sidebar-panel bg-[#080B10] border-r border-white/5 flex flex-col transition-all duration-300 relative z-40 ${
      collapsed ? 'w-16' : 'w-60'
    }`}>
      <div className="sidebar-orbit" aria-hidden="true">
        <div className="orbit-core"><Activity size={15} /></div>
        {!collapsed && <div><strong>MISSION CONTROL</strong><span>DEVELOPER WORKSPACE</span></div>}
      </div>
      
      {/* Collapse / Expand Toggle Button */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="absolute -right-3 top-6 bg-[#10161D] border border-white/10 text-slate-400 hover:text-white p-1 rounded-full shadow-lg z-50 hover:bg-[#18202A] transition-all"
        title={collapsed ? "Expand Sidebar" : "Collapse Sidebar"}
      >
        {collapsed ? <ChevronRight className="w-3.5 h-3.5" /> : <ChevronLeft className="w-3.5 h-3.5" />}
      </button>

      {/* Navigation Sections */}
      <div className="flex-1 py-4 px-2 space-y-6 overflow-y-auto">
        {navSections.map((section, idx) => (
          <div key={idx} className="space-y-1">
            {!collapsed && (
              <span className="text-[10px] font-mono font-bold text-slate-500 uppercase tracking-widest px-3 block mb-2">
                {section.title}
              </span>
            )}

            {section.items.map(item => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  title={collapsed ? item.label : undefined}
                  className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-xs font-mono transition-all ${
                    isActive
                      ? 'bg-cyan-500/10 text-cyan-400 font-bold border border-cyan-500/30 shadow-sm shadow-cyan-500/10'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-white/5'
                  }`}
                >
                  <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-cyan-400' : 'text-slate-500'}`} />
                  {!collapsed && <span className="truncate">{item.label}</span>}
                </button>
              );
            })}
          </div>
        ))}
      </div>

      {/* Sidebar Footer Indicator */}
      {!collapsed && (
        <div className="p-3 m-2 rounded-lg bg-[#0D1218] border border-white/5 font-mono text-[11px] text-slate-400">
          <div className="flex items-center justify-between">
            <span className="text-slate-500">ENGINE</span>
            <span className="text-emerald-400 font-bold text-[10px]">● RUNNING</span>
          </div>
          <div className="text-[10px] text-slate-500 mt-1 truncate">LangGraph v0.2 DAG</div>
        </div>
      )}

    </aside>
  );
}
