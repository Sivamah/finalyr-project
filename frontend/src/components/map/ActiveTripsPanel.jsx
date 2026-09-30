import React, { useState } from 'react';
import { Truck, CheckCircle2, ChevronDown, ChevronUp } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../../services/api';

/**
 * Minimal UI for the confirmed-partial "manual trip completion" integration.
 *
 * The live operations map draws active trips only as background polylines
 * (see `ActiveTripsLayer`) — nothing on the map is clickable to select a
 * specific Trip, so there was previously no path from the UI to
 * `POST /api/dmfe/trips/{id}/complete` at all (confirmed by reading
 * `LiveMapContainer.jsx`, `TripDetailsPanel.jsx` and `useOperationalNetwork.js`
 * in full: `selectedRequest`/`selectedVehicle` are populated only from the
 * pending-queue and fleet feeds, never from `activeTrips`).
 *
 * Rather than teach the map itself to select trips — which would mean
 * touching `ActiveTripsLayer`'s rendering and `LiveMapContainer`'s
 * click-handling, well beyond a minimal fix — this is a small, always
 * visible list of the trips the backend already reports as Active
 * (`GET /api/dmfe/trips?status=Active`, the same feed already driving the
 * background corridor layer), each with its own "Complete" action wired to
 * the existing, already-implemented completion endpoint. Nothing about
 * routing, OR-Tools, or the decision engine is touched.
 */
export default function ActiveTripsPanel({ trips = [], onCompleted }) {
  const [open, setOpen] = useState(true);
  const [completingId, setCompletingId] = useState(null);

  if (!trips.length) return null;

  const handleComplete = async (tripId) => {
    if (completingId) return;
    setCompletingId(tripId);
    try {
      await api.post(`/dmfe/trips/${tripId}/complete`);
      toast.success(`Trip #${tripId} completed — driver & vehicle released`);
      onCompleted?.();
    } catch (err) {
      toast.error(err.response?.data?.detail || `Could not complete trip #${tripId}`);
    } finally {
      setCompletingId(null);
    }
  };

  return (
    <div className="pointer-events-auto bg-[#0A0F1A]/75 rounded-2xl backdrop-blur-xl border border-white/10 shadow-[0_12px_40px_rgba(0,0,0,0.5)] w-full md:w-[280px] max-w-full overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between gap-2 px-4 py-3 text-left"
      >
        <span className="flex items-center gap-2 text-[12px] font-bold text-white">
          <Truck className="h-4 w-4 text-[#00F0FF]" /> Active Trips
          <span className="px-1.5 py-0.5 rounded-full text-[10px] bg-white/10 text-white/70 font-bold">
            {trips.length}
          </span>
        </span>
        {open ? <ChevronUp className="h-4 w-4 text-white/50" /> : <ChevronDown className="h-4 w-4 text-white/50" />}
      </button>

      {open && (
        <div className="max-h-[280px] overflow-y-auto custom-scrollbar border-t border-white/10 divide-y divide-white/5">
          {trips.map((t) => (
            <div key={t.id} className="flex items-center justify-between gap-2 px-4 py-2.5">
              <div className="min-w-0">
                <p className="text-[11.5px] font-mono font-semibold text-white truncate">
                  Trip #{t.id}{t.is_shared ? ' · shared' : ''}
                </p>
                <p className="text-[10.5px] text-white/45 truncate">
                  {t.vehicle_name || (t.vehicle_id ? `Vehicle #${t.vehicle_id}` : 'Vehicle —')}
                  {t.driver_name ? ` · ${t.driver_name}` : ''}
                </p>
              </div>
              <button
                type="button"
                onClick={() => handleComplete(t.id)}
                disabled={completingId === t.id}
                className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[10.5px] font-bold border border-[#22C55E]/30 bg-[#22C55E]/10 text-[#22C55E] hover:bg-[#22C55E]/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
                title="Mark this trip complete and release its driver/vehicle"
              >
                <CheckCircle2 className="h-3.5 w-3.5" />
                {completingId === t.id ? '…' : 'End Trip'}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
