import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowDownRight, Check } from 'lucide-react';
import { scrollToEl } from '../lib/smoothScroll';
import './landing.css';

const EASE = [0.16, 1, 0.3, 1];

function Reveal({ children, y = 48, delay = 0, className = '' }) {
  return (
    <motion.div
      className={`pl-reveal ${className}`}
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-80px' }}
      transition={{ duration: 0.9, ease: EASE, delay }}
    >
      {children}
    </motion.div>
  );
}

function LeftBracket() {
  return (
    <svg width="6" height="26" viewBox="0 0 4.576 24.64" aria-hidden="true">
      <path
        d="M 4.576 0 L 4.576 2.068 L 2.354 2.068 L 2.354 22.55 L 4.576 22.55 L 4.576 24.64 L 0 24.64 L 0 0 Z"
        fill="currentColor"
      />
    </svg>
  );
}

function RightBracket() {
  return (
    <svg width="6" height="26" viewBox="0 0 4.576 24.64" aria-hidden="true">
      <path
        d="M 4.576 24.64 L 0 24.64 L 0 22.55 L 2.222 22.55 L 2.222 2.068 L 0 2.068 L 0 0 L 4.576 0 Z"
        fill="currentColor"
      />
    </svg>
  );
}

function BracketCTA({ to, children, className = '' }) {
  return (
    <Link to={to} className={`pl-bracket relative ${className}`}>
      <LeftBracket />
      <span className="pl-label text-lg md:text-[22px] leading-[26px] font-medium tracking-wide">
        {children}
      </span>
      <RightBracket />
      <span className="pl-bracket-line" aria-hidden="true" />
    </Link>
  );
}

function Star({ className = '' }) {
  return (
    <svg viewBox="0 0 80 80" className={className} aria-hidden="true">
      <path
        transform="translate(40 40)"
        d="M40,0 L12.93,5.36 L28.28,28.28 L5.36,12.93 L0,40 L-5.36,12.93 L-28.28,28.28 L-12.93,5.36 L-40,0 L-12.93,-5.36 L-28.28,-28.28 L-5.36,-12.93 L0,-40 L5.36,-12.93 L28.28,-28.28 L12.93,-5.36 Z"
        fill="#E11D48"
      />
    </svg>
  );
}

function Triangle() {
  return (
    <svg width="52" height="34" viewBox="0 0 80 50" aria-hidden="true">
      <path d="M 68.084 39.851 L 0 39.851 L 34.042 0 Z" fill="#E11D48" />
    </svg>
  );
}

function Header() {
  return (
    <header className="fixed inset-x-0 top-0 z-50 border-b border-white/[0.06] bg-[#0a0a0c]/90 backdrop-blur-xl">
      <div className="mx-auto flex h-[84px] w-full max-w-[1440px] items-center justify-between px-6 lg:px-12">
        <Link to="/" className="group flex items-center gap-4" aria-label="SupplyPulse home">
          <span className="flex flex-col items-end gap-[7px]">
            <span className="flex items-center gap-[5px]">
              <span className="h-[5px] w-[5px] rounded-full bg-[#E11D48]" />
              <span className="h-[2px] w-4 bg-[#F1EFF5]" />
            </span>
            <span className="h-[2px] w-7 bg-[#F1EFF5]" />
          </span>
          <span className="flex items-end">
            <span className="pl-display text-2xl font-medium tracking-[-0.02em] normal-case text-[#F1EFF5] transition-colors group-hover:text-white">
              supplypulse
            </span>
            <span className="mb-[3px] ml-[3px] h-2 w-2 rounded-full bg-[#E11D48]" />
          </span>
        </Link>

        <Link to="/app" className="pl-link pl-label text-sm font-semibold tracking-[0.14em] text-[#F1EFF5]">
          Dashboard
          <ArrowDownRight className="h-4 w-4 text-[#E11D48]" strokeWidth={2.4} />
          <span className="pl-link-line" aria-hidden="true" />
        </Link>
      </div>
    </header>
  );
}

