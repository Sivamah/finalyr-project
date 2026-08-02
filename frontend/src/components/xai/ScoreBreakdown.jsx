import React from 'react';
import { Sliders, MapPin, Navigation, Clock, ShieldCheck, Zap, Gauge } from 'lucide-react';

function SingleFactorBar({ label, value, icon: Icon, colorClass, description }) {
  const roundedVal = Math.round(value || 0);

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="flex items-center gap-1.5 font-medium text-gray-300">
          <Icon className="h-3.5 w-3.5 text-gray-400" />
          {label}
        </span>
        <span className="font-mono font-bold text-white">{roundedVal}%</span>
      </div>
      <div className="w-full bg-gray-900 rounded-full h-2 overflow-hidden border border-gray-700/50">
        <div
          className={`h-2 rounded-full transition-all duration-500 ${colorClass || 'bg-indigo-500'}`}
          style={{ width: `${Math.min(100, Math.max(0, roundedVal))}%` }}
        />
      </div>
      {description && <p className="text-[10px] text-gray-500">{description}</p>}
    </div>
  );
}

export default function ScoreBreakdown({ factors = {} }) {
  const items = [
    {
      label: 'Pickup Distance Score',
      value: factors.pickup_distance_score ?? 85,
      icon: MapPin,
      colorClass: 'bg-blue-500',
      description: 'Proximity of pickup location to active provider fleet',
    },
    {
      label: 'Destination Similarity',
      value: factors.destination_similarity ?? 88,
      icon: Navigation,
      colorClass: 'bg-indigo-500',
      description: 'Route overlap & spatial convergence with shared direction',
    },
    {
      label: 'Estimated Delay Score',
      value: factors.estimated_delay_score ?? 90,
      icon: Clock,
      colorClass: 'bg-yellow-500',
      description: 'Low expected detour latency impact on ETA SLA',
    },
    {
      label: 'Vehicle Capacity Score',
      value: factors.vehicle_capacity_score ?? 95,
      icon: ShieldCheck,
      colorClass: 'bg-emerald-500',
      description: 'Passenger/volume headroom compliance',
    },
    {
      label: 'Priority Score',
      value: factors.priority_score ?? 80,
      icon: Zap,
      colorClass: 'bg-purple-500',
      description: 'Demand priority & urgency weighting factor',
    },
    {
      label: 'Overall Compatibility Score',
      value: factors.overall_compatibility_score ?? 89.5,
      icon: Gauge,
      colorClass: 'bg-cyan-400',
      description: 'Composite feasibility evaluation score',
    },
  ];

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-5 shadow-sm space-y-4">
      <div className="flex items-center justify-between border-b border-gray-700 pb-3">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <Sliders className="h-4 w-4 text-indigo-400" />
          Explanation Factors & Feature Scores
        </h3>
        <span className="text-xs font-mono text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20 font-bold">
          Weighted Model Matrix
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {items.map((item) => (
          <SingleFactorBar key={item.label} {...item} />
        ))}
      </div>
    </div>
  );
}
