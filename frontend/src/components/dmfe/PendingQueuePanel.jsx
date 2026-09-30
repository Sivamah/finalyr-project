import React from 'react';
import { Activity, Bike, ShoppingBag, Package, Clock, AlertCircle } from 'lucide-react';

const TYPE_CONFIG = {
  ride:   { label: 'Ride',    icon: Bike,        color: 'text-brand-primary',  bg: 'bg-brand-primary/10 border-brand-primary/20' },
  food:   { label: 'Food',    icon: ShoppingBag, color: 'text-brand-warning',   bg: 'bg-brand-warning/10  border-brand-warning/20'  },
  parcel: { label: 'Parcel',  icon: Package,     color: 'text-brand-accent',   bg: 'bg-brand-accent/10  border-brand-accent/20'  },
};

const PRIORITY_BADGE = {
  High:   'bg-brand-danger/15 text-brand-danger border-brand-danger/30',
  Medium: 'bg-brand-warning/15 text-brand-warning border-brand-warning/30',
  Low:    'bg-white/5 text-white/50 border-white/10',
};

function fmtTime(ts) {
  if (!ts) return '—';
  try {
    return new Date(ts).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
  } catch {
    return String(ts).slice(11, 16);
  }
}

function RequestRow({ req }) {
  const cfg = TYPE_CONFIG[req.request_type] || TYPE_CONFIG.ride;
  const Icon = cfg.icon;
  const priClass = PRIORITY_BADGE[req.priority] || PRIORITY_BADGE.Medium;

  return (
    <div className={`flex items-start gap-3.5 p-4 rounded-xl border ${cfg.bg} transition-colors hover:bg-white/[0.04]`}>
      <div className={`mt-0.5 p-2 rounded-xl bg-black/20 ${cfg.color}`}>
        <Icon className="h-4 w-4" />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2 flex-wrap mb-1">
          <div className="flex items-center gap-2">
            <span className={`text-[11px] tracking-wide font-bold uppercase ${cfg.color}`}>{cfg.label} #{req.id}</span>
            <span className={`text-[9px] uppercase px-1.5 py-0.5 rounded border font-bold tracking-wider ${priClass}`}>
              {req.priority}
            </span>
          </div>
          {req.demand > 1 && (
            <span className="text-[10px] text-brand-text-muted font-mono bg-white/5 px-1.5 py-0.5 rounded">×{req.demand}</span>
          )}
        </div>
        <p className="text-[12.5px] text-white/90 font-medium truncate mb-1.5">
          {req.pickup_address} <span className="text-white/30 mx-1">→</span> {req.drop_address}
        </p>
        <div className="flex items-center gap-2 text-[11px] text-brand-text-muted font-medium">
          <div className="flex items-center gap-1 bg-black/20 px-2 py-0.5 rounded-md">
            <Clock className="h-3 w-3" />
            <span>{fmtTime(req.created_at)}</span>
          </div>
          {req.estimated_distance_km > 0 && (
            <div className="bg-black/20 px-2 py-0.5 rounded-md">
              {req.estimated_distance_km} km
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function PendingQueuePanel({ requests = [], loading = false, onRefresh }) {
  return (
    <div className="glass-panel rounded-2xl flex flex-col h-full shadow-[0_10px_40px_rgba(5,8,22,0.6)] border border-white/[0.1]">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.08] shrink-0">
        <h3 className="text-[14px] font-bold text-white flex items-center gap-2.5">
          <Activity className="h-4 w-4 text-brand-primary" />
          Pending Queue
          <span className="px-2.5 py-0.5 rounded-full text-[10px] bg-white/[0.06] text-brand-text-muted font-bold border border-white/5">
            {requests.length}
          </span>
        </h3>
        {onRefresh && (
          <button
            onClick={onRefresh}
            className="text-[12px] text-brand-primary/80 hover:text-brand-primary font-medium transition-colors"
          >
            Refresh
          </button>
        )}
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-3">
        {loading ? (
          <div className="flex items-center justify-center h-32 text-brand-text-muted text-[12px]">
            Loading pending requests…
          </div>
        ) : requests.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-brand-text-muted gap-3">
            <AlertCircle className="h-7 w-7 opacity-30" />
            <p className="text-[12px]">No pending requests in queue</p>
          </div>
        ) : (
          requests.map((req, i) => <RequestRow key={req.id} req={req} index={i} />)
        )}
      </div>
    </div>
  );
}
