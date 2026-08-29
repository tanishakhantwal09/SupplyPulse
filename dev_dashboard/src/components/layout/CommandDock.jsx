import React from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowRight, Crosshair, Play, Zap } from 'lucide-react';
import { useSupplyPulse } from '../../context/SupplyPulseContext';
import { SeverityBadge } from '../ui/primitives';

export default function CommandDock() {
  const { selectedEvent, pipelineResult, isPipelineRunning, runPipeline } = useSupplyPulse();
  const navigate = useNavigate();

  const handleRun = () => {
    navigate('/pipeline');
    runPipeline();
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ y: 70, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.5, type: 'spring', stiffness: 220, damping: 26 }}
        className="pointer-events-auto fixed bottom-5 left-1/2 z-40 w-[calc(100%-24px)] max-w-2xl -translate-x-1/2 md:bottom-7"
      >
        <div className="glass-deep glass flex items-center justify-between gap-4 rounded-[26px] px-5 py-4">
          <div className="flex min-w-0 items-center gap-3.5">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-crimson to-blood text-white shadow-[0_10px_28px_-8px_rgba(225,29,72,0.6)]">
              <Crosshair className="h-4.5 w-4.5" />
            </div>
            <div className="min-w-0 leading-tight">
              <div className="truncate text-[14px] font-semibold tracking-tight text-ink">{selectedEvent?.nearest_port_name || 'no target'}</div>
              <div className="mono mt-0.5 truncate text-[9.5px] tracking-wide text-ash">
                {pipelineResult?.decision || 'pending'} → {pipelineResult?.recommended_alternate_port || '—'} · ${(pipelineResult?.rerouting_cost_usd || 0).toLocaleString()}
              </div>
            </div>
            <SeverityBadge severity={selectedEvent?.severity} className="hidden sm:inline-flex" />
          </div>

          <button
            onClick={handleRun}
            disabled={isPipelineRunning}
            className="btn-white flex shrink-0 items-center gap-2.5 rounded-full px-6 py-3 text-[13px] font-semibold tracking-tight"
          >
            {isPipelineRunning
              ? <><Zap className="h-4 w-4" /><span className="hidden sm:inline">executing…</span></>
              : <><Play className="h-4 w-4" fill="currentColor" /><span className="hidden sm:inline">execute</span><ArrowRight className="h-4 w-4 sm:hidden" /></>}
          </button>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
