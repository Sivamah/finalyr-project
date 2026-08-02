import React from 'react';
import { Bike, Utensils, Package, Navigation, Clock, PieChart, AlertCircle } from 'lucide-react';

export default function RequestAnalytics({ data = {} }) {
  const rideCount = data.total_ride_requests ?? 0;
  const foodCount = data.total_food_requests ?? 0;
  const parcelCount = data.total_parcel_requests ?? 0;
  const totalCount = rideCount + foodCount + parcelCount || 1;

  const ridePct = Math.round((rideCount / totalCount) * 100);
  const foodPct = Math.round((foodCount / totalCount) * 100);
  const parcelPct = Math.round((parcelCount / totalCount) * 100);

  const completionRate = data.completion_rate_pct ?? 0;
  const pendingRate = data.pending_rate_pct ?? 0;

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-5 shadow-sm mb-6">
      <div className="flex items-center justify-between mb-4 border-b border-gray-700 pb-3">
        <h3 className="text-base font-bold text-white flex items-center gap-2">
          <PieChart className="h-5 w-5 text-indigo-400" />
          Request Analytics Breakdown
        </h3>
        <span className="text-xs bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-2.5 py-1 rounded-full font-semibold">
          Operational Overview
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Category Breakdown */}
        <div className="bg-gray-900/60 border border-gray-700/60 rounded-xl p-4 space-y-3">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Service Volumes</p>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-2 text-xs text-blue-400 font-medium">
                <Bike className="h-3.5 w-3.5" /> Total Rides
              </span>
              <span className="text-sm font-bold text-white font-mono">{rideCount}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-2 text-xs text-orange-400 font-medium">
                <Utensils className="h-3.5 w-3.5" /> Total Food
              </span>
              <span className="text-sm font-bold text-white font-mono">{foodCount}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-2 text-xs text-purple-400 font-medium">
                <Package className="h-3.5 w-3.5" /> Total Parcels
              </span>
              <span className="text-sm font-bold text-white font-mono">{parcelCount}</span>
            </div>
          </div>
        </div>

        {/* Distance & Travel Metrics */}
        <div className="bg-gray-900/60 border border-gray-700/60 rounded-xl p-4 space-y-3">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Distance & Estimates</p>
          <div>
            <p className="text-xs text-gray-400 flex items-center gap-1">
              <Navigation className="h-3.5 w-3.5 text-cyan-400" /> Avg Estimated Distance
            </p>
            <p className="text-xl font-bold text-cyan-400 font-mono mt-0.5">
              {data.avg_estimated_distance_km ?? 0} <span className="text-xs font-normal text-gray-400">km</span>
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-400 flex items-center gap-1">
              <Clock className="h-3.5 w-3.5 text-amber-400" /> Avg Estimated Travel Time
            </p>
            <p className="text-xl font-bold text-amber-400 font-mono mt-0.5">
              ~{data.avg_estimated_travel_time_min ?? 0} <span className="text-xs font-normal text-gray-400">mins</span>
            </p>
          </div>
        </div>

        {/* Completion Rate Progress */}
        <div className="bg-gray-900/60 border border-gray-700/60 rounded-xl p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Completion Rate</span>
              <span className="text-sm font-bold text-green-400 font-mono">{completionRate}%</span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-2.5 mt-2 overflow-hidden">
              <div
                className="bg-green-500 h-2.5 rounded-full transition-all duration-500"
                style={{ width: `${Math.min(100, Math.max(0, completionRate))}%` }}
              />
            </div>
          </div>
          <p className="text-xs text-gray-500 mt-2">Percentage of requests processed & fulfilled</p>
        </div>

        {/* Pending Rate Progress */}
        <div className="bg-gray-900/60 border border-gray-700/60 rounded-xl p-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Pending Rate</span>
              <span className="text-sm font-bold text-amber-400 font-mono">{pendingRate}%</span>
            </div>
            <div className="w-full bg-gray-700 rounded-full h-2.5 mt-2 overflow-hidden">
              <div
                className="bg-amber-500 h-2.5 rounded-full transition-all duration-500"
                style={{ width: `${Math.min(100, Math.max(0, pendingRate))}%` }}
              />
            </div>
          </div>
          <p className="text-xs text-gray-500 mt-2">Percentage of requests remaining in active queue</p>
        </div>
      </div>
    </div>
  );
}
