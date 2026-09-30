import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Loader2, Info, Split, Combine, Route as RouteIcon,
  XCircle, MapPin, Flag, ExternalLink, Leaf, Fuel, Cloud,
  IndianRupee, Layers, Navigation
} from 'lucide-react';
import api from '../../services/api';
import LiveMapContainer from '../map/LiveMapContainer';
import { normalizeXaiHighlight } from '../../utils/xaiMap';
import { requestTypeMeta, decisionStateMeta } from '../../utils/requestSemantics';

export default function XaiMapPanel({ explanation, open = true }) {
  const navigate = useNavigate();
  const [queue, setQueue] = useState([]);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [viewMode, setViewMode] = useState('combined');
  const pollRef = useRef(null);
  const scrollRef = useRef(null);

  const highlight = useMemo(() => normalizeXaiHighlight(explanation), [explanation]);

  // Default to combined route view and reset scroll to top on selection change
  useEffect(() => {
    setViewMode('combined');
    if (scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  }, [explanation?.request_id]);

  // Background layer: live simulation queue
  const fetchLiveData = useCallback(async () => {
    try {
      const queueRes = await api.get('/simulation/queue?limit=120');
      setQueue(queueRes.data.items || []);
      setLastUpdated(new Date());
    } catch {
      // Silently ignore poll errors
    }
  }, []);

  useEffect(() => {
    if (!open) return undefined;
    fetchLiveData();
    pollRef.current = setInterval(() => {
      if (document.visibilityState === 'visible') fetchLiveData();
    }, 2500);
    return () => clearInterval(pollRef.current);
  }, [open, fetchLiveData]);

  const highlightRequestIds = useMemo(
    () => new Set(highlight?.requestIds || []),
    [highlight],
  );

  const filteredRequests = useMemo(
    () => queue.filter((item) => !highlightRequestIds.has(item.id)),
    [queue, highlightRequestIds],
  );

  if (!explanation) {
    return (
      <div className="glass-panel rounded-2xl p-16 text-center text-brand-text-muted h-full flex flex-col justify-center border border-white/5 bg-[#0A0F1A]/50">
        <Info className="h-10 w-10 mx-auto mb-3 opacity-40 text-[#00F0FF]" />
        <p className="text-sm font-semibold text-white">Select a Decision Card</p>
        <p className="text-xs text-white/40 mt-1">
          Click any decision card on the left to inspect its journey and compatibility attribution on the live map.
        </p>
      </div>
    );
  }

  const typeMeta = requestTypeMeta(highlight.requestType);
  const state = decisionStateMeta(highlight.status, highlight.decision);
  const isRejected =
    state.tone === 'danger' ||
    String(highlight.status || '').toLowerCase() === 'incompatible' ||
    String(highlight.status || '').toLowerCase() === 'rejected' ||
    ((highlight.explanation?.batched_with_request_ids || []).length > 0 && !highlight.isShared);
  const isShared = highlight.isShared && !isRejected;

  // Real savings presence check (never fake data)
  const hasSavings = (
    (Number.isFinite(highlight.distanceSavedKm) && highlight.distanceSavedKm > 0) ||
    (Number.isFinite(highlight.fuelSavedL) && highlight.fuelSavedL > 0) ||
    (Number.isFinite(highlight.co2SavedKg) && highlight.co2SavedKg > 0) ||
    (Number.isFinite(highlight.separateCostInr) && Number.isFinite(highlight.tripCostInr) && highlight.separateCostInr > highlight.tripCostInr)
  );

  const costSavedInr = (Number.isFinite(highlight.separateCostInr) && Number.isFinite(highlight.tripCostInr))
    ? Math.max(0, highlight.separateCostInr - highlight.tripCostInr)
    : null;

  const partnerRequests = (highlight.requestPoints || []).filter((p) => p.relation !== 'self');
  const totalRequestsInBatch = 1 + partnerRequests.length;

  return (
    <div ref={scrollRef} className="flex flex-col gap-3.5 w-full h-full min-h-0 overflow-y-auto custom-scrollbar pr-1">
      {/* ── CARD: ROUTE VISUALIZATION & LEAFLET MAP ── */}
      <div className="glass-panel rounded-2xl border border-white/10 shadow-[0_12px_40px_rgba(0,0,0,0.5)] overflow-hidden flex flex-col shrink-0">
        
        {/* Top Header Bar for Map Card */}
        <div className="px-4 py-3 border-b border-white/10 bg-[#071328]/85 backdrop-blur-xl flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-xl bg-[#00F0FF]/15 border border-[#00F0FF]/30 flex items-center justify-center text-[#00F0FF]">
              <Navigation className="h-4 w-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xs sm:text-sm font-bold text-white tracking-tight">
                  {isShared ? 'Batch Route Visualization' : 'Route Visualization'}
                </h2>
                {/* Route state pill */}
                {isRejected ? (
                  <span className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[9.5px] font-black uppercase tracking-wider bg-rose-500/20 text-rose-300 border border-rose-500/30">
                    <XCircle className="h-3 w-3 text-rose-400" />
                    REJECTED PAIRING
                  </span>
                ) : isShared ? (
                  <span className="flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[9.5px] font-black uppercase tracking-wider bg-[#00F0FF]/20 text-[#00F0FF] border border-[#00F0FF]/40 shadow-[0_0_12px_rgba(0,240,255,0.2)]">
                    <Combine className="h-3 w-3 text-[#00F0FF]" />
                    BATCHED / COMBINED ROUTE
                  </span>
                ) : (
                  <span className="flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[9.5px] font-black uppercase tracking-wider bg-sky-500/20 text-sky-300 border border-sky-500/30">
                    <RouteIcon className="h-3 w-3 text-sky-400" />
                    INDIVIDUAL / SEPARATE ROUTE
                  </span>
                )}
              </div>
              <p className="text-[10px] text-white/45 hidden sm:block">
                {isShared
                  ? `Optimized shared route for ${totalRequestsInBatch} combined requests`
                  : isRejected
                  ? 'Incompatible pairing — evaluated as individual standalone route'
                  : 'Direct transit route for standalone request'}
              </p>
            </div>
          </div>

          {/* Action buttons on top right */}
          <div className="flex items-center gap-2 shrink-0">
            {/* Separate / Combined toggle for batched trips */}
            {isShared && (
              <button
                type="button"
                onClick={() => setViewMode((m) => (m === 'combined' ? 'separate' : 'combined'))}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl text-[10.5px] font-semibold text-white/80 hover:text-white bg-white/10 hover:bg-white/15 border border-white/10 transition-colors"
                title={viewMode === 'combined' ? 'Show individual legs separately' : 'Show the combined shared trip'}
              >
                {viewMode === 'combined' ? (
                  <>
                    <Split className="h-3.5 w-3.5 text-[#00F0FF]" />
                    <span>Show Separate</span>
                  </>
                ) : (
                  <>
                    <Combine className="h-3.5 w-3.5 text-[#00F0FF]" />
                    <span>Show Combined</span>
                  </>
                )}
              </button>
            )}

            {/* View Full Map Link */}
            <button
              type="button"
              onClick={() => navigate(`/live-map?xai=${highlight.requestId}`)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-[11px] font-bold text-[#00F0FF] bg-[#00F0FF]/10 hover:bg-[#00F0FF]/20 border border-[#00F0FF]/30 transition-all hover:border-[#00F0FF]/60 shadow-sm"
              title="Open full interactive map"
            >
              <span>View Full Map</span>
              <ExternalLink className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        {/* Map Viewport Container */}
        <div className="relative w-full h-[300px] sm:h-[340px] xl:h-[330px] 2xl:h-[380px] bg-[#0A0F1A]">
          {/* Real Leaflet Map */}
          <LiveMapContainer
            mode="decision"
            requests={filteredRequests}
            selectedRequest={selectedRequest}
            onSelectRequest={(req) => setSelectedRequest(req)}
            onClosePopup={() => setSelectedRequest(null)}
            xaiHighlight={highlight}
            xaiViewMode={viewMode}
            className="absolute inset-0 w-full h-full"
          />

          {/* Loading Indicator */}
          {!lastUpdated && (
            <div className="absolute bottom-4 left-4 z-20 glass-panel-strong rounded-xl px-3 py-1.5 backdrop-blur-xl text-[10px] text-white/60 flex items-center gap-2 pointer-events-none border border-white/10 shadow-lg">
              <Loader2 className="h-3.5 w-3.5 animate-spin text-[#00F0FF]" />
              <span>Loading telemetry...</span>
            </div>
          )}

          {/* Clean Floating Map Legend in Bottom Corner */}
          <div className="absolute bottom-3.5 right-3.5 z-20 pointer-events-none">
            <div className="pointer-events-auto bg-[#071328]/92 backdrop-blur-xl border border-white/15 rounded-xl p-2.5 shadow-2xl flex flex-col gap-1.5 text-[10px] text-white/80">
              <span className="text-[8.5px] font-black text-white/40 uppercase tracking-widest block mb-0.5">Route Legend</span>
              <div className="flex items-center gap-2">
                <div className="w-3.5 h-1 rounded-full bg-[#00F0FF] shadow-[0_0_6px_#00F0FF]" />
                <span className="font-medium text-white/90">Combined Route</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3.5 h-1 rounded-full bg-white/40 border border-white/30 border-dashed" />
                <span className="font-medium text-white/70">Individual Route</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-2.5 h-2.5 rounded-full bg-[#22C55E] ring-1 ring-[#22C55E]/40" />
                <span>Pickup Point</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-2.5 h-2.5 rounded-sm bg-[#EF4444] ring-1 ring-[#EF4444]/40" />
                <span>Drop-off Point</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── BATCH & ROUTE DETAILS (BELOW MAP) ── */}
      <div className="glass-panel rounded-2xl p-4 border border-white/10 shadow-sm space-y-3.5">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <div className="h-7 w-7 rounded-lg bg-white/10 border border-white/15 flex items-center justify-center text-white/80">
              <Layers className="h-3.5 w-3.5 text-[#00F0FF]" />
            </div>
            <h3 className="text-xs sm:text-sm font-bold text-white tracking-tight uppercase tracking-wider">
              {isShared ? 'Batch Details' : 'Decision Details'}
            </h3>
          </div>
          <button
            type="button"
            onClick={() => navigate(`/live-map?xai=${highlight.requestId}`)}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10.5px] font-bold text-white/70 hover:text-white bg-white/5 hover:bg-white/10 border border-white/10 transition-colors"
          >
            <Navigation className="h-3 w-3 text-[#00F0FF]" />
            <span>View on Map</span>
          </button>
        </div>

        {/* 4 Metric Summary Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
          {/* Metric 1: Requests Count */}
          <div className="rounded-xl bg-white/[0.03] border border-white/5 p-3 hover:bg-white/[0.05] transition-colors">
            <span className="text-[10px] uppercase tracking-wider text-white/45 font-bold block">Requests</span>
            <span className="text-xl font-extrabold text-white tabular-nums tracking-tight mt-1 block">
              {totalRequestsInBatch}
            </span>
            <span className="text-[10px] text-white/40 block mt-0.5">
              {isShared ? 'Shared in batch' : 'Single passenger'}
            </span>
          </div>

          {/* Metric 2: Total Distance */}
          <div className="rounded-xl bg-white/[0.03] border border-white/5 p-3 hover:bg-white/[0.05] transition-colors">
            <span className="text-[10px] uppercase tracking-wider text-white/45 font-bold block">Total Distance</span>
            <span className="text-xl font-extrabold text-white tabular-nums tracking-tight mt-1 block">
              {Number.isFinite(highlight.estimatedDistanceKm) ? `${highlight.estimatedDistanceKm.toFixed(1)} km` : '—'}
            </span>
            <span className="text-[10px] text-white/40 block mt-0.5">Calculated route path</span>
          </div>

          {/* Metric 3: Routing Mode */}
          <div className="rounded-xl bg-white/[0.03] border border-white/5 p-3 hover:bg-white/[0.05] transition-colors">
            <span className="text-[10px] uppercase tracking-wider text-white/45 font-bold block">Routing Mode</span>
            <span className={`text-sm font-extrabold mt-1.5 block uppercase tracking-wide ${isShared ? 'text-[#00F0FF]' : isRejected ? 'text-rose-400' : 'text-sky-400'}`}>
              {isShared ? 'Combined' : isRejected ? 'Rejected' : 'Individual'}
            </span>
            <span className="text-[10px] text-white/40 block mt-0.5">
              {isShared ? 'Multi-request assignment' : 'Standalone dispatch'}
            </span>
          </div>

          {/* Metric 4: Impact / Status */}
          <div className="rounded-xl bg-white/[0.03] border border-white/5 p-3 hover:bg-white/[0.05] transition-colors">
            <span className="text-[10px] uppercase tracking-wider text-white/45 font-bold block">Impact / Status</span>
            {Number.isFinite(highlight.distanceSavedKm) && highlight.distanceSavedKm > 0 ? (
              <>
                <span className="text-sm font-extrabold text-emerald-400 mt-1.5 block">
                  &darr; {highlight.distanceSavedKm.toFixed(1)} km
                </span>
                <span className="text-[10px] text-emerald-400/60 block mt-0.5 font-medium">vs Individual Trips</span>
              </>
            ) : costSavedInr !== null && costSavedInr > 0 ? (
              <>
                <span className="text-sm font-extrabold text-emerald-400 mt-1.5 block">
                  &darr; ₹{costSavedInr}
                </span>
                <span className="text-[10px] text-emerald-400/60 block mt-0.5 font-medium">Combining Savings</span>
              </>
            ) : (
              <>
                <span className="text-sm font-extrabold text-white mt-1.5 block truncate">
                  {highlight.tripStatus || state.label}
                </span>
                <span className="text-[10px] text-white/40 block mt-0.5">Operational state</span>
              </>
            )}
          </div>
        </div>

        {/* Requests Table Breakdown */}
        <div className="space-y-2 pt-1">
          <div className="hidden sm:grid sm:grid-cols-12 gap-2 px-3 py-1.5 text-[9.5px] uppercase font-bold tracking-wider text-white/40 border-b border-white/5">
            <span className="col-span-1">#</span>
            <span className="col-span-2">Request ID</span>
            <span className="col-span-2">Type</span>
            <span className="col-span-3">Pickup Location</span>
            <span className="col-span-3">Drop Location</span>
            <span className="col-span-1 text-right">Role</span>
          </div>

          {/* Main Selected Request Row */}
          <div className="flex flex-col sm:grid sm:grid-cols-12 gap-2 p-3 rounded-xl bg-white/[0.03] border border-white/5 text-xs hover:bg-white/[0.05] transition-colors items-center">
            <span className="font-mono text-white/40 font-bold sm:col-span-1 hidden sm:block">1</span>
            <div className="flex items-center justify-between w-full sm:w-auto sm:col-span-2">
              <span className="font-mono font-bold text-white text-[12.5px]">#{highlight.requestId}</span>
              <span className="text-[9.5px] text-[#00F0FF] uppercase font-extrabold sm:hidden">Primary</span>
            </div>
            <div className="sm:col-span-2 w-full sm:w-auto">
              <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[9.5px] font-bold uppercase ${typeMeta.chipClass}`}>
                <typeMeta.Icon className="h-3 w-3" /> {typeMeta.label}
              </span>
            </div>
            <div className="sm:col-span-3 w-full flex items-center gap-1.5 text-[11px] text-white/80 min-w-0">
              <MapPin className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
              <span className="truncate">{highlight.pickupAddress || '—'}</span>
            </div>
            <div className="sm:col-span-3 w-full flex items-center gap-1.5 text-[11px] text-white/80 min-w-0">
              <Flag className="h-3.5 w-3.5 text-rose-400 shrink-0" />
              <span className="truncate">{highlight.dropAddress || '—'}</span>
            </div>
            <div className="sm:col-span-1 text-right hidden sm:block">
              <span className="px-2 py-0.5 rounded text-[9px] font-bold uppercase bg-[#00F0FF]/15 text-[#00F0FF] border border-[#00F0FF]/30">
                Primary
              </span>
            </div>
          </div>

          {/* Related / Partner Requests Rows */}
          {partnerRequests.map((p, idx) => {
            const pMeta = requestTypeMeta(p.request_type);
            return (
              <div
                key={p.id}
                className="flex flex-col sm:grid sm:grid-cols-12 gap-2 p-3 rounded-xl bg-white/[0.02] border border-white/5 text-xs hover:bg-white/[0.04] transition-colors items-center"
              >
                <span className="font-mono text-white/40 font-bold sm:col-span-1 hidden sm:block">{idx + 2}</span>
                <div className="flex items-center justify-between w-full sm:w-auto sm:col-span-2">
                  <span className="font-mono font-bold text-white text-[12.5px]">#{p.id}</span>
                  <span className="text-[9.5px] text-emerald-400 uppercase font-extrabold sm:hidden">Partner</span>
                </div>
                <div className="sm:col-span-2 w-full sm:w-auto">
                  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[9.5px] font-bold uppercase ${pMeta.chipClass}`}>
                    <pMeta.Icon className="h-3 w-3" /> {pMeta.label}
                  </span>
                </div>
                <div className="sm:col-span-3 w-full flex items-center gap-1.5 text-[11px] text-white/70 min-w-0">
                  <MapPin className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
                  <span className="truncate">{p.pickup_address || '—'}</span>
                </div>
                <div className="sm:col-span-3 w-full flex items-center gap-1.5 text-[11px] text-white/70 min-w-0">
                  <Flag className="h-3.5 w-3.5 text-rose-400 shrink-0" />
                  <span className="truncate">{p.drop_address || '—'}</span>
                </div>
                <div className="sm:col-span-1 text-right hidden sm:block">
                  <span className="px-2 py-0.5 rounded text-[9px] font-bold uppercase bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                    Partner
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── ESTIMATED IMPACT / SAVINGS (WHEN REAL SAVINGS EXIST) ── */}
      {hasSavings && (
        <div className="glass-panel rounded-2xl p-4 border border-white/10 shadow-sm space-y-3">
          <div className="flex items-center gap-2">
            <div className="h-6 w-6 rounded-lg bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <Leaf className="h-3.5 w-3.5" />
            </div>
            <span className="text-xs font-bold text-white uppercase tracking-wider">
              Estimated Impact
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
            {/* Distance Saved */}
            {Number.isFinite(highlight.distanceSavedKm) && highlight.distanceSavedKm > 0 && (
              <div className="p-3.5 rounded-xl bg-emerald-500/[0.07] border border-emerald-500/25 flex flex-col justify-between hover:bg-emerald-500/[0.1] transition-colors">
                <div className="flex items-center gap-1.5 text-emerald-400 mb-1">
                  <Leaf className="h-4 w-4" />
                  <span className="text-[10px] uppercase font-bold tracking-wider">Distance Saved</span>
                </div>
                <span className="text-xl font-extrabold text-white tabular-nums tracking-tight mt-1">
                  {highlight.distanceSavedKm.toFixed(1)} km
                </span>
                <span className="text-[9.5px] text-emerald-400/60 mt-0.5">Fleet routing reduction</span>
              </div>
            )}

            {/* Fuel Saved */}
            {Number.isFinite(highlight.fuelSavedL) && highlight.fuelSavedL > 0 && (
              <div className="p-3.5 rounded-xl bg-amber-500/[0.07] border border-amber-500/25 flex flex-col justify-between hover:bg-amber-500/[0.1] transition-colors">
                <div className="flex items-center gap-1.5 text-amber-400 mb-1">
                  <Fuel className="h-4 w-4" />
                  <span className="text-[10px] uppercase font-bold tracking-wider">Fuel Saved</span>
                </div>
                <span className="text-xl font-extrabold text-white tabular-nums tracking-tight mt-1">
                  {highlight.fuelSavedL.toFixed(2)} L
                </span>
                <span className="text-[9.5px] text-amber-400/60 mt-0.5">Calculated fuel conservation</span>
              </div>
            )}

            {/* CO2 Reduced */}
            {Number.isFinite(highlight.co2SavedKg) && highlight.co2SavedKg > 0 && (
              <div className="p-3.5 rounded-xl bg-cyan-500/[0.07] border border-cyan-500/25 flex flex-col justify-between hover:bg-cyan-500/[0.1] transition-colors">
                <div className="flex items-center gap-1.5 text-cyan-400 mb-1">
                  <Cloud className="h-4 w-4" />
                  <span className="text-[10px] uppercase font-bold tracking-wider">Emissions Reduced</span>
                </div>
                <span className="text-xl font-extrabold text-white tabular-nums tracking-tight mt-1">
                  {highlight.co2SavedKg.toFixed(2)} kg
                </span>
                <span className="text-[9.5px] text-cyan-400/60 mt-0.5">CO₂ offset via batching</span>
              </div>
            )}

            {/* Cost Saved */}
            {costSavedInr !== null && costSavedInr > 0 && (
              <div className="p-3.5 rounded-xl bg-purple-500/[0.07] border border-purple-500/25 flex flex-col justify-between hover:bg-purple-500/[0.1] transition-colors">
                <div className="flex items-center gap-1.5 text-purple-400 mb-1">
                  <IndianRupee className="h-4 w-4" />
                  <span className="text-[10px] uppercase font-bold tracking-wider">Cost Saved</span>
                </div>
                <span className="text-xl font-extrabold text-white tabular-nums tracking-tight mt-1">
                  ₹{costSavedInr.toLocaleString('en-IN')}
                </span>
                <span className="text-[9.5px] text-purple-400/60 mt-0.5">Shared operational economy</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}