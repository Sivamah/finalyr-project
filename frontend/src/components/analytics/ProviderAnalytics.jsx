import React from 'react';
import { Building2, Award, AlertTriangle, TrendingUp, CheckCircle, Clock } from 'lucide-react';

export default function ProviderAnalytics({ data = {} }) {
  const providerStats = data.provider_stats || [];
  const mostActive = data.most_active_provider || 'N/A';
  const leastActive = data.least_active_provider || 'N/A';

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-5 shadow-sm mb-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6 border-b border-gray-700 pb-3">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <Building2 className="h-5 w-5 text-orange-400" />
            Provider Analytics & Performance
          </h3>
          <p className="text-xs text-gray-400 mt-0.5">Utilization metrics, request share, and operational activity per provider</p>
        </div>

        {/* Most & Least Active Badges */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-xs">
            <Award className="h-4 w-4 text-emerald-400" />
            <div>
              <span className="text-gray-400 text-[10px] block font-medium">MOST ACTIVE</span>
              <span className="text-emerald-400 font-bold">{mostActive}</span>
            </div>
          </div>

          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-500/10 border border-amber-500/30 rounded-lg text-xs">
            <AlertTriangle className="h-4 w-4 text-amber-400" />
            <div>
              <span className="text-gray-400 text-[10px] block font-medium">LEAST ACTIVE</span>
              <span className="text-amber-400 font-bold">{leastActive}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Provider Performance Comparison Table */}
      <div className="overflow-x-auto">
        {providerStats.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-6">No provider statistics available</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700 text-left text-xs font-semibold text-gray-400 bg-gray-900/40">
                <th className="px-4 py-3">Provider Name</th>
                <th className="px-4 py-3">Total Requests</th>
                <th className="px-4 py-3">Completed</th>
                <th className="px-4 py-3">Pending</th>
                <th className="px-4 py-3">Avg Distance</th>
                <th className="px-4 py-3">Provider Share / Utilization</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700/50">
              {providerStats.map((p) => {
                const util = p.utilization_pct || 0;
                return (
                  <tr key={p.provider_id || p.provider_name} className="hover:bg-gray-700/30 transition-colors">
                    <td className="px-4 py-3 text-white font-medium flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-orange-400" />
                      {p.provider_name}
                    </td>
                    <td className="px-4 py-3 text-gray-200 font-mono font-semibold">{p.total_requests}</td>
                    <td className="px-4 py-3 text-green-400 font-mono">{p.completed_requests}</td>
                    <td className="px-4 py-3 text-amber-400 font-mono">{p.pending_requests}</td>
                    <td className="px-4 py-3 text-cyan-400 font-mono">{p.avg_distance_km} km</td>
                    <td className="px-4 py-3 min-w-[200px]">
                      <div className="flex items-center gap-3">
                        <div className="flex-1 bg-gray-700 rounded-full h-2 overflow-hidden">
                          <div
                            className="bg-orange-500 h-2 rounded-full transition-all duration-500"
                            style={{ width: `${Math.min(100, Math.max(0, util))}%` }}
                          />
                        </div>
                        <span className="text-xs font-bold text-orange-400 font-mono w-12 text-right">
                          {util}%
                        </span>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
