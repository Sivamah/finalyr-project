import React, { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  X, CheckCircle2, XCircle, Clock, Route as RouteIcon,
  Leaf, User, Truck, ShieldCheck,
  AlertTriangle, Layers, Info
} from 'lucide-react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { REQUEST_TYPE_META } from '../../utils/requestSemantics';
import { formatINR } from '../../utils/currencyUtils';
import { TILE_URL, TILE_ATTRIBUTION, TILE_SUBDOMAINS } from '../../utils/tileConfig';

// Fix default leaflet marker icon assets
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

/**
 * Component to force Leaflet to recalculate its size after the Framer Motion
 * drawer animation finishes. Prevents broken/cropped map tiles.
 */
function MapInvalidator({ stopPoints }) {
  const map = useMap();
  useEffect(() => {
    // Drawer animation takes 300ms. Wait slightly longer to ensure layout is settled.
    const timer = setTimeout(() => {
      map.invalidateSize();
      if (stopPoints && stopPoints.length > 0) {
        map.fitBounds(stopPoints, { padding: [20, 20] });
      }
    }, 350);
    return () => clearTimeout(timer);
  }, [map, stopPoints]);
  return null;
}


function qualitativeLabel(pct) {
  if (pct >= 85) return 'Excellent';
  if (pct >= 70) return 'High';
  if (pct >= 50) return 'Good';
  if (pct >= 30) return 'Marginal';
  return 'Low';
}

function FactorProgressBar({ label, score, rawDetail }) {
  const isAvailable = score !== undefined && score !== null && !isNaN(score);
  const pct = isAvailable ? Math.round(score <= 1.0 ? score * 100 : score) : null;
  const rating = isAvailable ? qualitativeLabel(pct) : 'Not available';

  const barColor =
    !isAvailable ? 'bg-white/10' :
    pct >= 70 ? 'bg-brand-success' :
    pct >= 40 ? 'bg-brand-warning' :
    'bg-brand-danger';

  const textColor =
    !isAvailable ? 'text-brand-text-muted' :
    pct >= 70 ? 'text-brand-success' :
    pct >= 40 ? 'text-brand-warning' :
    'text-brand-danger';

  return (
    <div className="glass-card p-3.5 space-y-2">
      <div className="flex items-center justify-between text-xs">
        <span className="font-semibold text-gray-200">{label}</span>
        <div className="flex items-center gap-2">
          {isAvailable ? (
            <>
              <span className={`font-mono font-bold ${textColor}`}>{pct}%</span>
              <span className="text-[11px] px-2 py-0.5 rounded bg-white/10 text-white/80 font-medium border border-white/5">
                {rating}
              </span>
            </>
          ) : (
            <span className="text-xs text-brand-text-muted italic">Not available</span>
          )}
        </div>
      </div>

      <div className="h-2 bg-white/5 rounded-full overflow-hidden">
        {isAvailable ? (
          <div
            className={`h-full ${barColor} rounded-full transition-all duration-500`}
            style={{ width: `${Math.max(4, pct)}%` }}
          />
        ) : (
          <div className="h-full bg-white/10 rounded-full w-0" />
        )}
      </div>

      {rawDetail && (
        <p className="text-[11px] text-brand-text-muted pt-0.5">
          {rawDetail}
        </p>
      )}
    </div>
  );
}

