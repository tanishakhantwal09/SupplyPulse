import React from 'react';
import { Compass, DollarSign, Package } from 'lucide-react';
import PageShell from '../components/layout/PageShell';
import { useSupplyPulse } from '../context/SupplyPulseContext';
import { NA, fmtUsd, hasPlan } from '../lib/format';
import { CredCard, RunStatusBanner, SeverityBadge } from '../components/ui/primitives';

export default function Explainability() {
  const { pipelineResult, selectedEvent } = useSupplyPulse();

  // Values come only from the last real run; formulas match the code.
  const r = pipelineResult;
  const plan = hasPlan(r);
  const cb = r?.cost_breakdown_usd || {};
  const v = (x) => (plan ? x : NA);

  const pillars = [
    {
      icon: Compass,
      tag: 'WARDROP EQUILIBRIUM',
      title: 'Ship Allocation Math',
      rows: [
        { label: 'Disrupted Seaport', value: r?.disrupted_port ?? selectedEvent?.nearest_port_name ?? NA },
        { label: 'Port with Most Ships', value: v(`${r?.recommended_alternate_port} (${r?.alternate_port_country})`) },
        { label: 'Great-circle Distance', value: v(`${r?.distance_nm} nm`) },
        { label: 'Equilibrium Travel Time T', value: v(`${r?.equilibrium_time_days} days`) },
        { label: 'Ports Receiving Ships', value: v((r?.ship_allocation || []).filter(a => a.vessels > 0).map(a => `${a.port} (${a.vessels})`).join(', ')) }
      ],
      formula: 't_i = s_i + p_i·(1 + 0.15·((L_i + x_i)/C_i)^4) = T at every port below the ceiling, L_i + x_i ≤ 0.95·C_i;  s_i = d_i / 400 nm/day,  d = 2R·arcsin(√(sin²(Δφ/2) + cos φ1·cos φ2·sin²(Δλ/2))), R = 3440.065 nm',
      note: 'Ships are allocated by a capacity-constrained Wardrop (1952) user equilibrium: no port is filled above 95% of capacity (ASSUMPTION, keeps the queue stable); ports below that share the same travel time T, a full port may be faster, and no unused port is faster. Ships that do not fit wait (excess demand). Port time uses the BPR function, U.S. Bureau of Public Roads (1964). s_i = sailing time, p_i = free-flow port time (1.0 day, ASSUMPTION), L_i = ships already at the port per day, C_i = daily capacity (ASSUMPTION, not yet calibrated), x_i = diverted ships per day. Open-ocean bypass routes have no port time. The 0.40 risk + 0.35 time + 0.25 cost score is shown for comparison only and is not used for allocation.'
    },
    {
      icon: Package,
      tag: 'COMMODITY EXPOSURE',
      title: 'Inventory Exposure',
      rows: [
        { label: 'Priority Cargo', value: v(r?.top_priority_commodity) },
        { label: 'Exposure Value', value: v(fmtUsd(r?.inventory_exposure_usd)) },
        { label: 'Unmatched Commodity Terms', value: v((r?.unmatched_commodities || []).join(', ') || 'none') }
      ],
      formula: 'Exposure = vessels × containers_per_vessel(severity) × sensitivity_share × value_per_container',
      note: 'containers_per_vessel and sensitivity_share are assumptions without a source yet; value_per_container comes from commodities.json.'
    },
    {
      icon: DollarSign,
      tag: 'COST AUDIT',
      title: 'Financial Impact',
      rows: [
        { label: 'Rerouting', value: v(fmtUsd(cb.rerouting_cost)) },
        { label: 'Trade Delay', value: v(fmtUsd(cb.delay_cost)) },
        { label: 'Freight Increase', value: v(fmtUsd(cb.freight_rate_increase)) },
        { label: 'Inventory at Risk', value: v(fmtUsd(cb.inventory_at_risk)) },
        { label: 'Operating Cost', value: v(fmtUsd(cb.operational_cost)) },
        { label: 'EU ETS Carbon', value: v(fmtUsd(cb.carbon_penalty)) },
        { label: 'Total', value: v(fmtUsd(r?.total_financial_impact_usd)) },
        { label: 'Single-port options', value: v((r?.single_port_options || []).map(o => `${o.port}: ${o.option} (${o.safety_label})`).join('; ') || 'none') },
        { label: 'Alert', value: v(`${r?.financial_alert ? 'TRIGGERED' : 'not triggered'} (threshold ${fmtUsd(r?.alert_threshold_usd)})`) }
      ],
      formula: 'Total = C_reroute + C_delay + C_freight + C_inventory + C_operational + C_carbon(EU ETS)',
      note: 'EU ETS coverage and phase-in follow Directive (EU) 2023/959. Daily trade value, inventory share, operating cost and alert thresholds are assumptions.'
    }
  ];

  return (
    <PageShell
      eyebrow="explainable multi-agent rationale"
      title="Why the System"
      accent="Decided."
      sub="The formulas the code uses, with the values from the last run. Constants without a source are marked as assumptions."
      right={
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2 text-xs">
            <span className="cred-label text-[10px] text-neutral-500">Signal gate</span>
            <span className="mono text-sm font-bold text-emerald-400">{r?.signal_gate ? `${r.signal_gate.action} ${r.signal_gate.score ?? ''}` : NA}</span>
          </div>
          {r?.severity && <SeverityBadge severity={r.severity} />}
        </div>
      }
    >
      <RunStatusBanner />
      {/* ── 1. Explainable Decision Matrix ───────────────────────────────── */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-16">
        {pillars.map((p) => (
          <CredCard key={p.title} elevated hover={false} className="p-8 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between border-b border-[rgba(225,29,72,0.25)] pb-5 mb-6">
                <div className="flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center bg-[rgba(225,29,72,0.12)] border border-[rgba(225,29,72,0.35)] text-[#E11D48]">
                    <p.icon className="h-4.5 w-4.5" />
                  </div>
                  <h3 className="text-base font-bold text-white tracking-tight">{p.title}</h3>
                </div>
                <span className="mono text-[10px] font-semibold text-neutral-500">
                  {p.tag}
                </span>
              </div>

              {/* Rows (Clean Dividers, No Nested Inset Boxes) */}
              <div className="divide-y divide-[rgba(225,29,72,0.2)] mb-6">
                {p.rows.map((row) => (
                  <div key={row.label} className="flex items-center justify-between gap-3 py-2.5 text-xs">
                    <span className="cred-label text-[10px] text-neutral-500">{row.label}</span>
                    <span className="mono font-semibold text-neutral-200 truncate max-w-[55%] text-right">
                      {row.value}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Formula & Explanatory Note */}
            <div className="mt-4 pt-4 border-t border-[rgba(225,29,72,0.25)] space-y-3">
              <div className="mono text-[11px] text-[#E11D48] overflow-x-auto bg-black/40 p-3 border border-[rgba(225,29,72,0.2)]">
                {p.formula}
              </div>
              <p className="text-xs text-neutral-400 leading-relaxed">
                {p.note}
              </p>
            </div>
          </CredCard>
        ))}
      </section>
    </PageShell>
  );
}
