import React from 'react';
import { Search, Filter, Layers, Building2, BrainCircuit, Activity, RotateCcw } from 'lucide-react';

export default function ExplanationFilters({
  search,
  onSearchChange,
  filters,
  onFilterChange,
  onResetFilters,
  providerOptions = [],
}) {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 shadow-sm mb-6">
      <div className="flex flex-col lg:flex-row gap-4 items-stretch lg:items-center justify-between">
        {/* Search Input */}
        <div className="relative flex-1 min-w-[280px]">
          <Search className="absolute left-3.5 top-2.5 h-4 w-4 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search explanations by Request ID, Provider, Type, or Reason..."
            className="w-full pl-10 pr-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        {/* Filters Dropdowns */}
        <div className="flex flex-wrap items-center gap-2.5 text-xs">
          {/* Request Type */}
          <div className="flex items-center gap-1.5 bg-gray-900 border border-gray-700 rounded-lg px-3 py-2">
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
          <div className="flex items-center gap-1.5 bg-gray-900 border border-gray-700 rounded-lg px-3 py-2">
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

          {/* Decision */}
          <div className="flex items-center gap-1.5 bg-gray-900 border border-gray-700 rounded-lg px-3 py-2">
            <BrainCircuit className="h-3.5 w-3.5 text-indigo-400" />
            <select
              value={filters.decision}
              onChange={(e) => onFilterChange('decision', e.target.value)}
              className="bg-transparent text-gray-200 text-xs font-medium focus:outline-none cursor-pointer"
            >
              <option value="All" className="bg-gray-800 text-white">All Decisions</option>
              <option value="Compatible" className="bg-gray-800 text-white">Compatible for Batching</option>
              <option value="Standalone" className="bg-gray-800 text-white">Standalone Direct Routing</option>
              <option value="Deferred" className="bg-gray-800 text-white">Deferred for Next Batch</option>
            </select>
          </div>

          {/* Status */}
          <div className="flex items-center gap-1.5 bg-gray-900 border border-gray-700 rounded-lg px-3 py-2">
            <Activity className="h-3.5 w-3.5 text-green-400" />
            <select
              value={filters.status}
              onChange={(e) => onFilterChange('status', e.target.value)}
              className="bg-transparent text-gray-200 text-xs font-medium focus:outline-none cursor-pointer"
            >
              <option value="All" className="bg-gray-800 text-white">All Statuses</option>
              <option value="Evaluated" className="bg-gray-800 text-white">Evaluated</option>
              <option value="Pending" className="bg-gray-800 text-white">Pending</option>
            </select>
          </div>

          {/* Reset */}
          <button
            onClick={onResetFilters}
            className="flex items-center gap-1 px-3 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg text-xs font-medium transition-colors"
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
