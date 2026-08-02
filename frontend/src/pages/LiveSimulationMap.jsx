import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Play, Pause, Square, RotateCcw, Zap, MapPin, Radio, Activity } from 'lucide-react';
import api from '../services/api';
import toast from 'react-hot-toast';

import LiveMapContainer from '../components/map/LiveMapContainer';
import StatisticsPanel from '../components/map/StatisticsPanel';
import MapFilters from '../components/map/MapFilters';

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

  // Search & Filters state
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
    pollRef.current = setInterval(fetchLiveData, 2500);
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
    return {
      active: filteredRequests.length,
      ride,
      food,
      parcel,
    };
  }, [filteredRequests]);

  const handleResetFilters = () => {
    setSearchTerm('');
    setFilterType('All');
    setFilterProvider('All');
    setFilterPriority('All');
  };

  // ───────────────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-4 pb-12">
      {/* Top Header & Quick Action Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Radio className="h-6 w-6 text-red-500 animate-pulse" />
            Live Google Maps Simulation
          </h1>
          <p className="text-gray-400 text-sm mt-0.5">Real-time pickup marker visualization for Coimbatore transportation requests</p>
        </div>

        {/* Engine Controls */}
        <div className="flex items-center gap-2">
          {status.running && !status.paused ? (
            <button
              onClick={handlePause}
              disabled={loading}
              className="flex items-center gap-1.5 px-3.5 py-1.5 bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white font-medium rounded-lg text-xs transition-colors"
            >
              <Pause className="h-4 w-4" /> Pause
            </button>
          ) : (
            <button
              onClick={handleStartResume}
              disabled={loading}
              className="flex items-center gap-1.5 px-3.5 py-1.5 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white font-medium rounded-lg text-xs transition-colors"
            >
              <Play className="h-4 w-4" /> {status.paused ? 'Resume' : 'Start'}
            </button>
          )}

          <button
            onClick={handleStop}
            disabled={loading || (!status.running && !status.paused)}
            className="flex items-center gap-1.5 px-3.5 py-1.5 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white font-medium rounded-lg text-xs transition-colors"
          >
            <Square className="h-4 w-4" /> Stop
          </button>

          <button
            onClick={handleClear}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 text-gray-200 font-medium rounded-lg text-xs transition-colors"
            title="Clear Queue"
          >
            <RotateCcw className="h-3.5 w-3.5" /> Clear
          </button>
        </div>
      </div>

      {/* Search & Filters Bar */}
      <MapFilters
        searchTerm={searchTerm}
        setSearchTerm={setSearchTerm}
        filterType={filterType}
        setFilterType={setFilterType}
        filterProvider={filterProvider}
        setFilterProvider={setFilterProvider}
        filterPriority={filterPriority}
        setFilterPriority={setFilterPriority}
        providerOptions={providerOptions}
        onResetFilters={handleResetFilters}
      />

      {/* Main Map View Area with Floating Telemetry Panel */}
      <div className="relative rounded-xl overflow-hidden shadow-2xl">
        {/* Statistics Panel Floating Overlay (Top Left) */}
        <div className="absolute top-4 left-4 z-10 w-full max-w-sm sm:max-w-md pointer-events-auto">
          <StatisticsPanel stats={stats} lastUpdated={lastUpdated} />
        </div>

        {/* Live Map Container */}
        <LiveMapContainer
          requests={filteredRequests}
          selectedRequest={selectedRequest}
          onSelectRequest={(req) => setSelectedRequest(req)}
          onClosePopup={() => setSelectedRequest(null)}
        />
      </div>
    </div>
  );
}
