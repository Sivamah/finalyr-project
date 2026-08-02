import React from 'react';
import { Search, Filter, RefreshCw } from 'lucide-react';

export default function MapFilters({
  searchTerm, setSearchTerm,
  filterType, setFilterType,
  filterProvider, setFilterProvider,
  filterPriority, setFilterPriority,
  providerOptions = [],
  onResetFilters,
}) {
  return (
    <div className="bg-gray-800/90 backdrop-blur-md border border-gray-700/80 rounded-xl p-3 shadow-lg flex flex-col md:flex-row items-stretch md:items-center gap-3">
      {/* Search Input */}
      <div className="relative flex-1">
        <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Search by Request ID, Provider, Pickup, or Destination..."
          className="w-full pl-9 pr-3 py-1.5 bg-gray-900/80 border border-gray-700 rounded-lg text-xs text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      {/* Filter Dropdowns */}
      <div className="flex flex-wrap items-center gap-2">
        {/* Type Filter */}
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          className="px-2.5 py-1.5 bg-gray-900/80 border border-gray-700 rounded-lg text-xs text-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="All">All Types</option>
          <option value="ride">Ride (Blue)</option>
          <option value="food">Food (Orange)</option>
          <option value="parcel">Parcel (Green)</option>
        </select>

        {/* Provider Filter */}
        <select
          value={filterProvider}
          onChange={(e) => setFilterProvider(e.target.value)}
          className="px-2.5 py-1.5 bg-gray-900/80 border border-gray-700 rounded-lg text-xs text-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="All">All Providers</option>
          {providerOptions.map(p => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>

        {/* Priority Filter */}
        <select
          value={filterPriority}
          onChange={(e) => setFilterPriority(e.target.value)}
          className="px-2.5 py-1.5 bg-gray-900/80 border border-gray-700 rounded-lg text-xs text-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          <option value="All">All Priorities</option>
          <option value="High">High Priority</option>
          <option value="Medium">Medium Priority</option>
          <option value="Low">Low Priority</option>
        </select>

        {/* Reset button */}
        {(searchTerm || filterType !== 'All' || filterProvider !== 'All' || filterPriority !== 'All') && (
          <button
            onClick={onResetFilters}
            className="flex items-center gap-1 px-2 py-1.5 bg-gray-700 hover:bg-gray-600 text-gray-300 text-xs font-medium rounded-lg transition-colors"
            title="Reset Filters"
          >
            <RefreshCw className="h-3 w-3" /> Reset
          </button>
        )}
      </div>
    </div>
  );
}
