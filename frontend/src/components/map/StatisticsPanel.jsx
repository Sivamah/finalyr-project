import React from 'react';
import { Activity, Bike, Utensils, Package, Clock } from 'lucide-react';

export default function StatisticsPanel({ stats, lastUpdated }) {
  return (
    <div className="glass-panel-strong rounded-[20px] p-4 backdrop-blur-xl">
      <div className="flex items-center justify-between pb-2.5 mb-3 border-b border-white/[0.07]">
        <h3 className="text-[10.5px] font-bold uppercase tracking-[0.16em] text-brand-text-secondary flex items-center gap-1.5">
          <Activity className="h-3.5 w-3.5 text-brand-primary" />
          Live Telemetry
        </h3>
        {lastUpdated && (
          <span className="text-[10.5px] text-brand-text-muted flex items-center gap-1 tabular-nums">
            <Clock className="h-3 w-3" />
            {lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <div className="surface-well rounded-xl p-2.5">
          <p className="text-[10px] text-brand-text-muted font-medium">Active</p>
          <p className="text-[18px] font-display font-semibold text-white leading-tight tabular-nums">{stats.active || 0}</p>
        </div>

        {[
          { label: 'Ride', value: stats.ride || 0, icon: Bike, color: '#3B82F6' },
          { label: 'Food', value: stats.food || 0, icon: Utensils, color: '#F59E0B' },
          { label: 'Parcel', value: stats.parcel || 0, icon: Package, color: '#10B981' },
        ].map((item) => (
          <div key={item.label} className="surface-well rounded-xl p-2.5">
            <p className="text-[10.5px] font-medium text-brand-text-secondary flex items-center gap-1">
              <item.icon className="h-3 w-3" style={{ color: item.color }} /> {item.label}
            </p>
            <p className="text-[18px] font-display font-semibold text-white leading-tight tabular-nums mt-0.5">{item.value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}