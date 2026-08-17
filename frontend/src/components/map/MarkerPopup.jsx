import React from 'react';
import { Bike, Utensils, Package, MapPin, X } from 'lucide-react';

const TYPE_META = {
  ride: { label: 'Ride', color: 'bg-blue-600', textColor: 'text-blue-400', Icon: Bike },
  food: { label: 'Food', color: 'bg-orange-600', textColor: 'text-orange-400', Icon: Utensils },
  parcel: { label: 'Parcel', color: 'bg-green-600', textColor: 'text-green-400', Icon: Package },
};

const PRIORITY_CLASSES = {
  High: 'text-red-400 bg-red-500/10 border-red-500/30',
  Medium: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
  Low: 'text-green-400 bg-green-500/10 border-green-500/30',
};

export default function MarkerPopup({ request, onClose }) {
  if (!request) return null;

  const reqType = request.request_type?.toLowerCase() || 'ride';
  const meta = TYPE_META[reqType] || TYPE_META.ride;
  const { Icon } = meta;

  const createdTimeStr = request.created_at
    ? new Date(request.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    : '—';

  return (
    <div className="bg-gray-800 text-white border border-gray-700 rounded-xl shadow-2xl p-4 w-72 space-y-3 font-sans">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-700 pb-2">
        <div className="flex items-center gap-2">
          <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-xs font-bold text-white ${meta.color}`}>
            <Icon className="h-3 w-3" />
            {meta.label}
          </span>
          <span className="text-gray-300 font-mono text-sm font-bold">#{request.id}</span>
        </div>
        {onClose && (
          <button onClick={onClose} className="text-gray-400 hover:text-white p-1 rounded hover:bg-gray-700">
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Provider & Priority */}
      <div className="flex items-center justify-between text-xs">
        <span className="text-gray-300 font-semibold">{request.provider_name || 'Unassigned'}</span>
        <span className={`px-2 py-0.5 rounded border text-[11px] font-medium ${PRIORITY_CLASSES[request.priority] || PRIORITY_CLASSES.Medium}`}>
          {request.priority || 'Medium'} Priority
        </span>
      </div>

      {/* Route Addresses */}
      <div className="bg-gray-900/80 rounded-lg p-2.5 space-y-1.5 text-xs">
        <div className="flex items-start gap-1.5">
          <MapPin className="h-3.5 w-3.5 text-green-400 shrink-0 mt-0.5" />
          <div className="min-w-0">
            <span className="text-gray-400 text-[10px] uppercase font-bold block">Pickup</span>
            <span className="text-gray-200 font-medium truncate block">{request.pickup_address || '—'}</span>
          </div>
        </div>

        <div className="flex items-start gap-1.5 border-t border-gray-800 pt-1.5">
          <MapPin className="h-3.5 w-3.5 text-red-400 shrink-0 mt-0.5" />
          <div className="min-w-0">
            <span className="text-gray-400 text-[10px] uppercase font-bold block">Destination</span>
            <span className="text-gray-200 font-medium truncate block">{request.drop_address || '—'}</span>
          </div>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-3 gap-1.5 text-center text-xs border-t border-gray-700 pt-2 text-gray-300">
        <div>
          <span className="text-[10px] text-gray-400 block">Distance</span>
          <span className="font-semibold text-indigo-300">{request.estimated_distance_km?.toFixed(1)} km</span>
        </div>
        <div>
          <span className="text-[10px] text-gray-400 block">Est. Time</span>
          <span className="font-semibold text-cyan-300">~{request.estimated_time_min?.toFixed(0)} m</span>
        </div>
        <div>
          <span className="text-[10px] text-gray-400 block">Created</span>
          <span className="font-semibold text-gray-300 text-[11px]">{createdTimeStr}</span>
        </div>
      </div>
    </div>
  );
}
