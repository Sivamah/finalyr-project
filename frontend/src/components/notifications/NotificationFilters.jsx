import React from 'react';
import { Search, Filter, Mail, Calendar, RotateCcw, Info, CheckCircle2, AlertTriangle, AlertOctagon } from 'lucide-react';

export default function NotificationFilters({
  search,
  onSearchChange,
  filters,
  onFilterChange,
  onResetFilters,
}) {
  const categories = [
    { key: 'All', label: 'All Categories', icon: Filter },
    { key: 'Information', label: 'Information', icon: Info },
    { key: 'Success', label: 'Success', icon: CheckCircle2 },
    { key: 'Warning', label: 'Warning', icon: AlertTriangle },
    { key: 'Error', label: 'Error', icon: AlertOctagon },
  ];

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 shadow-sm mb-6">
      <div className="flex flex-col lg:flex-row gap-4 items-stretch lg:items-center justify-between">
        {/* Search Bar */}
        <div className="relative flex-1 min-w-[280px]">
          <Search className="absolute left-3.5 top-2.5 h-4 w-4 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search activity by Keyword, Request ID (#101), or Provider..."
            className="w-full pl-10 pr-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        {/* Category Filters Chips */}
        <div className="flex flex-wrap items-center gap-2">
          {categories.map((c) => {
            const Icon = c.icon;
            const active = filters.category === c.key;
            return (
              <button
                key={c.key}
                onClick={() => onFilterChange('category', c.key)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors border ${
                  active
                    ? 'bg-indigo-600 border-indigo-500 text-white'
                    : 'bg-gray-900 border-gray-700 text-gray-400 hover:text-white hover:bg-gray-750'
                }`}
              >
                <Icon className="h-3.5 w-3.5" />
                {c.label}
              </button>
            );
          })}
        </div>

        {/* Read Status & Date Dropdowns */}
        <div className="flex items-center gap-2">
          {/* Read Status */}
          <div className="flex items-center gap-1.5 bg-gray-900 border border-gray-700 rounded-lg px-3 py-1.5">
            <Mail className="h-3.5 w-3.5 text-indigo-400" />
            <select
              value={filters.readStatus}
              onChange={(e) => onFilterChange('readStatus', e.target.value)}
              className="bg-transparent text-gray-200 text-xs font-medium focus:outline-none cursor-pointer"
            >
              <option value="All" className="bg-gray-800 text-white">All Statuses</option>
              <option value="Unread" className="bg-gray-800 text-white">Unread Only</option>
              <option value="Read" className="bg-gray-800 text-white">Read Only</option>
            </select>
          </div>

          {/* Date */}
          <div className="flex items-center gap-1.5 bg-gray-900 border border-gray-700 rounded-lg px-3 py-1.5">
            <Calendar className="h-3.5 w-3.5 text-green-400" />
            <select
              value={filters.date}
              onChange={(e) => onFilterChange('date', e.target.value)}
              className="bg-transparent text-gray-200 text-xs font-medium focus:outline-none cursor-pointer"
            >
              <option value="All" className="bg-gray-800 text-white">All Dates</option>
              <option value="Today" className="bg-gray-800 text-white">Today</option>
            </select>
          </div>

          {/* Reset */}
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
