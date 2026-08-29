import React, { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  LayoutGrid, Workflow, Radio, GitCommitHorizontal, Code2, Terminal,
  Activity, Cpu, Award, Database, X, HeartPulse
} from 'lucide-react';

const NAV_SECTIONS = [
  {
    title: 'operations',
    items: [
      { to: '/', label: 'overview', icon: LayoutGrid, end: true },
      { to: '/pipeline', label: 'pipeline', icon: Workflow },
      { to: '/events', label: 'signals', icon: Radio }
    ]
  },
  {
    title: 'debug & trace',
    items: [
      { to: '/trace', label: 'trace', icon: GitCommitHorizontal },
      { to: '/state', label: 'state', icon: Code2 },
      { to: '/logs', label: 'terminal', icon: Terminal }
    ]
  },
  {
    title: 'analysis',
    items: [
      { to: '/telemetry', label: 'telemetry', icon: Activity },
      { to: '/explainability', label: 'explainability', icon: Cpu },
      { to: '/evaluation', label: 'evaluation', icon: Award }
    ]
  },
  {
    title: 'system',
    items: [
      { to: '/reference', label: 'reference db', icon: Database }
    ]
  }
];

export default function Sidebar({ mobile = false, onNavigate }) {
  const location = useLocation();

  return (
    <aside className={`glass flex h-full flex-col overflow-hidden rounded-[28px] ${mobile ? 'rounded-r-none' : ''}`}>
      <div className="flex items-center gap-3 px-6 pb-7 pt-7">
        <div className="relative flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-crimson to-blood text-white shadow-[0_10px_30px_-8px_rgba(225,29,72,0.6)]">
          <HeartPulse className="h-5 w-5" strokeWidth={2.2} />
        </div>
        <div className="leading-tight">
          <div className="display text-[17px] text-ink">supplypulse</div>
          <div className="eyebrow mt-0.5">operations console</div>
        </div>
        {mobile && (
          <button onClick={onNavigate} className="ml-auto text-ash hover:text-ink" aria-label="close navigation">
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      <nav className="flex-1 space-y-7 overflow-y-auto px-4 pb-6">
        {NAV_SECTIONS.map((section) => (
          <div key={section.title}>
            <div className="eyebrow mb-2.5 px-3">{section.title}</div>
            <div className="space-y-1">
              {section.items.map((item) => {
                const Icon = item.icon;
                const active = item.end ? location.pathname === '/' : location.pathname.startsWith(item.to);
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    onClick={onNavigate}
                    className={`group relative flex items-center gap-3 rounded-2xl px-3.5 py-3 text-[13.5px] font-medium transition-colors duration-300 ${
                      active ? 'text-ink' : 'text-fog hover:text-ink'
                    }`}
                  >
                    {active && (
                      <motion.span
                        layoutId="nav-active-pill"
                        transition={{ type: 'spring', stiffness: 350, damping: 30 }}
                        className="absolute inset-0 rounded-2xl bg-white/[0.07] shadow-[inset_0_1px_0_rgba(255,255,255,0.08),0_10px_30px_-16px_rgba(0,0,0,0.7)]"
                      />
                    )}
                    <Icon className={`relative z-10 h-[17px] w-[17px] shrink-0 transition-colors duration-300 ${active ? 'text-crimson' : 'text-ash group-hover:text-fog'}`} />
                    <span className="relative z-10 truncate">{item.label}</span>
                    {active && <span className="glow-dot relative z-10 ml-auto text-crimson" style={{ width: 4, height: 4 }} />}
                  </NavLink>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      <div className="mx-4 mb-5 flex items-center justify-between rounded-2xl bg-white/[0.04] px-4 py-3.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.06)]">
        <div>
          <div className="eyebrow">engine</div>
          <div className="mono mt-1 text-[10px] text-ash">langgraph · groq</div>
        </div>
        <span className="flex items-center gap-1.5">
          <span className="glow-dot text-mint" style={{ width: 5, height: 5 }} />
          <span className="mono text-[10px] font-medium text-mint">live</span>
        </span>
      </div>
    </aside>
  );
}
