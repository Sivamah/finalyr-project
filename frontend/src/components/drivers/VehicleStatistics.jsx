import React from 'react';
import { Truck, CheckCircle2, Navigation, Wrench } from 'lucide-react';

function StatCard({ label, value, icon: Icon, color, bg }) {
  return (
    <div className="glass-card rounded-[18px] p-3.5 relative overflow-hidden group">
      <div className="absolute -right-8 -top-8 h-20 w-20 rounded-full blur-[24px] opacity-30 group-hover:opacity-60 transition-opacity duration-500 pointer-events-none" style={{ background: color }} />
      <div className="relative flex items-center justify-between">
        <div>
          <p className="text-[10px] font-medium text-brand-text-muted truncate tracking-wider uppercase">{label}</p>
          <p className="text-[20px] font-display font-semibold mt-1 tabular-nums tracking-tight" style={{ color }}>
            {value}
          </p>
        </div>
        <div
          className="p-2 rounded-[10px] border border-white/10 flex items-center justify-center"
          style={{ background: bg, boxShadow: `0 0 15px ${bg}` }}
        >
          <Icon className="h-4 w-4" style={{ color }} />
        </div>
      </div>
    </div>
  );
}

const THEME = {
  total: { color: '#FFFFFF', bg: 'rgba(148,163,184,0.08)' },
  available: { color: '#10B981', bg: 'rgba(16,185,129,0.16)' },
  service: { color: '#3B82F6', bg: 'rgba(59,130,246,0.16)' },
  maintenance: { color: '#F59E0B', bg: 'rgba(245,158,11,0.14)' },
};

export default function VehicleStatistics({ stats = {} }) {
  const cards = [
    { label: 'Total Vehicles', value: stats.total_vehicles ?? 0, icon: Truck, theme: 'total' },
    { label: 'Available', value: stats.available_vehicles ?? 0, icon: CheckCircle2, theme: 'available' },
    { label: 'In Service', value: stats.vehicles_in_service ?? 0, icon: Navigation, theme: 'service' },
    { label: 'Maintenance', value: stats.maintenance_vehicles ?? 0, icon: Wrench, theme: 'maintenance' },
  ];

  return (
    <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
      {cards.map((c) => (
        <StatCard key={c.label} {...c} {...THEME[c.theme]} />
      ))}
    </div>
  );
}