import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  MapPin, Flag, X, Loader2, BrainCircuit, User, Truck, Info,
  AlertTriangle, Route as RouteIcon, Check,
} from 'lucide-react';
import {
  requestTypeMeta, decisionStateMeta, vehicleStatusMeta, vehicleTypeMeta,
} from '../../utils/requestSemantics';
import { buildOperationalRoute, describeSequence } from '../../utils/operationalRoute';

/**
 * Right-hand inspector for the live operations map.
 *
 * NOTE ON THE PROP CONTRACT — this component previously declared
 * `{ request, onClose }` while `LiveSimulationMap` passed
 * `{ selectedRequest, xaiHighlight, xaiLoading, xaiError, onCloseTrip,
 *    onDismissXai }`.  `request` was therefore always undefined and the panel
 * was permanently stuck on its "no trip selected" placeholder, which also
 * meant the /live-map?xai= deep link rendered no explanation at all.  The
 * signature below matches what the page actually passes.
 *
 * Everything rendered here comes from the API payload.  Fields the backend did
 * not supply render as "—"; nothing is filled in with a plausible-looking
 * placeholder.
 */

function fmt(value, digits, suffix) {
  return Number.isFinite(value) ? `${value.toFixed(digits)}${suffix}` : '—';
}

function Shell({ children }) {
  return (
    <div className="bg-[#0A0F1A]/80 rounded-2xl p-4 sm:p-5 backdrop-blur-xl border border-white/10 shadow-[0_12px_40px_rgba(0,0,0,0.5)] w-full md:w-[320px] max-w-full">
      {children}
    </div>
  );
}

