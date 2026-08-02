import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { NavLink } from 'react-router-dom';
import {
  Zap, Play, Pause, Square, Trash2, RotateCcw, Activity, Clock,
  CheckCircle2, ListOrdered, Search, Filter, RefreshCw, Bike, Utensils,
  Package, MapPin, Gauge, Layers, Building2, TrendingUp, AlertCircle
} from 'lucide-react';
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import api from '../services/api';
import toast from 'react-hot-toast';

// ─── Type metadata ────────────────────────────────────────────────────────────

const TYPE_META = {
  ride: { label: 'Ride', color: '#2563eb', bgClass: 'bg-blue-600', textClass: 'text-blue-400', borderClass: 'border-blue-500/30', Icon: Bike },
  food: { label: 'Food', color: '#ea580c', bgClass: 'bg-orange-600', textClass: 'text-orange-400', borderClass: 'border-orange-500/30', Icon: Utensils },
  parcel: { label: 'Parcel', color: '#9333ea', bgClass: 'bg-purple-600', textClass: 'text-purple-400', borderClass: 'border-purple-500/30', Icon: Package },
};

const PRIORITY_CLASSES = {
  High: 'text-red-400 bg-red-500/10 border-red-500/30',
  Medium: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
  Low: 'text-green-400 bg-green-500/10 border-green-500/30',
};

const PIE_COLORS = ['#3b82f6', '#f97316', '#a855f7', '#10b981', '#ec4899', '#6366f1'];

function formatRuntime(seconds) {
  if (!seconds || seconds <= 0) return '00:00:00';
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  return [hrs, mins, secs].map(v => String(v).padStart(2, '0')).join(':');
}

