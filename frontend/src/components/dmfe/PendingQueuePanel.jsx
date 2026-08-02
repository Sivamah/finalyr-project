import React from 'react';
import { Activity, Bike, ShoppingBag, Package, Clock, AlertCircle } from 'lucide-react';

const TYPE_CONFIG = {
  ride:   { label: 'Ride',    icon: Bike,        color: 'text-indigo-400',  bg: 'bg-indigo-500/10 border-indigo-500/20' },
  food:   { label: 'Food',    icon: ShoppingBag, color: 'text-green-400',   bg: 'bg-green-500/10  border-green-500/20'  },
  parcel: { label: 'Parcel',  icon: Package,     color: 'text-amber-400',   bg: 'bg-amber-500/10  border-amber-500/20'  },
};

const PRIORITY_BADGE = {
  High:   'bg-red-500/15 text-red-400   border-red-500/30',
  Medium: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
  Low:    'bg-gray-600/40  text-gray-400  border-gray-600/40',
};

function fmtTime(ts) {
  if (!ts) return '—';
  try {
    return new Date(ts).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
  } catch {
    return String(ts).slice(11, 16);
  }
}

function RequestRow({ req, index }) {
  const cfg = TYPE_CONFIG[req.request_type] || TYPE_CONFIG.ride;
  const Icon = cfg.icon;
  const priClass = PRIORITY_BADGE[req.priority] || PRIORITY_BADGE.Medium;

  return (
    <div className={`flex items-start gap-3 p-3 rounded-lg border ${cfg.bg} transition-all hover:scale-[1.01]`}>
      <div className={`mt-0.5 p-1.5 rounded-lg bg-gray-900/60 ${cfg.color}`}>
        <Icon className="h-3.5 w-3.5" />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`text-[11px] font-bold ${cfg.color}`}>{cfg.label} #{req.id}</span>
          <span className={`text-[10px] px-1.5 py-0.5 rounded border font-bold ${priClass}`}>
            {req.priority}
          </span>
          {req.demand > 1 && (
            <span className="text-[10px] text-gray-400">×{req.demand}</span>
          )}
        </div>
        <p className="text-xs text-white font-medium mt-0.5 truncate">
          {req.pickup_address} → {req.drop_address}
        </p>
        <div className="flex items-center gap-1 mt-0.5 text-[10px] text-gray-500">
          <Clock className="h-3 w-3" />
          <span>{fmtTime(req.created_at)}</span>
          {req.estimated_distance_km > 0 && (
            <span className="ml-1">{req.estimated_distance_km} km</span>
          )}
        </div>
      </div>
    </div>
  );
}

export default function PendingQueuePanel({ requests = [], loading = false, onRefresh }) {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl flex flex-col h-full shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700 shrink-0">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <Activity className="h-4 w-4 text-indigo-400" />
          Pending Queue
          <span className="px-2 py-0.5 rounded-full text-[10px] bg-indigo-500/20 text-indigo-400 font-bold border border-indigo-500/30">
            {requests.length}
          </span>
        </h3>
        {onRefresh && (
          <button
            onClick={onRefresh}
            className="text-xs text-indigo-400 hover:text-indigo-300 font-medium transition-colors"
          >
            Refresh
          </button>
        )}
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {loading ? (
          <div className="flex items-center justify-center h-24 text-gray-500 text-xs">
            Loading pending requests…
          </div>
        ) : requests.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-24 text-gray-500 gap-2">
            <AlertCircle className="h-6 w-6 opacity-40" />
            <p className="text-xs">No pending requests in queue</p>
          </div>
        ) : (
          requests.map((req, i) => <RequestRow key={req.id} req={req} index={i} />)
        )}
      </div>
    </div>
  );
}
