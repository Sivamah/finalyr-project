import React from 'react';
import { Filter, Calendar, RotateCcw, Building2, Layers, Activity } from 'lucide-react';

export default function AnalyticsFilters({
  filters,
  onFilterChange,
  onResetFilters,
  providerOptions = [],
}) {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 shadow-sm mb-6">
      <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
        {/* Title */}
        <div className="flex items-center gap-2 text-white font-semibold text-sm">
          <Filter className="h-4 w-4 text-indigo-400" />
          <span>Dashboard Filters</span>
        </div>

        {/* Filter Controls Grid */}
        <div className="flex flex-wrap items-center gap-3 w-full lg:w-auto text-sm">
          {/* Preset Date Range Buttons */}
          <div className="flex items-center bg-gray-900 border border-gray-700 rounded-lg p-0.5">
            <button
              onClick={() => onFilterChange('preset', 'all')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                filters.preset === 'all'
                  ? 'bg-indigo-600 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              All Time
            </button>
            <button
              onClick={() => onFilterChange('preset', 'today')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                filters.preset === 'today'
                  ? 'bg-indigo-600 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              Today
            </button>
            <button
              onClick={() => onFilterChange('preset', 'hour')}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                filters.preset === 'hour'
                  ? 'bg-indigo-600 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              Last 1 Hour
            </button>
          </div>

          {/* Request Type */}
          <div className="flex items-center gap-1.5 bg-gray-900 border border-gray-700 rounded-lg px-3 py-1.5">
            <Layers className="h-3.5 w-3.5 text-blue-400" />
            <select
              value={filters.requestType}
              onChange={(e) => onFilterChange('requestType', e.target.value)}
              className="bg-transparent text-gray-200 text-xs font-medium focus:outline-none cursor-pointer"
            >
              <option value="All" className="bg-gray-800 text-white">All Request Types</option>
              <option value="ride" className="bg-gray-800 text-white">Ride</option>
              <option value="food" className="bg-gray-800 text-white">Food Delivery</option>
              <option value="parcel" className="bg-gray-800 text-white">Parcel Delivery</option>
            </select>
          </div>

          {/* Provider */}
          <div className="flex items-center gap-1.5 bg-gray-900 border border-gray-700 rounded-lg px-3 py-1.5">
            <Building2 className="h-3.5 w-3.5 text-orange-400" />
            <select
              value={filters.providerId}
              onChange={(e) => onFilterChange('providerId', e.target.value)}
              className="bg-transparent text-gray-200 text-xs font-medium focus:outline-none cursor-pointer"
            >
              <option value="0" className="bg-gray-800 text-white">All Providers</option>
              {providerOptions.map((p) => (
                <option key={p.id || p.provider_id} value={p.id || p.provider_id} className="bg-gray-800 text-white">
                  {p.name || p.provider_name}
                </option>
              ))}
            </select>
          </div>

          {/* Request Status */}
          <div className="flex items-center gap-1.5 bg-gray-900 border border-gray-700 rounded-lg px-3 py-1.5">
            <Activity className="h-3.5 w-3.5 text-green-400" />
            <select
              value={filters.status}
              onChange={(e) => onFilterChange('status', e.target.value)}
              className="bg-transparent text-gray-200 text-xs font-medium focus:outline-none cursor-pointer"
            >
              <option value="All" className="bg-gray-800 text-white">All Statuses</option>
              <option value="Pending" className="bg-gray-800 text-white">Pending / Active</option>
              <option value="Completed" className="bg-gray-800 text-white">Completed</option>
            </select>
          </div>

          {/* Reset Filters */}
          <button
            onClick={onResetFilters}
            className="flex items-center gap-1 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg text-xs font-medium transition-colors"
            title="Reset Filters"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Reset
          </button>
        </div>
      </div>
    </div>
  );
}
