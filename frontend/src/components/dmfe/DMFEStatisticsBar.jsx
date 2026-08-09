import React from 'react';
import { Activity, Layers, XCircle, Gauge } from 'lucide-react';
import { motion } from 'framer-motion';

const CARD_THEMES = {
  pending: { icon: Activity, accent: '#3B82F6', glow: 'rgba(59,130,246,0.35)' },
  batches: { icon: Layers, accent: '#10B981', glow: 'rgba(16,185,129,0.3)' },
  rejected: { icon: XCircle, accent: '#EF4444', glow: 'rgba(239,68,68,0.3)' },
  score: { icon: Gauge, accent: '#F59E0B', glow: 'rgba(245,158,11,0.3)' },
};

function StatCard({ label, value, icon: Icon, accent, glow, delay }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1], delay }}
      className="glass-card rounded-[22px] p-5 relative overflow-hidden"
    >
      <div
        className="absolute -right-10 -top-10 h-32 w-32 rounded-full blur-[40px] opacity-15 pointer-events-none"
        style={{ background: accent }}
      />
      <div className="relative flex items-center justify-between">
        <div>
          <p className="section-label">{label}</p>
          <p className="text-[26px] font-display font-semibold text-white mt-2 tabular-nums tracking-tight">
            {value}
          </p>
        </div>
        <div
          className="h-11 w-11 rounded-2xl border border-white/20 flex items-center justify-center"
          style={{ background: `${accent}26`, boxShadow: `0 0 20px ${glow}` }}
        >
          <Icon className="h-5 w-5" style={{ color: accent }} />
        </div>
      </div>
    </motion.div>
  );
}

export default function DMFEStatisticsBar({ stats = {}, lastResult = null }) {
  const totalPending = lastResult?.total_pending ?? stats.total_pending ?? 0;
  const batchesCreated = lastResult?.batches_created ?? stats.total_batches_created ?? 0;
  const rejected = lastResult?.rejected_count ?? stats.total_rejected ?? 0;
  const avgScore = (lastResult?.avg_compatibility_score ?? stats.avg_compatibility_score ?? 0).toFixed(1);

  const cards = [
    { label: 'Pending Requests', value: totalPending, key: 'pending' },
    { label: 'Batches Created', value: batchesCreated, key: 'batches' },
    { label: 'Rejected Pairs', value: rejected, key: 'rejected' },
    { label: 'Avg Compatibility', value: `${avgScore}%`, key: 'score' },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((c, i) => (
        <StatCard key={c.key} {...c} {...CARD_THEMES[c.key]} delay={i * 0.07} />
      ))}
    </div>
  );
}