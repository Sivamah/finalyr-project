import React, { useState } from 'react';
import { Bike, ShoppingBag, Package, ChevronDown, ChevronUp, Clock } from 'lucide-react';
import CompatibilityGauge from './CompatibilityGauge';
import FactorBreakdown from './FactorBreakdown';

const TYPE_ICONS = {
  ride:   { icon: Bike,        color: 'text-indigo-400', bg: 'bg-indigo-500/10' },
  food:   { icon: ShoppingBag, color: 'text-green-400',  bg: 'bg-green-500/10' },
  parcel: { icon: Package,     color: 'text-amber-400',  bg: 'bg-amber-500/10' },
};

function RequestPill({ req }) {
  const cfg = TYPE_ICONS[req.request_type] || TYPE_ICONS.ride;
  const Icon = cfg.icon;
  return (
    <div className={`flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-700 ${cfg.bg}`}>
      <Icon className={`h-3.5 w-3.5 shrink-0 ${cfg.color}`} />
      <div className="min-w-0">
        <p className={`text-[10px] font-bold ${cfg.color}`}>
          {req.request_type?.charAt(0).toUpperCase() + req.request_type?.slice(1)} #{req.id}
        </p>
        <p className="text-[10px] text-gray-300 truncate">
          {req.pickup_address} → {req.drop_address}
        </p>
      </div>
    </div>
  );
}

export default function CandidateBatchCard({ batch }) {
  const [expanded, setExpanded] = useState(false);

  const isCompatible = batch.decision === 'Compatible';
  const borderColor = isCompatible
    ? 'border-green-500/30 ring-1 ring-green-500/10'
    : 'border-red-500/20';
  const badgeCls = isCompatible
    ? 'bg-green-500/15 text-green-400 border-green-500/30'
    : 'bg-red-500/15 text-red-400 border-red-500/30';

  const requests = batch.requests_summary || [];

  return (
    <div className={`bg-gray-800 border ${borderColor} rounded-xl shadow-sm overflow-hidden`}>
      {/* Card Header — always visible */}
      <div className="p-4">
        <div className="flex items-start justify-between gap-3">
          {/* Left: batch code + decision */}
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs font-bold font-mono text-white">{batch.batch_code}</span>
            <span className={`text-[10px] px-2 py-0.5 rounded border font-bold ${badgeCls}`}>
              {batch.decision}
            </span>
            {batch.estimated_delay_min > 0 && (
              <span className="flex items-center gap-1 text-[10px] text-gray-400">
                <Clock className="h-3 w-3" /> +{batch.estimated_delay_min} min delay
              </span>
            )}
          </div>

          {/* Gauge */}
          <CompatibilityGauge score={batch.compatibility_score} size={88} />
        </div>

        {/* Included requests pills */}
        <div className="mt-3 space-y-1.5">
          {requests.map((req) => (
            <RequestPill key={req.id} req={req} />
          ))}
        </div>
      </div>

      {/* Expandable detail section */}
      <button
        type="button"
        onClick={() => setExpanded(v => !v)}
        className="w-full flex items-center justify-between px-4 py-2 bg-gray-900/50 border-t border-gray-700 text-xs text-gray-400 hover:text-white transition-colors"
      >
        <span>{expanded ? 'Hide' : 'Show'} factor breakdown & reasons</span>
        {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
      </button>

      {expanded && (
        <div className="px-4 py-4 border-t border-gray-700 space-y-4 bg-gray-900/30">
          {/* Factor bars */}
          <div>
            <h5 className="text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-2">
              Factor Score Breakdown
            </h5>
            <FactorBreakdown factorScores={batch.factor_scores || {}} />
          </div>

          {/* Explainability reasons */}
          {batch.reasons?.length > 0 && (
            <div>
              <h5 className="text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-2">
                Decision Explanation
              </h5>
              <ul className="space-y-1">
                {batch.reasons.map((r, i) => (
                  <li key={i} className={`text-xs ${
                    r.startsWith('✓') ? 'text-green-400'
                    : r.startsWith('✗') ? 'text-red-400'
                    : 'text-gray-400'
                  }`}>
                    {r}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
