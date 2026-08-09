import React from 'react';
import { motion } from 'framer-motion';

export default function PageHeader({ eyebrow, title, description, actions, live }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      className="flex flex-col lg:flex-row lg:items-end justify-between gap-5 mb-8"
    >
      <div className="max-w-2xl">
        {eyebrow && (
          <p className="section-label mb-2.5 flex items-center gap-2">
            {live && (
              <span className="relative flex h-1.5 w-1.5">
                <span className="absolute inline-flex h-full w-full rounded-full bg-brand-danger opacity-60 animate-ping" />
                <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-brand-danger" />
              </span>
            )}
            {eyebrow}
          </p>
        )}
        <h1 className="page-title">{title}</h1>
        {description && (
          <p className="mt-2.5 text-[13.5px] leading-relaxed text-brand-text-secondary">{description}</p>
        )}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2.5 shrink-0">{actions}</div>}
    </motion.div>
  );
}