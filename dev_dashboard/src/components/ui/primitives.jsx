import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Check, Copy } from 'lucide-react';

/* ── CountUp Numeric Animator ────────────────────────────────────────────── */
export function CountUp({ value, decimals = 0, prefix = '', suffix = '' }) {
  const num = typeof value === 'number' ? value : parseFloat(value) || 0;
  const [display, setDisplay] = useState(num);

  useEffect(() => {
    let start = 0;
    const duration = 850;
    const startTime = performance.now();

    const frame = (now) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const ease = 1 - Math.pow(1 - progress, 3);
      const current = start + (num - start) * ease;
      setDisplay(current);

      if (progress < 1) {
        requestAnimationFrame(frame);
      } else {
        setDisplay(num);
      }
    };

    requestAnimationFrame(frame);
  }, [num]);

  const formatted = decimals > 0
    ? display.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
    : Math.round(display).toLocaleString('en-US');

  return (
    <span>
      {prefix}{formatted}{suffix}
    </span>
  );
}

/* ── CRED Luxury Slab / Card ─────────────────────────────────────────────── */
export function CredCard({
  children,
  className = '',
  hover = true,
  elevated = false,
  crimson = false,
  onClick
}) {
  const baseClass = crimson
    ? 'cred-slab-crimson'
    : elevated
    ? 'cred-slab-elevated'
    : 'cred-slab';

  const hoverClass = hover ? 'cred-slab-hover cursor-pointer' : '';

  return (
    <div
      onClick={onClick}
      className={`relative overflow-hidden ${baseClass} ${hoverClass} ${className}`}
    >
      {children}
    </div>
  );
}

// Alias for backward compatibility across legacy imports
export const Panel = CredCard;

/* ── Severity & Status Badges (Tasteful & Minimal Typography) ──────────────── */
export function SeverityBadge({ severity, className = '' }) {
  const s = (severity || 'NORMAL').toUpperCase();

  const colors = {
    CRITICAL: 'text-rose-400',
    HIGH: 'text-amber-400',
    MEDIUM: 'text-sky-400',
    LOW: 'text-emerald-400'
  };

  const textColor = colors[s] || 'text-neutral-400';

  return (
    <span
      className={`inline-flex items-center text-[11px] font-bold tracking-wider uppercase ${textColor} ${className}`}
    >
      {s}
    </span>
  );
}

/* ── Hero Metric Display ─────────────────────────────────────────────────── */
export function CredHeroStat({
  label,
  value,
  prefix = '',
  suffix = '',
  decimals = 0,
  sublabel,
  trend,
  className = ''
}) {
  return (
    <div className={`flex flex-col ${className}`}>
      {label && <span className="cred-label mb-2.5">{label}</span>}
      <div className="cred-hero text-4xl sm:text-5xl md:text-6xl font-bold tracking-tight text-white mono">
        <CountUp value={value} decimals={decimals} prefix={prefix} suffix={suffix} />
      </div>
      {(sublabel || trend) && (
        <div className="mt-3.5 flex items-center gap-2.5 text-xs text-neutral-400">
          {trend && <span className="text-emerald-400 font-semibold">{trend}</span>}
          {sublabel && <span>{sublabel}</span>}
        </div>
      )}
    </div>
  );
}

/* ── KPI Stat Card ───────────────────────────────────────────────────────── */
export function CredStat({
  label,
  value,
  prefix = '',
  suffix = '',
  decimals = 0,
  sublabel,
  icon: Icon,
  className = ''
}) {
  return (
    <CredCard elevated hover={false} className={`p-6 sm:p-7 flex flex-col justify-between ${className}`}>
      <div className="flex items-center justify-between">
        <span className="cred-label">{label}</span>
        {Icon && <Icon className="h-4 w-4 text-neutral-500" />}
      </div>
      <div className="mono mt-5 text-2xl sm:text-3xl font-bold tracking-tight text-white">
        <CountUp value={value} decimals={decimals} prefix={prefix} suffix={suffix} />
      </div>
      {sublabel && <span className="mt-2 text-xs text-neutral-400">{sublabel}</span>}
    </CredCard>
  );
}

/* ── Liquid Pill Segmented Control / Tabs ────────────────────────────────── */
export function CredSegmentedTabs({ tabs, activeTab, onChange, className = '' }) {
  return (
    <div className={`inline-flex items-center gap-1.5 rounded-full bg-[#0E0E13] p-1.5 border border-white/[0.08] shadow-inner ${className}`}>
      {tabs.map((tab) => {
        const active = activeTab === tab.id;
        const Icon = tab.icon;
        return (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className={`relative flex items-center gap-2 rounded-full px-5 py-2.5 text-xs font-semibold tracking-tight transition-colors duration-200 cursor-pointer ${
              active ? 'text-white' : 'text-neutral-400 hover:text-neutral-200'
            }`}
          >
            {active && (
              <motion.span
                layoutId="cred-active-tab-pill"
                transition={{ type: 'spring', stiffness: 450, damping: 35 }}
                className="absolute inset-0 rounded-full bg-white/[0.12] border border-white/[0.15] shadow-sm"
              />
            )}
            {Icon && <Icon className={`relative z-10 h-3.5 w-3.5 ${active ? 'text-rose-400' : ''}`} />}
            <span className="relative z-10">{tab.label}</span>
            {tab.count !== undefined && (
              <span className="mono relative z-10 text-[10px] text-neutral-400 font-normal">
                ({tab.count})
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

/* ── Luxury JSON & State Code Viewer ─────────────────────────────────────── */
export function JsonBlock({ data, title = '', maxH = 'max-h-[380px]' }) {
  const [copied, setCopied] = useState(false);
  const jsonStr = typeof data === 'string' ? data : JSON.stringify(data, null, 2);

  const handleCopy = () => {
    navigator.clipboard.writeText(jsonStr);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  return (
    <div className="overflow-hidden rounded-2xl border border-white/[0.08] bg-[#0A0A0E] shadow-2xl">
      {title && (
        <div className="flex items-center justify-between border-b border-white/[0.06] bg-white/[0.02] px-5 py-3">
          <span className="mono text-[11px] font-semibold tracking-wider uppercase text-neutral-400">{title}</span>
          <button
            onClick={handleCopy}
            className="flex items-center gap-1.5 rounded-lg px-2.5 py-1 text-[11px] font-medium text-neutral-400 hover:bg-white/[0.08] hover:text-white transition-colors cursor-pointer"
          >
            {copied ? (
              <>
                <Check className="h-3.5 w-3.5 text-emerald-400" />
                <span className="text-emerald-400">Copied</span>
              </>
            ) : (
              <>
                <Copy className="h-3.5 w-3.5" />
                <span>Copy</span>
              </>
            )}
          </button>
        </div>
      )}
      <pre className={`mono overflow-auto p-5 text-[12px] leading-relaxed text-neutral-300 ${maxH}`}>
        <code>{jsonStr}</code>
      </pre>
    </div>
  );
}

/* ── Motion & Animation Wrappers ─────────────────────────────────────────── */
export function RiseItem({ children, className = '', delay = 0 }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, delay, ease: [0.16, 1, 0.3, 1] }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

export function StaggerGrid({ children, className = '' }) {
  return <div className={className}>{children}</div>;
}
