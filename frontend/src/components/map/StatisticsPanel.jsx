import React from 'react';
import { Activity, Bike, Utensils, Package, Clock } from 'lucide-react';

export default function StatisticsPanel({ stats, lastUpdated }) {
  return (
    <div className="bg-gray-800/90 backdrop-blur-md border border-gray-700/80 rounded-xl p-4 shadow-xl">
      <div className="flex items-center justify-between border-b border-gray-700/60 pb-2 mb-3">
        <h3 className="text-xs font-bold uppercase tracking-wider text-gray-300 flex items-center gap-1.5">
          <Activity className="h-4 w-4 text-indigo-400" />
          Live Request Telemetry
        </h3>
        {lastUpdated && (
          <span className="text-[11px] text-gray-400 flex items-center gap-1">
            <Clock className="h-3 w-3" />
            {lastUpdated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <div className="bg-gray-900/60 border border-gray-700/60 rounded-lg p-2.5">
          <p className="text-[11px] text-gray-400 font-medium">Active Requests</p>
          <p className="text-lg font-bold text-white leading-tight">{stats.active || 0}</p>
        </div>

        <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-2.5">
          <p className="text-[11px] text-blue-400 font-medium flex items-center gap-1">
            <Bike className="h-3 w-3" /> Ride
          </p>
          <p className="text-lg font-bold text-blue-300 leading-tight">{stats.ride || 0}</p>
        </div>

        <div className="bg-orange-500/10 border border-orange-500/30 rounded-lg p-2.5">
          <p className="text-[11px] text-orange-400 font-medium flex items-center gap-1">
            <Utensils className="h-3 w-3" /> Food
          </p>
          <p className="text-lg font-bold text-orange-300 leading-tight">{stats.food || 0}</p>
        </div>

        <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-2.5">
          <p className="text-[11px] text-green-400 font-medium flex items-center gap-1">
            <Package className="h-3 w-3" /> Parcel
          </p>
          <p className="text-lg font-bold text-green-300 leading-tight">{stats.parcel || 0}</p>
        </div>
      </div>
    </div>
  );
}
