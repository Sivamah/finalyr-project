import React, { useState } from 'react';
import { Bike, ShoppingBag, Package, ChevronDown, ChevronUp, Clock, UserPlus } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../../services/api';
import CompatibilityGauge from './CompatibilityGauge';
import FactorBreakdown from './FactorBreakdown';

const TYPE_ICONS = {
  ride:   { icon: Bike,        color: 'text-brand-primary', bg: 'bg-brand-primary/10 border-brand-primary/20' },
  food:   { icon: ShoppingBag, color: 'text-brand-warning', bg: 'bg-brand-warning/10 border-brand-warning/20' },
  parcel: { icon: Package,     color: 'text-brand-accent',  bg: 'bg-brand-accent/10 border-brand-accent/20' },
};

function RequestPill({ req }) {
  const cfg = TYPE_ICONS[req.request_type] || TYPE_ICONS.ride;
  const Icon = cfg.icon;
  return (
    <div className={`flex items-center gap-3 px-3 py-2.5 rounded-xl border ${cfg.bg}`}>
      <div className={`p-1.5 rounded-lg bg-black/20 ${cfg.color}`}>
        <Icon className="h-3.5 w-3.5 shrink-0" />
      </div>
      <div className="min-w-0">
        <p className={`text-[10px] font-bold tracking-wide uppercase ${cfg.color}`}>
          {req.request_type?.charAt(0).toUpperCase() + req.request_type?.slice(1)} #{req.id}
        </p>
        <p className="text-[11px] text-white/80 truncate mt-0.5">
          {req.pickup_address} <span className="text-white/30 mx-1">→</span> {req.drop_address}
        </p>
      </div>
    </div>
  );
}

export default function CandidateBatchCard({ batch, onAssigned }) {
  const [expanded, setExpanded] = useState(false);
  const [assigning, setAssigning] = useState(false);

  const requests = batch.requests_summary || [];

  /**
   * "Assign Driver & Vehicle" — the confirmed-partial "driver assignment"
   * AND "vehicle assignment" integrations, satisfied by ONE action: the
   * engine's POST /api/dmfe/assign/driver already selects the best
   * available driver AND vehicle together (dispatch_trip persists both on
   * the resulting Trip), so this is not two buttons wired to two
   * endpoints — it is the one endpoint that already does both, exposed in
   * the UI for the first time.
   */
  const handleAssign = async (e) => {
    e.stopPropagation();
    if (assigning || !batch.id) return;
    setAssigning(true);
    try {
      const res = await api.post('/dmfe/assign/driver', { batch_id: batch.id });
      const { driver, vehicle } = res.data || {};
      toast.success(
        driver && vehicle
          ? `Assigned ${driver.name} · ${vehicle.name} to ${batch.batch_code}`
          : `${batch.batch_code} dispatched`
      );
      onAssigned?.();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not assign a driver/vehicle for this batch');
    } finally {
      setAssigning(false);
    }
  };

  // A solo / "Individual" trip has no PAIR, so there is no pairwise
  // compatibility score to show.  The engine persists compatibility_score = 0.0
  // for these rows purely as a sentinel (decision_engine.py, Phase 9).  Painting
  // that 0.0 as a red "Incompatible" gauge misreports "not applicable" as
  // "measured and failed", and contradicts the "Individual" badge beside it.
  const isIndividual = batch.decision === 'Individual' || requests.length < 2;
  const isCompatible = batch.decision === 'Compatible';

  const borderColor = isIndividual
    ? 'border-white/10'
    : isCompatible
      ? 'border-brand-success/30 ring-1 ring-brand-success/10'
      : 'border-brand-danger/20';
  const badgeCls = isIndividual
    ? 'bg-white/5 text-brand-text-muted border-white/10'
    : isCompatible
      ? 'bg-brand-success/15 text-brand-success border-brand-success/30'
      : 'bg-brand-danger/15 text-brand-danger border-brand-danger/30';

  return (
    <div className={`glass-card border ${borderColor} rounded-2xl shadow-sm overflow-hidden`}>
      {/* Card Header — always visible */}
      <div className="p-5">
        <div className="flex items-start justify-between gap-3 mb-4">
          {/* Left: batch code + decision */}
          <div className="flex flex-col gap-2 flex-wrap">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[13px] font-bold font-mono text-white">{batch.batch_code}</span>
              <span className={`text-[10px] px-2 py-0.5 rounded border font-bold tracking-wider uppercase ${badgeCls}`}>
                {batch.decision}
              </span>
              {batch.status === 'Dispatched' && (
                <span className="text-[10px] px-2 py-0.5 rounded border font-bold tracking-wider uppercase bg-brand-primary/15 text-brand-primary border-brand-primary/30">
                  Dispatched
                </span>
              )}
            </div>
            {batch.estimated_delay_min > 0 && (
              <span className="flex items-center gap-1.5 text-[11px] font-medium text-brand-warning bg-brand-warning/10 border border-brand-warning/20 w-fit px-2 py-0.5 rounded">
                <Clock className="h-3 w-3" /> +{batch.estimated_delay_min} min delay
              </span>
            )}
          </div>

          {/* Gauge */}
          <CompatibilityGauge
            score={isIndividual ? null : batch.compatibility_score}
            naLabel="Solo trip"
            size={88}
          />
        </div>

        {/* Included requests pills */}
        <div className="mt-3 space-y-1.5">
          {requests.map((req) => (
            <RequestPill key={req.id} req={req} />
          ))}
        </div>

        {/* Assign Driver & Vehicle */}
        {batch.status !== 'Dispatched' && (
          <button
            type="button"
            onClick={handleAssign}
            disabled={assigning || !batch.id}
            className="mt-4 w-full flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-xl text-[12px] font-semibold border border-brand-primary/30 bg-brand-primary/10 text-brand-primary hover:bg-brand-primary/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title="Select and assign the best available driver + vehicle for this batch"
          >
            <UserPlus className={`h-3.5 w-3.5 ${assigning ? 'animate-pulse' : ''}`} />
            {assigning ? 'Assigning…' : 'Assign Driver & Vehicle'}
          </button>
        )}
      </div>

      {/* Expandable detail section */}
      <button
        type="button"
        onClick={() => setExpanded(v => !v)}
        className="w-full flex items-center justify-between px-5 py-2.5 bg-black/10 border-t border-white/5 text-[11px] font-bold uppercase tracking-wider text-brand-text-muted hover:text-white transition-colors"
      >
        <span>{expanded ? 'Hide' : 'Show'} factor breakdown & reasons</span>
        {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
      </button>

      {expanded && (
        <div className="px-5 py-5 border-t border-white/5 space-y-5 bg-black/20">
          {/* Factor bars */}
          <div>
            <h5 className="text-[11px] font-bold text-white/50 uppercase tracking-wider mb-3">
              Factor Score Breakdown
            </h5>
            <FactorBreakdown factorScores={batch.factor_scores || {}} />
          </div>

          {/* Explainability reasons */}
          {batch.reasons?.length > 0 && (
            <div>
              <h5 className="text-[11px] font-bold text-white/50 uppercase tracking-wider mb-3">
                Decision Explanation
              </h5>
              <ul className="space-y-1.5">
                {batch.reasons.map((r, i) => (
                  <li key={i} className={`text-[12px] ${
                    r.startsWith('✓') ? 'text-brand-success'
                    : r.startsWith('✗') ? 'text-brand-danger'
                    : 'text-brand-text-muted'
                  }`}>
                    {r}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
