import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import {
  BrainCircuit, RefreshCw, Search, LayoutGrid, CheckCircle2, XCircle,
  Route as RouteIcon, ChevronDown, X, Combine, Users
} from 'lucide-react';
import api from '../services/api';

import StatusBadge from '../components/ui/StatusBadge';
import DecisionCard from '../components/xai/DecisionCard';
import XaiMapPanel from '../components/xai/XaiMapPanel';
import XaiDecisionPanel from '../components/xai/XaiDecisionPanel';
import { normalizeXaiHighlight } from '../utils/xaiMap';

// ── Decision outcome grouping (Batched / Individual / Rejected) ────────────
// Preserved verbatim from existing logic:
function explanationOutcome(exp) {
  const decision = String(exp?.decision || '').toLowerCase();
  if (decision.includes('compatible for batching')) return 'batched';
  if ((exp?.batched_with_request_ids || []).length > 0) return 'rejected';
  return 'individual';
}

const OUTCOME_TABS = [
  { id: 'all', label: 'All Insights', icon: LayoutGrid },
  { id: 'batched', label: 'Batched / Combined', icon: CheckCircle2 },
  { id: 'individual', label: 'Individual / Separate', icon: RouteIcon },
  { id: 'rejected', label: 'Rejected', icon: XCircle },
];

