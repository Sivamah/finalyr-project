import React from 'react';
import { XCircle, Bike, ShoppingBag, Package } from 'lucide-react';

const TYPE_ICONS = {
  ride: { icon: Bike, color: 'text-indigo-400' },
  food: { icon: ShoppingBag, color: 'text-green-400' },
  parcel: { icon: Package, color: 'text-amber-400' },
};

export default function RejectedRequestsPanel({ rejectedBatches = [] }) {
  // Flatten: collect all request summaries from rejected batches
  const rejectedRequests = rejectedBatches.flatMap((batch) =>
    (batch.requests_summary || []).map((req) => ({
      ...req,
      batch_code: batch.batch_code,
      compatibility_score: batch.compatibility_score,
      rejection_reason: (batch.reasons || [])
        .filter(r => r.startsWith('✗'))
        .join(' | ') || 'Compatibility score below threshold',
    }))
  );

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl shadow-sm overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-700">
        <XCircle className="h-4 w-4 text-red-400" />
        <h3 className="text-sm font-bold text-white">
          Rejected Requests
          <span className="ml-2 px-2 py-0.5 rounded-full text-[10px] bg-red-500/20 text-red-400 font-bold border border-red-500/30">
            {rejectedRequests.length}
          </span>
        </h3>
      </div>

      {rejectedRequests.length === 0 ? (
        <div className="px-4 py-8 text-center text-gray-500 text-xs">
          No rejected requests — all evaluated pairs passed the threshold.
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-gray-900/60 border-b border-gray-700 text-[10px] font-bold text-gray-400 uppercase tracking-wider">
                <th className="py-2.5 px-3">Request</th>
                <th className="py-2.5 px-3">Route</th>
                <th className="py-2.5 px-3">Batch Code</th>
                <th className="py-2.5 px-3">Score</th>
                <th className="py-2.5 px-3">Rejection Reason</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700 text-xs">
              {rejectedRequests.map((req, i) => {
                const cfg = TYPE_ICONS[req.request_type] || TYPE_ICONS.ride;
                const Icon = cfg.icon;
                return (
                  <tr key={`${req.id}-${i}`} className="hover:bg-gray-750/40 transition-colors">
                    <td className="py-2.5 px-3">
                      <div className="flex items-center gap-1.5">
                        <Icon className={`h-3.5 w-3.5 ${cfg.color}`} />
                        <span className={`font-bold ${cfg.color}`}>
                          {req.request_type?.charAt(0).toUpperCase() + req.request_type?.slice(1)} #{req.id}
                        </span>
                      </div>
                    </td>
                    <td className="py-2.5 px-3 text-gray-300 text-[11px]">
                      {req.pickup_address} → {req.drop_address}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-gray-400 text-[11px]">
                      {req.batch_code}
                    </td>
                    <td className="py-2.5 px-3">
                      <span className="font-mono font-bold text-red-400 text-[11px]">
                        {req.compatibility_score?.toFixed(1)}%
                      </span>
                    </td>
                    <td className="py-2.5 px-3 text-red-400 text-[10px] max-w-[280px] truncate" title={req.rejection_reason}>
                      {req.rejection_reason}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
