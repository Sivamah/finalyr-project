import React from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { BrainCircuit } from 'lucide-react';

/**
 * A-DMFE Engine status panel.
 *
 * DATA HONESTY — every value here comes from GET /api/dmfe/statistics, which is
 * already fetched by the page. Nothing is synthesised.
 *
 * The reference design shows "Prediction Accuracy" and "Decision Confidence" as
 * headline percentages. The backend exposes NEITHER as an aggregate:
 *   - decision confidence is computed per batch (adaptive/decision.compute_confidence)
 *     and stored on the batch, not aggregated across runs;
 *   - prediction accuracy does not exist — the learning engine tracks a delay
 *     RESIDUAL in minutes, which is an error, not an accuracy.
 * Displaying either under those names would be showing one metric under another
 * metric's label. They are therefore omitted rather than invented.
 *
 * What IS shown, and where it comes from:
 *   Compatibility Score  avg_compatibility_score  mean CS across all analysis runs
 *   Effective threshold  latest_threshold         θ_eff actually applied last run
 *   Batching rate        batch_rate_pct           shared trips / total trips × 100
 */

const Meter = ({ label, value, suffix = '%', accent, max = 100, hint }) => {
  const pct = Math.max(0, Math.min(100, (Number(value) / max) * 100));
  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[11.5px] text-brand-text-secondary font-medium" title={hint}>
          {label}
        </span>
        <span className="text-[12.5px] font-semibold text-white tabular-nums">
          {Number(value).toFixed(1)}{suffix}
        </span>
      </div>
      <div
        className="h-1.5 w-full rounded-full bg-white/[0.06] overflow-hidden"
        role="progressbar"
        aria-label={label}
        aria-valuenow={Number(value)}
        aria-valuemin={0}
        aria-valuemax={max}
      >
        <motion.div
          className="h-full rounded-full"
          style={{ background: accent }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.8, ease: [0.22, 1, 0.36, 1] }}
        />
      </div>
    </div>
  );
};

/** Subtle orbital nodes. Decorative only — it does not depict model internals. */
const EngineVisual = () => {
  const reduce = useReducedMotion();
  return (
    <div className="relative h-[86px] w-[86px] shrink-0" aria-hidden="true">
      <div className="absolute inset-0 rounded-full bg-brand-purple/20 blur-xl" />
      {[0, 1, 2].map((ring) => (
        <div
          key={ring}
          className="absolute rounded-full border border-brand-purple/25"
          style={{
            inset: ring * 10,
            animation: reduce
              ? undefined
              : `spin ${14 + ring * 6}s linear infinite${ring % 2 ? ' reverse' : ''}`,
          }}
        >
          <span
            className="absolute h-1.5 w-1.5 rounded-full bg-brand-cyan shadow-[0_0_8px_rgba(34,211,238,0.9)]"
            style={{ top: -3, left: '50%' }}
          />
        </div>
      ))}
      <div className="absolute inset-0 flex items-center justify-center">
        <BrainCircuit className="h-6 w-6 text-brand-purple-light drop-shadow-[0_0_10px_rgba(139,92,246,0.7)]" />
      </div>
    </div>
  );
};

export default function AIEngineStatus({ stats, mode }) {
  const hasStats = Boolean(stats);
  const runs = stats?.total_runs ?? 0;
  const isActive = runs > 0;

  return (
    <div className="navy-glass-card p-5 flex flex-col">
      <div className="flex items-center gap-2 mb-4">
        <BrainCircuit className="h-4 w-4 text-brand-purple-light" />
        <h3 className="text-[14px] font-semibold text-white">AI Engine Status</h3>
      </div>

      <div className="flex items-start justify-between gap-3 mb-5">
        <div className="min-w-0">
          <p className="text-[13.5px] font-semibold text-white leading-tight">A-DMFE Engine</p>
          <p className="text-[11px] text-brand-text-muted leading-snug mt-0.5">
            Adaptive Dynamic
            <br />
            Feasibility Analysis
          </p>
          <span
            className={`inline-flex items-center gap-1.5 mt-2.5 px-2 py-0.5 rounded-full border text-[9.5px] font-bold uppercase tracking-[0.14em] ${
              isActive
                ? 'text-brand-success border-brand-success/30 bg-brand-success/10'
                : 'text-brand-text-muted border-white/10 bg-white/[0.04]'
            }`}
          >
            <span className="h-1.5 w-1.5 rounded-full bg-current" />
            {isActive ? 'Active' : 'Idle'}
          </span>
        </div>
        <EngineVisual />
      </div>

      {hasStats ? (
        <div className="space-y-3.5">
          <Meter
            label="Compatibility Score"
            value={stats.avg_compatibility_score ?? 0}
            accent="linear-gradient(90deg,#1677FF,#22D3EE)"
            hint="Mean compatibility score across all recorded analysis runs"
          />
          <Meter
            label="Effective Threshold"
            value={stats.latest_threshold ?? 0}
            accent="linear-gradient(90deg,#7C3AED,#8B5CF6)"
            hint="Context-adjusted threshold applied by the most recent run"
          />
          <Meter
            label="Batching Rate"
            value={stats.batch_rate_pct ?? 0}
            accent="linear-gradient(90deg,#22C55E,#22D3EE)"
            hint="Shared trips as a percentage of all dispatched trips"
          />
        </div>
      ) : (
        <p className="text-[11.5px] text-brand-text-muted">Engine statistics unavailable.</p>
      )}

      <div className="mt-5 pt-3.5 border-t border-white/[0.07] space-y-2">
        <div className="flex items-center justify-between text-[11.5px]">
          <span className="text-brand-text-secondary">Mode</span>
          <span className="flex items-center gap-1.5 text-white font-medium capitalize">
            <span className="h-1.5 w-1.5 rounded-full bg-brand-success shadow-[0_0_6px_rgba(34,197,94,0.8)]" />
            {mode || 'adaptive'}
          </span>
        </div>
        <div className="flex items-center justify-between text-[11.5px]">
          <span className="text-brand-text-secondary">Analysis runs</span>
          <span className="text-white font-medium tabular-nums">{runs.toLocaleString()}</span>
        </div>
        {stats?.last_run_at && (
          <div className="flex items-center justify-between text-[11.5px]">
            <span className="text-brand-text-secondary">Last run</span>
            <span className="text-brand-text-secondary tabular-nums">{stats.last_run_at}</span>
          </div>
        )}
      </div>
    </div>
  );
}
