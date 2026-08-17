import React, { useMemo } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import {
  PieChart, Pie, Cell, AreaChart, Area, XAxis, Tooltip, ResponsiveContainer,
} from 'recharts';
import { Fuel, Leaf } from 'lucide-react';

/**
 * Requests-by-type donut, performance area chart and the optimization-impact
 * cards. All series come from data the page already fetched — no extra requests.
 */

export const TYPE_COLORS = ['#3B82F6', '#F59E0B', '#22C55E'];

const tooltipStyle = {
  backgroundColor: 'rgba(7, 18, 37, 0.96)',
  border: '1px solid rgba(255,255,255,0.10)',
  borderRadius: '12px',
  boxShadow: '0 12px 32px rgba(0,0,0,0.5)',
  fontSize: '12px',
  color: '#fff',
  padding: '8px 12px',
};

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={tooltipStyle}>
      {label && (
        <p className="text-[10px] text-white/50 uppercase tracking-wider mb-1.5">{label}</p>
      )}
      {payload.map((entry) => (
        <div key={entry.dataKey ?? entry.name} className="flex items-center justify-between gap-6 text-[12px] mb-1 last:mb-0">
          <span className="flex items-center gap-1.5 text-white/70">
            <span className="h-2 w-2 rounded-full" style={{ background: entry.color || entry.stroke || entry.fill }} />
            {entry.name}
          </span>
          <span className="font-semibold text-white tabular-nums">{entry.value}</span>
        </div>
      ))}
    </div>
  );
}

/* ── Requests by Type ─────────────────────────────────────────────────────── */

export function RequestsByType({ mix = [] }) {
  const reduce = useReducedMotion();
  const total = useMemo(() => mix.reduce((s, r) => s + r.value, 0), [mix]);

  return (
    <div className="navy-glass-card p-5 flex flex-col">
      <h3 className="text-[14px] font-semibold text-white mb-4">Requests by Type</h3>

      {total === 0 ? (
        <p className="text-[12px] text-brand-text-muted py-8 text-center">No requests in the current queue.</p>
      ) : (
        <div className="flex items-center gap-5">
          <div className="relative h-[136px] w-[136px] shrink-0">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={mix}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={46}
                  outerRadius={66}
                  paddingAngle={3}
                  stroke="none"
                  isAnimationActive={!reduce}
                  animationDuration={700}
                >
                  {mix.map((entry, i) => (
                    <Cell key={entry.name} fill={TYPE_COLORS[i % TYPE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip content={<ChartTooltip />} />
              </PieChart>
            </ResponsiveContainer>
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
              <span className="text-[20px] font-display font-semibold text-white tabular-nums leading-none">
                {total.toLocaleString()}
              </span>
              <span className="text-[9.5px] text-brand-text-muted uppercase tracking-[0.16em] mt-1">Total</span>
            </div>
          </div>

          <div className="flex-1 min-w-0 space-y-2.5">
            {mix.map((entry, i) => (
              <div key={entry.name} className="flex items-center gap-2.5">
                <span
                  className="h-2 w-2 rounded-full shrink-0"
                  style={{ background: TYPE_COLORS[i % TYPE_COLORS.length] }}
                />
                <span className="text-[11.5px] text-brand-text-secondary truncate flex-1">{entry.name}</span>
                <span className="text-[11.5px] text-white font-medium tabular-nums">
                  {entry.value.toLocaleString()}
                  <span className="text-brand-text-muted ml-1">
                    ({((entry.value / total) * 100).toFixed(1)}%)
                  </span>
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Performance Overview ─────────────────────────────────────────────────── */

/**
 * The reference draws three lines. Only series the backend genuinely provides
 * are plotted — a third line is not invented to match the picture.
 */
export function PerformanceOverview({ generated = [], completed = [] }) {
  const reduce = useReducedMotion();

  const data = useMemo(() => {
    const byLabel = new Map();
    generated.forEach((d) => {
      const key = d.label ?? d.name ?? d.date ?? '';
      byLabel.set(key, { label: key, generated: d.count ?? 0, completed: 0 });
    });
    completed.forEach((d) => {
      const key = d.label ?? d.name ?? d.date ?? '';
      const row = byLabel.get(key) || { label: key, generated: 0, completed: 0 };
      row.completed = d.count ?? 0;
      byLabel.set(key, row);
    });
    return Array.from(byLabel.values());
  }, [generated, completed]);

  return (
    <div className="navy-glass-card p-5 flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[14px] font-semibold text-white">Performance Overview</h3>
        <span className="text-[10px] px-2.5 py-1 rounded-full bg-white/[0.05] border border-white/[0.08] text-brand-text-secondary">
          Recent activity
        </span>
      </div>

      {data.length === 0 ? (
        <p className="text-[12px] text-brand-text-muted py-10 text-center">No trend data available yet.</p>
      ) : (
        <>
          <div className="h-[150px] -ml-2">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data} margin={{ top: 4, right: 6, bottom: 0, left: 0 }}>
                <defs>
                  <linearGradient id="gradGenerated" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#1677FF" stopOpacity={0.45} />
                    <stop offset="100%" stopColor="#1677FF" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="gradCompleted" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#22C55E" stopOpacity={0.4} />
                    <stop offset="100%" stopColor="#22C55E" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis
                  dataKey="label"
                  tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip content={<ChartTooltip />} />
                <Area
                  type="monotone" dataKey="generated" name="Generated"
                  stroke="#1677FF" strokeWidth={2} fill="url(#gradGenerated)"
                  isAnimationActive={!reduce} animationDuration={700}
                />
                <Area
                  type="monotone" dataKey="completed" name="Completed"
                  stroke="#22C55E" strokeWidth={2} fill="url(#gradCompleted)"
                  isAnimationActive={!reduce} animationDuration={700}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
          <div className="flex items-center gap-5 mt-3">
            {[
              { label: 'Generated', color: '#1677FF' },
              { label: 'Completed', color: '#22C55E' },
            ].map((s) => (
              <span key={s.label} className="flex items-center gap-1.5 text-[11px] text-brand-text-secondary">
                <span className="h-2 w-2 rounded-full" style={{ background: s.color }} />
                {s.label}
              </span>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

/* ── Optimization Impact ──────────────────────────────────────────────────── */

export function OptimizationImpact({ stats }) {
  const reduce = useReducedMotion();
  const cards = [
    { icon: Fuel, label: 'Fuel Saved', value: stats?.fuel_saved ?? 0, unit: 'L', color: '#22C55E' },
    { icon: Leaf, label: 'CO₂ Reduced', value: stats?.co2_reduction ?? 0, unit: 'kg', color: '#22D3EE' },
  ];

  return (
    <div className="navy-glass-card p-5 flex flex-col">
      <h3 className="text-[14px] font-semibold text-white mb-4">Optimization Impact</h3>
      <div className="grid grid-cols-2 gap-3 flex-1">
        {cards.map((c, i) => (
          <motion.div
            key={c.label}
            initial={reduce ? false : { opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: reduce ? 0 : i * 0.08 }}
            className="rounded-2xl border border-white/[0.07] bg-white/[0.03] p-3.5 flex flex-col justify-between"
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] text-brand-text-secondary">{c.label}</span>
              <c.icon className="h-3.5 w-3.5" style={{ color: c.color }} />
            </div>
            <div className="flex items-baseline gap-1 mt-3">
              <span className="text-[20px] font-display font-semibold text-white tabular-nums leading-none">
                {Number(c.value).toFixed(1)}
              </span>
              <span className="text-[12px] text-brand-text-muted">{c.unit}</span>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
