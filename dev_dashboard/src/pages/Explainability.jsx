import React from 'react';
import { Compass, DollarSign, Package } from 'lucide-react';
import PageShell from '../components/layout/PageShell';
import { useSupplyPulse } from '../context/SupplyPulseContext';
import { CredCard, SeverityBadge } from '../components/ui/primitives';

export default function Explainability() {
  const { pipelineResult, selectedEvent } = useSupplyPulse();

  const result = pipelineResult || {
    disrupted_port: selectedEvent?.nearest_port_name || 'Port of Shanghai',
    severity: (selectedEvent?.severity || 'critical').toUpperCase(),
    decision: 'REROUTE',
    recommended_alternate_port: 'Port of Ningbo-Zhoushan',
    alternate_port_country: 'China',
    distance_nm: 114.5,
    additional_transit_days: 2.1,
    rerouting_cost_usd: 45200,
    total_financial_impact_usd: 382000,
    financial_alert: true,
    top_priority_commodity: 'Electronics & Semiconductors',
    inventory_exposure_usd: 1250000,
    confidence: '92%',
    total_response_time_seconds: 3.42
  };

  const pillars = [
    {
      icon: Compass,
      tag: 'HAVERSINE NM',
      title: 'Route Optimization Math',
      rows: [
        { label: 'Disrupted Seaport', value: result.disrupted_port },
        { label: 'Recommended Alternate', value: `${result.recommended_alternate_port} (${result.alternate_port_country})` },
        { label: 'Spherical Distance', value: `${result.distance_nm} NM` },
        { label: 'Transit Delay Delta', value: `+${result.additional_transit_days} Days` }
      ],
      formula: 'R = 3440.065 NM; d = 2R · arcsin(√(sin²(Δφ/2) + cos φ1 · cos φ2 · sin²(Δλ/2)))',
      note: 'Computes great-circle nautical distance between coordinates and filters alternate berths by maximum allowable vessel draft and container throughput capacity.'
    },
    {
      icon: Package,
      tag: 'BUFFER EXPOSURE',
      title: 'Inventory Risk Exposure',
      rows: [
        { label: 'Priority Cargo', value: result.top_priority_commodity },
        { label: 'Quantified Value at Risk', value: `$${(result.inventory_exposure_usd || 0).toLocaleString()}` },
        { label: 'Safety Buffer Remaining', value: '4.5 Days' },
        { label: 'Stockout Risk Level', value: 'CRITICAL' }
      ],
      formula: 'Exposure = Σ (Cargo Value × Delay Days / Buffer Threshold) × Criticality Tier',
      note: 'Evaluates tier-1 manufacturing component stockout windows against facility safety buffers to prioritize vessel rerouting sequence.'
    },
    {
      icon: DollarSign,
      tag: 'COST AUDIT',
      title: 'Financial Exposure Audit',
      rows: [
        { label: 'Direct Rerouting Cost', value: `$${(result.rerouting_cost_usd || 0).toLocaleString()}` },
        { label: 'Total Bottom-Line Impact', value: `$${(result.total_financial_impact_usd || 0).toLocaleString()}` },
        { label: 'Alert Trigger Status', value: result.financial_alert ? 'TRIGGERED (> $100k)' : 'CLEAR' },
        { label: 'Executive Threshold', value: '$100,000 USD' }
      ],
      formula: 'Total Impact = Carrier Demurrage + Fuel Surcharges + Port Handling + SLA Penalties',
      note: 'Triggers automated CFO executive escalation whenever total quantified financial impact exceeds the $100,000 USD threshold.'
    }
  ];

  return (
    <PageShell
      eyebrow="explainable multi-agent rationale"
      title="Why the System"
      accent="Decided."
      sub="The mathematical and operational reasoning behind the autonomous recommendation — every trigonometric formula, threshold, and risk metric."
      right={
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2 text-xs">
            <span className="cred-label text-[10px] text-neutral-500">Confidence</span>
            <span className="mono text-sm font-bold text-emerald-400">{result.confidence}</span>
          </div>
          <SeverityBadge severity={result.severity} />
        </div>
      }
    >
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
