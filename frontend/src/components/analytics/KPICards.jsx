import React from 'react';
import {
  FileText, Clock, CheckCircle2, Gauge, Timer, Building2, UserCheck
} from 'lucide-react';

function SingleKPICard({ label, value, unit = '', icon: Icon, iconBg, borderColor }) {
  return (
    <div className="glass-card rounded-[20px] p-4 lg:p-5 relative overflow-hidden group">
      <div className="flex items-center justify-between relative z-10">
        <div>
          <p className="text-[10px] font-bold text-brand-text-muted uppercase tracking-wider">{label}</p>
          <div className="flex items-baseline gap-1 mt-1.5">
            <span className="text-[26px] font-display font-semibold text-white tracking-tight">{value}</span>
            {unit && <span className="text-xs text-brand-text-muted font-medium ml-1">{unit}</span>}
          </div>
        </div>
        <div
          className="p-2.5 rounded-[12px] border flex items-center justify-center shrink-0 transition-transform duration-300 group-hover:scale-110"
          style={{ borderColor: borderColor ? borderColor.replace('border-', '') : 'rgba(255,255,255,0.1)', ...iconBg }}
        >
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
      iconBg: { backgroundColor: 'rgba(59, 130, 246, 0.1)', color: '#60a5fa' },
      borderColor: 'rgba(59, 130, 246, 0.2)',
    },
    {
      label: 'Pending Requests',
      value: kpi.pending_requests ?? 0,
      icon: Clock,
      iconBg: { backgroundColor: 'rgba(245, 158, 11, 0.1)', color: '#fbbf24' },
      borderColor: 'rgba(245, 158, 11, 0.2)',
    },
    {
      label: 'Completed Requests',
      value: kpi.completed_requests ?? 0,
      icon: CheckCircle2,
      iconBg: { backgroundColor: 'rgba(34, 197, 94, 0.1)', color: '#4ade80' },
      borderColor: 'rgba(34, 197, 94, 0.2)',
    },
    {
      label: 'Requests / Min (RPM)',
      value: kpi.requests_per_minute ?? 0,
      unit: 'req/m',
      icon: Gauge,
      iconBg: { backgroundColor: 'rgba(6, 182, 212, 0.1)', color: '#22d3ee' },
      borderColor: 'rgba(6, 182, 212, 0.2)',
    },
    {
      label: 'Avg Processing Time',
      value: kpi.avg_processing_time_sec ?? 0,
      unit: 'sec',
      icon: Timer,
      iconBg: { backgroundColor: 'rgba(168, 85, 247, 0.1)', color: '#c084fc' },
      borderColor: 'rgba(168, 85, 247, 0.2)',
    },
    {
      label: 'Total Providers',
      value: kpi.total_providers ?? 0,
      icon: Building2,
      iconBg: { backgroundColor: 'rgba(99, 102, 241, 0.1)', color: '#818cf8' },
      borderColor: 'rgba(99, 102, 241, 0.2)',
    },
    {
      label: 'Active Providers',
      value: kpi.active_providers ?? 0,
      icon: UserCheck,
      iconBg: { backgroundColor: 'rgba(16, 185, 129, 0.1)', color: '#34d399' },
      borderColor: 'rgba(16, 185, 129, 0.2)',
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-5 mb-6">
      {cards.map((card) => (
        <SingleKPICard key={card.label} {...card} />
      ))}
    </div>
  );
}
