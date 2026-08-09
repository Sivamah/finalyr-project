import React from 'react';
import {
  FileText, Activity, Clock, CheckCircle2, Gauge, Timer, Building2, UserCheck
} from 'lucide-react';

function SingleKPICard({ label, value, unit = '', icon: Icon, iconBg, borderColor }) {
  return (
    <div className={`bg-gray-800 border ${borderColor || 'border-gray-700'} rounded-xl p-4 shadow-sm hover:border-gray-600 transition-all`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs text-gray-400 font-medium truncate">{label}</p>
          <div className="flex items-baseline gap-1.5 mt-1">
            <span className="text-2xl font-bold text-white font-mono">{value}</span>
            {unit && <span className="text-xs text-gray-400 font-normal">{unit}</span>}
          </div>
        </div>
        <div className={`p-3 rounded-lg ${iconBg || 'bg-indigo-600/20 text-indigo-400'}`}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  );
}

export default function KPICards({ kpi = {} }) {
  const cards = [
    {
      label: 'Total Requests',
      value: kpi.total_requests ?? 0,
      icon: FileText,
      iconBg: 'bg-blue-500/10 text-blue-400',
      borderColor: 'border-blue-500/20',
    },
    {
      label: 'Pending Requests',
      value: kpi.pending_requests ?? 0,
      icon: Clock,
      iconBg: 'bg-amber-500/10 text-amber-400',
      borderColor: 'border-amber-500/20',
    },
    {
      label: 'Completed Requests',
      value: kpi.completed_requests ?? 0,
      icon: CheckCircle2,
      iconBg: 'bg-green-500/10 text-green-400',
      borderColor: 'border-green-500/20',
    },
    {
      label: 'Requests / Min (RPM)',
      value: kpi.requests_per_minute ?? 0,
      unit: 'req/m',
      icon: Gauge,
      iconBg: 'bg-cyan-500/10 text-cyan-400',
      borderColor: 'border-cyan-500/20',
    },
    {
      label: 'Avg Processing Time',
      value: kpi.avg_processing_time_sec ?? 0,
      unit: 'sec',
      icon: Timer,
      iconBg: 'bg-purple-500/10 text-purple-400',
      borderColor: 'border-purple-500/20',
    },
    {
      label: 'Total Providers',
      value: kpi.total_providers ?? 0,
      icon: Building2,
      iconBg: 'bg-indigo-500/10 text-indigo-400',
      borderColor: 'border-indigo-500/20',
    },
    {
      label: 'Active Providers',
      value: kpi.active_providers ?? 0,
      icon: UserCheck,
      iconBg: 'bg-emerald-500/10 text-emerald-400',
      borderColor: 'border-emerald-500/20',
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {cards.map((card) => (
        <SingleKPICard key={card.label} {...card} />
      ))}
    </div>
  );
}
