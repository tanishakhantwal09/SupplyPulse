import React from 'react';
import { motion } from 'framer-motion';

export default function PageShell({ eyebrow, title, accent, sub, right, children }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -12 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className="mx-auto w-full max-w-7xl px-6 lg:px-10 py-10 lg:py-16"
    >
      {(eyebrow || title) && (
        <div className="mb-12 lg:mb-16 flex flex-col justify-between gap-8 md:flex-row md:items-end">
          <div className="max-w-3xl">
            {eyebrow && (
              <div className="cred-label mb-3.5 text-rose-400">
                {eyebrow}
              </div>
            )}
            <h1 className="cred-hero text-3xl sm:text-4xl md:text-5xl lg:text-6xl text-white">
              {title} {accent && <span className="text-rose-500 font-extrabold">{accent}</span>}
            </h1>
            {sub && (
              <p className="mt-4 text-sm sm:text-base leading-relaxed text-neutral-400 max-w-2xl">
                {sub}
              </p>
            )}
          </div>
          {right && <div className="shrink-0 flex items-center gap-3">{right}</div>}
        </div>
      )}
      {children}
    </motion.div>
  );
}
