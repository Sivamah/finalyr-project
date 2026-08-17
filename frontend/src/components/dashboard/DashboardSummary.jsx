import React from 'react';
import { Layers, Clock, Leaf, Route } from 'lucide-react';

/**
 * Bottom summary strip.
 *
 * DATA HONESTY — deviations from the reference image, and why:
 *
 *  "Total Optimization 92.4%"  → replaced by BATCHING RATE (stats.batch_rate).
 *      The 92.4% in the reference (and in the previous Dashboard.jsx) was a
 *      hardcoded literal with no backend source.
 *
 *  "Avg. Waiting Time 18.6 min" → shown as AVG REQUEST LATENCY.
 *      This is time_analytics.avg_queue_waiting_time_sec, i.e. request
 *      created_at → trip completed_at, wall-clock. It is a valid live
 *      operational metric, but it is NOT the research "average waiting time"
 *      that was withdrawn from the evaluation tables (that one was an alias of
 *      avg_delay_min). Labelling it "waiting time" here would re-import the
 *      exact ambiguity the evaluation correction removed, so it carries an
 *      operational name instead.
 *
 *  "Cost Savings ₹24,560"      → omitted; replaced by SHARED TRIPS.
 *      /api/dashboard/stats exposes no cost aggregate. Trip.estimated_cost
 *      exists per row but is never summed server-side, and computing a rupee
 *      figure in the browser would be a new calculation in the presentation
 *      layer. Shared trips is a real dispatch outcome from the same payload.
 */

const Item = ({ icon: Icon, label, value, unit, accent, hint }) => (
  <div className="flex items-center gap-3.5 min-w-0" title={hint}>
    <div
      className="h-10 w-10 rounded-2xl flex items-center justify-center shrink-0 border"
      style={{ background: `${accent}1A`, borderColor: `${accent}33` }}
    >
      <Icon className="h-4 w-4" style={{ color: accent }} />
    </div>
    <div className="min-w-0">
      <p className="text-[10.5px] text-brand-text-muted truncate">{label}</p>
      <p className="text-[17px] font-display font-semibold text-white tabular-nums leading-tight">
        {value}
        {unit && <span className="text-[12px] text-brand-text-muted ml-1">{unit}</span>}
      </p>
    </div>
  </div>
);

export default function DashboardSummary({ stats, timeAnalytics }) {
  if (!stats) return null;

  const latencySec = timeAnalytics?.avg_queue_waiting_time_sec;
  const hasLatency = typeof latencySec === 'number' && latencySec > 0;

  return (
    <div className="navy-glass-card p-5">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
        <Item
          icon={Layers}
          label="Batching Rate"
          value={`${Number(stats.batch_rate ?? 0).toFixed(1)}`}
          unit="%"
          accent="#1677FF"
          hint="Shared trips as a percentage of all dispatched trips"
        />
        <Item
          icon={Clock}
          label="Avg Request Latency"
          value={hasLatency ? (latencySec / 60).toFixed(1) : '—'}
          unit={hasLatency ? 'min' : ''}
          accent="#7C3AED"
          hint="Request created to trip completed, wall-clock. Not the research delay metric."
        />
        <Item
          icon={Leaf}
          label="CO₂ Reduced"
          value={Math.round(Number(stats.co2_reduction ?? 0)).toLocaleString()}
          unit="kg"
          accent="#22D3EE"
          hint="Cumulative CO₂ saved across all dispatched trips"
        />
        <Item
          icon={Route}
          label="Shared Trips"
          value={Number(stats.total_optimizations ?? 0).toLocaleString()}
          accent="#22C55E"
          hint="Trips serving more than one request"
        />
      </div>
    </div>
  );
}
