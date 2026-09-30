import React from 'react';
import { Filter, RotateCcw, Building2, Layers, Activity } from 'lucide-react';

export default function AnalyticsFilters({
  filters,
  onFilterChange,
  onResetFilters,
  providerOptions = [],
}) {
  return (
    <div className="glass-panel rounded-[20px] p-4 lg:p-5 shadow-sm mb-6">
      <div className="flex flex-col xl:flex-row xl:flex-wrap items-start xl:items-center justify-between gap-3 lg:gap-4">
        {/* Title */}
        <div className="flex items-center gap-2 text-white font-display font-semibold text-sm shrink-0 mb-2 xl:mb-0">
          <Filter className="h-4 w-4 text-indigo-400" />
          <span>Dashboard Filters</span>
        </div>

        {/* Filter Controls — one horizontal cluster from sm up, wrapping as a
            unit. `flex-wrap` (never `nowrap`) is deliberate: at 1280 the 272px
            floating sidebar leaves ~888px, so title + controls cannot share a
            line. Wrapping keeps the row intact instead of overflowing it. */}
        <div className="flex flex-col sm:flex-row sm:flex-wrap items-start sm:items-center gap-3 lg:gap-4 w-full xl:w-auto min-w-0 text-sm">
          {/* Preset Date Range Buttons */}
          <div className="flex items-center bg-black/40 border border-white/10 rounded-[10px] p-0.5 shrink-0 w-full sm:w-auto">
            <button
              onClick={() => onFilterChange('preset', 'all')}
              className={`flex-1 sm:flex-none px-3 py-1.5 rounded-[8px] text-[11px] font-bold uppercase tracking-wider transition-colors ${
                filters.preset === 'all'
                  ? 'bg-brand-primary text-white shadow-sm'
                  : 'text-brand-text-muted hover:text-white'
              }`}
            >
              All Time
            </button>
            <button
              onClick={() => onFilterChange('preset', 'today')}
              className={`flex-1 sm:flex-none px-3 py-1.5 rounded-[8px] text-[11px] font-bold uppercase tracking-wider transition-colors ${
                filters.preset === 'today'
                  ? 'bg-brand-primary text-white shadow-sm'
                  : 'text-brand-text-muted hover:text-white'
              }`}
            >
              Today
            </button>
            <button
              onClick={() => onFilterChange('preset', 'hour')}
              className={`flex-1 sm:flex-none px-3 py-1.5 rounded-[8px] text-[11px] font-bold uppercase tracking-wider transition-colors ${
                filters.preset === 'hour'
                  ? 'bg-brand-primary text-white shadow-sm'
                  : 'text-brand-text-muted hover:text-white'
              }`}
            >
              Last 1 Hour
            </button>
          </div>

          <div className="hidden xl:block w-px h-6 bg-white/10 shrink-0" />

          {/* Select Controls & Reset — `shrink-0` removed so this group wraps
              to the next line on narrow viewports instead of overflowing them.
              The per-control `sm:w-auto` overrides `.input-glass`'s `w-full`,
              which under `sm:flex-none` (flex-basis: auto) would otherwise make
              every select claim a full row. */}
          <div className="flex flex-wrap items-center gap-3 w-full sm:w-auto">
            {/* Request Type */}
            <div className="flex items-center gap-2 input-glass px-3 py-1.5 flex-1 sm:flex-none sm:w-auto">
              <Layers className="h-3.5 w-3.5 text-blue-400 shrink-0" />
              <select
                value={filters.requestType}
                onChange={(e) => onFilterChange('requestType', e.target.value)}
                className="bg-transparent text-gray-200 text-xs font-semibold focus:outline-none cursor-pointer border-none p-0 w-full sm:w-auto"
              >
                <option value="All" className="bg-gray-900 text-white">All Request Types</option>
                <option value="ride" className="bg-gray-900 text-white">Ride</option>
                <option value="food" className="bg-gray-900 text-white">Food Delivery</option>
                <option value="parcel" className="bg-gray-900 text-white">Parcel Delivery</option>
              </select>
            </div>

            {/* Provider */}
            <div className="flex items-center gap-2 input-glass px-3 py-1.5 flex-1 sm:flex-none sm:w-auto">
              <Building2 className="h-3.5 w-3.5 text-orange-400 shrink-0" />
              <select
                value={filters.providerId}
                onChange={(e) => onFilterChange('providerId', e.target.value)}
                className="bg-transparent text-gray-200 text-xs font-semibold focus:outline-none cursor-pointer border-none p-0 w-full sm:w-auto"
              >
                <option value="0" className="bg-gray-900 text-white">All Providers</option>
                {providerOptions.map((p) => (
                  <option key={p.id || p.provider_id} value={p.id || p.provider_id} className="bg-gray-900 text-white">
                    {p.name || p.provider_name}
                  </option>
                ))}
              </select>
            </div>

            {/* Request Status */}
            <div className="flex items-center gap-2 input-glass px-3 py-1.5 flex-1 sm:flex-none sm:w-auto">
              <Activity className="h-3.5 w-3.5 text-green-400 shrink-0" />
              <select
                value={filters.status}
                onChange={(e) => onFilterChange('status', e.target.value)}
                className="bg-transparent text-gray-200 text-xs font-semibold focus:outline-none cursor-pointer border-none p-0 w-full sm:w-auto"
              >
                <option value="All" className="bg-gray-900 text-white">All Statuses</option>
                <option value="Pending" className="bg-gray-900 text-white">Pending / Active</option>
                <option value="Completed" className="bg-gray-900 text-white">Completed</option>
              </select>
            </div>

            {/* Reset Filters */}
            <button
              onClick={onResetFilters}
              className="btn-ghost py-1.5 px-3 text-xs shrink-0"
              title="Reset Filters"
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Reset
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