export default function SimulationMonitoring() {
  // ── State ──────────────────────────────────────────────────────────────────
  const [status, setStatus] = useState({
    running: false,
    paused: false,
    status_text: 'Stopped',
    total_generated: 0,
    queue_size: 0,
    history_size: 0,
    runtime_seconds: 0,
    requests_per_minute: 0,
    pending_ride: 0,
    pending_food: 0,
    pending_parcel: 0,
    completed_ride: 0,
    completed_food: 0,
    completed_parcel: 0,
  });

  const [queue, setQueue] = useState([]);
  const [history, setHistory] = useState([]);
  const [analytics, setAnalytics] = useState({
    requests_over_time: [],
    type_distribution: [],
    provider_distribution: [],
    queue_trend: [],
  });

  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('queue'); // 'queue' | 'history'

  // Search & Filters state
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('All');
  const [filterProvider, setFilterProvider] = useState('All');
  const [filterPriority, setFilterPriority] = useState('All');

  const pollRef = useRef(null);

  // ── Polling Data Fetching ───────────────────────────────────────────────────
  const fetchAllData = useCallback(async () => {
    try {
      const [statusRes, queueRes, histRes, analyticsRes] = await Promise.all([
        api.get('/simulation/status'),
        api.get('/simulation/queue?limit=200'),
        api.get('/simulation/history?limit=200'),
        api.get('/simulation/analytics'),
      ]);
      setStatus(statusRes.data);
      setQueue(queueRes.data.items || []);
      setHistory(histRes.data.items || []);
      setAnalytics(analyticsRes.data || {});
    } catch {
      // Silently catch polling errors to maintain smooth UI
    }
  }, []);

  useEffect(() => {
    fetchAllData();
    pollRef.current = setInterval(fetchAllData, 2500);
    return () => clearInterval(pollRef.current);
  }, [fetchAllData]);

  // ── Controls Handlers ──────────────────────────────────────────────────────
  const handleStartResume = async () => {
    setLoading(true);
    try {
      const endpoint = status.paused ? '/simulation/resume' : '/simulation/start';
      const res = await api.post(endpoint);
      setStatus(res.data);
      toast.success(status.paused ? 'Simulation Resumed' : 'Simulation Started');
      fetchAllData();
    } catch {
      toast.error('Failed to start/resume simulation');
    } finally { setLoading(false); }
  };

  const handlePause = async () => {
    setLoading(true);
    try {
      const res = await api.post('/simulation/pause');
      setStatus(res.data);
      toast.success('Simulation Paused');
      fetchAllData();
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
      fetchAllData();
    } catch {
      toast.error('Failed to stop simulation');
    } finally { setLoading(false); }
  };

  const handleClearQueue = async () => {
    if (!confirm('Clear all pending requests from the queue?')) return;
    setLoading(true);
    try {
      const res = await api.post('/simulation/clear-queue');
      setStatus(res.data);
      setQueue([]);
      toast.success('Pending Queue Cleared');
      fetchAllData();
    } catch {
      toast.error('Failed to clear queue');
    } finally { setLoading(false); }
  };

  const handleClearHistory = async () => {
    if (!confirm('Clear all completed request history?')) return;
    setLoading(true);
    try {
      const res = await api.post('/simulation/clear-history');
      setStatus(res.data);
      setHistory([]);
      toast.success('Completed History Cleared');
      fetchAllData();
    } catch {
      toast.error('Failed to clear history');
    } finally { setLoading(false); }
  };

  // ── Provider Options for Filter Dropdown ───────────────────────────────────
  const providerOptions = useMemo(() => {
    const set = new Set();
    queue.forEach(i => i.provider_name && set.add(i.provider_name));
    history.forEach(i => i.provider_name && set.add(i.provider_name));
    return Array.from(set);
  }, [queue, history]);

  // ── Filtered List Computations ─────────────────────────────────────────────
  const filterItem = useCallback((item) => {
    // Search matching
    const searchLower = searchTerm.toLowerCase();
    const matchesSearch = !searchTerm || (
      String(item.id).includes(searchLower) ||
      (item.provider_name && item.provider_name.toLowerCase().includes(searchLower)) ||
      (item.pickup_address && item.pickup_address.toLowerCase().includes(searchLower)) ||
      (item.drop_address && item.drop_address.toLowerCase().includes(searchLower))
    );

    // Dropdown filters
    const matchesType = filterType === 'All' || item.request_type?.toLowerCase() === filterType.toLowerCase();
    const matchesProvider = filterProvider === 'All' || item.provider_name === filterProvider;
    const matchesPriority = filterPriority === 'All' || item.priority === filterPriority;

    return matchesSearch && matchesType && matchesProvider && matchesPriority;
  }, [searchTerm, filterType, filterProvider, filterPriority]);

  const filteredQueue = useMemo(() => queue.filter(filterItem), [queue, filterItem]);
  const filteredHistory = useMemo(() => history.filter(filterItem), [history, filterItem]);

  // ───────────────────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6 pb-12">
      {/* ── Page Header & Controls ─────────────────────────────────────────── */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Zap className="h-6 w-6 text-yellow-400" />
            Simulation Monitoring Dashboard
          </h1>
          <p className="text-gray-400 text-sm mt-1">Real-time telemetry, queue management, and transportation analytics</p>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center gap-2">
          {status.running && !status.paused ? (
            <button
              onClick={handlePause}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white font-medium rounded-lg text-sm transition-colors"
            >
              <Pause className="h-4 w-4" /> Pause
            </button>
          ) : (
            <button
              onClick={handleStartResume}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white font-medium rounded-lg text-sm transition-colors"
            >
              <Play className="h-4 w-4" /> {status.paused ? 'Resume' : 'Start Simulation'}
            </button>
          )}

          <button
            onClick={handleStop}
            disabled={loading || (!status.running && !status.paused)}
            className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white font-medium rounded-lg text-sm transition-colors"
          >
            <Square className="h-4 w-4" /> Stop
          </button>

          <button
            onClick={handleClearQueue}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 text-gray-200 font-medium rounded-lg text-sm transition-colors"
            title="Clear Pending Requests"
          >
            <RotateCcw className="h-4 w-4" /> Clear Queue
          </button>

          <button
            onClick={handleClearHistory}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 text-gray-200 font-medium rounded-lg text-sm transition-colors"
            title="Clear Completed History"
          >
            <Trash2 className="h-4 w-4 text-red-400" /> Clear History
          </button>

          <NavLink
            to="/live-map"
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg text-sm transition-colors shadow-sm ml-auto"
          >
            <MapPin className="h-4 w-4" /> Live Map
          </NavLink>
        </div>
      </div>

      {/* ── 1. Main Simulation Status Bar Card ────────────────────────────── */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-5 shadow-lg">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {/* Status Indicator */}
          <div className="bg-gray-900/60 border border-gray-700/60 rounded-lg p-3">
            <p className="text-xs text-gray-400 font-medium mb-1">Status</p>
            <div className="flex items-center gap-2">
              {status.status_text === 'Running' && (
                <span className="flex items-center gap-1.5 px-2.5 py-0.5 bg-green-500/10 border border-green-500/30 rounded-full text-xs font-semibold text-green-400">
                  <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                  Running
                </span>
              )}
              {status.status_text === 'Paused' && (
                <span className="flex items-center gap-1.5 px-2.5 py-0.5 bg-amber-500/10 border border-amber-500/30 rounded-full text-xs font-semibold text-amber-400">
                  <span className="w-2 h-2 rounded-full bg-amber-400" />
                  Paused
                </span>
              )}
              {status.status_text === 'Stopped' && (
                <span className="flex items-center gap-1.5 px-2.5 py-0.5 bg-gray-700 border border-gray-600 rounded-full text-xs font-semibold text-gray-400">
                  <span className="w-2 h-2 rounded-full bg-gray-500" />
                  Stopped
                </span>
              )}
            </div>
          </div>

          {/* Total Generated */}
          <div className="bg-gray-900/60 border border-gray-700/60 rounded-lg p-3">
            <p className="text-xs text-gray-400 font-medium mb-0.5">Total Generated</p>
            <p className="text-xl font-bold text-white">{status.total_generated}</p>
          </div>

          {/* Active Queue Size */}
          <div className="bg-gray-900/60 border border-gray-700/60 rounded-lg p-3">
            <p className="text-xs text-gray-400 font-medium mb-0.5">Active Queue</p>
            <p className="text-xl font-bold text-yellow-400">{status.queue_size}</p>
          </div>

          {/* Completed Requests */}
          <div className="bg-gray-900/60 border border-gray-700/60 rounded-lg p-3">
            <p className="text-xs text-gray-400 font-medium mb-0.5">Completed</p>
            <p className="text-xl font-bold text-green-400">{status.history_size}</p>
          </div>

          {/* Runtime */}
          <div className="bg-gray-900/60 border border-gray-700/60 rounded-lg p-3">
            <p className="text-xs text-gray-400 font-medium mb-0.5">Runtime</p>
            <p className="text-xl font-bold text-indigo-400 font-mono">
              {formatRuntime(status.runtime_seconds)}
            </p>
          </div>

          {/* Requests Per Minute */}
          <div className="bg-gray-900/60 border border-gray-700/60 rounded-lg p-3">
            <p className="text-xs text-gray-400 font-medium mb-0.5">Rate (RPM)</p>
            <p className="text-xl font-bold text-cyan-400">
              {status.requests_per_minute} <span className="text-xs font-normal text-gray-400">req/m</span>
            </p>
          </div>
        </div>
      </div>

      {/* ── 4. Queue Statistics Breakdown Cards (6 Cards) ──────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <StatCard label="Pending Ride" value={status.pending_ride} icon={<Bike className="h-4 w-4 text-blue-400" />} color="border-blue-500/20 bg-blue-500/5" />
        <StatCard label="Pending Food" value={status.pending_food} icon={<Utensils className="h-4 w-4 text-orange-400" />} color="border-orange-500/20 bg-orange-500/5" />
        <StatCard label="Pending Parcel" value={status.pending_parcel} icon={<Package className="h-4 w-4 text-purple-400" />} color="border-purple-500/20 bg-purple-500/5" />
        <StatCard label="Completed Ride" value={status.completed_ride} icon={<CheckCircle2 className="h-4 w-4 text-blue-400" />} color="border-blue-500/20 bg-blue-500/5" />
        <StatCard label="Completed Food" value={status.completed_food} icon={<CheckCircle2 className="h-4 w-4 text-orange-400" />} color="border-orange-500/20 bg-orange-500/5" />
        <StatCard label="Completed Parcel" value={status.completed_parcel} icon={<CheckCircle2 className="h-4 w-4 text-purple-400" />} color="border-purple-500/20 bg-purple-500/5" />
      </div>

      {/* ── 9. Interactive Analytics & Charts ──────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Chart 1: Requests Generated Over Time */}
        <div className="bg-gray-800 border border-gray-700 rounded-xl p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-indigo-400" /> Requests Generated Over Time
          </h3>
          <div className="h-60 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={analytics.requests_over_time || []}>
                <defs>
                  <linearGradient id="reqColor" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="time" stroke="#9ca3af" fontSize={11} />
                <YAxis stroke="#9ca3af" fontSize={11} allowDecimals={false} />
                <Tooltip contentStyle={{ backgroundColor: '#1f2937', borderColor: '#4b5563', color: '#fff' }} />
                <Area type="monotone" dataKey="count" stroke="#6366f1" fillOpacity={1} fill="url(#reqColor)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 2: Queue Size Trend */}
        <div className="bg-gray-800 border border-gray-700 rounded-xl p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <Activity className="h-4 w-4 text-yellow-400" /> Queue Size Trend
          </h3>
          <div className="h-60 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={analytics.queue_trend || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="time" stroke="#9ca3af" fontSize={11} />
                <YAxis stroke="#9ca3af" fontSize={11} allowDecimals={false} />
                <Tooltip contentStyle={{ backgroundColor: '#1f2937', borderColor: '#4b5563', color: '#fff' }} />
                <Line type="monotone" dataKey="count" stroke="#eab308" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 3: Request Type Distribution */}
        <div className="bg-gray-800 border border-gray-700 rounded-xl p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <Layers className="h-4 w-4 text-blue-400" /> Request Type Distribution
          </h3>
          <div className="h-60 w-full flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={analytics.type_distribution || []}
                  dataKey="count"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                >
                  {(analytics.type_distribution || []).map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: '#1f2937', borderColor: '#4b5563', color: '#fff' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Chart 4: Provider Distribution */}
        <div className="bg-gray-800 border border-gray-700 rounded-xl p-5 shadow-sm">
          <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
            <Building2 className="h-4 w-4 text-orange-400" /> Provider Distribution
          </h3>
          <div className="h-60 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={analytics.provider_distribution || []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="name" stroke="#9ca3af" fontSize={11} />
                <YAxis stroke="#9ca3af" fontSize={11} allowDecimals={false} />
                <Tooltip contentStyle={{ backgroundColor: '#1f2937', borderColor: '#4b5563', color: '#fff' }} />
                <Bar dataKey="count" fill="#f97316" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* ── 5 & 6. Search & Filter Bar ─────────────────────────────────────── */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 shadow-sm">
        <div className="flex flex-col md:flex-row gap-3 items-stretch md:items-center justify-between">
          {/* Search bar */}
          <div className="relative flex-1">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search by Request ID, Provider, Pickup, or Destination..."
              className="w-full pl-9 pr-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          {/* Filter dropdowns */}
          <div className="flex flex-wrap items-center gap-2 text-sm">
            {/* Request Type */}
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className="px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="All">All Types</option>
              <option value="ride">Ride</option>
              <option value="food">Food</option>
              <option value="parcel">Parcel</option>
            </select>

            {/* Provider */}
            <select
              value={filterProvider}
              onChange={(e) => setFilterProvider(e.target.value)}
              className="px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="All">All Providers</option>
              {providerOptions.map(p => (
                <option key={p} value={p}>{p}</option>
              ))}
            </select>

            {/* Priority */}
            <select
              value={filterPriority}
              onChange={(e) => setFilterPriority(e.target.value)}
              className="px-3 py-2 bg-gray-900 border border-gray-700 rounded-lg text-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="All">All Priorities</option>
              <option value="High">High</option>
              <option value="Medium">Medium</option>
              <option value="Low">Low</option>
            </select>
          </div>
        </div>
      </div>

      {/* ── 2 & 3. Pending Queue & Completed Tables (Tabbed Interface) ─────── */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden shadow-lg">
        {/* Navigation Tabs */}
        <div className="flex items-center border-b border-gray-700 bg-gray-850 px-6">
          <button
            onClick={() => setActiveTab('queue')}
            className={`flex items-center gap-2 py-4 px-4 font-semibold text-sm border-b-2 transition-colors ${
              activeTab === 'queue'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            <ListOrdered className="h-4 w-4" />
            Pending Request Queue
            <span className="px-2 py-0.5 rounded-full text-xs bg-yellow-500/20 text-yellow-400 font-bold">
              {filteredQueue.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('history')}
            className={`flex items-center gap-2 py-4 px-4 font-semibold text-sm border-b-2 transition-colors ${
              activeTab === 'history'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            <CheckCircle2 className="h-4 w-4" />
            Completed Requests
            <span className="px-2 py-0.5 rounded-full text-xs bg-green-500/20 text-green-400 font-bold">
              {filteredHistory.length}
            </span>
          </button>
        </div>

        {/* Tab 1: Pending Queue Table */}
        {activeTab === 'queue' && (
          <div className="overflow-x-auto">
            {filteredQueue.length === 0 ? (
              <div className="text-center py-16 text-gray-500">
                <ListOrdered className="h-10 w-10 mx-auto mb-2 opacity-40" />
                <p className="text-base font-medium">No pending requests match your search or filter</p>
                <p className="text-xs text-gray-600 mt-1">Start the simulation or clear active filters</p>
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-700 bg-gray-900/40 text-left text-xs font-semibold text-gray-400">
                    <th className="px-5 py-3.5">Request ID</th>
                    <th className="px-5 py-3.5">Type</th>
                    <th className="px-5 py-3.5">Provider</th>
                    <th className="px-5 py-3.5">Pickup</th>
                    <th className="px-5 py-3.5">Destination</th>
                    <th className="px-5 py-3.5">Priority</th>
                    <th className="px-5 py-3.5">Distance</th>
                    <th className="px-5 py-3.5">Est. Time</th>
                    <th className="px-5 py-3.5">Created Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700/50">
                  {filteredQueue.map((item) => {
                    const meta = TYPE_META[item.request_type?.toLowerCase()] || TYPE_META.ride;
                    const { Icon } = meta;
                    const createdStr = item.created_at
                      ? new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
                      : '—';

                    return (
                      <tr key={item.id} className="hover:bg-gray-700/30 transition-colors">
                        <td className="px-5 py-3.5 text-gray-300 font-mono font-medium">#{item.id}</td>
                        <td className="px-5 py-3.5">
                          <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-xs font-bold text-white ${meta.bgClass}`}>
                            <Icon className="h-3 w-3" />
                            {meta.label}
                          </span>
                        </td>
                        <td className="px-5 py-3.5 text-white font-medium">{item.provider_name || '—'}</td>
                        <td className="px-5 py-3.5 text-gray-300">{item.pickup_address}</td>
                        <td className="px-5 py-3.5 text-gray-300">{item.drop_address}</td>
                        <td className="px-5 py-3.5">
                          <span className={`px-2.5 py-0.5 rounded border text-xs font-semibold ${PRIORITY_CLASSES[item.priority] || PRIORITY_CLASSES.Medium}`}>
                            {item.priority}
                          </span>
                        </td>
                        <td className="px-5 py-3.5 text-gray-300">{item.estimated_distance_km?.toFixed(1)} km</td>
                        <td className="px-5 py-3.5 text-gray-300">~{item.estimated_time_min?.toFixed(0)} min</td>
                        <td className="px-5 py-3.5 text-gray-400 text-xs">{createdStr}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        )}

        {/* Tab 2: Completed Requests Table */}
        {activeTab === 'history' && (
          <div className="overflow-x-auto">
            {filteredHistory.length === 0 ? (
              <div className="text-center py-16 text-gray-500">
                <CheckCircle2 className="h-10 w-10 mx-auto mb-2 opacity-40" />
                <p className="text-base font-medium">No completed requests recorded</p>
                <p className="text-xs text-gray-600 mt-1">Processed requests will automatically appear here</p>
              </div>
            ) : (
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-700 bg-gray-900/40 text-left text-xs font-semibold text-gray-400">
                    <th className="px-5 py-3.5">Request ID</th>
                    <th className="px-5 py-3.5">Type</th>
                    <th className="px-5 py-3.5">Provider</th>
                    <th className="px-5 py-3.5">Pickup</th>
                    <th className="px-5 py-3.5">Destination</th>
                    <th className="px-5 py-3.5">Completed Time</th>
                    <th className="px-5 py-3.5">Proc. Duration</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700/50">
                  {filteredHistory.map((item) => {
                    const meta = TYPE_META[item.request_type?.toLowerCase()] || TYPE_META.ride;
                    const { Icon } = meta;
                    const compStr = item.completed_at
                      ? new Date(item.completed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
                      : '—';

                    return (
                      <tr key={item.id} className="hover:bg-gray-700/30 transition-colors">
                        <td className="px-5 py-3.5 text-gray-300 font-mono font-medium">#{item.id}</td>
                        <td className="px-5 py-3.5">
                          <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded text-xs font-bold text-white ${meta.bgClass}`}>
                            <Icon className="h-3 w-3" />
                            {meta.label}
                          </span>
                        </td>
                        <td className="px-5 py-3.5 text-white font-medium">{item.provider_name || '—'}</td>
                        <td className="px-5 py-3.5 text-gray-300">{item.pickup_address}</td>
                        <td className="px-5 py-3.5 text-gray-300">{item.drop_address}</td>
                        <td className="px-5 py-3.5 text-gray-300 text-xs">{compStr}</td>
                        <td className="px-5 py-3.5 text-green-400 font-mono text-xs">{item.processing_duration_sec?.toFixed(1)}s</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Auxiliary Component: Stat Card ──────────────────────────────────────────

function StatCard({ label, value, icon, color }) {
  return (
    <div className={`border rounded-xl p-3.5 flex items-center gap-3 shadow-sm ${color || 'bg-gray-800 border-gray-700'}`}>
      <div className="shrink-0">{icon}</div>
      <div className="min-w-0">
        <p className="text-xs text-gray-400 truncate">{label}</p>
        <p className="text-lg font-bold text-white leading-tight">{value}</p>
      </div>
    </div>
  );
}
