import React from 'react';
import { Building2, Award, AlertTriangle } from 'lucide-react';

export default function ProviderAnalytics({ data = {} }) {
  const providerStats = data.provider_stats || [];
  const mostActive = data.most_active_provider || 'N/A';
  const leastActive = data.least_active_provider || 'N/A';

  return (
    <div className="glass-panel rounded-[20px] p-5 lg:p-6 shadow-sm mb-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6 border-b border-white/10 pb-4">
        <div>
          <h3 className="text-base font-display font-semibold text-white flex items-center gap-2">
            <Building2 className="h-5 w-5 text-brand-primary" />
            Provider Analytics & Performance
          </h3>
          <p className="text-[13px] text-brand-text-muted mt-1">Utilization metrics, request share, and operational activity per provider</p>
        </div>

        {/* Most & Least Active Badges */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2.5 px-3.5 py-2 bg-brand-success/10 border border-brand-success/20 rounded-[12px]">
            <Award className="h-4.5 w-4.5 text-brand-success" />
            <div>
              <span className="text-brand-success/70 text-[9px] block font-bold uppercase tracking-wider">MOST ACTIVE</span>
              <span className="text-brand-success font-display font-bold text-sm leading-tight">{mostActive}</span>
            </div>
          </div>

          <div className="flex items-center gap-2.5 px-3.5 py-2 bg-brand-warning/10 border border-brand-warning/20 rounded-[12px]">
            <AlertTriangle className="h-4.5 w-4.5 text-brand-warning" />
            <div>
              <span className="text-brand-warning/70 text-[9px] block font-bold uppercase tracking-wider">LEAST ACTIVE</span>
              <span className="text-brand-warning font-display font-bold text-sm leading-tight">{leastActive}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Provider Performance Comparison Table */}
      <div className="glass-card rounded-[16px] overflow-hidden bg-black/20 border border-white/5">
        <div className="overflow-x-auto">
          {providerStats.length === 0 ? (
            <p className="text-[13px] text-brand-text-muted text-center py-8">No provider statistics available</p>
          ) : (
            <table className="w-full text-sm text-left">
              <thead>
                <tr className="border-b border-white/10 text-[10px] font-bold text-brand-text-muted uppercase tracking-wider bg-black/20">
                  <th className="px-5 py-4">Provider Name</th>
                  <th className="px-5 py-4">Total Requests</th>
                  <th className="px-5 py-4">Completed</th>
                  <th className="px-5 py-4">Pending</th>
                  <th className="px-5 py-4">Avg Distance</th>
                  <th className="px-5 py-4">Provider Share / Utilization</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
              {providerStats.map((p) => {
                const util = p.utilization_pct || 0;
                return (
                  <tr key={p.provider_id || p.provider_name} className="hover:bg-white/[0.02] transition-colors">
                    <td className="px-5 py-4 text-white font-semibold flex items-center gap-2">
                      <div className="w-2 h-2 rounded-full bg-brand-primary" />
                      {p.provider_name}
                    </td>
                    <td className="px-5 py-4 text-gray-200 font-mono font-medium">{p.total_requests}</td>
                    <td className="px-5 py-4 text-brand-success font-mono font-medium">{p.completed_requests}</td>
                    <td className="px-5 py-4 text-brand-warning font-mono font-medium">{p.pending_requests}</td>
                    <td className="px-5 py-4 text-cyan-400 font-mono font-medium">{p.avg_distance_km} km</td>
                    <td className="px-5 py-4 min-w-[220px]">
                      <div className="flex items-center gap-3">
                        <div className="flex-1 bg-black/40 rounded-full h-2.5 overflow-hidden border border-white/5">
                          <div
                            className="bg-brand-primary h-2.5 rounded-full transition-all duration-500 relative"
                            style={{ width: `${Math.min(100, Math.max(0, util))}%` }}
                          >
                            <div className="absolute inset-0 bg-white/20" />
                          </div>
                        </div>
                        <span className="text-xs font-bold text-brand-primary font-mono w-12 text-right">
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
    </div>
  );
}
