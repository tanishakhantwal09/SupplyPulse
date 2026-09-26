import React, { useEffect, useState } from 'react';
import { motion, useMotionValue, useSpring, AnimatePresence } from 'framer-motion';
import { ArrowDownRight } from 'lucide-react';

const SPRING = { stiffness: 550, damping: 42, mass: 0.5 };
const RING_SPRING = { type: 'spring', duration: 0.45, bounce: 0.12 };

function resolveHover(target) {
  if (!(target instanceof Element)) return { label: null, link: false };

  if (target.closest('input, textarea, select')) {
    return { label: null, link: false };
  }

  const labeled = target.closest('[data-cursor-label]');
  if (labeled) {
    return { label: labeled.getAttribute('data-cursor-label'), link: false };
  }

  const el = target.closest('a, button, [role="button"], summary, label');
  if (!el) return { label: null, link: false };

  const explicit =
    el.getAttribute('data-cursor-label') || el.getAttribute('aria-label');
  if (explicit) return { label: explicit, link: false };

  if (el.tagName === 'A') {
    const text = (el.textContent || '').trim().replace(/\s+/g, ' ');
    if (text && text.length <= 18) return { label: text, link: false };
    return { label: 'Open', link: false };
  }

  if (el.tagName === 'BUTTON' || el.getAttribute('role') === 'button') {
    const text = (el.textContent || '').trim().replace(/\s+/g, ' ');
    if (text && text.length <= 18) return { label: text, link: false };
    return { label: 'Click', link: false };
  }

  return { label: 'Select', link: false };
}

export default function CustomCursor() {
  const [enabled] = useState(
    () =>
      typeof window !== 'undefined' &&
      window.matchMedia('(hover: hover) and (pointer: fine)').matches &&
      !window.matchMedia('(any-hover: none)').matches
  );
  const [visible, setVisible] = useState(false);
  const [label, setLabel] = useState(null);
  const [link, setLink] = useState(false);
  const [pressed, setPressed] = useState(false);

  const x = useMotionValue(-100);
  const y = useMotionValue(-100);
  const sx = useSpring(x, SPRING);
  const sy = useSpring(y, SPRING);

  useEffect(() => {
    if (!enabled) return undefined;

    const onMove = (e) => {
      x.set(e.clientX);
      y.set(e.clientY);
      setVisible(true);
      const next = resolveHover(e.target);
      setLabel(next.label);
      setLink(next.link);
    };
    const onLeave = () => setVisible(false);
    const onEnter = () => setVisible(true);
    const onDown = () => setPressed(true);
    const onUp = () => setPressed(false);

    document.body.classList.add('pl-custom-cursor');
    window.addEventListener('mousemove', onMove, { passive: true });
    document.documentElement.addEventListener('mouseleave', onLeave);
    document.documentElement.addEventListener('mouseenter', onEnter);
    window.addEventListener('mousedown', onDown);
    window.addEventListener('mouseup', onUp);

    return () => {
      document.body.classList.remove('pl-custom-cursor');
      window.removeEventListener('mousemove', onMove);
      document.documentElement.removeEventListener('mouseleave', onLeave);
      document.documentElement.removeEventListener('mouseenter', onEnter);
      window.removeEventListener('mousedown', onDown);
      window.removeEventListener('mouseup', onUp);
    };
  }, [enabled, x, y]);

  if (!enabled) return null;

  const expanded = !!label;

  return (
    <>
      {/* Dot — tracks the pointer instantly, hides while the label circle is open */}
      <motion.div
        aria-hidden="true"
        className="pointer-events-none fixed left-0 top-0 z-[100] mix-blend-difference"
        style={{ x, y, width: 0, height: 0 }}
      >
        <motion.div
          className="absolute left-0 top-0 -translate-x-1/2 -translate-y-1/2 rounded-full bg-white"
          animate={{
            width: expanded ? 0 : pressed ? 7 : 10,
            height: expanded ? 0 : pressed ? 7 : 10,
            opacity: visible && !expanded ? 1 : 0
          }}
          transition={{ type: 'spring', duration: 0.25, bounce: 0.12 }}
        />
      </motion.div>

      {/* Ring — trails on a spring, expands into the rotating dashed label circle */}
      <motion.div
        aria-hidden="true"
        className="pointer-events-none fixed left-0 top-0 z-[99] mix-blend-difference"
        style={{ x: sx, y: sy, width: 0, height: 0 }}
      >
        <motion.div
          className="absolute left-0 top-0 flex -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full"
          animate={{
            width: expanded ? (pressed ? 126 : 140) : link ? 56 : 40,
            height: expanded ? (pressed ? 126 : 140) : link ? 56 : 40,
            opacity: visible ? 1 : 0
          }}
          transition={RING_SPRING}
        >
          <motion.span
            className="absolute inset-0 rounded-full border border-solid border-white"
            animate={{ opacity: expanded ? 0 : 1 }}
            transition={{ duration: 0.2 }}
          />

          {expanded && (
            <motion.svg
              viewBox="0 0 140 140"
              className="absolute inset-0 h-full w-full"
              animate={{ rotate: 360 }}
              transition={{ duration: 14, ease: 'linear', repeat: Infinity }}
            >
              <circle
                cx="70"
                cy="70"
                r="67"
                fill="none"
                stroke="white"
                strokeWidth="1.5"
                strokeDasharray="2 8"
                strokeLinecap="round"
              />
            </motion.svg>
          )}

          <AnimatePresence mode="wait">
            {expanded && (
              <motion.span
                key={label}
                initial={{ opacity: 0, y: 6, scale: 0.9 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -4, scale: 0.95 }}
                transition={{ duration: 0.18, ease: [0.16, 1, 0.3, 1] }}
                className="relative flex max-w-[120px] flex-col items-center gap-1 px-2 text-center"
              >
                <ArrowDownRight className="h-4 w-4 flex-none text-white" strokeWidth={2} />
                <span className="pl-display whitespace-nowrap text-[10px] font-medium uppercase leading-tight tracking-[0.14em] text-white">
                  {label}
                </span>
              </motion.span>
            )}
          </AnimatePresence>
        </motion.div>
      </motion.div>
    </>
  );
}
