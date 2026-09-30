import React from 'react';
import { ChevronRight, Combine } from 'lucide-react';
import { requestTypeMeta } from '../../utils/requestSemantics';

/** Batched / Individual / Rejected — derived from payload fields */
function outcomeMeta(explanation) {
  const decision = String(explanation?.decision || '').toLowerCase();
  if (decision.includes('compatible for batching')) {
    return {
      label: 'Combined',
      color: '#10B981',
      bgClass: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
    };
  }
  if ((explanation?.batched_with_request_ids || []).length > 0) {
    return {
      label: 'Rejected',
      color: '#EF4444',
      bgClass: 'bg-rose-500/15 text-rose-400 border-rose-500/30',
    };
  }
  return {
    label: 'Individual',
    color: '#38BDF8',
    bgClass: 'bg-sky-500/15 text-sky-400 border-sky-500/30',
  };
}

function formatTime(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export default function DecisionCard({ explanation, isSelected, onSelect }) {
  if (!explanation) return null;

  const typeMeta = requestTypeMeta(explanation.request_type);
  const outcome = outcomeMeta(explanation);
  const confidence = explanation.confidence_score;
  const hasConfidence = Number.isFinite(confidence);
  const isEstimated = explanation.confidence_fallback === true;
  const compatScore = explanation.factors?.overall_compatibility_score;
  const hasCompat = Number.isFinite(compatScore);
  const time = formatTime(explanation.created_at);
  const reasonLine = explanation.reason || explanation.decision_summary || '';
  const isShared = outcome.label === 'Combined';

  return (
    <div
      onClick={onSelect}
      className={`group relative rounded-2xl p-3.5 cursor-pointer transition-all duration-200 overflow-hidden border ${
        isSelected
          ? 'border-[#00F0FF]/50 bg-gradient-to-r from-[#00F0FF]/15 via-[#0C1A32] to-[#0A1222] shadow-[0_0_24px_rgba(0,240,255,0.12)] ring-1 ring-[#00F0FF]/30 opacity-100'
          : 'border-white/[0.08] bg-[#081222]/80 hover:border-white/20 hover:bg-[#0D1C36]/90 opacity-80 hover:opacity-100'
      }`}
    >
      {/* Selected Indicator Bar on Left */}
      {isSelected && (
        <div className="absolute left-0 top-0 bottom-0 w-[4px] bg-[#00F0FF] shadow-[0_0_12px_#00F0FF] rounded-l-2xl" />
      )}

      <div className="flex items-start gap-3">
        {/* Avatar Circle with Service or Batch Icon */}
        <div
          className="h-10 w-10 rounded-xl flex items-center justify-center shrink-0 border shadow-sm transition-transform group-hover:scale-105 mt-0.5"
          style={{
            background: isShared ? 'rgba(16, 185, 129, 0.15)' : `${typeMeta.color}18`,
            borderColor: isShared ? 'rgba(16, 185, 129, 0.35)' : `${typeMeta.color}35`,
          }}
        >
          {isShared ? (
            <Combine className="h-5 w-5 text-emerald-400" />
          ) : (
            <typeMeta.Icon className="h-5 w-5" style={{ color: typeMeta.color }} />
          )}
        </div>

        {/* Center Content */}
        <div className="min-w-0 flex-1">
          {/* Header Row: Title & Outcome Badge */}
          <div className="flex items-center justify-between gap-1.5 mb-1">
            <span className="font-mono font-extrabold text-white text-[13px] tracking-tight truncate">
              {isShared && explanation.tripCode
                ? `BATCH #${explanation.tripCode}`
                : isShared
                ? `BATCH #${explanation.request_id}`
                : `REQ #${explanation.request_id}`}
            </span>
            {/* Outcome Badge */}
            <span className={`px-2 py-0.5 rounded-md text-[10px] font-black uppercase tracking-wider border shrink-0 ${outcome.bgClass}`}>
              {outcome.label}
            </span>
          </div>

          {/* Subtitle: Service type • distance • time */}
          <div className="flex items-center gap-1.5 text-[11px] text-white/50 mb-1.5 truncate">
            <span className="font-medium text-white/70">{typeMeta.label}</span>
            {Number.isFinite(explanation.estimated_distance_km) && (
              <>
                <span className="text-white/20">&bull;</span>
                <span>{explanation.estimated_distance_km.toFixed(1)} km</span>
              </>
            )}
            {time && (
              <>
                <span className="text-white/20">&bull;</span>
                <span className="text-white/40 font-mono text-[10.5px]">{time}</span>
              </>
            )}
          </div>

          {/* Reason Snippet */}
          {reasonLine && (
            <p className={`text-[11px] line-clamp-2 leading-relaxed mb-2.5 ${isSelected ? 'text-white/80 font-normal' : 'text-white/50'}`} title={reasonLine}>
              {reasonLine}
            </p>
          )}

          {/* Mini Score Metrics */}
          <div className="flex items-center justify-between gap-2 pt-2 border-t border-white/[0.08] text-[10.5px]">
            <div className="flex items-center gap-3">
              <span className="text-white/45 flex items-center gap-1">
                Compatibility:
                <span className={`font-mono font-bold ${hasCompat ? (isSelected ? 'text-[#00F0FF]' : 'text-white/90') : 'text-white/40'}`}>
                  {hasCompat ? `${Math.round(compatScore)}%` : '—'}
                </span>
              </span>
              <span className="text-white/45 flex items-center gap-1">
                Confidence:
                <span className={`font-mono font-bold ${hasConfidence ? 'text-white/90' : 'text-white/40'}`}>
                  {hasConfidence ? `${Math.round(confidence)}%` : '—'}
                </span>
                {hasConfidence && isEstimated && (
                  <span className="text-amber-400 font-sans text-[9px] font-semibold">(est)</span>
                )}
              </span>
            </div>
            <ChevronRight className={`h-3.5 w-3.5 shrink-0 text-white/30 transition-transform ${isSelected ? 'translate-x-0.5 text-[#00F0FF]' : 'group-hover:translate-x-0.5 group-hover:text-white/60'}`} />
          </div>
        </div>
      </div>
    </div>
  );
}

