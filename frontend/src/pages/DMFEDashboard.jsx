import React, { useState, useEffect, useCallback, useRef } from 'react';
import { GitBranchPlus, Play, RefreshCw, ToggleLeft, ToggleRight, ArrowRight, History } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../services/api';

import DMFEStatisticsBar from '../components/dmfe/DMFEStatisticsBar';
import PendingQueuePanel from '../components/dmfe/PendingQueuePanel';
import BatchesPanel from '../components/dmfe/BatchesPanel';
import RejectedRequestsPanel from '../components/dmfe/RejectedRequestsPanel';

export default function DMFEDashboard() {
  // ── State ────────────────────────────────────────────────────────────────
  const [stats, setStats]           = useState({});
  const [pendingRequests, setPending] = useState([]);
  const [lastResult, setLastResult] = useState(null);     // most recent /analyze response
  const [compatBatches, setCompatBatches] = useState([]);
  const [rejectedBatches, setRejectedBatches] = useState([]);
  const [history, setHistory]       = useState([]);

  const [analyzing, setAnalyzing]   = useState(false);
  const [loadingQueue, setLoadingQueue] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [activeTab, setActiveTab]   = useState('batches'); // 'batches' | 'rejected' | 'history'

  const autoRefreshRef = useRef(null);

  // ── Data fetchers ────────────────────────────────────────────────────────
  const fetchStats = useCallback(async () => {
    try {
      const res = await api.get('/dmfe/statistics');
      setStats(res.data || {});
    } catch (e) { /* silently ignore */ }
  }, []);

  const fetchPendingQueue = useCallback(async () => {
    setLoadingQueue(true);
    try {
      const res = await api.get('/simulation/queue?limit=50');
      // SimulationQueueResponse shape: { total, items }
      setPending(res.data?.items || []);
    } catch (e) {
      setPending([]);
    } finally {
      setLoadingQueue(false);
    }
  }, []);

  const fetchBatches = useCallback(async () => {
    try {
      const [compatRes, rejRes] = await Promise.all([
        api.get('/dmfe/batches?status=Pending&limit=50'),
        api.get('/dmfe/batches?status=Rejected&limit=50'),
      ]);
      // Batches from API are lightweight — we need full requests_summary
      // They come fully populated from the /analyze endpoint
      // Here we just update if we don't have a fresh lastResult
      if (!lastResult) {
        setCompatBatches(compatRes.data || []);
        setRejectedBatches(rejRes.data || []);
      }
    } catch (e) { /* silently ignore */ }
  }, [lastResult]);

  const fetchHistory = useCallback(async () => {
    try {
      const res = await api.get('/dmfe/history?limit=20');
      setHistory(res.data || []);
    } catch (e) { /* silently ignore */ }
  }, []);

  // ── Initial load ─────────────────────────────────────────────────────────
  useEffect(() => {
    fetchStats();
    fetchPendingQueue();
    fetchBatches();
    fetchHistory();
  }, [fetchStats, fetchPendingQueue, fetchBatches, fetchHistory]);

  // ── Auto-refresh every 5 seconds ─────────────────────────────────────────
  useEffect(() => {
    if (autoRefresh) {
      autoRefreshRef.current = setInterval(() => {
        fetchPendingQueue();
        fetchStats();
      }, 5000);
    } else {
      clearInterval(autoRefreshRef.current);
    }
    return () => clearInterval(autoRefreshRef.current);
  }, [autoRefresh, fetchPendingQueue, fetchStats]);

  // ── Run DMFE Analysis ─────────────────────────────────────────────────────
  const handleRunAnalysis = async () => {
    if (analyzing) return;
    setAnalyzing(true);
    try {
      const res = await api.post('/dmfe/analyze');
      const result = res.data;
      setLastResult(result);
      setCompatBatches(result.compatible_batches || []);
      setRejectedBatches(result.rejected_batches || []);
      setActiveTab('batches');
      await Promise.all([fetchStats(), fetchHistory(), fetchPendingQueue()]);
      toast.success(
        `DMFE Analysis complete: ${result.batches_created} batch${result.batches_created !== 1 ? 'es' : ''} created, ${result.rejected_count} rejected`
      );
    } catch (err) {
      toast.error('DMFE Analysis failed — check server logs');
    } finally {
      setAnalyzing(false);
    }
  };

  // ── Pipeline flow arrow helper ────────────────────────────────────────────
  const FlowArrow = () => (
    <div className="hidden lg:flex items-center justify-center text-gray-600">
      <ArrowRight className="h-6 w-6" />
    </div>
  );

  return (
    <div className="space-y-6 pb-12">
      {/* ── Page Header ─────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <GitBranchPlus className="h-6 w-6 text-indigo-400" />
            Dynamic Multi-Service Feasibility Engine
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Evaluates request combinations for batching feasibility using 8-factor compatibility scoring. No routing performed.
          </p>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-2">
          {/* Auto-refresh toggle */}
          <button
            type="button"
            onClick={() => setAutoRefresh(v => !v)}
            className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium transition-colors border ${
              autoRefresh
                ? 'bg-indigo-600/20 text-indigo-300 border-indigo-500/30'
                : 'bg-gray-800 text-gray-400 border-gray-700 hover:text-gray-200'
            }`}
          >
            {autoRefresh ? <ToggleRight className="h-4 w-4" /> : <ToggleLeft className="h-4 w-4" />}
            Auto-Refresh
          </button>

          {/* Refresh queue */}
          <button
            type="button"
            onClick={() => { fetchPendingQueue(); fetchStats(); fetchBatches(); }}
            className="flex items-center gap-1.5 px-3 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 text-gray-300 font-medium rounded-lg text-xs transition-colors"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Refresh
          </button>

          {/* Run Analysis */}
          <button
            type="button"
            onClick={handleRunAnalysis}
            disabled={analyzing}
            className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-lg text-xs transition-colors shadow-sm disabled:opacity-60 disabled:cursor-not-allowed"
          >
            <Play className={`h-4 w-4 ${analyzing ? 'animate-pulse' : ''}`} />
            {analyzing ? 'Analyzing…' : 'Run DMFE Analysis'}
          </button>
        </div>
      </div>

      {/* ── Statistics Bar ───────────────────────────────────────────────── */}
      <DMFEStatisticsBar stats={stats} lastResult={lastResult} />

      {/* ── Pipeline Flow: Queue → Analysis → Batches ───────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_auto_2fr] gap-4 min-h-[480px]">
        {/* Column 1: Pending Queue */}
        <PendingQueuePanel
          requests={pendingRequests}
          loading={loadingQueue}
          onRefresh={fetchPendingQueue}
        />

        {/* Arrow */}
        <FlowArrow />

        {/* Column 2: Results Area */}
        <div className="flex flex-col gap-4">
          {/* Tabs */}
          <div className="flex items-center border-b border-gray-700 bg-gray-800 rounded-t-xl px-2 pt-1">
            <button
              onClick={() => setActiveTab('batches')}
              className={`flex items-center gap-1.5 py-2.5 px-4 text-xs font-bold border-b-2 transition-colors ${
                activeTab === 'batches'
                  ? 'border-green-500 text-green-400'
                  : 'border-transparent text-gray-400 hover:text-gray-200'
              }`}
            >
              Compatible Batches
              <span className="px-1.5 py-0.5 rounded-full text-[10px] bg-green-500/20 text-green-400 border border-green-500/30">
                {compatBatches.length}
              </span>
            </button>

            <button
              onClick={() => setActiveTab('rejected')}
              className={`flex items-center gap-1.5 py-2.5 px-4 text-xs font-bold border-b-2 transition-colors ${
                activeTab === 'rejected'
                  ? 'border-red-500 text-red-400'
                  : 'border-transparent text-gray-400 hover:text-gray-200'
              }`}
            >
              Rejected
              <span className="px-1.5 py-0.5 rounded-full text-[10px] bg-red-500/20 text-red-400 border border-red-500/30">
                {rejectedBatches.length}
              </span>
            </button>

            <button
              onClick={() => setActiveTab('history')}
              className={`flex items-center gap-1.5 py-2.5 px-4 text-xs font-bold border-b-2 transition-colors ${
                activeTab === 'history'
                  ? 'border-indigo-500 text-indigo-400'
                  : 'border-transparent text-gray-400 hover:text-gray-200'
              }`}
            >
              <History className="h-3.5 w-3.5" />
              Analysis History
              <span className="px-1.5 py-0.5 rounded-full text-[10px] bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
                {history.length}
              </span>
            </button>
          </div>

          {/* Tab Content */}
          {activeTab === 'batches' && (
            <BatchesPanel batches={compatBatches} loading={analyzing} />
          )}

          {activeTab === 'rejected' && (
            <RejectedRequestsPanel rejectedBatches={rejectedBatches} />
          )}

          {activeTab === 'history' && (
            <div className="bg-gray-800 border border-gray-700 rounded-xl shadow-sm overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-700">
                <h3 className="text-sm font-bold text-white">Analysis Run History</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-gray-900/60 border-b border-gray-700 text-[10px] font-bold text-gray-400 uppercase tracking-wider">
                      <th className="py-2.5 px-4">Run #</th>
                      <th className="py-2.5 px-4">Pending</th>
                      <th className="py-2.5 px-4">Pairs Eval.</th>
                      <th className="py-2.5 px-4">Batches</th>
                      <th className="py-2.5 px-4">Rejected</th>
                      <th className="py-2.5 px-4">Avg Score</th>
                      <th className="py-2.5 px-4">Threshold</th>
                      <th className="py-2.5 px-4">Run At</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-700 text-xs">
                    {history.length === 0 ? (
                      <tr>
                        <td colSpan="8" className="py-8 text-center text-gray-500">
                          No analysis runs recorded yet. Click "Run DMFE Analysis" to begin.
                        </td>
                      </tr>
                    ) : (
                      history.map((run) => (
                        <tr key={run.id} className="hover:bg-gray-750/40 transition-colors">
                          <td className="py-2.5 px-4 font-mono font-bold text-indigo-400">#{run.id}</td>
                          <td className="py-2.5 px-4 text-gray-300">{run.total_pending}</td>
                          <td className="py-2.5 px-4 text-gray-300">{run.total_evaluated_pairs}</td>
                          <td className="py-2.5 px-4 font-bold text-green-400">{run.batches_created}</td>
                          <td className="py-2.5 px-4 font-bold text-red-400">{run.rejected_count}</td>
                          <td className="py-2.5 px-4 font-mono font-bold text-amber-400">
                            {run.avg_compatibility_score?.toFixed(1)}%
                          </td>
                          <td className="py-2.5 px-4 font-mono text-gray-400">≥{run.threshold_used}%</td>
                          <td className="py-2.5 px-4 font-mono text-gray-500 text-[11px]">{run.run_at}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
