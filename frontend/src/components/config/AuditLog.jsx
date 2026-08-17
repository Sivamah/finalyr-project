import React from 'react';
import { History, User, Clock } from 'lucide-react';

export default function AuditLog({ logs = [] }) {
  if (logs.length === 0) {
    return (
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-12 text-center text-gray-500">
        <History className="h-10 w-10 mx-auto mb-2 opacity-40" />
        <p className="text-base font-medium">No configuration audit logs recorded</p>
        <p className="text-xs text-gray-600 mt-1">Modifications to system parameters will generate timestamped audit entries here</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-5 shadow-sm space-y-4">
      <div className="flex items-center justify-between border-b border-gray-700 pb-3">
        <h3 className="text-base font-bold text-white flex items-center gap-2">
          <History className="h-5 w-5 text-indigo-400" />
          Configuration Change Audit Trail ({logs.length} Log Entries)
        </h3>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-900/60 border-b border-gray-700 text-[11px] font-bold text-gray-400 uppercase tracking-wider">
              <th className="py-3 px-4">Log ID</th>
              <th className="py-3 px-4">Category</th>
              <th className="py-3 px-4">Config Key</th>
              <th className="py-3 px-4">User</th>
              <th className="py-3 px-4">Previous Value</th>
              <th className="py-3 px-4">New Value</th>
              <th className="py-3 px-4">Timestamp</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700 text-xs">
            {logs.map((log) => (
              <tr key={log.id} className="hover:bg-gray-750/50 transition-colors">
                <td className="py-3 px-4 font-mono font-bold text-indigo-400">#{log.id}</td>
                <td className="py-3 px-4">
                  <span className="bg-gray-900 border border-gray-700 px-2 py-0.5 rounded text-[11px] font-medium text-gray-300">
                    {log.category}
                  </span>
                </td>
                <td className="py-3 px-4 font-mono font-bold text-white">
                  {log.config_key}
                </td>
                <td className="py-3 px-4 text-gray-300">
                  <div className="flex items-center gap-1.5 text-[11px]">
                    <User className="h-3 w-3 text-indigo-400" />
                    {log.user_email}
                  </div>
                </td>
                <td className="py-3 px-4 font-mono text-red-400 bg-red-500/5 px-2 py-1 rounded max-w-[180px] truncate">
                  {log.previous_value}
                </td>
                <td className="py-3 px-4 font-mono text-green-400 bg-green-500/5 px-2 py-1 rounded max-w-[180px] truncate font-bold">
                  {log.new_value}
                </td>
                <td className="py-3 px-4 font-mono text-gray-400 flex items-center gap-1">
                  <Clock className="h-3 w-3 text-gray-500" />
                  {log.created_at}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
