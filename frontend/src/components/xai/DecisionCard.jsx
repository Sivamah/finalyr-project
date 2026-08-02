import React from 'react';
import { Bike, Utensils, Package, BrainCircuit, CheckCircle2, AlertCircle, Clock, Sparkles } from 'lucide-react';

const TYPE_META = {
  ride: { label: 'Ride', bgClass: 'bg-blue-600', Icon: Bike },
  food: { label: 'Food', bgClass: 'bg-orange-600', Icon: Utensils },
  parcel: { label: 'Parcel', bgClass: 'bg-purple-600', Icon: Package },
};

export default function DecisionCard({ explanation, isSelected, onSelect }) {
  if (!explanation) return null;

  const typeMeta = TYPE_META[explanation.request_type?.toLowerCase()] || TYPE_META.ride;
  const { Icon } = typeMeta;

  const confidence = explanation.confidence_score || 90;
  const confidenceColor = confidence >= 85 ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30'
    : (confidence >= 75 ? 'text-amber-400 bg-amber-500/10 border-amber-500/30' : 'text-red-400 bg-red-500/10 border-red-500/30');

  const isCompatible = explanation.decision?.toLowerCase().includes('compatible');

  return (
    <div
      onClick={onSelect}
      className={`bg-gray-800 border rounded-xl p-5 cursor-pointer transition-all shadow-sm ${
        isSelected
          ? 'border-indigo-500 ring-2 ring-indigo-500/20 bg-gray-800/90'
          : 'border-gray-700 hover:border-gray-600 hover:bg-gray-750'
      }`}
    >
      {/* Top Header Row */}
      <div className="flex items-center justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <span className="font-mono font-bold text-white text-base">#{explanation.request_id}</span>
          <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-xs font-bold text-white ${typeMeta.bgClass}`}>
            <Icon className="h-3 w-3" />
            {typeMeta.label}
          </span>
          <span className="text-xs text-gray-400 font-medium">via {explanation.provider_name}</span>
        </div>

        {/* Status Badge */}
        <span className="flex items-center gap-1.5 px-2.5 py-0.5 bg-gray-900 border border-gray-700 rounded-full text-xs text-gray-300 font-medium">
          <span className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
          {explanation.status}
        </span>
      </div>

      {/* Decision Summary Banner */}
      <div className={`border rounded-lg p-3 mb-3 flex items-start justify-between gap-3 ${
        isCompatible
          ? 'bg-indigo-950/40 border-indigo-500/30 text-indigo-200'
          : 'bg-gray-900/60 border-gray-700 text-gray-300'
      }`}>
        <div>
          <p className="text-xs font-bold uppercase tracking-wider text-indigo-400 flex items-center gap-1.5 mb-1">
            <BrainCircuit className="h-3.5 w-3.5" />
            AI Decision
          </p>
          <p className="text-sm font-bold text-white">{explanation.decision}</p>
          <p className="text-xs text-gray-400 mt-1 leading-relaxed">{explanation.reason}</p>
        </div>

        {/* Confidence Score Pill */}
        <div className={`px-2.5 py-1 rounded-lg border text-center shrink-0 ${confidenceColor}`}>
          <span className="text-[10px] uppercase font-bold block opacity-80">Confidence</span>
          <span className="text-sm font-bold font-mono">{confidence}%</span>
        </div>
      </div>

      {/* Footer Metrics */}
      <div className="flex items-center justify-between text-xs text-gray-400 border-t border-gray-700/60 pt-2.5">
        <span className="truncate max-w-[220px]">
          📍 {explanation.pickup_address} → {explanation.drop_address}
        </span>
        <span className="font-mono text-cyan-400 font-medium shrink-0">
          Compat Score: {explanation.factors?.overall_compatibility_score}%
        </span>
      </div>
    </div>
  );
}
