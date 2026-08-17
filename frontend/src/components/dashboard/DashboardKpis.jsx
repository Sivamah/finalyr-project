import React from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { FileText, Car, Truck, Fuel, Cloud } from 'lucide-react';
import { LineChart, Line, ResponsiveContainer } from 'recharts';
import AnimatedNumber from '../ui/AnimatedNumber';

/**
 * Five KPI cards, matching the reference layout.
 *
 * DATA HONESTY — the reference shows a "▲ 12.5% vs yesterday" strip under every
 * value. No endpoint in this application returns a day-over-day comparison, so
 * that strip is deliberately absent rather than fabricated. If a comparison
 * endpoint is added later, pass a `trend` prop and the row will render.
 *
 * Sparklines use real series from GET /api/simulation/advanced-analytics
 * (charts.request_generation_trend / charts.completed_requests_trend). A card
 * with no matching real series simply renders without one.
 */

const TONES = {
  blue:   { bg: 'bg-blue-500/10',   text: 'text-blue-400',   border: 'border-blue-500/20',   hex: '#3B82F6' },
  purple: { bg: 'bg-purple-500/10', text: 'text-purple-400', border: 'border-purple-500/20', hex: '#A855F7' },
  cyan:   { bg: 'bg-cyan-500/10',   text: 'text-cyan-400',   border: 'border-cyan-500/20',   hex: '#22D3EE' },
  green:  { bg: 'bg-green-500/10',  text: 'text-green-400',  border: 'border-green-500/20',  hex: '#22C55E' },
  indigo: { bg: 'bg-indigo-500/10', text: 'text-indigo-400', border: 'border-indigo-500/20', hex: '#6366F1' },
};

const Sparkline = ({ data, color, dataKey = 'count' }) => (
  <div className="h-9 w-20" aria-hidden="true">
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data}>
        <Line
          type="monotone"
          dataKey={dataKey}
          stroke={color}
          strokeWidth={1.8}
          dot={false}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  </div>
);

const KpiCard = ({ icon: Icon, label, value, format, unit, tone, series, index, trend }) => {
  const reduce = useReducedMotion();
  const t = TONES[tone] || TONES.blue;

  return (
    <motion.div
      initial={reduce ? false : { opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: reduce ? 0 : index * 0.06, ease: [0.22, 1, 0.36, 1] }}
      className="navy-glass-card p-4 group transition-transform duration-300 hover:-translate-y-0.5"
    >
      <div className="flex items-start justify-between mb-3">
        <span className="text-[12.5px] text-brand-text-secondary font-medium">{label}</span>
        <div className={`h-8 w-8 rounded-xl ${t.bg} ${t.border} border flex items-center justify-center shrink-0`}>
          <Icon className={`h-4 w-4 ${t.text}`} />
        </div>
      </div>

      <div className="flex items-end justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-baseline gap-1">
            <span className="text-[26px] leading-none font-display font-semibold text-white tabular-nums tracking-tight">
              {format ? format(value) : <AnimatedNumber value={value} format={(v) => Math.round(v).toLocaleString()} />}
            </span>
            {unit && <span className="text-[13px] text-brand-text-muted">{unit}</span>}
          </div>
          {/* Rendered only when the backend actually supplies a comparison. */}
          {trend && (
            <p className="mt-1 text-[10.5px] font-medium text-brand-success">{trend}</p>
          )}
        </div>
        {series?.length > 1 && <Sparkline data={series} color={t.hex} />}
      </div>
    </motion.div>
  );
};

export default function DashboardKpis({ stats, genTrend = [], compTrend = [] }) {
  if (!stats) return null;

  const cards = [
    {
      icon: FileText, label: 'Total Requests', tone: 'blue',
      value: stats.total_requests ?? 0, series: genTrend,
    },
    {
      icon: Car, label: 'Active Trips', tone: 'purple',
      value: stats.total_optimizations ?? 0, series: compTrend,
    },
    {
      icon: Truck, label: 'Fleet Utilization', tone: 'cyan',
      value: stats.batch_rate ?? 0, format: (v) => `${Number(v).toFixed(1)}%`,
    },
    {
      icon: Fuel, label: 'Fuel Saved', tone: 'green',
      value: stats.fuel_saved ?? 0, format: (v) => Number(v).toFixed(1), unit: 'L',
      series: compTrend,
    },
    {
      icon: Cloud, label: 'CO₂ Reduced', tone: 'indigo',
      value: stats.co2_reduction ?? 0, format: (v) => Math.round(Number(v)).toLocaleString(), unit: 'kg',
      series: compTrend,
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-3.5">
      {cards.map((c, i) => (
        <KpiCard key={c.label} {...c} index={i} />
      ))}
    </div>
  );
}
