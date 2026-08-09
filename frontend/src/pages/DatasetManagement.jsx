import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Upload, Trash2, Database,
  Play, Square, RotateCcw, Loader2, Activity, Clock,
  CheckCircle2, ListOrdered, Zap, MapPin, Package, Bike, Utensils
} from 'lucide-react';
import api from '../services/api';
import toast from 'react-hot-toast';

import PageHeader from '../components/ui/PageHeader';

// ─── Type metadata ────────────────────────────────────────────────────────────

const TYPE_META = {
  ride: {
    label: 'Ride',
    color: 'bg-blue-600',
    textColor: 'text-blue-400',
    borderColor: 'border-blue-500/30',
    Icon: Bike,
  },
  food: {
    label: 'Food',
    color: 'bg-orange-600',
    textColor: 'text-orange-400',
    borderColor: 'border-orange-500/30',
    Icon: Utensils,
  },
  parcel: {
    label: 'Parcel',
    color: 'bg-purple-600',
    textColor: 'text-purple-400',
    borderColor: 'border-purple-500/30',
    Icon: Package,
  },
};

const PRIORITY_COLORS = {
  High: 'text-red-400 bg-red-500/10',
  Medium: 'text-amber-400 bg-amber-500/10',
  Low: 'text-green-400 bg-green-500/10',
};

// ─── Live Queue Card ──────────────────────────────────────────────────────────

function QueueCard({ item }) {
  const meta = TYPE_META[item.request_type?.toLowerCase()] || TYPE_META.ride;
  const { Icon } = meta;
  const ts = item.created_at ? new Date(item.created_at) : null;
  const timeStr = ts ? ts.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : '—';

  return (
    <div
      className={`bg-gray-800 border rounded-xl p-4 flex flex-col gap-2 hover:bg-gray-750 transition-colors animate-fade-in border-gray-700 ${meta.borderColor}`}
    >
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className={`flex items-center gap-1 px-2 py-0.5 rounded text-xs font-bold text-white ${meta.color}`}>
            <Icon className="h-3 w-3" />
            {meta.label}
          </span>
          <span className="text-gray-500 text-xs font-mono">#{item.id}</span>
        </div>
        <span className={`px-2 py-0.5 rounded text-xs font-medium ${PRIORITY_COLORS[item.priority] || PRIORITY_COLORS.Medium}`}>
          {item.priority}
        </span>
      </div>

      {/* Provider */}
      {item.provider_name && (
        <p className="text-xs text-gray-400 font-medium">{item.provider_name}</p>
      )}

      {/* Route */}
      <div className="flex items-start gap-2 text-sm">
        <MapPin className="h-4 w-4 text-green-400 shrink-0 mt-0.5" />
        <div className="min-w-0">
          <p className="text-white font-medium truncate">{item.pickup_address || '—'}</p>
          <p className="text-gray-500 text-xs mt-0.5">→ {item.drop_address || '—'}</p>
        </div>
      </div>

      {/* Stats row */}
      <div className="flex items-center gap-4 text-xs text-gray-500 border-t border-gray-700/60 pt-2 mt-1">
        <span className="flex items-center gap-1">
          <Activity className="h-3 w-3" />
          {item.estimated_distance_km?.toFixed(1)} km
        </span>
        <span className="flex items-center gap-1">
          <Clock className="h-3 w-3" />
          ~{item.estimated_time_min?.toFixed(0)} min
        </span>
        <span className="ml-auto">{timeStr}</span>
      </div>
    </div>
  );
}

// ─── Main Component ───────────────────────────────────────────────────────────