export default function ExplanationDashboard() {
  const [search, setSearch] = useState('');
  const [explanations, setExplanations] = useState([]);
  const [timestamp, setTimestamp] = useState(null);
  const [selectedExp, setSelectedExp] = useState(null);
  const [loading, setLoading] = useState(true);
  const [mapOpen, setMapOpen] = useState(true);
  const [outcomeTab, setOutcomeTab] = useState('all');
  const [leftOpen, setLeftOpen] = useState(true);

  const pollRef = useRef(null);

  // Card click → select item and open drawer if on mobile
  const handleCardClick = (exp) => {
    setSelectedExp(exp);
    setMapOpen(true);
  };

  // Fetch XAI explanations
  const fetchData = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (search) params.append('search', search);
      params.append('limit', '50');

      const listRes = await api.get(`/xai/explanations?${params.toString()}`);
      const items = listRes.data || [];
      setExplanations(items);
      setTimestamp(new Date().toISOString());

      // Keep selected item updated or pick first
      if (items.length > 0) {
        setSelectedExp((prev) => {
          if (!prev) return items[0];
          const match = items.find((i) => i.request_id === prev.request_id);
          return match || items[0];
        });
      } else {
        setSelectedExp(null);
      }
    } catch (err) {
      console.error('Failed to fetch XAI data:', err);
    } finally {
      setLoading(false);
    }
  }, [search]);

  // Polling: 2.5s
  useEffect(() => {
    fetchData();
    pollRef.current = setInterval(() => { if (document.visibilityState === 'visible') fetchData(); }, 2500);
    return () => clearInterval(pollRef.current);
  }, [fetchData]);

  // Grouped counts
  const explanationsByOutcome = useMemo(() => {
    const groups = { batched: [], individual: [], rejected: [] };
    explanations.forEach((exp) => {
      groups[explanationOutcome(exp)].push(exp);
    });
    return groups;
  }, [explanations]);

  const filteredExplanations = useMemo(
    () => (outcomeTab === 'all' ? explanations : (explanationsByOutcome[outcomeTab] || [])),
    [outcomeTab, explanations, explanationsByOutcome]
  );

  // Auto-sync selection with filtered results if current item is not in the filtered set
  useEffect(() => {
    if (filteredExplanations.length > 0) {
      if (!selectedExp || !filteredExplanations.some((i) => i.request_id === selectedExp.request_id)) {
        setSelectedExp(filteredExplanations[0]);
      }
    } else {
      setSelectedExp(null);
    }
  }, [filteredExplanations, selectedExp]);

  const highlight = useMemo(() => normalizeXaiHighlight(selectedExp), [selectedExp]);

  const totalCount = explanations.length;
  const batchedCount = explanationsByOutcome.batched.length;
  const individualCount = explanationsByOutcome.individual.length;
  const rejectedCount = explanationsByOutcome.rejected.length;

  const batchedPct = totalCount > 0 ? ((batchedCount / totalCount) * 100).toFixed(1) : '0.0';
  const individualPct = totalCount > 0 ? ((individualCount / totalCount) * 100).toFixed(1) : '0.0';
  const rejectedPct = totalCount > 0 ? ((rejectedCount / totalCount) * 100).toFixed(1) : '0.0';

  return (
    <div className="flex flex-col gap-3 max-w-[1780px] mx-auto w-full xl:h-[calc(100vh-140px)] xl:min-h-[580px] xl:max-h-[calc(100vh-140px)] xl:overflow-hidden pb-12 xl:pb-0">
      {/* ── 1. PAGE HEADER & TOP KPI SUMMARY CARDS ── */}
      <div className="flex flex-col gap-2.5 shrink-0">
        {/* Title bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-2xl bg-gradient-to-br from-[#00F0FF]/20 to-[#3B82F6]/20 border border-[#00F0FF]/30 flex items-center justify-center shadow-[0_0_15px_rgba(0,240,255,0.2)]">
              <BrainCircuit className="h-5 w-5 text-[#00F0FF]" />
            </div>
            <div>
              <h1 className="text-xl sm:text-2xl font-display font-bold text-white tracking-tight flex items-center gap-2">
                AI Insights
              </h1>
              <p className="text-xs text-white/50">
                Explainable decisions for every request and batch across the network
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <StatusBadge tone="success" label="Auto-refresh 2.5s" pulse />
            <button
              onClick={fetchData}
              className="btn-glass p-2 text-white/70 hover:text-white"
              title="Refresh decisions"
            >
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* 4 Top KPI Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-2.5">
          {/* Total Decisions */}
          <div className="glass-panel rounded-2xl p-3 sm:p-3.5 border border-white/10 bg-[#071328]/70 flex items-center justify-between hover:bg-[#091834]/80 hover:border-white/20 transition-all shadow-sm">
            <div className="min-w-0">
              <span className="text-[10px] uppercase tracking-wider text-white/45 font-bold block">Total Decisions</span>
              <span className="text-2xl lg:text-3xl font-extrabold font-display text-white tabular-nums tracking-tight mt-0.5 block">
                {totalCount}
              </span>
              <span className="text-[10px] text-white/40 mt-0.5 block truncate">Evaluated by A-DMFE</span>
            </div>
            <div className="h-10 w-10 rounded-xl bg-blue-500/15 border border-blue-500/30 flex items-center justify-center shrink-0 text-blue-400 shadow-[0_0_12px_rgba(59,130,246,0.15)]">
              <Users className="h-5 w-5" />
            </div>
          </div>

          {/* Batched / Combined */}
          <div className="glass-panel rounded-2xl p-3 sm:p-3.5 border border-emerald-500/25 bg-emerald-500/[0.04] flex items-center justify-between hover:bg-emerald-500/[0.08] hover:border-emerald-500/40 transition-all shadow-sm">
            <div className="min-w-0">
              <span className="text-[10px] uppercase tracking-wider text-emerald-400/80 font-bold block">Batched / Combined</span>
              <div className="flex items-baseline gap-2 mt-0.5">
                <span className="text-2xl lg:text-3xl font-extrabold font-display text-white tabular-nums tracking-tight">
                  {batchedCount}
                </span>
                <span className="text-xs font-bold text-emerald-400 tabular-nums">
                  {batchedPct}%
                </span>
              </div>
              <span className="text-[10px] text-emerald-400/60 mt-0.5 block truncate">Shared routing efficiency</span>
            </div>
            <div className="h-10 w-10 rounded-xl bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center shrink-0 text-emerald-400 shadow-[0_0_12px_rgba(16,185,129,0.15)]">
              <Combine className="h-5 w-5" />
            </div>
          </div>

          {/* Individual / Separate */}
          <div className="glass-panel rounded-2xl p-3 sm:p-3.5 border border-sky-500/25 bg-sky-500/[0.04] flex items-center justify-between hover:bg-sky-500/[0.08] hover:border-sky-500/40 transition-all shadow-sm">
            <div className="min-w-0">
              <span className="text-[10px] uppercase tracking-wider text-sky-400/80 font-bold block">Individual / Separate</span>
              <div className="flex items-baseline gap-2 mt-0.5">
                <span className="text-2xl lg:text-3xl font-extrabold font-display text-white tabular-nums tracking-tight">
                  {individualCount}
                </span>
                <span className="text-xs font-bold text-sky-400 tabular-nums">
                  {individualPct}%
                </span>
              </div>
              <span className="text-[10px] text-sky-400/60 mt-0.5 block truncate">Direct standalone transit</span>
            </div>
            <div className="h-10 w-10 rounded-xl bg-sky-500/15 border border-sky-500/30 flex items-center justify-center shrink-0 text-sky-400 shadow-[0_0_12px_rgba(56,189,248,0.15)]">
              <RouteIcon className="h-5 w-5" />
            </div>
          </div>

          {/* Rejected */}
          <div className="glass-panel rounded-2xl p-3 sm:p-3.5 border border-rose-500/25 bg-rose-500/[0.04] flex items-center justify-between hover:bg-rose-500/[0.08] hover:border-rose-500/40 transition-all shadow-sm">
            <div className="min-w-0">
              <span className="text-[10px] uppercase tracking-wider text-rose-400/80 font-bold block">Rejected</span>
              <div className="flex items-baseline gap-2 mt-0.5">
                <span className="text-2xl lg:text-3xl font-extrabold font-display text-white tabular-nums tracking-tight">
                  {rejectedCount}
                </span>
                <span className="text-xs font-bold text-rose-400 tabular-nums">
                  {rejectedPct}%
                </span>
              </div>
              <span className="text-[10px] text-rose-400/60 mt-0.5 block truncate">Below feasibility threshold</span>
            </div>
            <div className="h-10 w-10 rounded-xl bg-rose-500/15 border border-rose-500/30 flex items-center justify-center shrink-0 text-rose-400 shadow-[0_0_12px_rgba(244,63,94,0.15)]">
              <XCircle className="h-5 w-5" />
            </div>
          </div>
        </div>

        {/* ── 2. FILTER TABS & SEARCH BAR ── */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5 glass-panel rounded-2xl p-2 border border-white/10 shadow-sm">
          {/* Outcome Filter Tabs */}
          <div className="flex items-center gap-1.5 overflow-x-auto custom-scrollbar pb-1 sm:pb-0 shrink-0">
            {OUTCOME_TABS.map((tab) => {
              const isActive = outcomeTab === tab.id;
              const count = tab.id === 'all' ? totalCount : (explanationsByOutcome[tab.id]?.length || 0);
              return (
                <button
                  key={tab.id}
                  onClick={() => setOutcomeTab(tab.id)}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold whitespace-nowrap shrink-0 transition-all duration-200 ${
                    isActive
                      ? 'bg-gradient-to-r from-brand-primary/40 to-[#00F0FF]/30 text-white border border-[#00F0FF]/50 shadow-[0_0_16px_rgba(0,240,255,0.2)]'
                      : 'text-white/60 hover:text-white hover:bg-white/[0.05] border border-transparent'
                  }`}
                >
                  <tab.icon className={`h-3.5 w-3.5 shrink-0 ${isActive ? 'text-[#00F0FF]' : 'text-white/40'}`} />
                  <span className="shrink-0">{tab.label}</span>
                  <span className={`px-2 py-0.5 rounded-full text-[10px] font-mono font-bold shrink-0 ${
                    isActive ? 'bg-[#00F0FF]/25 text-[#00F0FF]' : 'bg-white/10 text-white/50'
                  }`}>
                    {count}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Search Input */}
          <div className="relative w-full sm:w-72 md:w-80 shrink-0">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-white/40 pointer-events-none" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by Request ID, Batch ID, reason…"
              className="w-full pl-10 pr-8 py-2 bg-[#081225]/90 border border-white/10 rounded-xl text-xs text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-[#00F0FF]/40 focus:border-[#00F0FF]/60 transition-all"
            />
            {search && (
              <button
                onClick={() => setSearch('')}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-white/40 hover:text-white"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* ── 3. MAIN 3-COLUMN WORKSPACE (Desktop: 3 cols, Mobile: Stack in order) ── */}
      {loading && !timestamp ? (
        <div className="flex flex-col xl:flex-row gap-4 items-stretch flex-1 min-h-[600px]">
          <div className="w-full xl:w-[24%] flex flex-col gap-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-24 bg-white/[0.03] border border-white/5 rounded-2xl animate-pulse" />
            ))}
          </div>
          <div className="flex-1 rounded-[24px] bg-white/[0.02] border border-white/5 animate-pulse min-h-[400px]" />
          <div className="w-full xl:w-[28%] bg-white/[0.03] border border-white/5 rounded-2xl animate-pulse min-h-[400px]" />
        </div>
      ) : (
        <div className="flex flex-col xl:flex-row gap-3.5 items-stretch flex-1 min-h-0 xl:h-full xl:overflow-hidden">
          {/* ── 1. LEFT COLUMN: Requests & Decisions List (~24%) ── */}
          <div className="w-full xl:w-[24%] xl:min-w-[290px] xl:max-w-[340px] shrink-0 flex flex-col gap-2 xl:h-full xl:min-h-0 xl:overflow-hidden">
            {/* Mobile collapsible toggle header */}
            <button
              onClick={() => setLeftOpen((o) => !o)}
              className="xl:hidden w-full flex items-center justify-between glass-panel rounded-2xl px-4 py-3 text-xs font-bold text-white shadow-sm border border-white/10"
            >
              <span className="flex items-center gap-2">
                <BrainCircuit className="h-4 w-4 text-[#00F0FF]" /> Requests &amp; Decisions
                <span className="text-[#00F0FF] font-mono text-[11px] font-bold">({filteredExplanations.length})</span>
              </span>
              <ChevronDown className={`h-4 w-4 transition-transform text-white/60 ${leftOpen ? 'rotate-180' : ''}`} />
            </button>

            <div className={`${leftOpen ? 'flex' : 'hidden'} xl:flex flex-col gap-2 min-h-0 xl:flex-1`}>
              {/* Header label for list */}
              <div className="hidden xl:flex items-center justify-between px-2 text-xs text-white/50 font-bold uppercase tracking-wider">
                <span className="flex items-center gap-1.5">
                  <span>Requests &amp; Decisions</span>
                  <span className="px-2 py-0.5 rounded-full bg-white/10 text-white/80 font-mono text-[10.5px]">
                    {filteredExplanations.length}
                  </span>
                </span>
                <span className="text-[10px] text-white/40 font-semibold lowercase">latest first</span>
              </div>

              {/* Decision list */}
              {filteredExplanations.length === 0 ? (
                <div className="glass-panel border border-white/10 rounded-2xl p-8 text-center flex flex-col items-center justify-center h-full">
                  <BrainCircuit className="h-8 w-8 text-[#00F0FF]/30 mb-3" />
                  <p className="text-sm font-bold text-white/80">No decisions to display</p>
                  <p className="text-xs text-white/40 mt-1 mb-4 text-center">
                    No {OUTCOME_TABS.find((t) => t.id === outcomeTab)?.label.toLowerCase()} decisions match your filters.
                  </p>
                  <button onClick={() => { setSearch(''); setOutcomeTab('all'); fetchData(); }} className="btn-glass text-xs">
                    <RefreshCw className="h-3.5 w-3.5" /> Reset Filters
                  </button>
                </div>
              ) : (
                <div className="space-y-2.5 overflow-y-auto pr-1 custom-scrollbar flex-1 min-h-0 max-h-[380px] xl:max-h-none pb-2">
                  {filteredExplanations.map((exp) => (
                    <DecisionCard
                      key={exp.id || exp.request_id}
                      explanation={exp}
                      isSelected={selectedExp?.request_id === exp.request_id}
                      onSelect={() => handleCardClick(exp)}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* ── 2. CENTER COLUMN: Live Route Map & Batch Overview (~48%) ── */}
          <div className="flex-1 min-w-0 xl:h-full relative flex flex-col min-h-0">
            <XaiMapPanel
              explanation={selectedExp}
              open={mapOpen}
            />
          </div>

          {/* ── 3. RIGHT COLUMN: Selected A-DMFE Decision & Explanation (~28%) ── */}
          <div className="w-full xl:w-[28%] xl:min-w-[330px] xl:max-w-[400px] xl:shrink-0 xl:h-full flex flex-col min-h-0">
            <XaiDecisionPanel highlight={highlight} />
          </div>
        </div>
      )}
    </div>
  );
}

