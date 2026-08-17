import React, { useState, useEffect, useMemo, useContext, useCallback } from 'react';
import { motion, useReducedMotion } from 'framer-motion';
import { Calendar, Maximize2, Minimize2 } from 'lucide-react';

import api from '../services/api';
import { AuthContext } from '../context/AuthContext';
import LiveMapContainer from '../components/map/LiveMapContainer';
import ActivityTimeline from '../components/notifications/ActivityTimeline';
import DashboardKpis from '../components/dashboard/DashboardKpis';
import AIEngineStatus from '../components/dashboard/AIEngineStatus';
import DashboardSummary from '../components/dashboard/DashboardSummary';
import {
  RequestsByType, PerformanceOverview, OptimizationImpact, TYPE_COLORS,
} from '../components/dashboard/DashboardCharts';

/**
 * A-DMFE Overview — redesigned against the reference operations-console layout.
 *
 * This page is a PRESENTATION LAYER ONLY. It performs no research computation;
 * every value is rendered from an existing backend payload.
 *
 * Endpoints (identical set and cadence to the previous Dashboard.jsx, plus one
 * call to /dmfe/statistics which the AI Engine card needs — the shared axios
 * cache in services/api.js dedupes it against the DMFE page):
 *   GET /api/dashboard/stats
 *   GET /api/simulation/queue?limit=120
 *   GET /api/simulation/advanced-analytics
 *   GET /api/notifications/timeline?limit=8
 *   GET /api/dmfe/statistics
 *
 * One 20s interval, gated on document.visibilityState, exactly as before. No
 * per-component polling was added.
 */

const FILTERS = [
  { key: 'All', type: null, color: null },
  { key: 'Passenger', type: 'ride', color: TYPE_COLORS[0] },
  { key: 'Food', type: 'food', color: TYPE_COLORS[1] },
  { key: 'Parcel', type: 'parcel', color: TYPE_COLORS[2] },
];

function greetingFor(date) {
  const h = date.getHours();
  if (h < 12) return 'Good Morning';
  if (h < 17) return 'Good Afternoon';
  return 'Good Evening';
}

