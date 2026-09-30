import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  MapPin, Flag, BrainCircuit, User, Truck,
  AlertTriangle, X, Users, Map as MapIcon,
  DollarSign, Layers, Navigation
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, LabelList,
} from 'recharts';
import {
  requestTypeMeta, decisionStateMeta,
} from '../../utils/requestSemantics';
import { buildOperationalRoute, describeSequenceNumbered } from '../../utils/operationalRoute';

/**
 * RIGHT-hand XAI decision detail panel for the AI Insights 3-column workspace.
 *
 * Visual hierarchy:
 * 1. Decision Header (Service type pill, ID, route mode pill, View on Map action)
 * 2. A-DMFE Decision Card with Circular Compatibility Score Gauge & Key Metrics
 * 3. Compatibility Factors (5 vibrant colored progress bars with decimal & % scores)
 * 4. AI Explanation (XAI) / Why this decision (numbered step rationale)
 * 5. Additional Details Tabs (Requests, Route Sequence, Savings & Economics)
 *
 * Source of truth: Real backend normalized highlight payload.
 * No invented metrics or fake data.
 */

function fmt(value, digits, suffix = '') {
  return Number.isFinite(value) ? `${value.toFixed(digits)}${suffix}` : '—';
}

function fmtInr(value) {
  return Number.isFinite(value)
    ? `₹${value.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`
    : '—';
}

