import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import PageShell from '../components/layout/PageShell';
import { useSupplyPulse } from '../context/SupplyPulseContext';
import { NA, hasPlan } from '../lib/format';
import { CredCard, RunStatusBanner } from '../components/ui/primitives';

const SECTIONS = ['all', 'input_event', 'gate_state', 'routing_state', 'inventory_state', 'financial_state', 'decision_state'];

export default function StatePage() {
  const { pipelineResult, selectedEvent } = useSupplyPulse();
  const [activeSection, setActiveSection] = useState('all');

  // Every value comes from the selected event or the last real API run; missing = "—".
  const r = pipelineResult;
  const plan = hasPlan(r);
  const v = (x) => (x === null || x === undefined ? NA : x);
  const fin = r?.llm_usage ? r : null;
  const stateSchema = {
    input_event: {
      origin: v(selectedEvent?.origin),
      nearest_port_name: v(selectedEvent?.nearest_port_name),
      severity: v(selectedEvent?.severity),
      goldstein_scale: v(selectedEvent?.goldstein_scale),
      avg_tone: v(selectedEvent?.avg_tone),
      num_mentions: v(selectedEvent?.num_mentions),
      affected_routes: v(selectedEvent?.affected_routes),
      affected_commodities: v(selectedEvent?.affected_commodities),
      mutated: false
    },
    gate_state: {
      action: v(r?.signal_gate?.action),
      score: v(r?.signal_gate?.score),
      factors: v(r?.signal_gate?.factors),
      mutated: true
    },
    routing_state: {
      recommended_alternate_port: plan ? r.recommended_alternate_port : NA,
      alternate_port_country: plan ? r.alternate_port_country : NA,
      distance_nm: plan ? r.distance_nm : NA,
      travel_time_days: plan ? r.travel_time_days : NA,
      equilibrium_time_days: plan ? r.equilibrium_time_days : NA,
      allocation_method: plan ? r.allocation_method : NA,
      ship_allocation: plan ? r.ship_allocation : NA,
      mutated: true
    },
    inventory_state: {
      top_priority_commodity: plan ? r.top_priority_commodity : NA,
      inventory_exposure_usd: plan ? r.inventory_exposure_usd : NA,
      mutated: true
    },
    financial_state: {
      total_financial_impact_usd: plan ? r.total_financial_impact_usd : NA,
      rerouting_cost_usd: plan ? r.rerouting_cost_usd : NA,
      plan_weighted_delay_days: plan ? r.plan_weighted_delay_days : NA,
      financial_alert: plan ? r.financial_alert : NA,
      alert_threshold_usd: plan ? r.alert_threshold_usd : NA,
      mutated: true
    },
    decision_state: {
      status: v(r?.status),
      decision: v(r?.decision),
      agents_activated: v(r?.agents_activated),
      total_response_time_seconds: v(r?.total_response_time_seconds),
      llm_tokens_in_out: fin ? `${r.llm_usage.input_tokens} / ${r.llm_usage.output_tokens}` : NA,
      mutated: true
    }
  };

  return (
    <PageShell
      eyebrow="langgraph memory & state inspector"
      title="The Directed"
      accent="State Machine."
      sub="State values from the selected event and the last real pipeline run."
      right={
        <div className="flex flex-wrap items-center gap-6 text-xs">
          {SECTIONS.map((sec) => (
            <button
              key={sec}
              onClick={() => setActiveSection(sec)}
              className={`transition-colors cursor-pointer py-1 font-semibold tracking-wider uppercase ${
                activeSection === sec
                  ? 'text-white border-b-2 border-rose-500'
                  : 'text-neutral-500 hover:text-neutral-300'
              }`}
            >
              {sec.replace('_state', '').replace('_', ' ')}
            </button>
          ))}
        </div>
      }
    >
      <RunStatusBanner />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mb-16">
        <AnimatePresence mode="popLayout">
          {Object.entries(stateSchema).map(([key, val]) => {
            if (activeSection !== 'all' && activeSection !== key) return null;
            const fields = { ...val };
            delete fields.mutated;

            return (
              <motion.div
                key={key}
                layout
                initial={{ opacity: 0, scale: 0.98, y: 12 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.98, y: -8 }}
                transition={{ duration: 0.25 }}
              >
                <CredCard hover={false} className="h-full p-8 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between border-b border-[rgba(225,29,72,0.25)] pb-5 mb-6">
                      <span className="cred-label text-rose-400">
                        {key.replace('_', ' ')}
                      </span>
                      {val.mutated ? (
                        <span className="mono text-[11px] font-bold text-emerald-400 uppercase tracking-wider">
                          MUTATED
                        </span>
                      ) : (
                        <span className="mono text-[11px] font-bold text-neutral-500 uppercase tracking-wider">
                          READ ONLY
                        </span>
                      )}
                    </div>

                    <div className="divide-y divide-[rgba(225,29,72,0.2)]">
                      {Object.entries(fields).map(([fKey, fVal]) => (
                        <div
                          key={fKey}
                          className="flex items-center justify-between gap-4 py-3 text-xs"
                        >
                          <span className="mono text-neutral-500 truncate">
                            {fKey}:
                          </span>
                          <span className="mono font-semibold text-neutral-200 truncate max-w-[60%] text-right">
                            {typeof fVal === 'object' ? JSON.stringify(fVal) : String(fVal)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </CredCard>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </PageShell>
  );
}
