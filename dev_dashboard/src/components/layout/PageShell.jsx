import React from 'react';
import { motion } from 'framer-motion';

const EASE = [0.16, 1, 0.3, 1];

export default function PageShell({ eyebrow, title, accent, sub, right, children }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.4, ease: EASE }}
      className="mx-auto w-full max-w-[1440px] px-6 lg:px-12 py-10 lg:py-14"
    >
      {(eyebrow || title) && (
        <div className="mb-12 lg:mb-16 border-y border-[rgba(225,29,72,0.3)] px-1 py-9 flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            {eyebrow && (
              <div className="pl-label mb-3 text-[11px] font-semibold tracking-[0.18em] uppercase text-[#E11D48]">
                {eyebrow}
              </div>
            )}
            <h1 className="cred-hero text-3xl sm:text-4xl md:text-5xl lg:text-[54px] text-white">
              {title}{' '}
              {accent && (
                <span className="pl-serif font-medium normal-case text-[1.06em] text-[#E11D48]">
                  {accent}
                </span>
              )}
            </h1>
            {sub && (
              <p className="pl-label mt-4 text-[11px] sm:text-xs font-medium tracking-[0.14em] uppercase leading-relaxed text-neutral-400 max-w-2xl">
                {sub}
              </p>
            )}
          </div>
          {right && <div className="shrink-0 flex flex-wrap items-center gap-3">{right}</div>}
        </div>
      )}
      {children}
    </motion.div>
  );
}
