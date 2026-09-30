import React from 'react';
import { History, User, Truck, Clock } from 'lucide-react';

export default function AssignmentHistory({ history = [] }) {
  if (history.length === 0) {
    return (
      <div className="glass-panel rounded-[20px] p-12 text-center text-brand-text-muted">
        <History className="h-10 w-10 mx-auto mb-3 opacity-40 text-brand-primary" />
        <p className="text-base font-medium text-white">No assignment logs recorded</p>
        <p className="text-xs mt-1">Driver vehicle assignment events will be logged here</p>
      </div>
    );
  }

  return (
    <div className="glass-panel rounded-[20px] overflow-hidden shadow-sm">
      <div className="flex items-center justify-between border-b border-white/10 p-4 lg:p-5">
        <h3 className="text-base font-display font-semibold text-white flex items-center gap-2">
          <History className="h-5 w-5 text-brand-primary" />
          Assignment History <span className="text-brand-text-muted text-sm font-medium">({history.length})</span>
        </h3>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-black/20 border-b border-white/10 text-[10px] font-bold text-brand-text-muted uppercase tracking-wider">
              <th className="py-3 px-4">Log ID</th>
              <th className="py-3 px-4">Driver</th>
              <th className="py-3 px-4">Vehicle Assigned</th>
              <th className="py-3 px-4">Assignment Time</th>
              <th className="py-3 px-4">Completion Time</th>
              <th className="py-3 px-4">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/5 text-xs">
            {history.map((h) => (
              <tr key={h.id} className="hover:bg-white/[0.02] transition-colors">
                <td className="py-3.5 px-4 font-mono text-brand-primary font-bold">#{h.id}</td>
                <td className="py-3.5 px-4 font-bold text-gray-100 flex items-center gap-2">
                  <User className="h-3.5 w-3.5 text-brand-text-muted" />
                  {h.driver_name}
                </td>
                <td className="py-3.5 px-4 font-medium text-gray-300">
                  <span className="bg-black/40 border border-white/10 px-2.5 py-1 rounded-[6px] flex items-center gap-1.5 w-fit">
                    <Truck className="h-3 w-3 text-brand-primary opacity-80" />
                    {h.vehicle_name}
                  </span>
                </td>
                <td className="py-3.5 px-4 font-mono text-gray-300 flex items-center gap-1.5">
                  <Clock className="h-3 w-3 text-brand-text-muted" />
                  {h.assignment_time}
                </td>
                <td className="py-3.5 px-4 font-mono text-brand-text-muted">
                  {h.completion_time || '—'}
                </td>
                <td className="py-3.5 px-4">
                  <span className={`px-2.5 py-1 rounded-[6px] text-[10px] uppercase tracking-wide font-bold border ${
                    h.status === 'Active'
                      ? 'bg-brand-success/10 text-brand-success border-brand-success/30'
                      : 'bg-white/5 text-gray-400 border-white/10'
                  }`}>
                    {h.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
