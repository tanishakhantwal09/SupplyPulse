import React, { useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ArrowUpRight } from 'lucide-react';
import { useSupplyPulse } from '../../context/SupplyPulseContext';

const NAV_ITEMS = [
  { to: '/app', label: 'Overview', end: true },
  { to: '/pipeline', label: 'Pipeline' },
  { to: '/events', label: 'Signals' },
  { to: '/evaluation', label: 'Evaluation' },
  { to: '/telemetry', label: 'Telemetry' },
  { to: '/trace', label: 'Trace' },
  { to: '/state', label: 'State' },
  { to: '/reference', label: 'Reference' },
  { to: '/logs', label: 'Terminal' }
];

const EASE = [0.16, 1, 0.3, 1];

function HamburgerIcon({ open }) {
  return (
    <span className="relative flex h-5 w-6 flex-col items-end justify-center gap-[6px]">
      <motion.span
        animate={open ? { rotate: 45, y: 4, width: 24 } : { rotate: 0, y: 0, width: 16 }}
        transition={{ duration: 0.3, ease: EASE }}
        className="block h-[2px] bg-current"
      />
      <motion.span
        animate={open ? { rotate: -45, y: -4, width: 24 } : { rotate: 0, y: 0, width: 24 }}
        transition={{ duration: 0.3, ease: EASE }}
        className="block h-[2px] bg-current"
      />
    </span>
  );
}

export default function FloatingMenu() {
  const { menuOpen, setMenuOpen } = useSupplyPulse();

  useEffect(() => {
    document.body.style.overflow = menuOpen ? 'hidden' : '';
    return () => {
      document.body.style.overflow = '';
    };
  }, [menuOpen]);

  return (
    <>
      {/* ── Detached Floating Menu Trigger (Far Left Margin) ───────────── */}
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4, ease: EASE }}
        className="fixed left-4 sm:left-6 lg:left-7 top-[98px] z-40"
      >
        <button
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label={menuOpen ? 'Close navigation menu' : 'Open navigation menu'}
          title="Navigation Menu"
          className={`group relative flex h-11 w-11 sm:h-12 sm:w-12 cursor-pointer items-center justify-center border transition-all duration-300 ${
            menuOpen
              ? 'border-[#E11D48] bg-[rgba(225,29,72,0.2)] text-[#E11D48] shadow-[0_8px_30px_rgba(0,0,0,0.9),0_0_24px_rgba(225,29,72,0.45)]'
              : 'border-[rgba(225,29,72,0.4)] bg-[#0B0B0E]/90 backdrop-blur-xl text-[#F1EFF5] shadow-[0_10px_32px_rgba(0,0,0,0.85),0_0_16px_rgba(225,29,72,0.15)] hover:border-[#E11D48] hover:bg-[rgba(225,29,72,0.15)] hover:text-[#E11D48] hover:shadow-[0_10px_36px_rgba(0,0,0,0.95),0_0_24px_rgba(225,29,72,0.35)] active:scale-95'
          }`}
        >
          <HamburgerIcon open={menuOpen} />
        </button>
      </motion.div>

      {/* ── Full-Screen Overlay Navigation Modal (Pulsr aesthetic) ─────── */}
      <AnimatePresence>
        {menuOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.3, ease: EASE }}
            className="fixed inset-0 z-[60] bg-[#0A0A0C]/[0.98] backdrop-blur-2xl overflow-y-auto"
            data-lenis-prevent
          >
            <div className="mx-auto flex min-h-full w-full max-w-[1440px] flex-col px-6 pb-12 pt-8 lg:px-12">
              {/* Overlay top row */}
              <div className="flex h-[68px] items-center justify-between">
                <span className="pl-label text-[11px] font-semibold tracking-[0.18em] uppercase text-neutral-500">
                  Navigation
                </span>
                <button
                  onClick={() => setMenuOpen(false)}
                  aria-label="Close menu"
                  className="flex h-11 w-11 cursor-pointer items-center justify-center border border-[rgba(225,29,72,0.4)] text-[#F1EFF5] transition-colors hover:bg-[rgba(225,29,72,0.12)] hover:text-[#E11D48]"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              {/* Links */}
              <nav className="flex flex-1 flex-col justify-center py-10">
                {NAV_ITEMS.map((item, i) => (
                  <motion.div
                    key={item.to}
                    initial={{ opacity: 0, y: 36 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.55, delay: 0.06 + i * 0.045, ease: EASE }}
                  >
                    <NavLink
                      to={item.to}
                      end={item.end}
                      onClick={() => setMenuOpen(false)}
                      className={({ isActive }) =>
                        `group flex items-baseline gap-5 border-b border-white/[0.06] py-3 lg:py-4 transition-colors ${
                          isActive ? 'text-[#E11D48]' : 'text-[#F1EFF5] hover:text-[#E11D48]'
                        }`
                      }
                    >
                      <span className="mono w-8 flex-none text-xs text-neutral-500 transition-colors group-hover:text-[#E11D48]">
                        {String(i + 1).padStart(2, '0')}
                      </span>
                      <span className="relative block flex-1 transition-transform duration-300 group-hover:translate-x-2">
                        <span className="pl-display uppercase block text-3xl lg:text-[44px] leading-tight opacity-100 transition-all duration-300 group-hover:-translate-y-1.5 group-hover:opacity-0">
                          {item.label}
                        </span>
                        <span
                          aria-hidden="true"
                          className="pl-serif absolute inset-0 flex items-center text-[1.35em] lg:text-[50px] leading-none normal-case opacity-0 transition-all duration-300 group-hover:translate-y-1.5 group-hover:opacity-100"
                        >
                          {item.label}
                        </span>
                      </span>
                      <ArrowUpRight className="ml-auto h-5 w-5 flex-none self-center text-neutral-700 opacity-0 transition-all duration-300 group-hover:text-[#E11D48] group-hover:opacity-100" />
                    </NavLink>
                  </motion.div>
                ))}
              </nav>

              {/* Overlay bottom row */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.5, delay: 0.5, ease: EASE }}
                className="flex items-center justify-between border-t border-[rgba(225,29,72,0.3)] pt-6"
              >
                <span className="pl-label text-[11px] font-semibold tracking-[0.18em] uppercase text-neutral-600">
                  © 2026 SupplyPulse — Autonomous Operations Intelligence
                </span>
              </motion.div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