function ScoreGauge({ score, size = 76, strokeWidth = 5.5 }) {
  if (!Number.isFinite(score)) {
    return (
      <div className="flex flex-col items-center justify-center p-2 rounded-2xl bg-white/[0.03] border border-white/10 min-w-[76px] min-h-[76px]">
        <span className="text-[16px] font-mono font-bold text-white/30">—</span>
        <span className="text-[8px] uppercase tracking-wider text-white/40 mt-0.5 text-center font-bold">Score</span>
      </div>
    );
  }
  const pct = Math.min(100, Math.max(0, score));
  const radius = (size - strokeWidth * 2) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (pct / 100) * circumference;
  const displayVal = (score > 1 ? score / 100 : score).toFixed(2);
  const color = pct >= 70 ? '#00F0FF' : pct >= 40 ? '#F59E0B' : '#EF4444';

  return (
    <div className="relative flex flex-col items-center justify-center shrink-0">
      <svg width={size} height={size} className="transform -rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="rgba(255, 255, 255, 0.08)"
          strokeWidth={strokeWidth}
          fill="transparent"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          fill="transparent"
          className="transition-all duration-700 ease-out"
          style={{ filter: `drop-shadow(0 0 6px ${color}88)` }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
        <span className="text-[14px] font-mono font-black text-white leading-none tracking-tight">
          {displayVal}
        </span>
        <span className="text-[7.5px] uppercase tracking-wider text-white/50 font-bold mt-1 leading-none text-center">
          Score
        </span>
      </div>
    </div>
  );
}

function AddressRow({ Icon, tone, label, value }) {
  return (
    <div className="flex items-start gap-2.5 bg-white/[0.02] border border-white/5 rounded-xl p-2.5 hover:bg-white/[0.04] transition-colors">
      <div
        className="h-6 w-6 rounded-lg flex items-center justify-center shrink-0 mt-0.5 border"
        style={{ background: `${tone}18`, borderColor: `${tone}44` }}
      >
        <Icon className="h-3 w-3" style={{ color: tone }} />
      </div>
      <div className="min-w-0 flex-1">
        <span className="text-[9px] uppercase tracking-wider text-white/40 font-bold block mb-0.5">{label}</span>
        <span className="text-[11.5px] text-white/90 font-medium truncate block leading-tight">{value || '—'}</span>
      </div>
    </div>
  );
}

function classify(highlight, isRejected) {
  if (isRejected) {
    return {
      label: 'Rejected',
      sublabel: 'REJECTED / STANDALONE',
      color: '#EF4444',
      badge: 'bg-rose-500/15 text-rose-400 border-rose-500/30',
    };
  }
  if (highlight.isShared) {
    return {
      label: 'Combined',
      sublabel: highlight.tripCode ? 'COMBINED / DISPATCHED' : 'COMBINED / PLANNED',
      color: '#00F0FF',
      badge: 'bg-[#00F0FF]/15 text-[#00F0FF] border-[#00F0FF]/30 shadow-[0_0_10px_rgba(0,240,255,0.15)]',
    };
  }
  return {
    label: 'Individual',
    sublabel: highlight.tripCode ? 'INDIVIDUAL / DISPATCHED' : 'INDIVIDUAL / PLANNED',
    color: '#38BDF8',
    badge: 'bg-sky-500/15 text-sky-400 border-sky-500/30',
  };
}

export default function XaiDecisionPanel({ highlight }) {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('requests');
  const scrollRef = useRef(null);

  // Reset scroll to top when a different decision or batch is selected
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  }, [highlight?.requestId]);

  if (!highlight) {
    return (
      <div className="glass-panel rounded-2xl p-6 backdrop-blur-xl border border-white/10 shadow-[0_12px_32px_rgba(0,0,0,0.4)] w-full h-full flex flex-col items-center justify-center text-center">
        <div className="h-12 w-12 rounded-2xl bg-[#00F0FF]/10 border border-[#00F0FF]/25 flex items-center justify-center mb-3">
          <BrainCircuit className="h-6 w-6 text-[#00F0FF]" />
        </div>
        <p className="text-[14px] font-bold text-white tracking-wide">No Decision Selected</p>
        <p className="text-[11.5px] text-white/45 mt-1.5 leading-relaxed max-w-[240px]">
          Select an item from the Requests & Decisions list to view detailed factor attribution and operational routes.
        </p>
      </div>
    );
  }

  const meta = requestTypeMeta(highlight.requestType);
  const state = decisionStateMeta(highlight.status, highlight.decision);
  const isRejected =
    state.tone === 'danger' ||
    String(highlight.status || '').toLowerCase() === 'incompatible' ||
    String(highlight.status || '').toLowerCase() === 'rejected' ||
    ((highlight.explanation?.batched_with_request_ids || []).length > 0 && !highlight.isShared);
  const route = buildOperationalRoute(highlight);
  const sequence = describeSequenceNumbered(route.stops);
  const classification = classify(highlight, isRejected);
  const f = highlight.factors || {};
  const related = (highlight.requestPoints || []).filter((p) => p.relation !== 'self');

  const handleViewOnMap = () => navigate(`/live-map?xai=${highlight.requestId}`);

  const hasProfitCompare = Number.isFinite(highlight.driverProfitInr) && Number.isFinite(highlight.soloProfitInr);
  const profitChartData = hasProfitCompare
    ? [
      { name: 'Solo', value: highlight.soloProfitInr },
      { name: 'Combined', value: highlight.driverProfitInr },
    ]
    : [];
  const profitPct = hasProfitCompare && highlight.soloProfitInr > 0
    ? ((highlight.driverProfitInr - highlight.soloProfitInr) / highlight.soloProfitInr) * 100
    : 0;

  // Factor score visual list
  const factorRows = [
    { label: 'Pickup Proximity', value: f.pickup_distance_score, color: '#38BDF8' },
    { label: 'Route Similarity', value: f.destination_similarity, color: '#A855F7' },
    { label: 'Time-window Overlap', value: f.estimated_delay_score, color: '#00F0FF' },
    { label: 'Vehicle Capacity', value: f.vehicle_capacity_score, color: '#F59E0B' },
    { label: 'Request Priority', value: f.priority_score, color: '#EC4899' },
  ];

  // Distinct step colors for XAI numbered reasons
  const stepColors = [
    { bg: 'rgba(56, 189, 248, 0.15)', border: 'rgba(56, 189, 248, 0.35)', text: '#38BDF8' },
    { bg: 'rgba(168, 85, 247, 0.15)', border: 'rgba(168, 85, 247, 0.35)', text: '#A855F7' },
    { bg: 'rgba(0, 240, 255, 0.15)', border: 'rgba(0, 240, 255, 0.35)', text: '#00F0FF' },
    { bg: 'rgba(245, 158, 11, 0.15)', border: 'rgba(245, 158, 11, 0.35)', text: '#F59E0B' },
    { bg: 'rgba(34, 197, 94, 0.15)', border: 'rgba(34, 197, 94, 0.35)', text: '#22C55E' },
  ];

  return (
    <div className="glass-panel rounded-2xl p-3.5 sm:p-4 backdrop-blur-xl border border-white/10 shadow-[0_12px_32px_rgba(0,0,0,0.4)] w-full flex flex-col overflow-hidden h-[540px] sm:h-[600px] xl:h-full">
      
      {/* 1. PINNED DECISION HEADER (Stays visible at the top of the right workspace) */}
      <div className="shrink-0 flex items-center justify-between gap-3 pb-3 border-b border-white/10 flex-wrap">
        <div className="flex items-center gap-2.5 min-w-0">
          <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] font-bold border shrink-0 uppercase tracking-wide ${meta.chipClass}`}>
            <meta.Icon className="h-3.5 w-3.5" /> {meta.label}
          </span>
          <div className="min-w-0">
            <span className="text-white font-mono text-[14px] font-extrabold tracking-tight truncate block">
              #{highlight.requestId}
            </span>
            <span className="text-[9.5px] uppercase tracking-wider font-extrabold block" style={{ color: classification.color }}>
              {highlight.isShared ? 'BATCHED ROUTE' : isRejected ? 'REJECTED PAIRING' : 'SEPARATE ROUTE'}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0 ml-auto">
          <span className={`px-2.5 py-0.5 rounded-full text-[9px] font-extrabold uppercase tracking-wide border ${classification.badge}`}>
            {classification.sublabel}
          </span>
          <button
            type="button"
            onClick={handleViewOnMap}
            className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10px] font-bold border border-[#00F0FF]/30 bg-[#00F0FF]/10 text-[#00F0FF] hover:bg-[#00F0FF]/20 transition-all hover:border-[#00F0FF]/50 shadow-sm"
            title="Open route on Live Map"
          >
            <MapIcon className="h-3 w-3" />
            <span>Map</span>
          </button>
        </div>
      </div>

      {/* 2. INDEPENDENT INTERNAL SCROLL AREA FOR COMPLETE SELECTED BATCH DETAILS */}
      <div ref={scrollRef} className="flex-1 min-h-0 overflow-y-auto custom-scrollbar pr-1 pt-3 space-y-3">
        
        {/* 1. A-DMFE DECISION & KEY METRICS (Score Gauge & Confidence) */}
        <div className="rounded-2xl border border-white/10 bg-gradient-to-br from-[#00F0FF]/[0.05] via-white/[0.02] to-transparent p-3.5 relative overflow-hidden shadow-inner space-y-3">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 mb-1.5">
                <span className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider font-extrabold text-[#00F0FF]">
                  <BrainCircuit className="h-3.5 w-3.5" /> A-DMFE Decision
                </span>
                <span
                  className="px-2 py-0.5 rounded text-[8.5px] font-black uppercase tracking-wider border"
                  style={{
                    backgroundColor: `${state.color}18`,
                    borderColor: `${state.color}44`,
                    color: state.color,
                  }}
                >
                  {isRejected ? 'REJECTED' : highlight.isShared ? 'COMBINED' : 'INDIVIDUAL'}
                </span>
              </div>
              <p className="text-[12.5px] font-bold leading-snug tracking-tight" style={{ color: state.color }}>
                {highlight.decision || 'No decision recorded'}
              </p>
              {highlight.reason && (
                <p className="text-[11px] text-white/70 mt-1 leading-relaxed line-clamp-3">
                  {highlight.reason}
                </p>
              )}
            </div>
            
            {/* Circular Compatibility Score Gauge */}
            <div className="shrink-0 flex flex-col items-center">
              <ScoreGauge score={highlight.score} />
              <span className="text-[8.5px] text-white/50 font-bold uppercase tracking-wider mt-1 text-center">
                Compatibility Score
              </span>
            </div>
          </div>

          {/* Key Metrics: Model Confidence with (estimated) Distinction */}
          <div className="pt-2.5 border-t border-white/10 flex items-center justify-between text-[10.5px]">
            <span className="text-white/45 uppercase tracking-wider font-bold text-[9px]">Model Confidence</span>
            <div className="flex items-center gap-1.5 font-mono font-bold text-white/90">
              <span>{fmt(highlight.confidence, 1, '%')}</span>
              {highlight.confidenceFallback && (
                <span className="px-1.5 py-0.5 rounded text-[8.5px] bg-amber-500/15 border border-amber-500/30 text-amber-400 font-sans font-semibold">
                  (estimated)
                </span>
              )}
            </div>
          </div>
        </div>

        {/* 2. WHY THIS DECISION / AI EXPLANATION (XAI) */}
        <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-3.5 space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase tracking-wider font-bold text-white/70 flex items-center gap-1.5">
              <BrainCircuit className="h-3.5 w-3.5 text-[#38BDF8]" /> Why this decision? (XAI)
            </span>
            <span className="text-[9px] px-2 py-0.5 rounded bg-white/5 text-white/60 border border-white/10 font-bold uppercase tracking-wider">
              Reasoning
            </span>
          </div>

          {(highlight.keyReasons || []).length > 0 ? (
            <div className="space-y-2">
              {highlight.keyReasons.map((r, i) => {
                const s = stepColors[i % stepColors.length];
                return (
                  <div
                    key={i}
                    className="flex items-start gap-2.5 p-2.5 rounded-xl bg-white/[0.02] border border-white/5 hover:bg-white/[0.04] transition-colors"
                  >
                    <div
                      className="h-5 w-5 rounded-full flex items-center justify-center shrink-0 text-[10px] font-mono font-bold mt-0.5 border"
                      style={{
                        background: isRejected ? 'rgba(239, 68, 68, 0.15)' : s.bg,
                        borderColor: isRejected ? 'rgba(239, 68, 68, 0.35)' : s.border,
                        color: isRejected ? '#EF4444' : s.text,
                      }}
                    >
                      {i + 1}
                    </div>
                    <span className="text-[11px] text-white/80 leading-relaxed font-normal flex-1">
                      {r}
                    </span>
                  </div>
                );
              })}
            </div>
          ) : highlight.reason ? (
            <div className="flex items-start gap-2.5 p-2.5 rounded-xl bg-white/[0.02] border border-white/5">
              <div className="h-5 w-5 rounded-full flex items-center justify-center shrink-0 text-[10px] font-mono font-bold mt-0.5 bg-[#00F0FF]/15 border border-[#00F0FF]/35 text-[#00F0FF]">
                1
              </div>
              <span className="text-[11px] text-white/80 leading-relaxed font-normal flex-1">
                {highlight.reason}
              </span>
            </div>
          ) : (
            <p className="text-[11px] text-white/35 italic bg-white/[0.02] p-2.5 rounded-xl border border-white/5">
              No detailed rationale points recorded for this decision.
            </p>
          )}
        </div>

        {/* 3. COMPATIBILITY FACTORS (5 vibrant visual bars) */}
        <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-3.5 space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase tracking-wider font-bold text-white/70 flex items-center gap-1.5">
              <Layers className="h-3.5 w-3.5 text-[#00F0FF]" /> Compatibility Factors
            </span>
            <span className="text-[9px] text-white/40 uppercase font-mono">0.00 – 1.00</span>
          </div>

          {highlight.factors ? (
            <div className="space-y-2.5">
              {factorRows.map(({ label, value, color }) => {
                const has = Number.isFinite(value);
                const pct = has ? Math.min(100, Math.max(0, value)) : 0;
                const decimalStr = has ? (value > 1 ? (value / 100).toFixed(2) : value.toFixed(2)) : '—';
                return (
                  <div key={label} className="group">
                    <div className="flex items-center justify-between text-[11px] mb-1">
                      <span className="text-white/80 font-medium flex items-center gap-1.5">
                        <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: color }} />
                        {label}
                      </span>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] text-white/40 font-mono">
                          {has ? `${Math.round(pct)}%` : ''}
                        </span>
                        <span className="text-white font-mono font-bold text-[11px] tabular-nums">
                          {decimalStr}
                        </span>
                      </div>
                    </div>
                    <div className="h-2 rounded-full bg-white/[0.06] overflow-hidden p-0.5 border border-white/5">
                      {has && (
                        <div
                          className="h-full rounded-full transition-all duration-500 ease-out"
                          style={{
                            width: `${pct}%`,
                            backgroundColor: color,
                            boxShadow: `0 0 8px ${color}66`,
                          }}
                        />
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-[11px] text-white/40 italic py-1">No compatibility factors recorded for this item.</p>
          )}
        </div>


        {/* 5. ADDITIONAL DETAILS TABS (Requests, Route Sequence, Savings) */}
        <div className="rounded-2xl border border-white/10 bg-white/[0.02] overflow-hidden">
          {/* Tab Navigation */}
          <div className="flex items-center border-b border-white/10 bg-white/[0.02] p-1 gap-1">
            {[
              { id: 'requests', label: 'Requests', icon: Users },
              { id: 'route', label: 'Route Sequence', icon: Navigation },
              { id: 'savings', label: 'Savings & Impact', icon: DollarSign },
            ].map(t => {
              const Icon = t.icon;
              const isActive = activeTab === t.id;
              return (
                <button
                  key={t.id}
                  onClick={() => setActiveTab(t.id)}
                  className={`flex-1 flex items-center justify-center gap-1.5 py-2 px-2 rounded-xl text-[10.5px] font-bold transition-all ${
                    isActive
                      ? 'bg-[#00F0FF]/15 text-[#00F0FF] border border-[#00F0FF]/30 shadow-sm'
                      : 'text-white/45 hover:text-white/75 hover:bg-white/5 border border-transparent'
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  <span>{t.label}</span>
                </button>
              );
            })}
          </div>

          <div className="p-3.5">
            {/* TAB: Requests */}
            {activeTab === 'requests' && (
              <div className="space-y-3">
                {/* Driver / Vehicle info if dispatched */}
                {(highlight.driver || highlight.vehicle) && (
                  <div className="grid grid-cols-2 gap-2 bg-white/[0.03] border border-white/5 rounded-xl p-2.5 text-[10.5px]">
                    {highlight.driver && (
                      <div className="flex items-center gap-2 min-w-0">
                        <div className="h-7 w-7 rounded-lg bg-[#38BDF8]/15 border border-[#38BDF8]/30 flex items-center justify-center shrink-0">
                          <User className="h-3.5 w-3.5 text-[#38BDF8]" />
                        </div>
                        <div className="min-w-0">
                          <span className="text-[8.5px] uppercase tracking-wider text-white/40 font-bold block">Assigned Driver</span>
                          <span className="text-white/90 font-medium truncate block">{highlight.driver.name}</span>
                        </div>
                      </div>
                    )}
                    {highlight.vehicle && (
                      <div className="flex items-center gap-2 min-w-0">
                        <div className="h-7 w-7 rounded-lg bg-[#A855F7]/15 border border-[#A855F7]/30 flex items-center justify-center shrink-0">
                          <Truck className="h-3.5 w-3.5 text-[#A855F7]" />
                        </div>
                        <div className="min-w-0">
                          <span className="text-[8.5px] uppercase tracking-wider text-white/40 font-bold block">Vehicle</span>
                          <span className="text-white/90 font-medium truncate block">
                            {highlight.vehicle.name} {highlight.vehicle.type ? `(${highlight.vehicle.type})` : ''}
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Primary Request Pickup & Drop */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-[10px]">
                    <span className="text-white/50 uppercase font-bold tracking-wider">Primary Request</span>
                    <span className="font-mono text-white/70 font-bold">#{highlight.requestId}</span>
                  </div>
                  <AddressRow Icon={MapPin} tone="#22C55E" label="Pickup Location" value={highlight.pickupAddress} />
                  <AddressRow Icon={Flag} tone="#EF4444" label="Drop Location" value={highlight.dropAddress} />
                </div>

                {/* Combined Trip Partners (if shared) */}
                {highlight.isShared && related.length > 0 && (
                  <div className="rounded-xl border border-[#00F0FF]/25 bg-[#00F0FF]/[0.04] p-3 space-y-2.5">
                    <div className="flex items-center justify-between">
                      <span className="flex items-center gap-1.5 text-[9.5px] uppercase tracking-wider text-[#00F0FF] font-bold">
                        <Users className="h-3 w-3" /> Shared Trip Members ({1 + related.length} Requests)
                      </span>
                    </div>

                    <div className="space-y-2">
                      {related.map((p) => {
                        const pMeta = requestTypeMeta(p.request_type);
                        return (
                          <div key={p.id} className="p-2 rounded-lg bg-black/20 border border-white/5 space-y-1">
                            <div className="flex items-center justify-between">
                              <span className="inline-flex items-center gap-1 text-[10px] font-bold text-white font-mono">
                                <pMeta.Icon className="h-3 w-3 shrink-0" style={{ color: pMeta.color }} />
                                #{p.id}
                              </span>
                              <span className="text-[8.5px] uppercase px-1.5 py-0.5 rounded bg-white/5 text-white/50 border border-white/10 font-bold">
                                {p.relation === 'partner' ? 'Batched Partner' : 'Trip Member'}
                              </span>
                            </div>
                            <div className="text-[10px] text-white/60 space-y-0.5">
                              <p className="truncate flex items-center gap-1.5">
                                <span className="h-1.5 w-1.5 rounded-full bg-[#22C55E]" />
                                {p.pickup_address || '—'}
                              </p>
                              <p className="truncate flex items-center gap-1.5">
                                <span className="h-1.5 w-1.5 rounded-full bg-[#EF4444]" />
                                {p.drop_address || '—'}
                              </p>
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    {highlight.decisionSummary && (
                      <div className="pt-2 border-t border-white/10">
                        <span className="block text-[8.5px] uppercase tracking-wider text-white/40 font-bold mb-0.5">Summary</span>
                        <p className="text-[10.5px] text-white/70 leading-relaxed">{highlight.decisionSummary}</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* TAB: Route Sequence */}
            {activeTab === 'route' && (
              <div>
                {isRejected ? (
                  <div className="flex items-center gap-2 p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-[#EF4444] text-[11px]">
                    <X className="h-4 w-4 shrink-0" />
                    <span>Rejected pairing — no route stops were scheduled.</span>
                  </div>
                ) : sequence.length > 0 ? (
                  <div className="space-y-2">
                    <ol className="space-y-1.5">
                      {sequence.map((line, idx) => (
                        <li
                          key={idx}
                          className="flex items-start gap-2 text-[11px] text-white/85 font-mono leading-relaxed bg-white/[0.02] p-2 rounded-lg border border-white/5"
                        >
                          <span className="h-4 w-4 rounded-full bg-white/10 flex items-center justify-center shrink-0 text-[9px] font-bold text-white/60">
                            {idx + 1}
                          </span>
                          <span className="flex-1">{line}</span>
                        </li>
                      ))}
                    </ol>
                    {route.isPlanned && (
                      <p className="text-[10px] text-amber-400 mt-2 flex items-center gap-1.5 bg-amber-500/10 border border-amber-500/20 p-2 rounded-lg">
                        <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                        Planned leg — driver has not yet started this leg.
                      </p>
                    )}
                  </div>
                ) : (
                  <p className="text-[11px] text-white/40 italic py-2 text-center">No route sequence available for this decision.</p>
                )}
              </div>
            )}

            {/* TAB: Savings & Economics */}
            {activeTab === 'savings' && (
              <div>
                {highlight.tripCode ? (
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-2">
                      <div className="rounded-xl border border-white/10 bg-white/[0.02] p-2.5">
                        <span className="block text-[8.5px] uppercase tracking-wider text-white/40 font-bold mb-1">Trip Cost</span>
                        <span className="text-[15px] font-extrabold text-white font-mono tabular-nums">{fmtInr(highlight.tripCostInr)}</span>
                      </div>
                      <div className="rounded-xl border border-white/10 bg-white/[0.02] p-2.5">
                        <span className="block text-[8.5px] uppercase tracking-wider text-white/40 font-bold mb-1">Separate Cost</span>
                        <span className="text-[15px] font-extrabold text-white font-mono tabular-nums">{fmtInr(highlight.separateCostInr)}</span>
                      </div>
                    </div>

                    {highlight.isShared && Number.isFinite(highlight.tripCostInr) && Number.isFinite(highlight.separateCostInr) && (
                      <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                        <div className="flex items-center justify-between text-[11px] font-bold text-emerald-400 mb-1">
                          <span>Combining Savings</span>
                          <span>{fmtInr(highlight.separateCostInr - highlight.tripCostInr)}</span>
                        </div>
                        <div className="text-[10px] text-emerald-300/70 flex flex-wrap gap-x-2 gap-y-0.5">
                          {Number.isFinite(highlight.distanceSavedKm) && highlight.distanceSavedKm > 0 && (
                            <span>{fmt(highlight.distanceSavedKm, 1, ' km')} dist</span>
                          )}
                          {Number.isFinite(highlight.fuelSavedL) && highlight.fuelSavedL > 0 && (
                            <span>{fmt(highlight.fuelSavedL, 2, ' L')} fuel</span>
                          )}
                          {Number.isFinite(highlight.co2SavedKg) && highlight.co2SavedKg > 0 && (
                            <span>{fmt(highlight.co2SavedKg, 2, ' kg')} CO₂</span>
                          )}
                        </div>
                      </div>
                    )}

                    <div className="flex items-center justify-between p-2 rounded-lg bg-white/[0.02] border border-white/5 text-[11px]">
                      <span className="text-white/45">Driver Profit (Dispatched)</span>
                      <span className="text-white/90 font-mono font-bold tabular-nums">{fmtInr(highlight.driverProfitInr)}</span>
                    </div>

                    {hasProfitCompare && (
                      <div className="pt-2 border-t border-white/10">
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="text-[8.5px] uppercase tracking-wider text-white/40 font-bold">Driver Profit: Solo vs Combined</span>
                          <span className={`text-[10.5px] font-bold font-mono ${
                            profitPct > 0 ? 'text-[#22C55E]' : profitPct < 0 ? 'text-[#F59E0B]' : 'text-white/50'
                          }`}>
                            {profitPct > 0 ? '+' : ''}{profitPct.toFixed(1)}%
                          </span>
                        </div>
                        <div className="h-[90px] -ml-2">
                          <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={profitChartData} margin={{ top: 14, right: 8, left: 0, bottom: 0 }}>
                              <XAxis
                                dataKey="name"
                                tick={{ fill: 'rgba(255,255,255,0.45)', fontSize: 9.5 }}
                                axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
                                tickLine={false}
                              />
                              <YAxis hide domain={[0, (max) => max * 1.25]} />
                              <Tooltip
                                cursor={{ fill: 'rgba(255,255,255,0.04)' }}
                                contentStyle={{ background: '#0A0F1A', border: '1px solid rgba(255,255,255,0.15)', borderRadius: 8, fontSize: 10 }}
                                labelStyle={{ color: 'rgba(255,255,255,0.6)' }}
                                itemStyle={{ color: '#fff' }}
                                formatter={(value) => [fmtInr(value), 'Profit']}
                              />
                              <Bar dataKey="value" radius={[4, 4, 0, 0]} maxBarSize={48}>
                                {profitChartData.map((entry) => (
                                  <Cell key={entry.name} fill={entry.name === 'Combined' ? '#00F0FF' : '#94A3B8'} />
                                ))}
                                <LabelList
                                  dataKey="value"
                                  position="top"
                                  formatter={fmtInr}
                                  style={{ fill: 'rgba(255,255,255,0.75)', fontSize: 9.5, fontWeight: 600 }}
                                />
                              </Bar>
                            </BarChart>
                          </ResponsiveContainer>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-[11px] text-white/40 italic py-2 text-center">Economics not available for this decision.</p>
                )}
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
