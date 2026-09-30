import React from 'react';
import { Bike, Utensils, Package, Navigation, Clock, PieChart } from 'lucide-react';

export default function RequestAnalytics({ data = {} }) {
  const rideCount = data.total_ride_requests ?? 0;
  const foodCount = data.total_food_requests ?? 0;
  const parcelCount = data.total_parcel_requests ?? 0;

  const completionRate = data.completion_rate_pct ?? 0;
  const pendingRate = data.pending_rate_pct ?? 0;

  return (
    <div className="glass-panel rounded-[20px] p-5 lg:p-6 shadow-sm mb-6">
      <div className="flex items-center justify-between mb-5 border-b border-white/10 pb-4">
        <h3 className="text-base font-display font-semibold text-white flex items-center gap-2">
          <PieChart className="h-5 w-5 text-brand-primary" />
          Request Analytics Breakdown
        </h3>
        <span className="text-[10px] bg-brand-primary/10 text-brand-primary border border-brand-primary/20 px-3 py-1.5 rounded-full font-bold uppercase tracking-wider">
          Operational Overview
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Category Breakdown */}
        <div className="glass-card bg-black/20 border border-white/5 rounded-[16px] p-4 lg:p-5 space-y-4">
          <p className="text-[10px] font-bold text-brand-text-muted uppercase tracking-wider">Service Volumes</p>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-2 text-xs text-blue-400 font-semibold">
                <Bike className="h-4 w-4" /> Total Rides
              </span>
              <span className="text-base font-bold text-white font-mono">{rideCount}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-2 text-xs text-orange-400 font-semibold">
                <Utensils className="h-4 w-4" /> Total Food
              </span>
              <span className="text-base font-bold text-white font-mono">{foodCount}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-2 text-xs text-purple-400 font-semibold">
                <Package className="h-4 w-4" /> Total Parcels
              </span>
              <span className="text-base font-bold text-white font-mono">{parcelCount}</span>
            </div>
          </div>
        </div>

        {/* Distance & Travel Metrics */}
        <div className="glass-card bg-black/20 border border-white/5 rounded-[16px] p-4 lg:p-5 space-y-4">
          <p className="text-[10px] font-bold text-brand-text-muted uppercase tracking-wider">Distance & Estimates</p>
          <div>
            <p className="text-xs text-brand-text-muted flex items-center gap-1.5 font-medium">
              <Navigation className="h-4 w-4 text-cyan-400" /> Avg Estimated Distance
            </p>
            <p className="text-2xl font-bold text-cyan-400 font-mono mt-1">
              {data.avg_estimated_distance_km ?? 0} <span className="text-xs font-medium text-brand-text-muted">km</span>
            </p>
          </div>
          <div>
            <p className="text-xs text-brand-text-muted flex items-center gap-1.5 font-medium">
              <Clock className="h-4 w-4 text-amber-400" /> Avg Estimated Travel Time
            </p>
            <p className="text-2xl font-bold text-amber-400 font-mono mt-1">
              ~{data.avg_estimated_travel_time_min ?? 0} <span className="text-xs font-medium text-brand-text-muted">mins</span>
            </p>
          </div>
        </div>

        {/* Completion Rate Progress */}
        <div className="glass-card bg-black/20 border border-white/5 rounded-[16px] p-4 lg:p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-bold text-brand-text-muted uppercase tracking-wider">Completion Rate</span>
              <span className="text-xl font-bold text-brand-success font-mono">{completionRate}%</span>
            </div>
            <div className="w-full bg-black/40 rounded-full h-3 mt-3 overflow-hidden border border-white/5">
              <div
                className="bg-brand-success h-full rounded-full transition-all duration-500 relative"
                style={{ width: `${Math.min(100, Math.max(0, completionRate))}%` }}
              >
                <div className="absolute inset-0 bg-white/20" />
              </div>
            </div>
          </div>
          <p className="text-[11px] text-brand-text-muted mt-3">Percentage of requests processed & fulfilled</p>
        </div>

        {/* Pending Rate Progress */}
        <div className="glass-card bg-black/20 border border-white/5 rounded-[16px] p-4 lg:p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-bold text-brand-text-muted uppercase tracking-wider">Pending Rate</span>
              <span className="text-xl font-bold text-brand-warning font-mono">{pendingRate}%</span>
            </div>
            <div className="w-full bg-black/40 rounded-full h-3 mt-3 overflow-hidden border border-white/5">
              <div
                className="bg-brand-warning h-full rounded-full transition-all duration-500 relative"
                style={{ width: `${Math.min(100, Math.max(0, pendingRate))}%` }}
              >
                <div className="absolute inset-0 bg-white/20" />
              </div>
            </div>
          </div>
          <p className="text-[11px] text-brand-text-muted mt-3">Percentage of requests remaining in active queue</p>
        </div>
      </div>
    </div>
  );
}
