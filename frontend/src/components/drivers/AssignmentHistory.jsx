import React from 'react';
import { History, User, Truck, Clock, CheckCircle2 } from 'lucide-react';

export default function AssignmentHistory({ history = [] }) {
  if (history.length === 0) {
    return (
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-12 text-center text-gray-500">
        <History className="h-10 w-10 mx-auto mb-2 opacity-40" />
        <p className="text-base font-medium">No assignment logs recorded</p>
        <p className="text-xs text-gray-600 mt-1">Driver vehicle assignment events will be logged here</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-5 shadow-sm">
      <div className="flex items-center justify-between border-b border-gray-700 pb-3 mb-4">
        <h3 className="text-base font-bold text-white flex items-center gap-2">
          <History className="h-5 w-5 text-indigo-400" />
          Driver-Vehicle Assignment History ({history.length})
        </h3>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-900/60 border-b border-gray-700 text-[11px] font-bold text-gray-400 uppercase tracking-wider">
              <th className="py-3 px-4">Log ID</th>
              <th className="py-3 px-4">Driver</th>
              <th className="py-3 px-4">Vehicle Assigned</th>
              <th className="py-3 px-4">Assignment Time</th>
              <th className="py-3 px-4">Completion Time</th>
              <th className="py-3 px-4">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700 text-xs">
            {history.map((h) => (
              <tr key={h.id} className="hover:bg-gray-750/50 transition-colors">
                <td className="py-3 px-4 font-mono text-indigo-400 font-bold">#{h.id}</td>
                <td className="py-3 px-4 font-bold text-white flex items-center gap-2">
                  <User className="h-3.5 w-3.5 text-gray-400" />
                  {h.driver_name}
                </td>
                <td className="py-3 px-4 font-medium text-gray-300">
                  <span className="bg-gray-900 border border-gray-700 px-2 py-0.5 rounded flex items-center gap-1.5 w-fit">
                    <Truck className="h-3 w-3 text-indigo-400" />
                    {h.vehicle_name}
                  </span>
                </td>
                <td className="py-3 px-4 font-mono text-gray-300 flex items-center gap-1">
                  <Clock className="h-3 w-3 text-gray-500" />
                  {h.assignment_time}
                </td>
                <td className="py-3 px-4 font-mono text-gray-400">
                  {h.completion_time || '—'}
                </td>
                <td className="py-3 px-4">
                  <span className={`px-2 py-0.5 rounded text-[11px] font-bold border ${
                    h.status === 'Active'
                      ? 'bg-green-500/10 text-green-400 border-green-500/30'
                      : 'bg-gray-500/10 text-gray-400 border-gray-500/30'
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
