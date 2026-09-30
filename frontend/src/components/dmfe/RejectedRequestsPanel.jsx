import React from 'react';
import { XCircle, Bike, ShoppingBag, Package } from 'lucide-react';

const TYPE_ICONS = {
  ride: { icon: Bike, color: 'text-brand-primary' },
  food: { icon: ShoppingBag, color: 'text-brand-warning' },
  parcel: { icon: Package, color: 'text-brand-accent' },
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
    <div className="glass-panel rounded-2xl shadow-[0_10px_40px_rgba(5,8,22,0.6)] border border-white/[0.1] overflow-hidden">
      <div className="flex items-center gap-2 px-5 py-4 border-b border-white/[0.08]">
        <XCircle className="h-4 w-4 text-brand-danger" />
        <h3 className="text-[14px] font-bold text-white">
          Rejected Requests
          <span className="ml-2.5 px-2.5 py-0.5 rounded-full text-[10px] bg-white/[0.06] text-brand-text-muted font-bold border border-white/5">
            {rejectedRequests.length}
          </span>
        </h3>
      </div>

      {rejectedRequests.length === 0 ? (
        <div className="px-5 py-10 text-center text-brand-text-muted text-[12px]">
          No rejected requests — all evaluated pairs passed the threshold.
        </div>
      ) : (
        <div className="overflow-x-auto custom-scrollbar">
          <table className="table-glass">
            <thead>
              <tr>
                <th className="whitespace-nowrap">Request</th>
                <th>Route</th>
                <th>Batch Code</th>
                <th>Score</th>
                <th>Rejection Reason</th>
              </tr>
            </thead>
            <tbody>
              {rejectedRequests.map((req, i) => {
                const cfg = TYPE_ICONS[req.request_type] || TYPE_ICONS.ride;
                const Icon = cfg.icon;
                return (
                  <tr key={`${req.id}-${i}`}>
                    <td>
                      <div className="flex items-center gap-1.5">
                        <Icon className={`h-3.5 w-3.5 ${cfg.color}`} />
                        <span className={`font-bold uppercase tracking-wide text-[10px] ${cfg.color}`}>
                          {req.request_type?.charAt(0).toUpperCase() + req.request_type?.slice(1)} #{req.id}
                        </span>
                      </div>
                    </td>
                    <td className="text-white/80 text-[11px]">
                      {req.pickup_address} <span className="text-white/30 mx-1">→</span> {req.drop_address}
                    </td>
                    <td className="font-mono text-brand-text-muted text-[11px]">
                      {req.batch_code}
                    </td>
                    <td>
                      <span className="font-mono font-bold text-brand-danger text-[11px]">
                        {req.compatibility_score?.toFixed(1)}%
                      </span>
                    </td>
                    <td className="text-brand-danger text-[11px] max-w-[280px] truncate" title={req.rejection_reason}>
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
