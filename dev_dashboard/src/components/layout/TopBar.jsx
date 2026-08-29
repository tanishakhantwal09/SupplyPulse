import React, { useState, useRef, useEffect } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, Play, Zap } from 'lucide-react';
import { useSupplyPulse } from '../../context/SupplyPulseContext';
import { SeverityBadge } from '../ui/primitives';

export default function TopBar() {
  const {
    isPipelineRunning,
    runPipeline,
    selectedEvent,
    scenariosList,
    selectedScenarioIndex,
    selectScenario
  } = useSupplyPulse();

  const navigate = useNavigate();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

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
    <header className="fixed top-0 z-50 w-full border-b border-white/[0.06] bg-[#0A0A0C]/90 backdrop-blur-xl">
      <div className="mx-auto flex h-[84px] w-full max-w-[1440px] items-center justify-between px-6 lg:px-12">
        {/* Left: Brand + Scenario Switcher */}
        <div className="flex items-center gap-5">
          <NavLink to="/" className="group flex items-center gap-4" aria-label="SupplyPulse home">
            <span className="flex flex-col items-end gap-[7px]">
              <span className="flex items-center gap-[5px]">
                <span className="h-[5px] w-[5px] rounded-full bg-[#E11D48]" />
                <span className="h-[2px] w-4 bg-[#F1EFF5] transition-colors group-hover:bg-white" />
              </span>
              <span className="h-[2px] w-7 bg-[#F1EFF5] transition-colors group-hover:bg-white" />
            </span>
            <span className="flex items-end">
              <span className="pl-display text-xl lg:text-2xl font-medium tracking-[-0.02em] text-[#F1EFF5] transition-colors group-hover:text-white">
                supplypulse
              </span>
              <span className="mb-[3px] ml-[3px] h-2 w-2 rounded-full bg-[#E11D48]" />
            </span>
          </NavLink>

          <span className="hidden md:inline text-neutral-800">|</span>

          {/* Scenario Selector Dropdown */}
          <div className="relative hidden md:block" ref={dropdownRef}>
            <button
              onClick={() => setDropdownOpen(!dropdownOpen)}
              data-cursor-label="Scenarios"
              className="flex items-center gap-2.5 px-3 py-1.5 text-xs text-neutral-300 hover:text-white transition-all cursor-pointer border border-transparent hover:border-[rgba(225,29,72,0.4)]"
            >
              <span className="mono text-[11px] font-semibold text-[#E11D48]">
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
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 4 }}
                  transition={{ duration: 0.15 }}
                  className="absolute left-0 top-full mt-2 z-50 w-80 max-h-72 overflow-y-auto border border-[rgba(225,29,72,0.35)] bg-[#0B0B0F] shadow-2xl p-1.5"
                  data-lenis-prevent
                >
                  <div className="px-3 py-2 text-[10px] font-semibold tracking-wider uppercase text-neutral-500 border-b border-[rgba(225,29,72,0.2)]">
                    Select Benchmark Scenario ({scenariosList.length})
                  </div>
                  {scenariosList.slice(0, 15).map((sc, idx) => (
                    <button
                      key={sc.scenario_id || idx}
                      onClick={() => {
                        selectScenario(idx);
                        setDropdownOpen(false);
                      }}
                      className={`w-full text-left px-3.5 py-2.5 text-xs transition-colors flex items-center justify-between cursor-pointer mt-1 ${
                        selectedScenarioIndex === idx
                          ? 'bg-[rgba(225,29,72,0.12)] text-white font-semibold'
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

        {/* Right: Action CTA */}
        <div className="flex items-center gap-6 ml-6 shrink-0">
          <button
            onClick={handleRun}
            disabled={isPipelineRunning}
            className="cred-btn-primary text-xs cursor-pointer whitespace-nowrap shrink-0"
          >
            {isPipelineRunning ? (
              <>
                <Zap className="h-3.5 w-3.5 text-[#E11D48]" />
                <span>Running…</span>
              </>
            ) : (
              <>
                <Play className="h-3.5 w-3.5 fill-[#0A0A0C]" />
                <span>Run Pipeline</span>
              </>
            )}
          </button>
        </div>
      </div>
    </header>
  );
}
