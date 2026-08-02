import React from 'react';
import { BrainCircuit, Sliders, MapPin, Clock, Scale, ShieldAlert } from 'lucide-react';

export default function AIRules({ config = {}, onChange }) {
  const prioW = config.priority_weight ?? 0.35;
  const distW = config.distance_weight ?? 0.25;
  const timeW = config.time_weight ?? 0.25;
  const capW = config.capacity_weight ?? 0.15;

  const totalWeight = Math.round((prioW + distW + timeW + capW) * 100);

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 shadow-sm space-y-6">
      {/* Header */}
      <div className="border-b border-gray-700 pb-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <BrainCircuit className="h-5 w-5 text-indigo-400" />
            AI Optimization Rules & Weights Configurator
          </h3>
          <p className="text-xs text-gray-400 mt-0.5">
            Configure future decision parameters, scoring thresholds, and multi-objective optimization weights
          </p>
        </div>

        {/* Total Weight Badge */}
        <div className={`px-3 py-1.5 rounded-lg text-xs font-bold font-mono flex items-center gap-1.5 border ${
          totalWeight === 100
            ? 'bg-green-500/10 text-green-400 border-green-500/30'
            : 'bg-amber-500/10 text-amber-400 border-amber-500/30'
        }`}>
          <Scale className="h-4 w-4" />
          Total Weight: {totalWeight}% {totalWeight === 100 ? '(Balanced)' : '(Unbalanced)'}
        </div>
      </div>

      {/* Info Warning Banner */}
      <div className="bg-indigo-950/40 border border-indigo-500/30 rounded-xl p-4 flex items-start gap-3 text-xs text-indigo-200">
        <ShieldAlert className="h-5 w-5 text-indigo-400 shrink-0 mt-0.5" />
        <div>
          <span className="font-bold text-indigo-300">Future AI Rule Definition:</span>
          <p className="text-indigo-200/80 mt-0.5">
            These thresholds and priority weights are stored in system configurations for future optimization models. They do not trigger OR-Tools or vehicle routing algorithms in this phase.
          </p>
        </div>
      </div>

      {/* Section 1: Radii & Score Thresholds */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label className="block text-xs font-semibold text-gray-300 mb-1 flex items-center gap-1.5">
            <MapPin className="h-3.5 w-3.5 text-indigo-400" />
            Maximum Pickup Radius (KM)
          </label>
          <input
            type="number"
            min="0.5"
            max="50.0"
            step="0.5"
            value={config.max_pickup_radius_km ?? 5.0}
            onChange={(e) => onChange('max_pickup_radius_km', parseFloat(e.target.value) || 1.0)}
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono"
          />
          <p className="text-[11px] text-gray-500 mt-1">Maximum allowed distance from provider location to pickup point</p>
        </div>

        <div>
          <label className="block text-xs font-semibold text-gray-300 mb-1 flex items-center gap-1.5">
            <MapPin className="h-3.5 w-3.5 text-blue-400" />
            Maximum Delivery Radius (KM)
          </label>
          <input
            type="number"
            min="1.0"
            max="100.0"
            step="1.0"
            value={config.max_delivery_radius_km ?? 15.0}
            onChange={(e) => onChange('max_delivery_radius_km', parseFloat(e.target.value) || 2.0)}
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono"
          />
          <p className="text-[11px] text-gray-500 mt-1">Maximum allowed total delivery coverage radius</p>
        </div>

        <div>
          <label className="block text-xs font-semibold text-gray-300 mb-1 flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5 text-amber-400" />
            Maximum Allowed Delay Tolerance (Minutes)
          </label>
          <input
            type="number"
            min="1"
            max="120"
            value={config.max_allowed_delay_min ?? 20.0}
            onChange={(e) => onChange('max_allowed_delay_min', parseFloat(e.target.value) || 5.0)}
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono"
          />
          <p className="text-[11px] text-gray-500 mt-1">Acceptable detour/wait delay limit before penalty</p>
        </div>

        <div>
          <label className="block text-xs font-semibold text-gray-300 mb-1 flex items-center gap-1.5">
            <Sliders className="h-3.5 w-3.5 text-green-400" />
            Minimum Compatibility Score Cutoff (%)
          </label>
          <input
            type="number"
            min="0"
            max="100"
            value={config.min_compatibility_score ?? 70.0}
            onChange={(e) => onChange('min_compatibility_score', parseFloat(e.target.value) || 50.0)}
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono"
          />
          <p className="text-[11px] text-gray-500 mt-1">Minimum score required for vehicle-request assignment match</p>
        </div>
      </div>

      {/* Section 2: Multi-Objective Weight Sliders */}
      <div className="border border-gray-700 rounded-xl p-5 bg-gray-900/40 space-y-4">
        <h4 className="text-xs font-bold text-gray-300 uppercase tracking-wider">
          Multi-Objective Weight Sliders
        </h4>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {/* Priority Weight */}
          <div>
            <div className="flex justify-between text-xs font-bold text-white mb-1">
              <span>Priority Weight</span>
              <span className="font-mono text-indigo-400">{Math.round(prioW * 100)}%</span>
            </div>
            <input
              type="range"
              min="0.0"
              max="1.0"
              step="0.05"
              value={prioW}
              onChange={(e) => onChange('priority_weight', parseFloat(e.target.value))}
              className="w-full accent-indigo-500 cursor-pointer"
            />
          </div>

          {/* Distance Weight */}
          <div>
            <div className="flex justify-between text-xs font-bold text-white mb-1">
              <span>Distance Weight</span>
              <span className="font-mono text-blue-400">{Math.round(distW * 100)}%</span>
            </div>
            <input
              type="range"
              min="0.0"
              max="1.0"
              step="0.05"
              value={distW}
              onChange={(e) => onChange('distance_weight', parseFloat(e.target.value))}
              className="w-full accent-blue-500 cursor-pointer"
            />
          </div>

          {/* Time Weight */}
          <div>
            <div className="flex justify-between text-xs font-bold text-white mb-1">
              <span>Time Weight</span>
              <span className="font-mono text-green-400">{Math.round(timeW * 100)}%</span>
            </div>
            <input
              type="range"
              min="0.0"
              max="1.0"
              step="0.05"
              value={timeW}
              onChange={(e) => onChange('time_weight', parseFloat(e.target.value))}
              className="w-full accent-green-500 cursor-pointer"
            />
          </div>

          {/* Capacity Weight */}
          <div>
            <div className="flex justify-between text-xs font-bold text-white mb-1">
              <span>Capacity Weight</span>
              <span className="font-mono text-amber-400">{Math.round(capW * 100)}%</span>
            </div>
            <input
              type="range"
              min="0.0"
              max="1.0"
              step="0.05"
              value={capW}
              onChange={(e) => onChange('capacity_weight', parseFloat(e.target.value))}
              className="w-full accent-amber-500 cursor-pointer"
            />
          </div>
        </div>
      </div>
    </div>
  );
}
