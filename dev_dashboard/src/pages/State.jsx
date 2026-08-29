import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import PageShell from '../components/layout/PageShell';
import { useSupplyPulse } from '../context/SupplyPulseContext';
import { CredCard } from '../components/ui/primitives';

const SECTIONS = ['all', 'input_event', 'routing_state', 'inventory_state', 'financial_state', 'decision_state'];

export default function StatePage() {
  const { pipelineResult, selectedEvent } = useSupplyPulse();
  const [activeSection, setActiveSection] = useState('all');

  const stateSchema = {
    input_event: {
      nearest_port_name: selectedEvent?.nearest_port_name || 'Port of Shanghai',
      severity: selectedEvent?.severity || 'critical',
      goldstein_scale: selectedEvent?.goldstein_scale || -6.2,
      avg_tone: selectedEvent?.avg_tone || -4.5,
      affected_routes: selectedEvent?.alternative_routes || ['R01', 'R05'],
      affected_commodities: selectedEvent?.affected_commodities || ['Electronics & Semiconductors'],
      mutated: false
    },
    routing_state: {
      recommended_alternate_port: pipelineResult?.recommended_alternate_port || 'Port of Ningbo-Zhoushan',
      alternate_port_country: pipelineResult?.alternate_port_country || 'China',
      distance_nm: pipelineResult?.distance_nm || 114.5,
      additional_transit_days: pipelineResult?.additional_transit_days || 2.1,
      rerouting_cost_usd: pipelineResult?.rerouting_cost_usd || 45200,
      mutated: true
    },
    inventory_state: {
      top_priority_commodity: pipelineResult?.top_priority_commodity || 'Electronics & Semiconductors',
      inventory_exposure_usd: pipelineResult?.inventory_exposure_usd || 1250000,
      safety_buffer_days: 4.5,
      stockout_risk: 'CRITICAL',
      mutated: true
    },
    financial_state: {
      total_financial_impact_usd: pipelineResult?.total_financial_impact_usd || 382000,
      financial_alert: pipelineResult?.financial_alert ?? true,
      demurrage_usd: 85000,
      fuel_surcharges_usd: 24500,
      mutated: true
    },
    decision_state: {
      decision: pipelineResult?.decision || 'REROUTE',
      confidence: pipelineResult?.confidence || '92%',
      agents_activated: pipelineResult?.agents_activated || ['supervisor', 'route_optimization', 'inventory', 'financial_auditor', 'supervisor_final'],
      total_response_time_seconds: pipelineResult?.total_response_time_seconds || 3.42,
      mutated: true
    }
  };

  return (
    <PageShell
      eyebrow="langgraph memory & state inspector"
      title="The Directed"
      accent="State Machine."
      sub="Live immutable and mutated state attributes flowing across the LangGraph multi-agent execution channels."
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