function Hero() {
  return (
    <section id="top" className="flex flex-col items-center gap-12 px-6 pb-28 pt-[176px] lg:gap-[54px] lg:pb-[160px] lg:pt-[210px]">
      <Reveal y={56}>
        <h1 className="pl-display uppercase max-w-[980px] text-center text-[42px] leading-[1.04] md:text-[64px] lg:text-[74px]">
          Disruption detected.
          <br />
          <span className="pl-serif text-[1.06em] font-medium lowercase tracking-normal">
            resolved
          </span>{' '}
          in seconds.
        </h1>
      </Reveal>

      <Star className="pl-spin h-16 w-16 lg:h-20 lg:w-20" />

      <Reveal y={40} delay={0.08}>
        <h3 className="pl-label max-w-[860px] text-center text-base leading-relaxed font-medium md:text-2xl md:leading-[36px]">
          An autonomous multi-agent crew that detects disruption, reroutes freight and quantifies
          the damage <span className="text-[#E11D48]">before it reaches your bottom line.</span>
        </h3>
      </Reveal>

      <Reveal y={40} delay={0.14} className="w-full">
        <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-4 md:gap-x-9">
          {['Data first', 'Business driven', 'Agent native'].map((item, i) => (
            <React.Fragment key={item}>
              {i > 0 && <span className="hidden text-neutral-600 md:inline font-light text-xl select-none">/</span>}
              <span className="pl-label text-sm font-medium uppercase tracking-wide text-[#E11D48] md:text-2xl">
                {item}
              </span>
            </React.Fragment>
          ))}
        </div>
      </Reveal>

      <Reveal y={40} delay={0.2}>
        <BracketCTA to="/app">Launch Dashboard</BracketCTA>
      </Reveal>
    </section>
  );
}

const AGENTS = [
  { id: '01', name: 'Supervisor', role: 'Triage & task delegation' },
  { id: '02', name: 'Route Optimization', role: 'Maritime reroute' },
  { id: '03', name: 'Inventory', role: 'Exposure audit' },
  { id: '04', name: 'Financial Auditor', role: 'Impact model' },
  { id: '05', name: 'Decision', role: 'Final verdict' }
];