function PanelHeader({ meta, title, onClose, closeTitle }) {
  return (
    <div className="flex items-center justify-between gap-2 mb-4">
      <div className="flex items-center gap-2 min-w-0">
        {meta && (
          <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] font-bold border shrink-0 uppercase tracking-wide ${meta.chipClass}`}>
            <meta.Icon className="h-3.5 w-3.5" /> {meta.label}
          </span>
        )}
        <span className="text-white font-mono text-[14px] font-bold truncate">{title}</span>
      </div>
      {onClose && (
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-white/50 hover:text-white transition-colors shrink-0"
          title={closeTitle}
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}

function AddressRow({ Icon, tone, label, value }) {
  return (
    <div className="flex items-start gap-3 bg-white/[0.02] border border-white/5 rounded-xl p-3.5">
      <div
        className="h-6 w-6 rounded-full flex items-center justify-center shrink-0 mt-0.5 border"
        style={{ background: `${tone}22`, borderColor: `${tone}4D` }}
      >
        <Icon className="h-3 w-3" style={{ color: tone }} />
      </div>
      <div className="min-w-0 flex-1">
        <span className="text-[10px] uppercase tracking-wider text-white/40 font-bold block mb-0.5">{label}</span>
        <span className="text-[12.5px] text-white/90 font-medium truncate block">{value || '—'}</span>
      </div>
    </div>
  );
}

// ── Live queue request (marker tapped on the map) ────────────────────────────

function QueueRequestCard({ request, onClose }) {
  const meta = requestTypeMeta(request.request_type);

  return (
    <Shell>
      <PanelHeader meta={meta} title={`#${request.id}`} onClose={onClose} closeTitle="Close request details" />

      <div className="flex items-center justify-between bg-white/5 border border-white/10 rounded-xl p-3 mb-4">
        <div className="flex flex-col gap-0.5 min-w-0">
          <span className="text-[10px] text-white/40 uppercase tracking-wider font-semibold">Provider</span>
          <span className="text-[13px] text-white font-medium truncate">{request.provider_name || '—'}</span>
        </div>
        <div className="w-px h-8 bg-white/10 mx-3" />
        <div className="flex flex-col gap-0.5 items-end shrink-0">
          <span className="text-[10px] text-white/40 uppercase tracking-wider font-semibold">Status</span>
          <span className="text-[13px] text-white font-medium">{request.status || '—'}</span>
        </div>
      </div>

      <div className="space-y-2 mb-4">
        <AddressRow Icon={MapPin} tone="#22C55E" label="Pickup" value={request.pickup_address} />
        <AddressRow Icon={Flag} tone="#EF4444" label="Drop-off" value={request.drop_address} />
      </div>

      <div className="grid grid-cols-3 gap-2 text-center text-[12px] border-t border-white/10 pt-3">
        {[
          ['Distance', fmt(request.estimated_distance_km, 1, ' km')],
          ['Est. time', fmt(request.estimated_time_min, 0, ' min')],
          ['Priority', request.priority || '—'],
        ].map(([label, value]) => (
          <div key={label} className="flex flex-col gap-1">
            <span className="text-[9.5px] text-white/40 uppercase tracking-wider font-semibold">{label}</span>
            <span className="font-semibold text-white tabular-nums">{value}</span>
          </div>
        ))}
      </div>

      <p className="mt-3 text-[10px] text-white/35 leading-relaxed">
        Queued request — open the Explainable Decisions view for its full A-DMFE
        factor attribution.
      </p>
    </Shell>
  );
}

// ── A-DMFE decision focus (deep-linked via /live-map?xai=) ───────────────────

function DecisionCardPanel({ highlight, onDismiss }) {
  const meta = requestTypeMeta(highlight.requestType);
  const state = decisionStateMeta(highlight.status, highlight.decision);
  const route = buildOperationalRoute(highlight);
  const sequence = describeSequence(route.stops);
  const f = highlight.factors || {};

  return (
    <Shell>
      <PanelHeader meta={meta} title={`#${highlight.requestId}`} onClose={onDismiss} closeTitle="Clear decision focus" />

      <div className="rounded-xl border p-3 mb-4" style={{ borderColor: `${state.color}44`, background: `${state.color}12` }}>
        <span className="flex items-center gap-1.5 text-[9.5px] uppercase tracking-wider font-bold mb-1 text-[#00F0FF]">
          <BrainCircuit className="h-3.5 w-3.5" /> A-DMFE decision
        </span>
        <p className="text-[13px] font-bold" style={{ color: state.color }}>
          {highlight.decision || 'No decision recorded'}
        </p>
        {highlight.reason && (
          <p className="text-[11px] text-white/55 mt-1 leading-relaxed">{highlight.reason}</p>
        )}
      </div>

      <div className="grid grid-cols-2 gap-2 mb-5">
        {[
          ['Compatibility', fmt(highlight.score, 1, '%')],
          ['Confidence', highlight.confidenceFallback
            ? `${fmt(highlight.confidence, 1, '%')} (est)`
            : fmt(highlight.confidence, 1, '%')],
        ].map(([label, value]) => (
          <div key={label} className="rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2.5">
            <span className="block text-[9px] uppercase tracking-wider text-white/40 font-bold mb-0.5">{label}</span>
            <span className="text-[17px] font-bold text-white tabular-nums tracking-tight">{value}</span>
          </div>
        ))}
      </div>

      {(highlight.driver || highlight.vehicle) && (
        <div className="flex items-center gap-4 bg-white/5 border border-white/10 rounded-xl p-3 mb-4 text-[11px]">
          {highlight.driver && (
            <span className="flex items-center gap-1.5 min-w-0">
              <User className="h-3.5 w-3.5 text-[#38BDF8] shrink-0" />
              <span className="text-white/75 truncate">{highlight.driver.name}</span>
            </span>
          )}
          {highlight.vehicle && (
            <span className="flex items-center gap-1.5 min-w-0">
              <Truck className="h-3.5 w-3.5 text-[#38BDF8] shrink-0" />
              <span className="text-white/75 truncate">
                {highlight.vehicle.name}{highlight.vehicle.type ? ` · ${highlight.vehicle.type}` : ''}
              </span>
            </span>
          )}
        </div>
      )}

      <div className="space-y-2 mb-4">
        <AddressRow Icon={MapPin} tone="#22C55E" label="Pickup" value={highlight.pickupAddress} />
        <AddressRow Icon={Flag} tone="#EF4444" label="Drop-off" value={highlight.dropAddress} />
      </div>

      {sequence.length > 1 && (
        <div className="mb-4">
          <span className="flex items-center gap-1.5 text-[9px] uppercase tracking-wider text-white/40 font-bold mb-1.5">
            <RouteIcon className="h-3 w-3" /> Operational sequence
          </span>
          <p className="text-[10.5px] text-white/70 font-mono leading-relaxed">{sequence.join(' → ')}</p>
          {route.isPlanned && (
            <p className="text-[10px] text-[#F59E0B] mt-1.5 flex items-start gap-1.5">
              <AlertTriangle className="h-3 w-3 shrink-0 mt-0.5" />
              Planned leg — no vehicle dispatched for this request yet.
            </p>
          )}
        </div>
      )}

      {highlight.factors && (
        <div className="space-y-1.5 mb-5 text-[11px] border-t border-white/10 pt-4">
          {[
            ['Pickup distance', fmt(f.pickup_distance_km, 2, ' km')],
            ['Route similarity', fmt(f.route_similarity_pct, 1, '%')],
            ['Estimated delay', fmt(f.estimated_delay_min, 1, ' min')],
            ['Trip distance', fmt(highlight.estimatedDistanceKm, 1, ' km')],
          ].map(([label, value]) => (
            <div key={label} className="flex items-center justify-between">
              <span className="text-white/50">{label}</span>
              <span className="text-white/90 font-mono font-medium tabular-nums">{value}</span>
            </div>
          ))}
        </div>
      )}

      <div className="border-t border-white/10 pt-3">
        <span className="text-[9px] uppercase tracking-wider text-white/40 font-bold block mb-2">Engine rationale</span>
        {(highlight.keyReasons || []).length > 0 ? (
          <ul className="space-y-1.5">
            {highlight.keyReasons.slice(0, 5).map((r, i) => (
              <li key={i} className="flex items-start gap-2 text-[10.5px] text-white/70">
                <Check className="h-3 w-3 text-[#22C55E] shrink-0 mt-0.5" />
                <span className="leading-relaxed">{r}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-[10.5px] text-white/35 italic">
            No factor rationale recorded for this decision.
          </p>
        )}
      </div>

      {highlight.tripCode && (
        <p className="mt-3 pt-3 border-t border-white/10 text-[10px] text-[#00F0FF] font-mono">
          {highlight.tripCode}{highlight.isShared ? ' · shared trip' : ' · individual trip'}
        </p>
      )}
    </Shell>
  );
}

// ── Vehicle inspector (fleet marker tapped on the map) ──────────────────────

function VehicleCard({ vehicle, onClose }) {
  const status = vehicleStatusMeta(vehicle.status);
  const type = vehicleTypeMeta(vehicle.vehicle_type);
  const TypeIcon = type.Icon;

  return (
    <Shell>
      <div className="flex items-center justify-between gap-2 mb-4">
        <div className="flex items-center gap-2 min-w-0">
          <span
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] font-bold border shrink-0 uppercase tracking-wide"
            style={{ color: status.color, borderColor: `${status.color}66`, background: `${status.color}1A` }}
          >
            <TypeIcon className="h-3.5 w-3.5" /> {status.label}
          </span>
          <span className="text-white font-mono text-[14px] font-bold truncate">
            {vehicle.vehicle_name || `#${vehicle.vehicle_id}`}
          </span>
        </div>
        {onClose && (
          <button onClick={onClose} className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-white/50 hover:text-white transition-colors shrink-0" title="Close vehicle details">
            <X className="h-4 w-4" />
          </button>
        )}
      </div>

      <div className="space-y-1.5 text-[11.5px] border-t border-white/10 pt-3">
        {[
          ['Type', type.label],
          ['Registration', vehicle.registration_number || '—'],
          ['Driver', vehicle.driver_name && vehicle.driver_name !== 'Unassigned' ? vehicle.driver_name : '—'],
          ['Provider', vehicle.provider_name || '—'],
          ['Position', Number.isFinite(vehicle.lat) && Number.isFinite(vehicle.lng)
            ? `${vehicle.lat.toFixed(4)}, ${vehicle.lng.toFixed(4)}` : '—'],
        ].map(([label, value]) => (
          <div key={label} className="flex items-center justify-between gap-3">
            <span className="text-white/45 shrink-0">{label}</span>
            <span className="text-white/85 truncate text-right">{value}</span>
          </div>
        ))}
      </div>

      <p className="mt-3 pt-3 border-t border-white/10 text-[10px] text-white/35 leading-relaxed">
        Fleet position as last reported by the platform. Vehicles without a
        recorded position are not shown on the map.
      </p>
    </Shell>
  );
}

// ── Panel ───────────────────────────────────────────────────────────────────

export default function TripDetailsPanel({
  selectedRequest,
  selectedVehicle = null,
  xaiHighlight,
  xaiLoading = false,
  xaiError = null,
  onCloseTrip,
  onCloseVehicle,
  onDismissXai,
}) {
  let key = 'hint';
  let content = null;

  if (xaiLoading) {
    key = 'xai-loading';
    content = (
      <Shell>
        <div className="flex items-center gap-2.5 text-[12px] text-white/60">
          <Loader2 className="h-4 w-4 animate-spin text-[#00F0FF]" />
          Loading A-DMFE explanation…
        </div>
      </Shell>
    );
  } else if (xaiError) {
    key = 'xai-error';
    content = (
      <Shell>
        <div className="flex items-start gap-2.5">
          <AlertTriangle className="h-4 w-4 text-[#EF4444] shrink-0 mt-0.5" />
          <div className="min-w-0 flex-1">
            <p className="text-[12px] text-white/80 leading-relaxed">{xaiError}</p>
            {onDismissXai && (
              <button onClick={onDismissXai} className="mt-2 text-[11px] text-[#00F0FF] hover:underline">
                Dismiss
              </button>
            )}
          </div>
        </div>
      </Shell>
    );
  } else if (xaiHighlight) {
    key = `xai-${xaiHighlight.requestId}`;
    content = <DecisionCardPanel highlight={xaiHighlight} onDismiss={onDismissXai} />;
  } else if (selectedRequest) {
    key = `trip-${selectedRequest.id}`;
    content = <QueueRequestCard request={selectedRequest} onClose={onCloseTrip} />;
  } else if (selectedVehicle) {
    key = `veh-${selectedVehicle.vehicle_id}`;
    content = <VehicleCard vehicle={selectedVehicle} onClose={onCloseVehicle} />;
  } else {
    content = (
      <Shell>
        <div className="text-center py-2">
          <Info className="h-9 w-9 mx-auto mb-3 opacity-40 text-[#00F0FF]" />
          <p className="text-[13px] font-semibold text-white">Nothing selected</p>
          <p className="text-[11px] text-white/50 mt-1 leading-relaxed">
            Select a request marker to inspect it, or open a decision from the
            Explainable Decisions view to see its route here.
          </p>
        </div>
      </Shell>
    );
  }

  return (
    <div className="w-full max-h-[calc(100vh-15rem)] overflow-y-auto custom-scrollbar pointer-events-auto pr-1">
      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={key}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 20 }}
          transition={{ duration: 0.25 }}
        >
          {content}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
