import React from 'react';
import { Layers, AlertCircle } from 'lucide-react';
import CandidateBatchCard from './CandidateBatchCard';

export default function BatchesPanel({ batches = [], loading = false }) {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl flex flex-col h-full shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700 shrink-0">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <Layers className="h-4 w-4 text-green-400" />
          Candidate Batches
          <span className="px-2 py-0.5 rounded-full text-[10px] bg-green-500/20 text-green-400 font-bold border border-green-500/30">
            {batches.length}
          </span>
        </h3>
      </div>

      {/* Batch list */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {loading ? (
          <div className="flex items-center justify-center h-24 text-gray-500 text-xs">
            Running analysis…
          </div>
        ) : batches.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 text-gray-500 gap-2">
            <AlertCircle className="h-7 w-7 opacity-30" />
            <p className="text-xs text-center">
              No compatible batches found.<br />
              Run DMFE Analysis to evaluate pending requests.
            </p>
          </div>
        ) : (
          batches.map((batch) => (
            <CandidateBatchCard key={batch.id || batch.batch_code} batch={batch} />
          ))
        )}
      </div>
    </div>
  );
}