export default function DatasetManagement() {
  // ── Dataset state ──────────────────────────────────────────────────────────
  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef();
  const [form, setForm] = useState({
    name: '', data_type: 'Vehicles', file_type: 'csv', description: '',
  });

  // ── Simulation state ───────────────────────────────────────────────────────
  const [simStatus, setSimStatus] = useState({
    running: false,
    total_generated: 0,
    queue_size: 0,
    history_size: 0,
    started_at: null,
    stopped_at: null,
  });
  const [queue, setQueue] = useState([]);
  const [history, setHistory] = useState([]);
  const [simLoading, setSimLoading] = useState(false);
  const pollRef = useRef(null);

  // ── Dataset functions ──────────────────────────────────────────────────────
  useEffect(() => { fetchDatasets(); }, []);

  const fetchDatasets = async () => {
    try {
      const res = await api.get('/orchestration/datasets');
      setDatasets(res.data);
    } catch { toast.error('Failed to load datasets'); }
    finally { setLoading(false); }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    setUploading(true);
    const fd = new FormData();
    fd.append('name', form.name);
    fd.append('file_type', form.file_type);
    fd.append('data_type', form.data_type);
    fd.append('description', form.description);
    if (fileRef.current?.files[0]) fd.append('file', fileRef.current.files[0]);

    try {
      await api.post('/orchestration/datasets/upload', fd);
      toast.success('Dataset uploaded');
      setForm({ name: '', data_type: 'Vehicles', file_type: 'csv', description: '' });
      if (fileRef.current) fileRef.current.value = '';
      fetchDatasets();
    } catch { toast.error('Upload failed'); }
    finally { setUploading(false); }
  };

  const handleDelete = async (id) => {
    if (!confirm('Delete this dataset?')) return;
    try {
      await api.delete(`/orchestration/datasets/${id}`);
      toast.success('Dataset deleted');
      fetchDatasets();
    } catch { toast.error('Delete failed'); }
  };

  // ── Simulation polling ─────────────────────────────────────────────────────
  const fetchSimState = useCallback(async () => {
    try {
      const [statusRes, queueRes, histRes] = await Promise.all([
        api.get('/simulation/status'),
        api.get('/simulation/queue'),
        api.get('/simulation/history'),
      ]);
      setSimStatus(statusRes.data);
      setQueue(queueRes.data.items || []);
      setHistory(histRes.data.items || []);
    } catch {
      // silently ignore poll errors — avoids toast spam during transitions
    }
  }, []);

  // Start / stop polling based on running state
  useEffect(() => {
    fetchSimState(); // initial fetch on mount

    pollRef.current = setInterval(() => { if (document.visibilityState === 'visible') fetchSimState(); }, 3000);
    return () => clearInterval(pollRef.current);
  }, [fetchSimState]);

  // ── Simulation controls ────────────────────────────────────────────────────
  const handleStart = async () => {
    setSimLoading(true);
    try {
      const res = await api.post('/simulation/start');
      setSimStatus(res.data);
      toast.success('Simulation started');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to start simulation');
    } finally { setSimLoading(false); }
  };

  const handleStop = async () => {
    setSimLoading(true);
    try {
      const res = await api.post('/simulation/stop');
      setSimStatus(res.data);
      toast.success('Simulation stopped');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to stop simulation');
    } finally { setSimLoading(false); }
  };

  const handleClear = async () => {
    if (!confirm('Clear all simulation requests from the queue?')) return;
    setSimLoading(true);
    try {
      await api.post('/simulation/clear');
      setSimStatus({ running: false, total_generated: 0, queue_size: 0, history_size: 0, started_at: null, stopped_at: null });
      setQueue([]);
      setHistory([]);
      toast.success('Simulation cleared');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to clear simulation');
    } finally { setSimLoading(false); }
  };

  // ── Dataset type color map ─────────────────────────────────────────────────
  const typeColors = {
    Vehicles: 'bg-blue-600', Requests: 'bg-amber-600', Restaurants: 'bg-orange-600',
    'Parcel Centers': 'bg-purple-600', Traffic: 'bg-red-600',
    'Road Network': 'bg-green-600', Coordinates: 'bg-cyan-600',
  };

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="pb-10 max-w-[1500px] mx-auto">
      <PageHeader
        eyebrow="System"
        title="Datasets"
        description="Upload reference data — vehicles, requests, restaurants, parcels, traffic and road networks."
      />

      {/* ═══════════════════════════════════════════════════════════
          LIVE SIMULATION SECTION
      ══════════════════════════════════════════════════════════════ */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 mb-6">
        {/* Section header */}
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <Zap className="h-5 w-5 text-yellow-400" />
            Live Simulation Engine
          </h2>
          {/* Status badge */}
          <div className="flex items-center gap-2">
            {simStatus.running ? (
              <span className="flex items-center gap-1.5 px-3 py-1 bg-green-500/10 border border-green-500/30 rounded-full text-xs font-semibold text-green-400">
                <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                Running
              </span>
            ) : (
              <span className="flex items-center gap-1.5 px-3 py-1 bg-gray-700 border border-gray-600 rounded-full text-xs font-semibold text-gray-400">
                <span className="w-1.5 h-1.5 rounded-full bg-gray-500" />
                Stopped
              </span>
            )}
          </div>
        </div>

        {/* Control buttons */}
        <div className="flex flex-wrap items-center gap-3 mb-6">
          <button
            id="sim-start-btn"
            onClick={handleStart}
            disabled={simLoading || simStatus.running}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors"
          >
            {simLoading && !simStatus.running ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Play className="h-4 w-4" />
            )}
            Start Simulation
          </button>

          <button
            id="sim-stop-btn"
            onClick={handleStop}
            disabled={simLoading || !simStatus.running}
            className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors"
          >
            {simLoading && simStatus.running ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Square className="h-4 w-4" />
            )}
            Stop Simulation
          </button>

          <button
            id="sim-clear-btn"
            onClick={handleClear}
            disabled={simLoading}
            className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors"
          >
            <RotateCcw className="h-4 w-4" />
            Clear
          </button>

          <p className="text-xs text-gray-500 ml-auto">
            Auto-generates 1 request every 3–5 seconds
          </p>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <StatCard
            label="Total Generated"
            value={simStatus.total_generated}
            icon={<Activity className="h-4 w-4 text-indigo-400" />}
          />
          <StatCard
            label="Active Queue"
            value={simStatus.queue_size}
            icon={<ListOrdered className="h-4 w-4 text-yellow-400" />}
          />
          <StatCard
            label="Completed"
            value={simStatus.history_size}
            icon={<CheckCircle2 className="h-4 w-4 text-green-400" />}
          />
          <StatCard
            label="Started At"
            value={
              simStatus.started_at
                ? new Date(simStatus.started_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                : '—'
            }
            icon={<Clock className="h-4 w-4 text-gray-400" />}
          />
        </div>

        {/* Live Queue panel */}
        <div className="mb-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-white flex items-center gap-2">
              <ListOrdered className="h-4 w-4 text-yellow-400" />
              Live Queue
              {queue.length > 0 && (
                <span className="ml-1 px-2 py-0.5 bg-yellow-500/20 text-yellow-400 rounded-full text-xs font-bold">
                  {queue.length}
                </span>
              )}
            </h3>
            <span className="text-xs text-gray-500">Refreshes every 3s</span>
          </div>

          {queue.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-10 text-gray-600 border border-dashed border-gray-700 rounded-xl">
              <ListOrdered className="h-8 w-8 mb-2 opacity-40" />
              <p className="text-sm">Queue is empty</p>
              <p className="text-xs mt-1">Start the simulation to see live requests appear here</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3 max-h-[520px] overflow-y-auto pr-1">
              {queue.map((item) => (
                <QueueCard key={item.id} item={item} />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Completed Requests section (structure ready for Phase 2 / DMFE) */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 mb-6">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2 mb-4">
          <CheckCircle2 className="h-5 w-5 text-green-400" />
          Completed Requests
        </h2>
        {history.length === 0 ? (
          <div className="text-center py-10 text-gray-600">
            <CheckCircle2 className="h-8 w-8 mx-auto mb-2 opacity-40" />
            <p className="text-sm">No completed requests yet</p>
            <p className="text-xs mt-1">Requests processed by DMFE will appear here in Phase 2</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-400 border-b border-gray-700 text-xs">
                  <th className="px-4 py-2 font-medium">ID</th>
                  <th className="px-4 py-2 font-medium">Type</th>
                  <th className="px-4 py-2 font-medium">Provider</th>
                  <th className="px-4 py-2 font-medium">Route</th>
                  <th className="px-4 py-2 font-medium">Status</th>
                  <th className="px-4 py-2 font-medium">Time</th>
                </tr>
              </thead>
              <tbody>
                {history.map((item) => {
                  const meta = TYPE_META[item.request_type?.toLowerCase()] || TYPE_META.ride;
                  return (
                    <tr key={item.id} className="border-b border-gray-700/40 hover:bg-gray-700/20">
                      <td className="px-4 py-2 text-gray-400 font-mono">#{item.id}</td>
                      <td className="px-4 py-2">
                        <span className={`px-2 py-0.5 rounded text-xs font-medium text-white ${meta.color}`}>
                          {meta.label}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-gray-300">{item.provider_name || '—'}</td>
                      <td className="px-4 py-2 text-gray-300">
                        {item.pickup_address} → {item.drop_address}
                      </td>
                      <td className="px-4 py-2">
                        <span className="px-2 py-0.5 bg-green-500/10 text-green-400 rounded text-xs font-medium">
                          {item.status}
                        </span>
                      </td>
                      <td className="px-4 py-2 text-gray-500 text-xs">
                        {item.created_at ? new Date(item.created_at).toLocaleTimeString() : '—'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ═══════════════════════════════════════════════════════════
          EXISTING — Upload Dataset Section (unchanged)
      ══════════════════════════════════════════════════════════════ */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 mb-6">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Upload className="h-5 w-5 text-indigo-400" /> Upload Dataset
        </h2>
        <form onSubmit={handleUpload} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Name</label>
              <input
                type="text" required value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                placeholder="Dataset name"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Data Type</label>
              <select
                value={form.data_type}
                onChange={(e) => setForm({ ...form, data_type: e.target.value })}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                {['Vehicles', 'Requests', 'Restaurants', 'Parcel Centers', 'Traffic', 'Road Network', 'Coordinates'].map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">File Type</label>
              <select
                value={form.file_type}
                onChange={(e) => setForm({ ...form, file_type: e.target.value })}
                className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="csv">CSV</option>
                <option value="json">JSON</option>
                <option value="xlsx">Excel</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">File</label>
              <input
                type="file" ref={fileRef} accept=".csv,.json,.xlsx"
                className="w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-indigo-600 file:text-white hover:file:bg-indigo-700"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Description</label>
            <input
              type="text" value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="Optional description"
            />
          </div>
          <button
            type="submit" disabled={uploading}
            className="px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50"
          >
            {uploading ? 'Uploading...' : 'Upload'}
          </button>
        </form>
      </div>

      {/* ═══════════════════════════════════════════════════════════
          EXISTING — Dataset table (unchanged)
      ══════════════════════════════════════════════════════════════ */}
      {loading ? (
        <div className="flex items-center justify-center h-32">
          <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-indigo-500" />
        </div>
      ) : datasets.length === 0 ? (
        <div className="text-center py-16 text-gray-500">
          <Database className="h-12 w-12 mx-auto mb-3 opacity-50" />
          <p className="text-lg font-medium">No datasets uploaded</p>
          <p className="text-sm">Upload CSV, JSON, or Excel files containing vehicle, request, or route data</p>
        </div>
      ) : (
        <div className="bg-gray-800 border border-gray-700 rounded-xl overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-700 text-left text-sm text-gray-400">
                <th className="px-5 py-3 font-medium">Name</th>
                <th className="px-5 py-3 font-medium">Type</th>
                <th className="px-5 py-3 font-medium">Format</th>
                <th className="px-5 py-3 font-medium">Rows</th>
                <th className="px-5 py-3 font-medium">Date</th>
                <th className="px-5 py-3 font-medium"></th>
              </tr>
            </thead>
            <tbody>
              {datasets.map((d) => (
                <tr key={d.id} className="border-b border-gray-700/50 text-sm hover:bg-gray-700/30">
                  <td className="px-5 py-3 text-white font-medium">{d.name}</td>
                  <td className="px-5 py-3">
                    <span className={`px-2 py-0.5 rounded text-xs font-medium text-white ${typeColors[d.data_type] || 'bg-gray-600'}`}>
                      {d.data_type}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-gray-300 uppercase">{d.file_type}</td>
                  <td className="px-5 py-3 text-gray-300">{d.row_count}</td>
                  <td className="px-5 py-3 text-gray-400">
                    {d.created_at ? new Date(d.created_at).toLocaleDateString() : '-'}
                  </td>
                  <td className="px-5 py-3">
                    <button onClick={() => handleDelete(d.id)} className="text-gray-500 hover:text-red-400">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─── Stat Card sub-component ──────────────────────────────────────────────────

function StatCard({ label, value, icon }) {
  return (
    <div className="bg-gray-900/50 border border-gray-700/60 rounded-lg px-4 py-3 flex items-center gap-3">
      <div className="shrink-0">{icon}</div>
      <div className="min-w-0">
        <p className="text-xs text-gray-500">{label}</p>
        <p className="text-lg font-bold text-white leading-tight">{value}</p>
      </div>
    </div>
  );
}
