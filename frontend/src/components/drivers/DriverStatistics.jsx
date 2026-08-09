import React from 'react';
import { Users, UserCheck, UserX, UserMinus } from 'lucide-react';

function StatCard({ label, value, icon: Icon, color, bg }) {
  return (
    <div className="glass-card rounded-[20px] p-4 relative overflow-hidden group">
      <div className="absolute -right-8 -top-8 h-24 w-24 rounded-full blur-[36px] opacity-10 group-hover:opacity-25 transition-opacity duration-500 pointer-events-none" style={{ background: color }} />
      <div className="relative flex items-center justify-between">
        <div>
          <p className="text-[10.5px] font-medium text-brand-text-muted truncate tracking-wide">{label}</p>
          <p className="text-[22px] font-display font-semibold mt-1.5 tabular-nums tracking-tight" style={{ color }}>
            {value}
          </p>
        </div>
        <div
          className="p-2.5 rounded-xl border border-white/15 flex items-center justify-center"
          style={{ background: bg, boxShadow: `0 0 18px ${bg}` }}
        >
          <Icon className="h-4.5 w-4.5" style={{ color }} />
        </div>
      </div>
    </div>
  );
}

const THEME = {
  total: { color: '#FFFFFF', bg: 'rgba(148,163,184,0.08)' },
  available: { color: '#10B981', bg: 'rgba(16,185,129,0.16)' },
  busy: { color: '#F59E0B', bg: 'rgba(245,158,11,0.14)' },
  offline: { color: '#9AA7BD', bg: 'rgba(148,163,184,0.1)' },
};

export default function DriverStatistics({ stats = {} }) {
  const cards = [
    { label: 'Total Drivers', value: stats.total_drivers ?? 0, icon: Users, theme: 'total' },
    { label: 'Available', value: stats.available_drivers ?? 0, icon: UserCheck, theme: 'available' },
    { label: 'Busy', value: stats.busy_drivers ?? 0, icon: UserMinus, theme: 'busy' },
    { label: 'Offline', value: stats.offline_drivers ?? 0, icon: UserX, theme: 'offline' },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((c) => (
        <StatCard key={c.label} {...c} {...THEME[c.theme]} />
      ))}
    </div>
  );
}