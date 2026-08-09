import React from 'react';

const STYLES = {
  success: {
    icon: 'bg-brand-success',
    text: 'text-brand-success',
    border: 'border-brand-success/25',
    bg: 'bg-brand-success/10',
  },
  warning: {
    icon: 'bg-brand-warning',
    text: 'text-brand-warning',
    border: 'border-brand-warning/25',
    bg: 'bg-brand-warning/10',
  },
  danger: {
    icon: 'bg-brand-danger',
    text: 'text-brand-danger',
    border: 'border-brand-danger/25',
    bg: 'bg-brand-danger/10',
  },
  info: {
    icon: 'bg-brand-primary',
    text: 'text-brand-primary',
    border: 'border-brand-primary/25',
    bg: 'bg-brand-primary/10',
  },
  neutral: {
    icon: 'bg-brand-text-muted',
    text: 'text-brand-text-secondary',
    border: 'border-white/[0.1]',
    bg: 'bg-white/[0.04]',
  },
};

export default function StatusBadge({ tone = 'neutral', label, pulse, count }) {
  const s = STYLES[tone] || STYLES.neutral;
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full px-3 py-1 border ${s.border} ${s.bg} text-[11px] font-semibold tracking-wide`}
    >
      <span className="relative flex h-1.5 w-1.5">
        {pulse && (
          <span className={`absolute inline-flex h-full w-full rounded-full ${s.icon} opacity-60 animate-ping`} />
        )}
        <span className={`relative inline-flex rounded-full h-1.5 w-1.5 ${s.icon} ${pulse ? '' : ''}`} />
      </span>
      <span className={s.text}>{label}</span>
      {count !== undefined && <span className="text-brand-text-muted font-medium">· {count}</span>}
    </span>
  );
}