import React from 'react';
import { Activity, Layers, XCircle, BarChart2 } from 'lucide-react';

function StatCard({ label, value, icon: Icon, colorClass, borderClass }) {
  return (
    <div className={`bg-gray-800 border ${borderClass} rounded-xl p-4 flex items-center justify-between shadow-sm`}>
      <div>
        <p className="text-xs text-gray-400 font-medium">{label}</p>
        <p className={`text-xl font-bold font-mono mt-0.5 ${colorClass}`}>{value}</p>
      </div>
      <div className={`p-2.5 rounded-lg bg-gray-900/60 ${colorClass}`}>
        <Icon className="h-5 w-5" />
      </div>
    </div>
  );
}

export default function DMFEStatisticsBar({ stats = {}, lastResult = null }) {
  const totalPending   = lastResult?.total_pending ?? stats.total_pending ?? 0;
  const batchesCreated = lastResult?.batches_created ?? stats.total_batches_created ?? 0;
  const rejected       = lastResult?.rejected_count ?? stats.total_rejected ?? 0;
  const avgScore       = (lastResult?.avg_compatibility_score ?? stats.avg_compatibility_score ?? 0).toFixed(1);

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      <StatCard
        label="Pending Requests"
        value={totalPending}
        icon={Activity}
        colorClass="text-indigo-400"
        borderClass="border-indigo-500/20"
      />
      <StatCard
        label="Batches Created"
        value={batchesCreated}
        icon={Layers}
        colorClass="text-green-400"
        borderClass="border-green-500/20"
      />
      <StatCard
        label="Rejected Pairs"
        value={rejected}
        icon={XCircle}
        colorClass="text-red-400"
        borderClass="border-red-500/20"
      />
      <StatCard
        label="Avg Compatibility"
        value={`${avgScore}%`}
        icon={BarChart2}
        colorClass="text-amber-400"
        borderClass="border-amber-500/20"
      />
    </div>
  );
}
