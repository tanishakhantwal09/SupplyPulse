import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowUpRight, CheckCircle2, Search } from 'lucide-react';
import PageShell from '../components/layout/PageShell';
import { useSupplyPulse } from '../context/SupplyPulseContext';
import { CredCard, SeverityBadge } from '../components/ui/primitives';

export default function Events() {
  const { scenariosList, selectedScenarioIndex, selectScenario, runPipeline } = useSupplyPulse();
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const [filterSeverity, setFilterSeverity] = useState('ALL');

  const filtered = scenariosList.filter((sc) => {
    const matchesSearch =
      sc.affected_port?.toLowerCase().includes(search.toLowerCase()) ||
      sc.disruption_type?.toLowerCase().includes(search.toLowerCase()) ||
      sc.scenario_id?.toLowerCase().includes(search.toLowerCase()) ||
      sc.country_code?.toLowerCase().includes(search.toLowerCase());
    const matchesSeverity =
      filterSeverity === 'ALL' || sc.severity?.toUpperCase() === filterSeverity;
    return matchesSearch && matchesSeverity;
  });

  return (
    <PageShell
      eyebrow="disruption signal registry"
      title="Global Disruption"
      accent="Signals."
      sub="Live GDELT telemetry, geopolitical conflicts, weather catastrophes, and maritime labor disputes across critical trade corridors."
      right={
        <div className="flex items-center gap-2">
          <span className="mono text-xs text-neutral-400 font-medium">
            Showing <b className="text-white">{filtered.length}</b> of {scenariosList.length} signals
          </span>
        </div>
      }
    >
      {/* ── 1. Search & Filter Controls ─────────────────────────────────── */}
      <section className="mb-12 flex flex-wrap items-center justify-between gap-6 border-b border-white/[0.06] pb-8">
        {/* Search Bar */}
        <div className="relative w-full max-w-md">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-neutral-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search port, country, disruption type, or scenario ID…"
            className="w-full rounded-xl bg-white/[0.03] border border-white/[0.07] pl-11 pr-5 py-3 text-xs sm:text-sm text-white placeholder:text-neutral-500 focus:border-white/[0.2] focus:outline-none transition-colors"
          />
        </div>

        {/* Severity Filter */}
        <div className="flex items-center gap-6 text-xs">
          {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((sev) => (
            <button
              key={sev}
              onClick={() => setFilterSeverity(sev)}
              className={`transition-colors cursor-pointer py-1 font-semibold tracking-wider uppercase ${
                filterSeverity === sev
                  ? 'text-white border-b-2 border-rose-500'
                  : 'text-neutral-500 hover:text-neutral-300'
              }`}
            >
              {sev}
            </button>
          ))}
        </div>
      </section>

      {/* ── 2. Signal Cards Grid ────────────────────────────────────────── */}
      <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-16">
        {filtered.slice(0, 36).map((sc, idx) => {
          const isSelected = selectedScenarioIndex === idx;

          return (
            <CredCard
              key={sc.scenario_id || idx}
              onClick={() => selectScenario(idx)}
              className={`p-7 flex flex-col justify-between min-h-[280px] ${
                isSelected
                  ? 'bg-[#15151F] border-rose-500/60 shadow-[0_0_30px_rgba(225,29,72,0.2)]'
                  : ''
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-4">
                  <span className="mono text-xs font-bold text-neutral-400">
                    {sc.scenario_id}
                  </span>
                  <SeverityBadge severity={sc.severity} />
                </div>

                <h3 className="text-xl font-bold text-white mb-1 tracking-tight">
                  {sc.affected_port}
                </h3>
                <span className="text-xs font-semibold text-rose-400 block mb-4 capitalize">
                  {sc.disruption_type?.replace(/_/g, ' ')}
                </span>

                <div className="grid grid-cols-2 gap-4 pt-4 border-t border-white/[0.06] text-xs text-neutral-400">
                  <div>
                    <span className="cred-label block text-[10px] text-neutral-500 mb-0.5">
                      Duration
                    </span>
                    <span className="mono font-bold text-white text-sm">
                      {sc.duration_hours} Hours
                    </span>
                  </div>
                  <div>
                    <span className="cred-label block text-[10px] text-neutral-500 mb-0.5">
                      Freight Surge
                    </span>
                    <span className="mono font-bold text-amber-400 text-sm">
                      +{sc.freight_impact_pct}%
                    </span>
                  </div>
                </div>
              </div>

              <div className="mt-6 pt-4 border-t border-white/[0.06] flex items-center justify-between">
                {isSelected ? (
                  <span className="flex items-center gap-1.5 text-xs font-bold text-rose-400">
                    <CheckCircle2 className="h-4 w-4" /> Active Scenario
                  </span>
                ) : (
                  <span className="text-xs text-neutral-400 hover:text-white transition-colors">
                    Click to load
                  </span>
                )}

                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    selectScenario(idx);
                    navigate('/pipeline');
                    runPipeline();
                  }}
                  className="cred-btn-primary px-4 py-1.5 text-xs font-semibold flex items-center gap-1.5"
                >
                  <span>Solve</span>
                  <ArrowUpRight className="h-3.5 w-3.5" />
                </button>
              </div>
            </CredCard>
          );
        })}
      </section>
    </PageShell>
  );
}
