import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Filter, X, ChevronLeft } from 'lucide-react';

/**
 * Compact left floating filter panel for the live operations map.
 * Collapsible to keep the map clean while the simulation is idle.
 *
 * The ID/provider/address search box that used to live here now sits in the
 * top control bar (KpiBar) instead, so it is not duplicated on screen; this
 * panel keeps the Type/Provider/Priority dropdowns.
 */
export default function MapFilterPanel({
  filterType,
  onFilterTypeChange,
  filterProvider,
  onFilterProviderChange,
  filterPriority,
  onFilterPriorityChange,
  providerOptions,
  hasFilters,
  onResetFilters,
}) {
  const [collapsed, setCollapsed] = useState(typeof window !== 'undefined' ? window.innerWidth < 768 : false);

  return (
    <div className="pointer-events-auto glass-panel-strong rounded-2xl p-3 backdrop-blur-xl border border-white/[0.1] shadow-[0_10px_40px_rgba(5,8,22,0.6)] w-[264px]">
      {/* Header */}
      <div className="flex items-center justify-between mb-2.5">
        <span className="text-[10px] font-bold uppercase tracking-[0.16em] text-brand-text-secondary flex items-center gap-1.5">
          <Filter className="h-3.5 w-3.5 text-brand-primary" />
          Filters
          {hasFilters && <span className="h-1.5 w-1.5 rounded-full bg-brand-primary shadow-[0_0_8px_rgba(22,119,255,0.9)]" />}
        </span>
        <button
          onClick={() => setCollapsed((c) => !c)}
          className="btn-icon !h-6 !w-6 !rounded-lg"
          title={collapsed ? 'Expand filters' : 'Collapse filters'}
        >
          <ChevronLeft className={`h-3.5 w-3.5 transition-transform duration-300 ${collapsed ? 'rotate-180' : ''}`} />
        </button>
      </div>

      <AnimatePresence initial={false}>
        {!collapsed && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden"
          >
            <div className="space-y-2">
              <select value={filterType} onChange={(e) => onFilterTypeChange(e.target.value)} className="select-glass w-full !rounded-xl !py-2">
                <option value="All">All Types</option>
                <option value="Ride">Ride</option>
                <option value="Food">Food</option>
                <option value="Parcel">Parcel</option>
              </select>

              <select value={filterProvider} onChange={(e) => onFilterProviderChange(e.target.value)} className="select-glass w-full !rounded-xl !py-2">
                <option value="All">All Providers</option>
                {providerOptions.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>

              <select value={filterPriority} onChange={(e) => onFilterPriorityChange(e.target.value)} className="select-glass w-full !rounded-xl !py-2">
                <option value="All">All Priority</option>
                <option value="High">High</option>
                <option value="Medium">Medium</option>
                <option value="Low">Low</option>
              </select>

              {hasFilters && (
                <button onClick={onResetFilters} className="btn-ghost !text-brand-primary w-full justify-center">
                  <X className="h-3.5 w-3.5" /> Reset filters
                </button>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}