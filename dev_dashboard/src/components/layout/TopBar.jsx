import React, { useState, useRef, useEffect } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, Play, Zap, Menu, X } from 'lucide-react';
import { useSupplyPulse } from '../../context/SupplyPulseContext';
import { SeverityBadge } from '../ui/primitives';

const NAV_ITEMS = [
  { to: '/', label: 'Overview', end: true },
  { to: '/pipeline', label: 'Pipeline' },
  { to: '/events', label: 'Signals' },
  { to: '/evaluation', label: 'Evaluation' },
  { to: '/telemetry', label: 'Telemetry' },
  { to: '/trace', label: 'Trace' },
  { to: '/state', label: 'State' },
  { to: '/reference', label: 'Reference' },
  { to: '/logs', label: 'Terminal' }
];

export default function TopBar() {
  const {
    serverStatus,
    isPipelineRunning,
    runPipeline,
    selectedEvent,
    scenariosList,
    selectedScenarioIndex,
    selectScenario
  } = useSupplyPulse();

  const navigate = useNavigate();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const dropdownRef = useRef(null);
  const apiOnline = serverStatus === 'online';

  // Close dropdown on outside click
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleRun = () => {
    navigate('/pipeline');
    runPipeline();
  };

  return (
    <header className="sticky top-0 z-50 w-full border-b border-white/[0.07] bg-[#070709]/90 backdrop-blur-2xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 lg:px-10 h-18">
        {/* Left: Brand & Scenario Switcher */}
        <div className="flex items-center gap-5">
          <NavLink to="/" className="flex items-center gap-3 group">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-rose-600 to-rose-700 text-white font-black text-xs tracking-wider shadow-[0_0_20px_rgba(225,29,72,0.4)]">
              SP
            </div>
            <div className="flex flex-col">
              <span className="font-bold text-sm tracking-tight text-white group-hover:text-rose-400 transition-colors">
                SupplyPulse
              </span>
              <span className="text-[10px] tracking-wider uppercase font-semibold text-neutral-500">
                Autonomous Core
              </span>
            </div>
          </NavLink>

          <span className="text-neutral-800 hidden md:inline">|</span>

          {/* Scenario Selector Dropdown */}
          <div className="relative hidden md:block" ref={dropdownRef}>
            <button
              onClick={() => setDropdownOpen(!dropdownOpen)}
              className="flex items-center gap-2.5 rounded-lg px-3 py-1.5 text-xs text-neutral-300 hover:text-white hover:bg-white/[0.05] transition-all cursor-pointer"
            >
              <span className="mono text-[11px] font-semibold text-rose-400">
                {selectedEvent?.scenario_id || 'SYN_0001'}
              </span>
              <span className="text-neutral-600">·</span>
              <span className="truncate max-w-[160px] font-medium text-neutral-200">
                {selectedEvent?.nearest_port_name}
              </span>
              <ChevronDown className={`h-3.5 w-3.5 text-neutral-500 transition-transform duration-200 ${dropdownOpen ? 'rotate-180' : ''}`} />
            </button>

            <AnimatePresence>
              {dropdownOpen && (
                <motion.div
                  initial={{ opacity: 0, y: 6, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 4, scale: 0.98 }}
                  transition={{ duration: 0.15 }}
                  className="absolute left-0 top-full mt-2 z-50 w-80 max-h-72 overflow-y-auto rounded-2xl bg-[#111117] border border-white/[0.1] shadow-2xl p-1.5"
                >
                  <div className="px-3 py-2 text-[10px] font-semibold tracking-wider uppercase text-neutral-500 border-b border-white/[0.05]">
                    Select Benchmark Scenario ({scenariosList.length})
                  </div>
                  {scenariosList.slice(0, 15).map((sc, idx) => (
                    <button
                      key={sc.scenario_id || idx}
                      onClick={() => {
                        selectScenario(idx);
                        setDropdownOpen(false);
                      }}
                      className={`w-full text-left rounded-xl px-3.5 py-2.5 text-xs transition-colors flex items-center justify-between cursor-pointer mt-1 ${
                        selectedScenarioIndex === idx
                          ? 'bg-white/[0.08] text-white font-semibold'
                          : 'text-neutral-300 hover:bg-white/[0.04] hover:text-white'
                      }`}
                    >
                      <div className="truncate pr-3">
                        <span className="mono text-[10px] text-neutral-500 block">{sc.scenario_id}</span>
                        <span className="truncate block font-medium">{sc.affected_port}</span>
                      </div>
                      <SeverityBadge severity={sc.severity} />
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Center: Navigation Links */}
        <nav className="hidden lg:flex items-center gap-7">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `relative py-2 text-xs tracking-tight transition-colors duration-150 ${
                  isActive
                    ? 'text-white font-semibold'
                    : 'text-neutral-400 hover:text-neutral-200'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <span>{item.label}</span>
                  {isActive && (
                    <motion.div
                      layoutId="topbar-active-indicator"
                      className="absolute -bottom-2.5 left-0 right-0 h-[2px] bg-rose-500"
                      transition={{ type: 'spring', stiffness: 500, damping: 35 }}
                    />
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Right: Status & Action CTA */}
        <div className="flex items-center gap-6 ml-6 shrink-0">
          <div className="hidden sm:flex items-center text-xs text-neutral-400 whitespace-nowrap shrink-0">
            <span className="mono text-[11px] text-neutral-400 font-medium">{apiOnline ? 'API Online' : 'Local Engine'}</span>
          </div>

          <button
            onClick={handleRun}
            disabled={isPipelineRunning}
            className="cred-btn-primary text-xs cursor-pointer whitespace-nowrap shrink-0"
          >
            {isPipelineRunning ? (
              <>
                <Zap className="h-3.5 w-3.5 text-rose-600" />
                <span>Running Pipeline…</span>
              </>
            ) : (
              <>
                <Play className="h-3.5 w-3.5 fill-black" />
                <span>Run Pipeline</span>
              </>
            )}
          </button>

          {/* Mobile Menu Toggle */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="lg:hidden p-2 rounded-xl text-neutral-400 hover:text-white hover:bg-white/[0.06] transition-colors"
          >
            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer Menu */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="lg:hidden border-t border-white/[0.08] bg-[#0C0C10] px-6 py-4"
          >
            <div className="grid grid-cols-2 gap-2">
              {NAV_ITEMS.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  onClick={() => setMobileMenuOpen(false)}
                  className={({ isActive }) =>
                    `rounded-xl px-4 py-2.5 text-xs font-semibold transition-all ${
                      isActive
                        ? 'bg-rose-500/20 text-white border border-rose-500/30'
                        : 'text-neutral-400 hover:text-white hover:bg-white/[0.04]'
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
