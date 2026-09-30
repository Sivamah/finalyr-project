import React from 'react';
import { Layers, AlertCircle } from 'lucide-react';
import CandidateBatchCard from './CandidateBatchCard';

export default function BatchesPanel({ batches = [], loading = false, onAssigned }) {
  // The list holds every batch row the run created — shared batches AND the
  // solo ("Individual") trips for requests that found no partner. Show the
  // split so a screen full of solo trips is not read as "100 compatible".
  const shared = batches.filter((b) => b.decision === 'Compatible').length;
  const solo = batches.length - shared;

  return (
    <div className="glass-panel rounded-2xl flex flex-col h-full shadow-[0_10px_40px_rgba(5,8,22,0.6)] border border-white/[0.1]">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-white/[0.08] shrink-0">
        <h3 className="text-[14px] font-bold text-white flex items-center gap-2.5">
          <Layers className="h-4 w-4 text-brand-success" />
          Candidate Batches
          <span className="px-2.5 py-0.5 rounded-full text-[10px] bg-white/[0.06] text-brand-text-muted font-bold border border-white/5">
            {batches.length}
          </span>
        </h3>
        <span className="text-[11px] text-brand-text-muted font-medium tabular-nums">
          {shared} shared · {solo} solo
        </span>
      </div>

      {/* Batch list */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-4">
        {loading ? (
          <div className="flex items-center justify-center h-32 text-brand-text-muted text-[12px]">
            Running analysis…
          </div>
        ) : batches.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-brand-text-muted gap-3">
            <AlertCircle className="h-7 w-7 opacity-30" />
            <p className="text-[12px] text-center leading-relaxed">
              No batches created yet.<br />
              Run DMFE Analysis to evaluate pending requests.
            </p>
          </div>
        ) : (
          batches.map((batch) => (
            <CandidateBatchCard key={batch.id || batch.batch_code} batch={batch} onAssigned={onAssigned} />
          ))
        )}
      </div>
    </div>
  );
}
