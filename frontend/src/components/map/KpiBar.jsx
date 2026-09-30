import React from 'react';
import { Play, Square, Search } from 'lucide-react';

/**
 * Floating top control bar for the live operations map.
 *
 * Deliberately minimal: engine state, Start/Stop, and a search box — the
 * previous version of this bar also carried a live-count badge per request
 * type (Trips/Deployed/Ride/Food/Parcel/Queue/Generated) plus a clock, which
 * read as cluttered next to the map. Those counts are still computed by the
 * page (queue/fleet data drives the map markers directly); they are just no
 * longer duplicated here as a row of badges. Pause/Clear-queue controls were
 * dropped from this bar for the same reason — Stop already halts the engine.
 */
export default function KpiBar({
  status,
  engineActive,
  loading,
  onStartResume,
  onStop,
  searchTerm,
  onSearchChange,
}) {
  return (
    <div className="pointer-events-auto glass-panel-strong rounded-2xl p-3 sm:px-4 sm:py-2.5 backdrop-blur-xl flex flex-wrap sm:flex-nowrap items-center justify-center gap-3 sm:gap-4 shadow-[0_10px_40px_rgba(5,8,22,0.6)] border border-white/[0.1] w-full max-w-[90vw] sm:max-w-max">
      <div className="flex items-center gap-3 shrink-0 justify-center w-full sm:w-auto">
        {/* Engine state */}
        <div className="flex items-center gap-2 pr-3 border-r border-white/[0.08] shrink-0">
          <span className="relative flex h-2 w-2">
            <span className={`absolute inline-flex h-full w-full rounded-full animate-ping ${engineActive ? 'bg-brand-success' : 'bg-brand-text-muted'}`} />
            <span className={`relative inline-flex rounded-full h-2 w-2 ${engineActive ? 'bg-brand-success shadow-[0_0_10px_rgba(34,197,94,0.9)]' : 'bg-brand-text-muted'}`} />
          </span>
          <span className="text-[11px] font-bold tracking-[0.14em] uppercase text-white whitespace-nowrap">
            {engineActive ? 'Live' : status.paused ? 'Paused' : 'Idle'}
          </span>
        </div>

        {/* Start / Stop */}
        <div className="flex items-center gap-1.5 shrink-0">
          <button onClick={onStartResume} disabled={loading || engineActive} className="btn-primary !px-2.5 !py-1.5 !rounded-xl !text-[11px] disabled:opacity-40 disabled:cursor-not-allowed" title={status.paused ? 'Resume engine' : 'Start engine'}>
            <Play className="h-3.5 w-3.5" /> {status.paused ? 'Resume' : 'Start'}
          </button>
          <button onClick={onStop} disabled={loading || (!status.running && !status.paused)} className="btn-glass !px-2.5 !py-1.5 !rounded-xl !text-[11px] !text-brand-danger disabled:opacity-40 disabled:cursor-not-allowed" title="Stop engine">
            <Square className="h-3 w-3" /> Stop
          </button>
        </div>
      </div>

      {/* Search — same request search that used to live only in the left
          Filters panel, surfaced here so it sits next to the controls. */}
      <div className="relative w-full sm:max-w-[260px] sm:pl-4 sm:border-l sm:border-white/[0.08]">
        <Search className="absolute left-3 sm:left-7 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-brand-text-muted pointer-events-none" />
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search ID, provider, address…"
          className="input-glass w-full !rounded-xl !py-1.5 !pl-9 sm:!pl-9 !text-[12px]"
        />
      </div>
    </div>
  );
}
