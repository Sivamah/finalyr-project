import React from 'react';

/**
 * 8-factor horizontal progress bar breakdown.
 * Each factor shows: name, value bar (0-100%), and numeric score.
 */

const FACTOR_META = {
  pickup:        { label: 'Pickup Distance',       color: 'bg-indigo-500' },
  destination:   { label: 'Destination Similarity', color: 'bg-blue-500' },
  route_overlap: { label: 'Route Overlap',          color: 'bg-cyan-500' },
  time:          { label: 'Time Compatibility',     color: 'bg-green-500' },
  capacity:      { label: 'Vehicle Capacity',       color: 'bg-amber-500' },
  priority:      { label: 'Priority Score',         color: 'bg-orange-500' },
};

function FactorRow({ factorKey, score }) {
  const meta = FACTOR_META[factorKey] || { label: factorKey, color: 'bg-gray-500' };
  const pct = Math.round((score || 0) * 100);
  const textColor = pct >= 70 ? 'text-green-400' : pct >= 40 ? 'text-amber-400' : 'text-red-400';

  return (
    <div className="space-y-1">
      <div className="flex justify-between items-center">
        <span className="text-[11px] text-gray-400 font-medium">{meta.label}</span>
        <span className={`text-[11px] font-bold font-mono ${textColor}`}>{pct}%</span>
      </div>
      <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
        <div
          className={`h-full ${meta.color} rounded-full transition-all duration-700`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export default function FactorBreakdown({ factorScores = {} }) {
  const keys = Object.keys(FACTOR_META).filter(k => k in factorScores);

  if (keys.length === 0) {
    return (
      <p className="text-xs text-gray-500 italic">No factor data available</p>
    );
  }

  return (
    <div className="space-y-2.5">
      {keys.map(k => (
        <FactorRow key={k} factorKey={k} score={factorScores[k]} />
      ))}
    </div>
  );
}
