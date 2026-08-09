import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Play, Pause, Square, RotateCcw, Radio, Search, X } from 'lucide-react';
import { motion } from 'framer-motion';
import api from '../services/api';
import toast from 'react-hot-toast';

import LiveMapContainer from '../components/map/LiveMapContainer';
import StatisticsPanel from '../components/map/StatisticsPanel';
import PageHeader from '../components/ui/PageHeader';

export default function LiveSimulationMap() {
  // ── State ──────────────────────────────────────────────────────────────────
  const [queue, setQueue] = useState([]);
  const [status, setStatus] = useState({
    running: false,
    paused: false,
    status_text: 'Stopped',
    total_generated: 0,
    queue_size: 0,
  });

  const [selectedRequest, setSelectedRequest] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [loading, setLoading] = useState(false);

  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('All');
  const [filterProvider, setFilterProvider] = useState('All');
  const [filterPriority, setFilterPriority] = useState('All');

  const pollRef = useRef(null);

  // ── Data Fetching ──────────────────────────────────────────────────────────
  const fetchLiveData = useCallback(async () => {
    try {
      const [statusRes, queueRes] = await Promise.all([
        api.get('/simulation/status'),
        api.get('/simulation/queue?limit=200'),
      ]);
      setStatus(statusRes.data);
      setQueue(queueRes.data.items || []);
      setLastUpdated(new Date());
    } catch {
      // Silently ignore poll errors
    }
  }, []);

  useEffect(() => {
    fetchLiveData();
    pollRef.current = setInterval(() => { if (document.visibilityState === 'visible') fetchLiveData(); }, 2500);
    return () => clearInterval(pollRef.current);
  }, [fetchLiveData]);

  // ── Controls Handlers ──────────────────────────────────────────────────────
  const handleStartResume = async () => {
    setLoading(true);
    try {
      const endpoint = status.paused ? '/simulation/resume' : '/simulation/start';
      const res = await api.post(endpoint);
      setStatus(res.data);
      toast.success(status.paused ? 'Simulation Resumed' : 'Simulation Started');
      fetchLiveData();
    } catch {
      toast.error('Failed to start simulation');
    } finally { setLoading(false); }
  };

  const handlePause = async () => {
    setLoading(true);
    try {
      const res = await api.post('/simulation/pause');
      setStatus(res.data);
      toast.success('Simulation Paused');
      fetchLiveData();
    } catch {
      toast.error('Failed to pause simulation');
    } finally { setLoading(false); }
  };

  const handleStop = async () => {
    setLoading(true);
    try {
      const res = await api.post('/simulation/stop');
      setStatus(res.data);
      toast.success('Simulation Stopped');
      fetchLiveData();
    } catch {
      toast.error('Failed to stop simulation');
    } finally { setLoading(false); }
  };

  const handleClear = async () => {
    if (!confirm('Clear all pending requests from the queue?')) return;
    setLoading(true);
    try {
      const res = await api.post('/simulation/clear-queue');
      setStatus(res.data);
      setQueue([]);
      setSelectedRequest(null);
      toast.success('Queue Cleared');
      fetchLiveData();
    } catch {
      toast.error('Failed to clear queue');
    } finally { setLoading(false); }
  };

  // ── Provider Options for Filter Dropdown ───────────────────────────────────
  const providerOptions = useMemo(() => {
    const set = new Set();
    queue.forEach(i => i.provider_name && set.add(i.provider_name));
    return Array.from(set);
  }, [queue]);

  // ── Filtered Requests Computation ──────────────────────────────────────────
  const filteredRequests = useMemo(() => {
    return queue.filter(item => {
      const searchLower = searchTerm.toLowerCase();
      const matchesSearch = !searchTerm || (
        String(item.id).includes(searchLower) ||
        (item.provider_name && item.provider_name.toLowerCase().includes(searchLower)) ||
        (item.pickup_address && item.pickup_address.toLowerCase().includes(searchLower)) ||
        (item.drop_address && item.drop_address.toLowerCase().includes(searchLower))
      );

      const matchesType = filterType === 'All' || item.request_type?.toLowerCase() === filterType.toLowerCase();
      const matchesProvider = filterProvider === 'All' || item.provider_name === filterProvider;
      const matchesPriority = filterPriority === 'All' || item.priority === filterPriority;

      return matchesSearch && matchesType && matchesProvider && matchesPriority;
    });
  }, [queue, searchTerm, filterType, filterProvider, filterPriority]);

  // ── Computed Statistics for Overlaid Panel ─────────────────────────────────
  const stats = useMemo(() => {
    let ride = 0, food = 0, parcel = 0;
    filteredRequests.forEach(r => {
      const t = r.request_type?.toLowerCase();
      if (t === 'ride') ride++;
      else if (t === 'food') food++;
      else if (t === 'parcel') parcel++;
    });
    return { active: filteredRequests.length, ride, food, parcel };
  }, [filteredRequests]);

  const handleResetFilters = () => {
    setSearchTerm('');
    setFilterType('All');
    setFilterProvider('All');
    setFilterPriority('All');
  };

  const hasFilters = searchTerm || filterType !== 'All' || filterProvider !== 'All' || filterPriority !== 'All';
  const engineActive = status.running && !status.paused;

  return (
    <div className="space-y-6 max-w-[1500px] mx-auto">
      <PageHeader
        eyebrow="Live Operations"
        live
        title="Coimbatore Live Network"
        description="Real-time request telemetry across the city — pickup markers, queue composition and engine state."
        actions={
          <div className="flex items-center gap-2.5">
            <div className="chip">
              <span className="relative flex h-1.5 w-1.5">
                <span className={`absolute inline-flex h-full w-full rounded-full animate-ping ${engineActive ? 'bg-brand-success' : 'bg-brand-text-muted'}`} />
                <span className={`relative inline-flex rounded-full h-1.5 w-1.5 ${engineActive ? 'bg-brand-success' : 'bg-brand-text-muted'}`} />
              </span>
              {engineActive ? 'Engine running' : status.paused ? 'Paused' : 'Stopped'}
            </div>

            {engineActive ? (
              <button onClick={handlePause} disabled={loading} className="btn-glass !text-brand-warning">
                <Pause className="h-4 w-4" /> Pause
              </button>
            ) : (
              <button onClick={handleStartResume} disabled={loading} className="btn-primary">
                <Play className="h-4 w-4" /> {status.paused ? 'Resume' : 'Start Engine'}
              </button>
            )}

            <button
              onClick={handleStop}
              disabled={loading || (!status.running && !status.paused)}
              className="btn-glass !text-brand-danger disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Square className="h-3.5 w-3.5" /> Stop
            </button>

            <button
              onClick={handleClear}
              disabled={loading}
              className="btn-glass disabled:opacity-40 disabled:cursor-not-allowed"
              title="Clear Queue"
            >
              <RotateCcw className="h-3.5 w-3.5" /> Clear
            </button>
          </div>
        }
      />

      {/* ── Filter bar ───────────────────────────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1], delay: 0.05 }}
        className="glass-panel rounded-[20px] p-4 flex flex-col lg:flex-row gap-3 lg:items-center"
      >
        <div className="relative flex-1 min-w-[240px]">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 h-4 w-4 text-brand-text-muted pointer-events-none" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search request ID, provider, address…"
            className="input-glass !pl-11"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <select value={filterType} onChange={(e) => setFilterType(e.target.value)} className="select-glass">
            <option value="All">All Types</option>
            <option value="Ride">Ride</option>
            <option value="Food">Food</option>
            <option value="Parcel">Parcel</option>
          </select>

          <select value={filterProvider} onChange={(e) => setFilterProvider(e.target.value)} className="select-glass max-w-[160px]">
            <option value="All">All Providers</option>
            {providerOptions.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>

          <select value={filterPriority} onChange={(e) => setFilterPriority(e.target.value)} className="select-glass">
            <option value="All">All Priority</option>
            <option value="High">High</option>
            <option value="Medium">Medium</option>
            <option value="Low">Low</option>
          </select>

          {hasFilters && (
            <button onClick={handleResetFilters} className="btn-ghost !text-brand-primary">
              <X className="h-3.5 w-3.5" /> Reset
            </button>
          )}
        </div>
      </motion.div>

      {/* ── Main Map with floating telemetry ─────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1], delay: 0.1 }}
        className="glass-panel-strong rounded-[30px] p-2"
      >
        <div className="relative rounded-[24px] overflow-hidden h-[62vh] min-h-[520px]">
          <LiveMapContainer
            requests={filteredRequests}
            selectedRequest={selectedRequest}
            onSelectRequest={(req) => setSelectedRequest(req)}
            onClosePopup={() => setSelectedRequest(null)}
            className="relative w-full h-full rounded-[24px] overflow-hidden"
          />

          {/* Floating telemetry (top-left) */}
          <div className="absolute top-5 left-5 z-20 w-[300px] sm:w-[340px] pointer-events-auto">
            <StatisticsPanel stats={stats} lastUpdated={lastUpdated} />
          </div>

          {/* Engine state (top-right) */}
          <div className="absolute top-5 right-5 z-20 hidden sm:flex flex-col items-end gap-2">
            <div className="glass-panel-strong rounded-2xl px-4 py-3 backdrop-blur-xl">
              <div className="flex items-center gap-2.5">
                <Radio className={`h-4 w-4 ${engineActive ? 'text-brand-success' : 'text-brand-text-muted'}`} />
                <span className="text-[11px] font-bold tracking-[0.16em] uppercase text-white">Simulation Engine</span>
              </div>
              <p className="text-[11px] text-brand-text-secondary mt-1">
                {status.status_text || (engineActive ? 'Running' : 'Stopped')} · {status.total_generated || 0} generated
              </p>
            </div>
          </div>

          <div className="absolute inset-0 pointer-events-none rounded-[24px] shadow-[inset_0_0_120px_rgba(5,8,22,0.55)] border border-white/[0.04]" />
        </div>
      </motion.div>
    </div>
  );
}