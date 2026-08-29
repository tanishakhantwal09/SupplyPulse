import React, { useEffect, useRef, useState } from 'react';
import { Check, Copy } from 'lucide-react';
import PageShell from '../components/layout/PageShell';
import { useSupplyPulse } from '../context/SupplyPulseContext';
import { CredCard } from '../components/ui/primitives';

const LOG_COLOR = (log) => {
  if (log.includes('[ERROR')) return 'text-rose-400 font-semibold';
  if (log.includes('[SUCCESS') || log.includes('[FINAL')) return 'text-emerald-400 font-semibold';
  if (log.includes('[EVENT')) return 'text-amber-400 font-semibold';
  if (log.includes('[PIPELINE')) return 'text-rose-400';
  if (log.includes('[AGENT')) return 'text-sky-400';
  if (log.includes('[GDELT')) return 'text-rose-400';
  if (log.includes('[SIMULATION')) return 'text-amber-400';
  return 'text-neutral-300';
};

export default function Logs() {
  const { terminalLogs, serverStatus } = useSupplyPulse();
  const isOnline = serverStatus === 'online';
  const [copied, setCopied] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [terminalLogs]);

  const handleCopy = () => {
    navigator.clipboard.writeText(terminalLogs.join('\n'));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <PageShell
      eyebrow="system stdout & observability"
      title="Engine Execution"
      accent="Stdout."
      sub="Live streaming terminal logs from the Python API backend, LangGraph state machine, and multi-agent consensus nodes."
      right={
        <button
          onClick={handleCopy}
          className="cred-btn-secondary text-xs"
        >
          {copied ? (
            <>
              <Check className="h-3.5 w-3.5 text-emerald-400" />
              <span className="text-emerald-400">Copied to Clipboard</span>
            </>
          ) : (
            <>
              <Copy className="h-3.5 w-3.5" />
              <span>Copy All Logs</span>
            </>
          )}
        </button>
      }
    >
      <section className="mb-16">
        <CredCard elevated hover={false} className="p-0 overflow-hidden">
          {/* Terminal Window Header */}
          <div className="flex items-center justify-between border-b border-[rgba(225,29,72,0.3)] bg-[#0A0A0E] px-6 py-4">
            <div className="flex items-center gap-3">
              <span className="mono text-xs font-semibold text-neutral-300">
                supplypulse@langgraph — session_stream.log
              </span>
              <span className={`mono text-[10px] font-bold px-2 py-0.5 tracking-wider uppercase border ${
                isOnline
                  ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400'
                  : 'border-neutral-700 bg-neutral-900 text-neutral-400'
              }`}>
                {isOnline ? 'ONLINE' : 'OFFLINE'}
              </span>
            </div>
            <span className="mono text-xs text-neutral-500 font-medium">
              {terminalLogs.length} events logged
            </span>
          </div>

          {/* Terminal Content */}
          <div data-lenis-prevent className="mono h-[58vh] overflow-y-auto bg-[#07070A] p-6 text-xs leading-relaxed">
            {terminalLogs.map((log, idx) => (
              <div
                key={idx}
                className={`flex gap-4 px-3 py-1 hover:bg-white/[0.03] transition-colors ${LOG_COLOR(log)}`}
              >
                <span className="w-8 shrink-0 select-none text-right text-neutral-600 font-normal">
                  {idx + 1}
                </span>
                <span className="break-all">{log}</span>
              </div>
            ))}
            <div ref={endRef} />
          </div>
        </CredCard>
      </section>
    </PageShell>
  );
}