export default function OrchestrationDetailsDrawer({ isOpen, onClose, result }) {
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') onClose?.();
    };
    if (isOpen) {
      window.addEventListener('keydown', onKey);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      window.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [isOpen, onClose]);

  if (!result) return null;

  const isAccepted = result.decision !== 'Rejected' && result.status !== 'Rejected';
  const isShared = result.is_shared || (result.requests && result.requests.length > 1);
  const requests = result.requests || [];
  const stops = result.best_route_json?.stops || [];

  const factorScores = result.factor_scores || {};
  const factorDetails = result.factor_details || {};
  const reasons = result.reasons || [];

  // Build route polyline points if valid coordinates exist
  const stopPoints = stops
    .filter((s) => s.lat && s.lng && !isNaN(s.lat) && !isNaN(s.lng))
    .map((s) => [s.lat, s.lng]);

  const mapCenter = stopPoints.length > 0 ? stopPoints[0] : [11.0168, 76.9558];

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[90] overflow-hidden">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="absolute inset-0 bg-black/40 backdrop-blur-[2px]"
            onClick={onClose}
          />

          {/* Drawer Container */}
          <div className="fixed inset-y-0 right-0 max-w-full flex pl-6 sm:pl-10">
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
              className="w-screen max-w-2xl bg-gray-900/90 backdrop-blur-2xl border-l border-white/10 shadow-[0_0_50px_rgba(0,0,0,0.5)] flex flex-col h-full overflow-hidden text-gray-100"
            >
              {/* Drawer Top Header */}
              <div className="px-6 py-4.5 border-b border-white/10 bg-black/40 flex items-center justify-between shrink-0">
                <div className="flex items-center gap-3 flex-wrap">
                  <div className="flex items-center gap-2">
                    <Layers className="h-5 w-5 text-brand-primary" />
                    <span className="text-base font-bold font-mono tracking-tight text-white">
                      {result.batch_id || `Trip #${result.id}`}
                    </span>
                  </div>

                  {isAccepted ? (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-brand-success/15 text-brand-success border border-brand-success/30">
                      <CheckCircle2 className="h-3.5 w-3.5" /> Accepted / Feasible
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-brand-danger/15 text-brand-danger border border-brand-danger/30">
                      <XCircle className="h-3.5 w-3.5" /> Rejected / Incompatible
                    </span>
                  )}

                  <span className="text-xs px-2 py-0.5 rounded bg-white/10 text-white/80 border border-white/5 font-medium">
                    {isShared ? 'Shared Batch' : 'Individual Request'}
                  </span>
                </div>

                <button
                  onClick={onClose}
                  className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-brand-text-muted hover:text-white transition-colors"
                  aria-label="Close details"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {/* Scrollable Content Body */}
              <div className="flex-1 overflow-y-auto custom-scrollbar p-6 space-y-6">

                {/* VISUAL DECISION FLOW INDICATOR */}
                <div className="glass-card rounded-2xl p-4 border border-white/5">
                  <p className="text-[11px] font-bold uppercase tracking-wider text-brand-text-muted mb-3 flex items-center gap-1.5">
                    <ShieldCheck className="h-4 w-4 text-brand-primary" />
                    A-DMFE Orchestration Pipeline Flow
                  </p>
                  <div className="grid grid-cols-3 sm:grid-cols-7 gap-1.5 text-center">
                    {[
                      { step: 1, label: 'Requests', status: 'done' },
                      { step: 2, label: 'A-DMFE Feasibility', status: 'done' },
                      { step: 3, label: 'Compatibility', status: 'done' },
                      { step: 4, label: 'Batch Decision', status: isAccepted ? 'done' : 'failed' },
                      { step: 5, label: 'Driver & Vehicle', status: isAccepted ? 'done' : 'skipped' },
                      { step: 6, label: 'OR-Tools Route', status: isAccepted ? 'done' : 'skipped' },
                      { step: 7, label: 'Final Result', status: isAccepted ? 'done' : 'failed' },
                    ].map((s) => {
                      const isFailed = s.status === 'failed';
                      const isSkipped = s.status === 'skipped';

                      const dotClass = isFailed
                        ? 'bg-brand-danger/20 text-brand-danger border-brand-danger/40'
                        : isSkipped
                        ? 'bg-white/5 text-white/40 border-white/10'
                        : 'bg-brand-success/20 text-brand-success border-brand-success/40';

                      return (
                        <div key={s.step} className="flex flex-col items-center">
                          <div
                            className={`h-7 w-7 rounded-full border flex items-center justify-center text-xs font-bold font-mono mb-1 ${dotClass}`}
                          >
                            {isFailed ? '✗' : s.step}
                          </div>
                          <span className={`text-[10px] leading-tight font-medium ${isFailed ? 'text-brand-danger' : isSkipped ? 'text-white/40' : 'text-white/80'}`}>
                            {s.label}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* SECTION A: DECISION SUMMARY */}
                <div className="space-y-3">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-brand-text-muted flex items-center gap-2">
                    <Info className="h-4 w-4 text-brand-primary" />
                    Decision Summary
                  </h3>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                    <div className="glass-card border border-white/5 rounded-xl p-3">
                      <p className="text-[11px] text-brand-text-muted">Orchestration Decision</p>
                      <p className={`text-sm font-bold mt-1 ${isAccepted ? 'text-brand-success' : 'text-brand-danger'}`}>
                        {isAccepted ? 'Accepted / Feasible' : 'Rejected'}
                      </p>
                    </div>

                    <div className="glass-card border border-white/5 rounded-xl p-3">
                      <p className="text-[11px] text-brand-text-muted">Compatibility Score</p>
                      <p className="text-sm font-bold text-white mt-1 font-mono">
                        {result.compatibility_score !== undefined && result.compatibility_score !== null
                          ? `${Number(result.compatibility_score).toFixed(1)}%`
                          : 'Not available'}
                      </p>
                    </div>

                    <div className="glass-card border border-white/5 rounded-xl p-3">
                      <p className="text-[11px] text-brand-text-muted">Requests Included</p>
                      <p className="text-sm font-bold text-white mt-1">
                        {result.request_count ?? requests.length}
                      </p>
                    </div>

                    <div className="glass-card border border-white/5 rounded-xl p-3">
                      <p className="text-[11px] text-brand-text-muted">Provider</p>
                      <p className="text-sm font-bold text-gray-200 mt-1 truncate" title={result.chosen_provider}>
                        {result.chosen_provider || '—'}
                      </p>
                    </div>

                    <div className="glass-card border border-white/5 rounded-xl p-3">
                      <p className="text-[11px] text-brand-text-muted">Vehicle</p>
                      <p className="text-sm font-bold text-gray-200 mt-1 truncate" title={result.chosen_vehicle}>
                        {result.chosen_vehicle || '—'}
                      </p>
                    </div>

                    <div className="glass-card border border-white/5 rounded-xl p-3">
                      <p className="text-[11px] text-brand-text-muted">Estimated Duration</p>
                      <p className="text-sm font-bold text-white mt-1 font-mono">
                        {isAccepted && result.eta_mins ? `${result.eta_mins} min` : '—'}
                      </p>
                    </div>

                    <div className="glass-card border border-white/5 rounded-xl p-3">
                      <p className="text-[11px] text-brand-text-muted">Estimated Cost</p>
                      <p className="text-sm font-bold text-brand-success mt-1 font-mono">
                        {isAccepted && result.estimated_cost !== undefined ? formatINR(result.estimated_cost) : '—'}
                      </p>
                    </div>

                    <div className="glass-card border border-white/5 rounded-xl p-3">
                      <p className="text-[11px] text-brand-text-muted">Distance Saved</p>
                      <p className="text-sm font-bold text-brand-primary mt-1 font-mono">
                        {isAccepted && result.distance_saved_km !== undefined ? `${result.distance_saved_km} km` : '—'}
                      </p>
                    </div>
                  </div>

                  {isAccepted && (
                    <div className="flex items-center gap-4 text-xs text-brand-text-muted pt-1 px-1">
                      <span className="flex items-center gap-1.5">
                        <Leaf className="h-3.5 w-3.5 text-brand-success" />
                        Estimated CO₂ Saved: <strong className="text-gray-200">{result.co2_saved_kg || 0} kg</strong>
                      </span>
                      <span className="flex items-center gap-1.5">
                        <RouteIcon className="h-3.5 w-3.5 text-brand-primary" />
                        Fuel Saved: <strong className="text-gray-200">{result.fuel_saved_l || 0} L</strong>
                      </span>
                    </div>
                  )}
                </div>

                {/* SECTION B: REQUESTS INCLUDED */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-brand-text-muted flex items-center gap-2">
                      <Layers className="h-4 w-4 text-brand-primary" />
                      Requests Included ({requests.length})
                    </h3>
                    <span className="text-xs text-brand-text-muted">
                      {isShared ? 'Shared multi-service batch' : 'Individual trip (solo)'}
                    </span>
                  </div>

                  {requests.length === 0 ? (
                    <div className="glass-card border border-white/5 rounded-xl p-4 text-center text-xs text-brand-text-muted">
                      No request details available for this result.
                    </div>
                  ) : (
                    <div className="space-y-2.5">
                      {requests.map((req, idx) => {
                        const rawType = (req.request_type || 'ride').toLowerCase();
                        const typeMeta = REQUEST_TYPE_META[rawType] || REQUEST_TYPE_META.ride;
                        const TypeIcon = typeMeta.Icon;

                        return (
                          <div
                            key={req.id || idx}
                            className="glass-card border border-white/5 rounded-xl p-3.5 hover:border-white/20 transition-colors"
                          >
                            <div className="flex items-center justify-between gap-2 mb-2">
                              <div className="flex items-center gap-2">
                                <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-lg text-xs font-bold border ${typeMeta.chipClass}`}>
                                  <TypeIcon className="h-3.5 w-3.5" />
                                  {typeMeta.longLabel || typeMeta.label}
                                </span>
                                <span className="font-mono text-xs font-bold text-white">
                                  #{req.id}
                                </span>
                              </div>

                              <div className="flex items-center gap-2">
                                <span className="text-[11px] px-2 py-0.5 rounded bg-white/10 text-white/80 border border-white/5 font-medium">
                                  Priority: {req.priority || 'Medium'}
                                </span>
                                {req.demand > 1 && (
                                  <span className="text-[11px] px-2 py-0.5 rounded bg-brand-primary/20 text-brand-primary border border-brand-primary/30 font-medium">
                                    Demand: {req.demand}
                                  </span>
                                )}
                              </div>
                            </div>

                            <div className="space-y-1 text-xs text-gray-300">
                              <div className="flex items-start gap-2">
                                <span className="h-2 w-2 rounded-full bg-brand-success mt-1.5 shrink-0" />
                                <span className="text-brand-text-muted font-medium shrink-0">Pickup:</span>
                                <span className="text-white/90 truncate">{req.pickup_address}</span>
                              </div>
                              <div className="flex items-start gap-2">
                                <span className="h-2 w-2 rounded-full bg-brand-danger mt-1.5 shrink-0" />
                                <span className="text-brand-text-muted font-medium shrink-0">Drop:</span>
                                <span className="text-white/90 truncate">{req.drop_address}</span>
                              </div>
                            </div>

                            {req.max_acceptable_delay_min && (
                              <p className="text-[11px] text-brand-text-muted mt-2 flex items-center gap-1">
                                <Clock className="h-3 w-3" /> Max Allowed Delay: {req.max_acceptable_delay_min} min
                              </p>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>

                {/* SECTION C: A-DMFE FEASIBILITY ANALYSIS */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-brand-text-muted flex items-center gap-2">
                      <ShieldCheck className="h-4 w-4 text-brand-success" />
                      A-DMFE Feasibility Analysis
                    </h3>
                    <span className="text-xs text-brand-text-muted">
                      Rule-based adaptive compatibility factors
                    </span>
                  </div>

                  <div className="space-y-2">
                    <FactorProgressBar
                      label="Pickup Proximity"
                      score={factorScores.pickup}
                      rawDetail={
                        factorDetails.pickup_distance_m !== undefined
                          ? `Evaluated pickup distance: ${(factorDetails.pickup_distance_m / 1000).toFixed(2)} km`
                          : null
                      }
                    />

                    <FactorProgressBar
                      label="Route Similarity"
                      score={factorScores.route}
                      rawDetail={
                        factorDetails.route_overlap_label
                          ? `Route overlap classification: ${factorDetails.route_overlap_label}`
                          : null
                      }
                    />

                    <FactorProgressBar
                      label="Time Compatibility"
                      score={factorScores.time}
                      rawDetail={
                        factorDetails.time_diff_min !== undefined
                          ? `Time window difference: ${factorDetails.time_diff_min} min`
                          : null
                      }
                    />

                    <FactorProgressBar
                      label="Vehicle Capacity"
                      score={factorScores.capacity}
                      rawDetail={
                        factorDetails.capacity_note ||
                        (factorDetails.capacity_utilization_pct !== undefined
                          ? `Predicted utilization: ${factorDetails.capacity_utilization_pct}%`
                          : null)
                      }
                    />

                    <FactorProgressBar
                      label="Priority Compatibility"
                      score={factorScores.priority}
                      rawDetail={
                        factorDetails.priority_label
                          ? `Combined batch priority: ${factorDetails.priority_label}`
                          : null
                      }
                    />
                  </div>
                </div>

                {/* SECTION D: WHY WAS THIS BATCH ACCEPTED / REJECTED? */}
                <div className="space-y-3">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-brand-text-muted flex items-center gap-2">
                    {isAccepted ? (
                      <CheckCircle2 className="h-4 w-4 text-brand-success" />
                    ) : (
                      <AlertTriangle className="h-4 w-4 text-brand-danger" />
                    )}
                    {isAccepted ? 'Why Was This Batch Accepted?' : 'Why Was This Batch Rejected?'}
                  </h3>

                  {isAccepted ? (
                    <div className="bg-brand-success/10 border border-brand-success/30 rounded-xl p-4 space-y-2 text-xs">
                      <p className="text-brand-success font-medium">
                        A-DMFE feasibility checks passed successfully:
                      </p>
                      <ul className="space-y-1.5 text-white/80">
                        {reasons.length > 0 ? (
                          reasons.map((r, i) => (
                            <li key={i} className="flex items-start gap-2">
                              <span className="text-brand-success font-bold shrink-0">✓</span>
                              <span>{String(r)}</span>
                            </li>
                          ))
                        ) : (
                          <>
                            <li className="flex items-start gap-2">
                              <span className="text-brand-success font-bold">✓</span>
                              <span>Pickup locations are geographically proximate and within allowable clustering threshold.</span>
                            </li>
                            <li className="flex items-start gap-2">
                              <span className="text-brand-success font-bold">✓</span>
                              <span>Route corridors exhibit compatible headings without excessive detour delay.</span>
                            </li>
                            <li className="flex items-start gap-2">
                              <span className="text-brand-success font-bold">✓</span>
                              <span>Selected vehicle has sufficient capacity to carry combined demand simultaneously.</span>
                            </li>
                          </>
                        )}
                      </ul>
                    </div>
                  ) : (
                    <div className="bg-brand-danger/10 border border-brand-danger/30 rounded-xl p-4 space-y-2 text-xs">
                      <p className="text-brand-danger font-semibold flex items-center gap-1.5">
                        <AlertTriangle className="h-4 w-4 text-brand-danger shrink-0" />
                        Feasibility Constraint Not Satisfied:
                      </p>
                      <p className="text-brand-danger/80 font-medium">
                        {result.failed_gate || 'A-DMFE Compatibility Gate Failed'}
                      </p>
                      <ul className="space-y-1 text-white/80 mt-2">
                        {reasons.map((r, i) => (
                          <li key={i} className="flex items-start gap-2">
                            <span className="text-brand-danger shrink-0">•</span>
                            <span>{String(r)}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>

                {/* SECTION E: DRIVER & VEHICLE ASSIGNMENT */}
                <div className="space-y-3">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-brand-text-muted flex items-center gap-2">
                    <Truck className="h-4 w-4 text-brand-primary" />
                    Driver & Vehicle Assignment
                  </h3>

                  {isAccepted ? (
                    <div className="glass-panel border border-white/10 rounded-xl p-4 space-y-3">
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <div className="bg-white/5 border border-white/5 rounded-lg p-3">
                          <p className="text-[11px] text-brand-text-muted flex items-center gap-1">
                            <User className="h-3.5 w-3.5 text-brand-primary" /> Assigned Driver
                          </p>
                          <p className="text-sm font-bold text-white mt-1">
                            {result.driver?.name || 'Driver Assigned'}
                          </p>
                          <p className="text-[11px] text-brand-text-muted mt-0.5">
                            Status: <span className="text-brand-success">{result.driver?.status || 'Assigned'}</span>
                            {result.driver?.rating && ` · Rating: ★${result.driver.rating}`}
                          </p>
                        </div>

                        <div className="bg-white/5 border border-white/5 rounded-lg p-3">
                          <p className="text-[11px] text-brand-text-muted flex items-center gap-1">
                            <Truck className="h-3.5 w-3.5 text-brand-primary" /> Assigned Vehicle
                          </p>
                          <p className="text-sm font-bold text-white mt-1">
                            {result.vehicle?.name || result.chosen_vehicle || 'Vehicle Assigned'}
                          </p>
                          <p className="text-[11px] text-brand-text-muted mt-0.5">
                            Capacity: {result.vehicle?.capacity || result.vehicle_capacity || 4} seats/units
                            {result.vehicle?.plate_number && ` · ${result.vehicle.plate_number}`}
                          </p>
                        </div>
                      </div>

                      <div className="bg-black/20 rounded-lg p-3 text-xs space-y-1.5 border border-white/5">
                        <div className="flex justify-between text-brand-text-muted text-[11px]">
                          <span>Capacity Utilization</span>
                          <span className="font-mono text-gray-200">
                            {result.current_load || requests.length} / {result.vehicle?.capacity || result.vehicle_capacity || 4} units ({result.utilization_pct || 50}%)
                          </span>
                        </div>
                        <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-brand-primary rounded-full"
                            style={{ width: `${Math.min(100, Math.max(10, result.utilization_pct || 50))}%` }}
                          />
                        </div>
                        <p className="text-[11px] text-brand-text-muted pt-1">
                          {result.assignment_reason || 'Assignment engine selected this driver/vehicle pair based on vehicle capacity match, driver availability, and pickup proximity.'}
                        </p>
                      </div>
                    </div>
                  ) : (
                    <div className="glass-card border border-white/5 rounded-xl p-4 text-xs text-brand-text-muted">
                      <p className="font-medium text-white/80">No driver or vehicle assigned.</p>
                      <p className="text-[11px] text-brand-text-muted mt-1">
                        Requests in an unfeasible or rejected batch are not dispatched and remain in queue for solo dispatch or alternative matching.
                      </p>
                    </div>
                  )}
                </div>

                {/* SECTION F: ROUTE OPTIMIZATION (OR-Tools) */}
                {isAccepted && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <h3 className="text-xs font-bold uppercase tracking-wider text-brand-text-muted flex items-center gap-2">
                        <RouteIcon className="h-4 w-4 text-brand-primary" />
                        Route Optimization (Google OR-Tools)
                      </h3>
                      <span className="text-[11px] px-2 py-0.5 rounded bg-brand-primary/15 text-brand-primary border border-brand-primary/30 font-medium">
                        Route Status: Optimized
                      </span>
                    </div>

                    {/* Research note highlighting A-DMFE vs OR-Tools distinction */}
                    <div className="bg-brand-primary/10 border border-brand-primary/20 rounded-xl p-3 text-xs text-brand-primary/90 leading-relaxed">
                      <strong>Methodology distinction:</strong> A-DMFE determines feasible batching first; Google OR-Tools then determines the optimal stop sequence and route order for the accepted batch.
                    </div>

                    {/* Route Stops Sequence */}
                    {stops.length > 0 ? (
                      <div className="glass-card border border-white/5 rounded-xl p-4 space-y-3">
                        <p className="text-xs font-semibold text-white/80">OR-Tools Stop Sequence:</p>
                        <div className="relative pl-6 space-y-4 border-l border-brand-primary/30 ml-2">
                          {stops.map((s, idx) => {
                            const isPickup = s.action === 'pickup';
                            return (
                              <div key={idx} className="relative">
                                <div
                                  className={`absolute -left-[31px] top-0 h-4 w-4 rounded-full border-2 border-gray-900 flex items-center justify-center text-[9px] font-bold text-white ${
                                    isPickup ? 'bg-brand-success' : 'bg-brand-danger'
                                  }`}
                                >
                                  {idx + 1}
                                </div>
                                <div className="text-xs">
                                  <div className="flex items-center gap-2">
                                    <span className={`font-bold uppercase tracking-wide text-[10px] ${isPickup ? 'text-brand-success' : 'text-brand-danger'}`}>
                                      {isPickup ? 'Pickup' : 'Drop'}
                                    </span>
                                    {s.service_label && (
                                      <span className="px-1.5 py-0.2 rounded text-[10px] bg-white/10 text-white/80 border border-white/5">
                                        {s.service_label}
                                      </span>
                                    )}
                                    <span className="font-mono text-brand-text-muted text-[11px]">
                                      #{s.request_id}
                                    </span>
                                    {s.arrival_min !== undefined && (
                                      <span className="ml-auto text-[11px] text-brand-primary font-mono">
                                        +{s.arrival_min} min
                                      </span>
                                    )}
                                  </div>
                                  <p className="text-white/80 text-[11px] mt-0.5">
                                    {s.address || `Stop #${idx + 1}`}
                                  </p>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    ) : (
                      <div className="glass-card border border-white/5 rounded-xl p-4 text-xs text-brand-text-muted">
                        Stop sequence generated directly from pickup and drop locations.
                      </div>
                    )}

                    {/* Compact Leaflet Mini-map if coordinates exist */}
                    {stopPoints.length > 0 && (
                      <div className="rounded-xl overflow-hidden border border-white/10 w-full h-[260px] relative z-0 bg-gray-900/50 flex shrink-0">
                        <MapContainer
                          center={mapCenter}
                          zoom={12}
                          scrollWheelZoom={false}
                          className="w-full h-full absolute inset-0 z-0"
                          style={{ height: '100%', width: '100%', minHeight: '260px', background: 'transparent' }}
                        >
                          <MapInvalidator stopPoints={stopPoints} />
                          <TileLayer
                            attribution={TILE_ATTRIBUTION}
                            url={TILE_URL}
                            subdomains={TILE_SUBDOMAINS}
                          />
                          {stops.filter((s) => s.lat && s.lng).map((s, idx) => (
                            <Marker key={idx} position={[s.lat, s.lng]}>
                              <Popup>
                                <div className="text-xs">
                                  <strong>Stop {idx + 1}: {s.action?.toUpperCase()}</strong>
                                  <br />
                                  {s.address}
                                </div>
                              </Popup>
                            </Marker>
                          ))}
                          {stopPoints.length >= 2 && (
                            <Polyline
                              positions={stopPoints}
                              color="#6366f1"
                              weight={3}
                              opacity={0.8}
                              dashArray="5, 8"
                            />
                          )}
                        </MapContainer>
                      </div>
                    )}
                  </div>
                )}

                {/* SECTION G: FINAL OUTCOME SUMMARY */}
                <div className="space-y-3">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-brand-text-muted flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4 text-brand-primary" />
                    Final Outcome
                  </h3>

                  <div className="glass-panel border border-white/10 rounded-xl p-4">
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                      <div>
                        <span className="text-brand-text-muted text-[11px]">Decision</span>
                        <p className={`font-bold mt-0.5 ${isAccepted ? 'text-brand-success' : 'text-brand-danger'}`}>
                          {isAccepted ? 'Feasible' : 'Rejected'}
                        </p>
                      </div>
                      <div>
                        <span className="text-brand-text-muted text-[11px]">Compatibility</span>
                        <p className="font-bold text-white mt-0.5 font-mono">
                          {result.compatibility_score !== undefined ? `${Number(result.compatibility_score).toFixed(1)}%` : '—'}
                        </p>
                      </div>
                      <div>
                        <span className="text-brand-text-muted text-[11px]">Vehicle</span>
                        <p className="font-bold text-white mt-0.5 truncate">{result.chosen_vehicle || '—'}</p>
                      </div>
                      <div>
                        <span className="text-brand-text-muted text-[11px]">Duration</span>
                        <p className="font-bold text-white mt-0.5 font-mono">
                          {isAccepted && result.eta_mins ? `${result.eta_mins} min` : '—'}
                        </p>
                      </div>
                      <div>
                        <span className="text-brand-text-muted text-[11px]">Distance</span>
                        <p className="font-bold text-white mt-0.5 font-mono">
                          {isAccepted && result.best_route_json?.distance_km ? `${result.best_route_json.distance_km} km` : '—'}
                        </p>
                      </div>
                      <div>
                        <span className="text-brand-text-muted text-[11px]">Estimated Cost</span>
                        <p className="font-bold text-brand-success mt-0.5 font-mono">
                          {isAccepted ? formatINR(result.estimated_cost) : '—'}
                        </p>
                      </div>
                      <div>
                        <span className="text-brand-text-muted text-[11px]">CO₂ Saved</span>
                        <p className="font-bold text-brand-success mt-0.5 font-mono">
                          {isAccepted ? `${result.co2_saved_kg || 0} kg` : '—'}
                        </p>
                      </div>
                      <div>
                        <span className="text-brand-text-muted text-[11px]">Batch Code</span>
                        <p className="font-bold text-white/80 mt-0.5 font-mono text-[11px] truncate">
                          {result.batch_id}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

              </div>

              {/* Drawer Footer */}
              <div className="px-6 py-4 border-t border-white/10 bg-black/60 flex justify-end shrink-0">
                <button
                  type="button"
                  onClick={onClose}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-white/5 hover:bg-white/10 text-white border border-white/10 transition-colors"
                >
                  Close Details
                </button>
              </div>
            </motion.div>
          </div>
        </div>
      )}
    </AnimatePresence>
  );
}