function ConsoleMock() {
  const [active, setActive] = useState(1);

  useEffect(() => {
    const t = setInterval(() => setActive((a) => (a + 1) % AGENTS.length), 1500);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="overflow-hidden rounded-lg border border-white/[0.07] bg-[#0c0c10]">
      <div className="flex items-center justify-between border-b border-white/[0.07] px-5 py-3.5">
        <div className="flex items-center gap-3">
          <span className="pl-pulse h-2 w-2 rounded-full bg-[#E11D48]" />
          <span className="pl-mono text-[11px] tracking-[0.14em] text-neutral-300">
            SUPPLYPULSE // LIVE SIMULATION
          </span>
        </div>
        <span className="pl-mono hidden text-[11px] tracking-[0.14em] text-neutral-500 sm:block">
          PORT OF SHANGHAI · SEV CRITICAL
        </span>
      </div>

      <div className="divide-y divide-white/[0.05]">
        {AGENTS.map((agent, i) => {
          const done = i < active;
          const running = i === active;
          return (
            <div key={agent.id} className="flex items-center gap-4 px-5 py-3.5">
              <span
                className={`pl-mono w-6 text-[11px] ${
                  running ? 'text-[#E11D48]' : done ? 'text-neutral-500' : 'text-neutral-700'
                }`}
              >
                {agent.id}
              </span>
              <span
                className={`h-2 w-2 flex-none rounded-full ${
                  running ? 'pl-pulse bg-[#E11D48]' : done ? 'bg-[#F1EFF5]' : 'bg-neutral-700'
                }`}
              />
              <div className="min-w-0 flex-1">
                <p
                  className={`pl-label truncate text-[13px] font-medium tracking-wide ${
                    running ? 'text-white' : done ? 'text-neutral-300' : 'text-neutral-600'
                  }`}
                >
                  {agent.name}
                </p>
                <p className="pl-mono truncate text-[10px] tracking-[0.08em] text-neutral-600">
                  {agent.role}
                </p>
              </div>
              <span
                className={`pl-mono w-20 flex-none text-right text-[10px] tracking-[0.14em] ${
                  running ? 'text-[#E11D48]' : done ? 'text-neutral-500' : 'text-neutral-700'
                }`}
              >
                {running ? 'RUNNING' : done ? 'COMPLETE' : 'QUEUED'}
              </span>
            </div>
          );
        })}
      </div>

      <div className="border-t border-white/[0.07] px-5 py-3">
        <div className="h-[3px] w-full overflow-hidden rounded-full bg-white/[0.05]">
          <div className="pl-shimmer h-full w-full" />
        </div>
      </div>
    </div>
  );
}

function ScrollCircle() {
  const scrollToWork = () => {
    scrollToEl(document.getElementById('what-we-do'), -40);
  };
  return (
    <button
      type="button"
      onClick={scrollToWork}
      className="group relative flex h-[132px] w-[132px] flex-none cursor-pointer flex-col items-center justify-between py-4 lg:h-[140px] lg:w-[140px]"
      aria-label="Scroll to what we do"
    >
      <svg viewBox="0 0 140 140" className="pl-spin-fast absolute inset-0 h-full w-full" aria-hidden="true">
        <circle
          cx="70"
          cy="70"
          r="66"
          fill="none"
          stroke="#F1EFF5"
          strokeWidth="1.5"
          strokeDasharray="2 8"
          strokeLinecap="round"
        />
      </svg>
      <ArrowDownRight
        className="h-6 w-6 text-[#F1EFF5] transition-transform duration-300 group-hover:translate-y-1"
        strokeWidth={1.8}
      />
      <span className="pl-display uppercase text-[11px] font-medium tracking-[0.08em] text-[#F1EFF5]">
        Time to scroll
      </span>
    </button>
  );
}

function Showcase() {
  return (
    <section className="relative mx-auto w-full max-w-[1440px] px-4 pb-28 lg:px-16 lg:pb-[180px]">
      <div className="absolute right-[6%] top-0 bottom-0 hidden w-[6px] flex-col items-center xl:flex">
        <span
          className="w-px flex-1"
          style={{ background: 'linear-gradient(180deg, rgba(225,29,72,0.5) 0%, rgba(225,29,72,0.04) 100%)' }}
        />
      </div>

      <div className="relative border-y border-[rgba(225,29,72,0.3)]">
        <div className="absolute right-6 top-4 flex gap-1 lg:right-10">
          <Triangle />
          <Triangle />
        </div>

        <div className="px-4 py-10 lg:px-16 lg:py-14">
          <Reveal y={64}>
            <ConsoleMock />
          </Reveal>
        </div>
      </div>

      <div className="mt-10 flex flex-col items-start gap-10 lg:mt-14 lg:flex-row lg:items-end lg:justify-between">
        <div className="flex max-w-[640px] flex-col gap-9">
          <Reveal y={40}>
            <h3 className="pl-label text-2xl font-bold leading-tight md:text-[36px] md:leading-[1.2]">
              See how SupplyPulse can power your supply chain
            </h3>
          </Reveal>
          <Reveal y={40} delay={0.08}>
            <BracketCTA to="/app">Open Dashboard</BracketCTA>
          </Reveal>
        </div>
        <Reveal y={40} delay={0.12}>
          <ScrollCircle />
        </Reveal>
      </div>
    </section>
  );
}

function NetworkFigure() {
  return (
    <svg viewBox="0 0 220 220" className="h-[220px] w-[220px]" aria-hidden="true">
      <g stroke="#E11D48" fill="none" strokeWidth="0.8">
        <path d="M110 30 L190 110 L110 190 L30 110 Z" strokeDasharray="3 4" />
        <path d="M110 30 L110 190 M30 110 L190 110" strokeDasharray="3 4" />
        <path d="M60 60 L160 160 M160 60 L60 160" strokeDasharray="1 5" opacity="0.6" />
        <circle cx="110" cy="110" r="14" />
        <circle cx="110" cy="30" r="4" fill="#E11D48" stroke="none" />
        <circle cx="190" cy="110" r="4" fill="#E11D48" stroke="none" />
        <circle cx="110" cy="190" r="4" fill="#E11D48" stroke="none" />
        <circle cx="30" cy="110" r="4" fill="#E11D48" stroke="none" />
      </g>
    </svg>
  );
}

function WhatWeDo() {
  return (
    <section id="what-we-do" className="scroll-mt-24" data-cursor-label="What we do">
      <div className="border-y border-[rgba(225,29,72,0.3)]">
        <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-3 px-6 py-9 lg:flex-row lg:items-end lg:justify-between lg:px-24">
          <h2 className="pl-display uppercase text-[34px] leading-tight md:text-[56px]">What we do</h2>
          <h5 className="pl-label text-sm font-medium tracking-wide text-neutral-300 md:text-2xl">
            Ditch the silos. Unify your supply chain.
          </h5>
        </div>
      </div>

      <div className="mx-auto grid w-full max-w-[1440px] grid-cols-1 lg:grid-cols-[40%_60%]">
        <div className="hidden items-center justify-center border-r border-[rgba(225,29,72,0.3)] py-24 lg:flex">
          <NetworkFigure />
        </div>

        <div className="flex flex-col gap-10 px-6 py-16 lg:px-28 lg:py-40">
          <Reveal y={40}>
            <p className="pl-label max-w-[560px] text-sm leading-relaxed normal-case tracking-normal text-neutral-400 md:text-base md:leading-[1.6]">
              Disruption doesn't wait for the morning report. SupplyPulse continuously ingests
              global event signals and turns raw noise into one quantified picture of operational
              risk.
            </p>
          </Reveal>
          <Reveal y={40}>
            <p className="pl-label max-w-[560px] text-sm leading-relaxed normal-case tracking-normal text-white md:text-base md:leading-[1.6]">
              The moment an event hits, five specialist agents — Supervisor, Route, Inventory,
              Financial and Decision — reach consensus in seconds: where to reroute, what it costs,
              and what to protect first.
            </p>
          </Reveal>
          <Reveal y={40}>
            <p className="pl-label max-w-[560px] text-sm leading-relaxed normal-case tracking-normal text-neutral-400 md:text-base md:leading-[1.6]">
              No black boxes. Every assessment is fully traceable — inputs, prompts, reasoning and
              state — so your team always stays in control.
            </p>
          </Reveal>
          <Reveal y={40} className="flex justify-end">
            <BracketCTA to="/pipeline">The Pipeline</BracketCTA>
          </Reveal>
        </div>
      </div>
    </section>
  );
}

function RouteVisual() {
  return (
    <div className="relative aspect-[16/9] w-full overflow-hidden rounded-lg border border-white/[0.07] bg-[#0c0c10]">
      <svg viewBox="0 0 640 360" className="absolute inset-0 h-full w-full" aria-hidden="true">
        <g stroke="rgba(241,239,245,0.07)" strokeWidth="1">
          {[...Array(9)].map((_, i) => (
            <line key={`v${i}`} x1={i * 80} y1="0" x2={i * 80} y2="360" />
          ))}
          {[...Array(5)].map((_, i) => (
            <line key={`h${i}`} x1="0" y1={i * 90} x2="640" y2={i * 90} />
          ))}
        </g>
        <path
          d="M90 280 C 200 140, 320 300, 430 160 S 560 90, 575 80"
          fill="none"
          stroke="#E11D48"
          strokeWidth="2"
          strokeDasharray="6 6"
        />
        <circle cx="90" cy="280" r="7" fill="#F1EFF5" />
        <circle cx="430" cy="160" r="7" fill="#E11D48" />
        <circle cx="575" cy="80" r="7" fill="#E11D48" />
      </svg>
      <div className="absolute left-4 top-4 flex items-center gap-2.5">
        <span className="pl-mono text-[10px] tracking-[0.16em] text-neutral-400">
          REROUTE // SHANGHAI → NINGBO-ZHOUSHAN
        </span>
      </div>
      <span className="pl-mono absolute bottom-4 right-4 text-[10px] tracking-[0.16em] text-neutral-500">
        +2 DAYS TRANSIT · GEODESIC PATH
      </span>
    </div>
  );
}

function LedgerVisual() {
  return (
    <div className="relative aspect-[16/9] w-full overflow-hidden rounded-lg border border-white/[0.07] bg-[#0c0c10]">
      <div className="absolute inset-0 flex items-end justify-between gap-3 px-8 pb-10 pt-8">
        {[38, 55, 30, 72, 48, 88, 64, 100].map((h, i) => (
          <div key={i} className="flex flex-1 flex-col justify-end gap-2">
            <div
              className={`w-full rounded-t-sm ${i === 7 ? 'bg-[#E11D48]' : 'bg-[rgba(225,29,72,0.28)]'}`}
              style={{ height: `${h}%` }}
            />
          </div>
        ))}
      </div>
      <span
        className="absolute inset-x-8 bottom-9 h-px"
        style={{ background: 'rgba(241,239,245,0.12)' }}
      />
      <div className="absolute left-4 top-4 flex items-center gap-2.5">
        <span className="pl-mono text-[10px] tracking-[0.16em] text-neutral-400">
          FINANCIAL AUDIT // FREIGHT SURGE + DEMURRAGE
        </span>
      </div>
      <span className="pl-mono absolute bottom-4 right-4 text-[10px] tracking-[0.16em] text-[#E11D48]">
        PEAK EXPOSURE
      </span>
    </div>
  );
}

function Value() {
  return (
    <section>
      <div className="border-b border-[rgba(225,29,72,0.3)]">
        <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-3 px-6 py-9 lg:flex-row-reverse lg:items-end lg:justify-between lg:px-24">
          <h2 className="pl-display uppercase text-[34px] leading-tight md:text-[56px]">
            Creating value today
          </h2>
          <h5 className="pl-label text-sm font-medium tracking-wide text-neutral-300 md:text-2xl">
            Live scenarios. Real numbers.
          </h5>
        </div>
      </div>

      <div className="mx-auto grid w-full max-w-[1440px] grid-cols-1 lg:grid-cols-[60%_40%]" data-cursor-label="Case Studies">
        <div className="flex flex-col gap-8 px-6 py-16 lg:border-r lg:border-[rgba(225,29,72,0.3)] lg:px-28 lg:py-24">
          <Reveal y={56}>
            <RouteVisual />
          </Reveal>
          <Reveal y={40}>
            <h3 className="pl-label max-w-[520px] text-lg font-medium leading-snug md:text-2xl">
              How SupplyPulse reroutes a Shanghai port closure in seconds
            </h3>
          </Reveal>
          <Reveal y={40} className="flex flex-col gap-8 md:flex-row md:items-end md:justify-between">
            <p className="pl-label max-w-[383px] text-sm leading-relaxed normal-case tracking-normal text-neutral-400">
              A critical closure hits the world's busiest port. The pipeline weighs geodesic
              alternatives, audits inventory buffers and prices the detour — then hands you a
              decision, not a dashboard full of maybes.
            </p>
            <BracketCTA to="/app" className="flex-none">
              Run Scenario
            </BracketCTA>
          </Reveal>
        </div>

        <div className="hidden items-center justify-center py-24 lg:flex">
          <svg viewBox="0 0 220 220" className="h-[200px] w-[200px]" aria-hidden="true">
            <g stroke="#E11D48" fill="none" strokeWidth="0.8">
              <path d="M20 180 L80 120 L140 150 L200 60" />
              <path d="M20 180 L80 120" strokeDasharray="2 4" />
              <path d="M140 150 L200 60" strokeDasharray="2 4" />
              <rect x="68" y="108" width="24" height="24" transform="rotate(45 80 120)" />
              <circle cx="140" cy="150" r="5" fill="#E11D48" stroke="none" />
              <circle cx="200" cy="60" r="5" fill="#E11D48" stroke="none" />
            </g>
          </svg>
        </div>
      </div>

      <div className="mx-auto grid w-full max-w-[1440px] grid-cols-1 lg:grid-cols-[40%_60%]">
        <div className="hidden items-center justify-center border-r border-[rgba(225,29,72,0.3)] py-24 lg:flex">
          <NetworkFigure />
        </div>

        <div className="flex flex-col items-start gap-8 px-6 py-16 text-left lg:items-end lg:px-28 lg:py-24 lg:text-right">
          <Reveal y={56} className="w-full">
            <LedgerVisual />
          </Reveal>
          <Reveal y={40}>
            <h3 className="pl-label max-w-[520px] text-lg font-medium leading-snug md:text-2xl">
              From live alert to audited financial impact — one traceable run
            </h3>
          </Reveal>
          <Reveal
            y={40}
            className="flex flex-col gap-8 md:flex-row-reverse md:items-end md:justify-between"
          >
            <p className="pl-label max-w-[383px] text-sm leading-relaxed normal-case tracking-normal text-neutral-400">
              Freight surges, demurrage, stockout risk — quantified line by line while the event is
              still unfolding. Every number links back to the agent, prompt and state that produced
              it.
            </p>
            <BracketCTA to="/trace" className="flex-none">
              Read the Trace
            </BracketCTA>
          </Reveal>
        </div>
      </div>
    </section>
  );
}

function BigArrow() {
  return (
    <svg viewBox="0 0 62 82" className="h-[70px] w-[54px] -rotate-12" aria-hidden="true">
      <path
        d="M31 4 L58 34 L44 34 L44 78 L18 78 L18 34 L4 34 Z"
        fill="none"
        stroke="#E11D48"
        strokeWidth="0.8"
        strokeDasharray="3 3"
      />
    </svg>
  );
}

function Clarity() {
  return (
    <section>
      <div className="border-b border-[rgba(225,29,72,0.3)]">
        <div className="mx-auto flex w-full max-w-[1440px] flex-col items-center gap-2 px-6 py-9 text-center lg:px-24">
          <h2 className="pl-display uppercase text-[34px] leading-tight md:text-[56px]">
            Turn complexity into clarity
          </h2>
          <h5 className="pl-label text-sm font-medium tracking-wide text-neutral-300 md:text-2xl">
            Curious what SupplyPulse can do for your operation?
          </h5>
        </div>
      </div>

      <div className="mx-auto w-full max-w-[1440px] px-6 py-20 lg:px-24 lg:py-28">
        <div className="flex justify-center pb-14">
          <BigArrow />
        </div>

        <div className="relative mx-auto w-full border border-[rgba(225,29,72,0.3)] px-6 py-16 md:w-[85%] lg:px-24 lg:py-24" data-cursor-label="Let's build together">
          <div className="absolute right-3 top-0 hidden h-[70%] w-px bg-[rgba(225,29,72,0.3)] lg:block" />

          <div className="flex flex-col items-center gap-14">
            <Reveal y={40}>
              <p className="pl-label max-w-[620px] text-sm leading-relaxed normal-case tracking-normal text-neutral-400 md:text-base md:leading-[1.6]">
                The future of operations isn't another dashboard. It's turning live data into
                decisions — a clear data model, defined entities, working integrations. You could
                build that from scratch, or run it with SupplyPulse.
              </p>
            </Reveal>
            <div className="flex flex-col items-center gap-9">
              <Reveal y={40}>
                <h3 className="pl-label text-center text-xl font-bold leading-snug md:text-[32px]">
                  See how SupplyPulse can power your business
                </h3>
              </Reveal>
              <Reveal y={40} delay={0.08}>
                <BracketCTA to="/app">Run the Pipeline</BracketCTA>
              </Reveal>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function Amplify() {
  return (
    <section className="mx-auto flex w-full max-w-[1440px] flex-col items-center gap-5 px-6 pb-40 pt-8 text-center lg:px-24 lg:pb-[220px]">
      <Reveal y={72}>
        <h2 className="flex flex-wrap items-baseline justify-center gap-x-4">
          <span className="pl-display uppercase text-[34px] leading-tight md:text-[56px]">Amplify human</span>
          <span className="pl-serif text-[40px] leading-none text-[#E11D48] md:text-[64px]">
            potential
          </span>
        </h2>
      </Reveal>
      <Reveal y={40} delay={0.08}>
        <h5 className="pl-label text-sm font-medium tracking-wide text-neutral-300 md:text-2xl">
          Through intelligent, adaptable automation. Focused on outcomes.
        </h5>
      </Reveal>
    </section>
  );
}

function Footer() {
  const [email, setEmail] = useState('');
  const [subscribed, setSubscribed] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (email.trim()) setSubscribed(true);
  };

  return (
    <footer className="w-full bg-[#E11D48] text-[#16090C]">
      <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-14 px-6 pb-10 pt-16 lg:px-12 lg:pt-20">
        <Reveal y={60}>
          <p className="pl-wordmark flex items-end">
            supplypulse
            <span className="mb-[0.14em] ml-[0.04em] inline-block h-[0.09em] w-[0.09em] rounded-full bg-[#16090C]" />
          </p>
        </Reveal>

        <div className="flex flex-col gap-10 lg:flex-row lg:items-end lg:justify-between">
          <form onSubmit={handleSubmit} className="flex w-full max-w-[424px] items-end gap-8">
            {subscribed ? (
              <p className="pl-label flex items-center gap-2 pb-3 text-sm font-semibold tracking-wide">
                <Check className="h-4 w-4" strokeWidth={3} /> Subscribed — welcome aboard
              </p>
            ) : (
              <>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="Email"
                  aria-label="Email for updates"
                  className="pl-email w-full pb-3 text-base"
                />
                <button
                  type="submit"
                  className="pl-label flex-none cursor-pointer border-b-2 border-[#16090C] pb-1.5 text-sm font-semibold tracking-wide transition-opacity hover:opacity-70"
                >
                  Submit
                </button>
              </>
            )}
          </form>

          <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
            <span className="pl-label text-sm font-semibold tracking-wide">© 2026 SupplyPulse</span>
            {['Privacy policy', 'Terms of service'].map((label) => (
              <span key={label} className="pl-label text-sm font-medium tracking-wide opacity-80">
                [{label}]
              </span>
            ))}
          </div>
        </div>
      </div>
    </footer>
  );
}

export default function Landing() {
  return (
    <div className="pl-page min-h-screen w-full overflow-x-clip">
      <Header />
      <main>
        <Hero />
        <Showcase />
        <WhatWeDo />
        <Value />
        <Clarity />
        <Amplify />
      </main>
      <Footer />
    </div>
  );
}