function HeaderClock() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    // Minute resolution is enough for the header; a 1s timer would re-render
    // the whole header 60× more often for no visible benefit.
    const t = setInterval(() => setNow(new Date()), 30000);
    return () => clearInterval(t);
  }, []);
  return (
    <div className="hidden md:flex items-center gap-3 rounded-2xl border border-white/[0.08] bg-white/[0.04] px-4 py-2 backdrop-blur-md">
      <div className="text-right leading-tight">
        <p className="text-[11.5px] text-brand-text-secondary tabular-nums">
          {now.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
        </p>
        <p className="text-[13px] font-semibold text-white tabular-nums">
          {now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
        </p>
      </div>
      <Calendar className="h-4 w-4 text-brand-text-muted" aria-hidden="true" />
    </div>
  );
}

export default function DashboardOverview() {
  const { user } = useContext(AuthContext);
  const reduce = useReducedMotion();

  const [stats, setStats] = useState(null);
  const [dmfeStats, setDmfeStats] = useState(null);
  const [mapRequests, setMapRequests] = useState([]);
  const [charts, setCharts] = useState({});
  const [timeAnalytics, setTimeAnalytics] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [loading, setLoading] = useState(true);

  const [mapFilter, setMapFilter] = useState('All');
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [mapExpanded, setMapExpanded] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const fetchAll = async () => {
      const [statsRes, queueRes, chartsRes, tlRes, dmfeRes] = await Promise.allSettled([
        api.get('/dashboard/stats'),
        api.get('/simulation/queue?limit=120'),
        api.get('/simulation/advanced-analytics'),
        api.get('/notifications/timeline?limit=8'),
        api.get('/dmfe/statistics'),
      ]);
      if (cancelled) return;

      if (statsRes.status === 'fulfilled') setStats(statsRes.value.data);
      if (queueRes.status === 'fulfilled') setMapRequests(queueRes.value.data?.items || []);
      if (chartsRes.status === 'fulfilled') {
        setCharts(chartsRes.value.data?.charts || {});
        setTimeAnalytics(chartsRes.value.data?.time_analytics || null);
      }
      if (tlRes.status === 'fulfilled') setTimeline(tlRes.value.data || []);
      if (dmfeRes.status === 'fulfilled') setDmfeStats(dmfeRes.value.data);
      setLoading(false);
    };

    fetchAll();
    const t = setInterval(() => {
      if (document.visibilityState === 'visible') fetchAll();
    }, 20000);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, []);

  const requestMix = useMemo(() => {
    const count = { ride: 0, food: 0, parcel: 0 };
    mapRequests.forEach((r) => {
      const t = r.request_type?.toLowerCase();
      if (count[t] !== undefined) count[t] += 1;
      else count.ride += 1;
    });
    return [
      { name: 'Passenger', value: count.ride },
      { name: 'Food Delivery', value: count.food },
      { name: 'Parcel Delivery', value: count.parcel },
    ].filter((i) => i.value > 0);
  }, [mapRequests]);

  // Filtering happens on the already-fetched queue — no second dataset, no refetch.
  const visibleRequests = useMemo(() => {
    const f = FILTERS.find((x) => x.key === mapFilter);
    if (!f?.type) return mapRequests;
    return mapRequests.filter((r) => r.request_type?.toLowerCase() === f.type);
  }, [mapRequests, mapFilter]);

  const handleSelect = useCallback((req) => setSelectedRequest(req), []);
  const handleClose = useCallback(() => setSelectedRequest(null), []);

  // Leaflet/Google both need a resize signal after the container box changes.
  useEffect(() => {
    const id = window.setTimeout(() => window.dispatchEvent(new Event('resize')), 320);
    return () => window.clearTimeout(id);
  }, [mapExpanded]);

  const firstName = user?.full_name ? user.full_name.split(' ')[0] : 'Admin';
  const genTrend = charts.request_generation_trend || [];
  const compTrend = charts.completed_requests_trend || [];

  if (loading && !stats) {
    return (
      <div className="flex items-center justify-center h-[70vh]">
        <div className="flex flex-col items-center gap-4">
          <div className="h-12 w-12 rounded-full border-2 border-white/10 border-t-brand-primary animate-spin" />
          <p className="text-[11px] font-medium text-brand-text-muted uppercase tracking-[0.22em]">
            Initializing overview
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative px-1 pb-4">
      <div className="absolute inset-0 pointer-events-none overflow-hidden" aria-hidden="true">
        <div className="absolute -top-[8%] -left-[4%] h-[46%] w-[46%] rounded-full bg-brand-primary/10 blur-[140px]" />
        <div className="absolute bottom-[8%] -right-[8%] h-[38%] w-[38%] rounded-full bg-brand-purple/[0.08] blur-[140px]" />
      </div>

      <motion.div
        initial={reduce ? false : { opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
        className="relative max-w-[1640px] mx-auto space-y-4"
      >
        {/* ── Header ─────────────────────────────────────────────────────── */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div>
            <h1 className="text-[26px] md:text-[28px] font-display font-semibold text-white tracking-tight leading-tight">
              {greetingFor(new Date())}, {firstName} <span aria-hidden="true">👋</span>
            </h1>
            <p className="text-[13px] text-brand-text-secondary mt-0.5">
              AI-Powered Unified Mobility &amp; Delivery Platform
            </p>
          </div>
          <HeaderClock />
        </div>

        {/* ── KPI row ────────────────────────────────────────────────────── */}
        <DashboardKpis stats={stats} genTrend={genTrend} compTrend={compTrend} />

        {/* ── Live operations + right rail ───────────────────────────────── */}
        <div className={`grid gap-4 ${mapExpanded ? 'grid-cols-1' : 'grid-cols-1 xl:grid-cols-3'}`}>
          <div className={mapExpanded ? '' : 'xl:col-span-2'}>
            <div className="navy-glass-card p-4 flex flex-col">
              <div className="flex items-center justify-between mb-3 gap-3">
                <h2 className="text-[15px] font-semibold text-white">Live Operations</h2>
                <div className="flex items-center gap-2">
                  <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-brand-success/10 border border-brand-success/20">
                    <span className="h-1.5 w-1.5 rounded-full bg-brand-success animate-pulse" />
                    <span className="text-[10.5px] text-brand-success font-medium">Live</span>
                  </span>
                  <button
                    type="button"
                    onClick={() => setMapExpanded((v) => !v)}
                    className="btn-icon !h-8 !w-8"
                    aria-label={mapExpanded ? 'Collapse map' : 'Expand map'}
                    title={mapExpanded ? 'Collapse map' : 'Expand map'}
                  >
                    {mapExpanded
                      ? <Minimize2 className="h-3.5 w-3.5" />
                      : <Maximize2 className="h-3.5 w-3.5" />}
                  </button>
                </div>
              </div>

              {/* Filter chips — drive the existing queue filter, no new dataset */}
              <div className="flex flex-wrap gap-2 mb-3" role="group" aria-label="Filter requests by type">
                {FILTERS.map((f) => {
                  const active = mapFilter === f.key;
                  return (
                    <button
                      key={f.key}
                      type="button"
                      onClick={() => setMapFilter(f.key)}
                      aria-pressed={active}
                      className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-[11.5px] font-medium border transition-all duration-300 ${
                        active
                          ? 'bg-white/[0.14] border-white/25 text-white'
                          : 'bg-white/[0.03] border-white/[0.08] text-brand-text-secondary hover:text-white hover:bg-white/[0.07]'
                      }`}
                    >
                      {f.color && (
                        <span className="h-1.5 w-1.5 rounded-full" style={{ background: f.color }} />
                      )}
                      {f.key}
                    </button>
                  );
                })}
                <span className="ml-auto self-center text-[11px] text-brand-text-muted tabular-nums">
                  {visibleRequests.length} shown
                </span>
              </div>

              {/* Height is viewport-relative, never a hardcoded pixel box, so the
                  map recalculates cleanly on resize and expand/collapse. */}
              <div
                className="rounded-2xl overflow-hidden border border-white/[0.07] transition-[height] duration-300"
                style={{ height: mapExpanded ? '68vh' : 'clamp(380px, 46vh, 560px)' }}
              >
                <LiveMapContainer
                  requests={visibleRequests}
                  selectedRequest={selectedRequest}
                  onSelectRequest={handleSelect}
                  onClosePopup={handleClose}
                  className="w-full h-full"
                />
              </div>
            </div>
          </div>

          {!mapExpanded && (
            <div className="flex flex-col gap-4 min-w-0">
              <AIEngineStatus stats={dmfeStats} mode="adaptive" />

              <div className="navy-glass-card p-5 flex flex-col min-h-0">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-[14px] font-semibold text-white">Live Activity</h3>
                  <span className="text-[10.5px] text-brand-text-muted tabular-nums">
                    {timeline.length} events
                  </span>
                </div>
                <div className="max-h-[320px] overflow-y-auto custom-scrollbar -mr-1 pr-1">
                  <ActivityTimeline timeline={timeline} />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ── Charts row ─────────────────────────────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <RequestsByType mix={requestMix} />
          <PerformanceOverview generated={genTrend} completed={compTrend} />
          <OptimizationImpact stats={stats} />
        </div>

        {/* ── Summary strip ──────────────────────────────────────────────── */}
        <DashboardSummary stats={stats} timeAnalytics={timeAnalytics} />
      </motion.div>
    </div>
  );
}
