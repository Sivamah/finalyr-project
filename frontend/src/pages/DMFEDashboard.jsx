import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Play, RefreshCw, ArrowRight, History, Layers, XCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import toast from 'react-hot-toast';
import api from '../services/api';

import PageHeader from '../components/ui/PageHeader';
import DMFEStatisticsBar from '../components/dmfe/DMFEStatisticsBar';
import PendingQueuePanel from '../components/dmfe/PendingQueuePanel';
import BatchesPanel from '../components/dmfe/BatchesPanel';
import RejectedRequestsPanel from '../components/dmfe/RejectedRequestsPanel';

export default function DMFEDashboard() {
  const [stats, setStats] = useState({});
  const [pendingRequests, setPending] = useState([]);
  const [lastResult, setLastResult] = useState(null);
  const [compatBatches, setCompatBatches] = useState([]);
  const [rejectedBatches, setRejectedBatches] = useState([]);
  const [history, setHistory] = useState([]);

  const [analyzing, setAnalyzing] = useState(false);
  const [loadingQueue, setLoadingQueue] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [activeTab, setActiveTab] = useState('batches');
  const [demoMode, setDemoMode] = useState(false);
  const [seeding, setSeeding] = useState(false);

  const autoRefreshRef = useRef(null);

  const fetchStats = useCallback(async () => {
    try {
      const res = await api.get('/dmfe/statistics');
      setStats(res.data || {});
    } catch { /* silent */ }
  }, []);

  const fetchPendingQueue = useCallback(async () => {
    setLoadingQueue(true);
    try {
      const demoParam = demoMode ? '&demo_only=true' : '';
      const res = await api.get(`/simulation/queue?limit=50${demoParam}`);
      setPending(res.data?.items || []);
    } catch {
      setPending([]);
    } finally {
      setLoadingQueue(false);
    }
  }, [demoMode]);

  const fetchBatches = useCallback(async () => {
    try {
      const demoParam = demoMode ? '&demo_only=true' : '';
      // The pipeline dispatches analysis batches (Pending -> Dispatched), so
      // a Pending-only fetch makes the "Compatible Batches" tab go empty the
      // moment a run completes.  Show both so created batches stay visible.
      const [compatRes, dispatchedRes, rejRes] = await Promise.all([
        api.get(`/dmfe/batches?status=Pending&limit=50${demoParam}`),
        api.get(`/dmfe/batches?status=Dispatched&limit=50${demoParam}`),
        api.get(`/dmfe/batches?status=Rejected&limit=50${demoParam}`),
      ]);
      const merged = [...(compatRes.data || []), ...(dispatchedRes.data || [])];
      const seen = new Set();
      const deduped = [];
      // Solo ("Individual") rows are persisted LAST in each run
      // (decision_engine.py Phase 9), so they always carry the highest ids.
      // Sorting by id alone therefore buries every shared batch below every
      // solo trip and the tab looks like it produced nothing but solo trips.
      // Rank shared batches first, then newest-first within each group.
      const rank = (b) => (b.decision === 'Compatible' ? 0 : 1);
      const byRankThenId = (x, y) => rank(x) - rank(y) || (y.id || 0) - (x.id || 0);
      for (const b of merged.sort(byRankThenId)) {
        if (!seen.has(b.id)) {
          seen.add(b.id);
          deduped.push(b);
        }
      }
      setCompatBatches(deduped);
      setRejectedBatches(rejRes.data || []);
    } catch { /* silent */ }
  }, [demoMode]);

  const fetchHistory = useCallback(async () => {
    try {
      const res = await api.get('/dmfe/history?limit=20');
      setHistory(res.data || []);
    } catch { /* silent */ }
  }, []);

  useEffect(() => {
    fetchStats();
    fetchPendingQueue();
    fetchBatches();
    fetchHistory();
  }, [fetchStats, fetchPendingQueue, fetchBatches, fetchHistory]);

  useEffect(() => {
    if (autoRefresh) {
      autoRefreshRef.current = setInterval(() => {
        if (document.visibilityState !== 'visible') return;
        fetchPendingQueue();
        fetchStats();
      }, 5000);
    } else {
      clearInterval(autoRefreshRef.current);
    }
    return () => clearInterval(autoRefreshRef.current);
  }, [autoRefresh, fetchPendingQueue, fetchStats]);

  /**
   * Demo Mode filters the queue and the batch list to requests tagged
   * "[A-DMFE Demo Scenario]" on pickup_address. Nothing in the application
   * used to create such a row — the only producer was the standalone script
   * backend/scripts/verify_demo.py — so the toggle always showed two empty
   * panels. This seeds the curated scenario through POST /api/dmfe/demo/seed.
   *
   * The seeded rows are ordinary Pending requests: the engine scores them with
   * the same code path as live traffic, so the demo shows real behaviour.
   */
  const handleSeedDemo = async () => {
    if (seeding) return;
    setSeeding(true);
    try {
      const res = await api.post('/dmfe/demo/seed');
      toast.success(res.data?.message || 'Demo scenario seeded');
      await Promise.all([fetchPendingQueue(), fetchBatches(), fetchStats()]);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not seed the demo scenario');
    } finally {
      setSeeding(false);
    }
  };

  const handleClearDemo = async () => {
    if (seeding) return;
    setSeeding(true);
    try {
      const res = await api.delete('/dmfe/demo/clear');
      toast.success(res.data?.message || 'Demo requests cleared');
      await Promise.all([fetchPendingQueue(), fetchBatches(), fetchStats()]);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Could not clear the demo scenario');
    } finally {
      setSeeding(false);
    }
  };

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
    } catch {
      toast.error('DMFE Analysis failed — check server logs');
    } finally {
      setAnalyzing(false);
    }
  };

  const TABS = [
    { id: 'batches', label: 'Created Batches', icon: Layers, count: compatBatches.length },
    { id: 'rejected', label: 'Rejected', icon: XCircle, count: rejectedBatches.length },
    { id: 'history', label: 'Analysis History', icon: History, count: history.length },
  ];

  return (
    <div className="space-y-7 max-w-[1500px] mx-auto">
      <PageHeader
        eyebrow="Requests"
        title="Feasibility Engine"
        description="The Adaptive Dynamic Multi-Service Feasibility Engine scores request pairings across 8 compatibility factors before routing."
        actions={
          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={() => setDemoMode((v) => !v)}
              className={`btn-glass ${demoMode ? '!text-amber-400 !border-amber-400/50 !bg-amber-400/10' : ''}`}
            >
              <span className={`relative flex h-1.5 w-1.5 ${demoMode ? '' : 'opacity-50'}`}>
                <span className={`absolute inline-flex h-full w-full rounded-full animate-ping ${demoMode ? 'bg-amber-400' : 'bg-brand-text-muted'}`} />
                <span className={`relative inline-flex rounded-full h-1.5 w-1.5 ${demoMode ? 'bg-amber-400' : 'bg-brand-text-muted'}`} />
              </span>
              Demo Mode {demoMode ? 'On' : 'Off'}
            </button>

            <button
              type="button"
              onClick={() => setAutoRefresh((v) => !v)}
              className={`btn-glass ${autoRefresh ? '!text-brand-secondary !border-brand-secondary/40 !bg-brand-secondary/10' : ''}`}
            >
              <span className={`relative flex h-1.5 w-1.5 ${autoRefresh ? '' : 'opacity-50'}`}>
                <span className={`absolute inline-flex h-full w-full rounded-full animate-ping ${autoRefresh ? 'bg-brand-secondary' : 'bg-brand-text-muted'}`} />
                <span className={`relative inline-flex rounded-full h-1.5 w-1.5 ${autoRefresh ? 'bg-brand-secondary' : 'bg-brand-text-muted'}`} />
              </span>
              Auto-Refresh {autoRefresh ? 'On' : 'Off'}
            </button>

            <button
              type="button"
              onClick={() => { fetchPendingQueue(); fetchStats(); fetchBatches(); }}
              className="btn-glass"
            >
              <RefreshCw className="h-3.5 w-3.5" /> Refresh
            </button>

            <button
              type="button"
              onClick={handleRunAnalysis}
              disabled={analyzing}
              className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Play className={`h-4 w-4 ${analyzing ? 'animate-pulse' : ''}`} />
              {analyzing ? 'Analyzing…' : 'Run Analysis'}
            </button>
          </div>
        }
      />

      {demoMode && (
        <div className="bg-amber-500/15 border border-amber-500/30 text-amber-400 px-4 py-3 rounded-lg flex flex-wrap items-center justify-center gap-x-4 gap-y-2 text-sm shadow-sm">
          <span className="font-bold tracking-wide">
            ⚠️ DEMO MODE — showing the curated scenario only
          </span>
          <span className="text-amber-400/70 text-[12px]">
            {pendingRequests.length === 0
              ? 'No demo requests in the queue yet — seed the scenario to populate it.'
              : `${pendingRequests.length} demo request${pendingRequests.length !== 1 ? 's' : ''} pending. Run Analysis to batch them.`}
          </span>
          <span className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleSeedDemo}
              disabled={seeding}
              className="btn-glass !text-amber-300 !border-amber-400/50 !bg-amber-400/10 disabled:opacity-50"
            >
              {seeding ? 'Working…' : 'Seed demo scenario'}
            </button>
            <button
              type="button"
              onClick={handleClearDemo}
              disabled={seeding}
              className="btn-glass !text-amber-300/70 !border-amber-400/30 disabled:opacity-50"
            >
              Clear
            </button>
          </span>
        </div>
      )}

      <DMFEStatisticsBar stats={stats} lastResult={lastResult} />

      {/* ── Pipeline: Queue → Analysis → Results ─────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_auto_2fr] gap-5 min-h-[480px]">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
          className="min-h-full"
        >
          <PendingQueuePanel requests={pendingRequests} loading={loadingQueue} onRefresh={fetchPendingQueue} />
        </motion.div>

        <div className="hidden lg:flex items-center justify-center">
          <div className="flex flex-col items-center gap-1 text-brand-text-muted">
            <motion.div
              animate={{ x: [0, 6, 0] }}
              transition={{ duration: 2.4, repeat: Infinity, ease: 'easeInOut' }}
            >
              <ArrowRight className="h-5 w-5 text-brand-primary/60" />
            </motion.div>
            <span className="text-[10px] uppercase tracking-[0.18em] font-semibold">Analyze</span>
          </div>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1], delay: 0.1 }}
          className="flex flex-col gap-5 min-h-full"
        >
          {/* Tab pills */}
          <div className="glass-panel rounded-[18px] p-1.5 flex items-center gap-1.5 w-fit">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`tab-pill ${activeTab === tab.id ? 'tab-pill-active' : ''}`}
              >
                <tab.icon className="h-4 w-4" />
                {tab.label}
                <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-bold ${
                  activeTab === tab.id ? 'bg-white/15 text-white' : 'bg-white/[0.06] text-brand-text-muted'
                }`}>
                  {tab.count}
                </span>
              </button>
            ))}
          </div>

          <div className="flex-1">
            <AnimatePresence mode="wait">
              <motion.div
                key={activeTab}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
              >
                {activeTab === 'batches' && <BatchesPanel batches={compatBatches} loading={analyzing} />}
                {activeTab === 'rejected' && <RejectedRequestsPanel rejectedBatches={rejectedBatches} />}
                {activeTab === 'history' && (
                  <div className="surface-card rounded-[22px] overflow-hidden">
                    <div className="px-5 py-4 border-b border-white/[0.06] flex items-center justify-between">
                      <h3 className="text-[13px] font-semibold text-white">Analysis Run History</h3>
                      <span className="text-[11px] text-brand-text-muted font-mono">{history.length} runs</span>
                    </div>
                    <div className="overflow-x-auto custom-scrollbar">
                      <table className="table-glass">
                        <thead>
                          <tr>
                            <th>Run</th>
                            <th>Pending</th>
                            <th>Pairs Eval.</th>
                            <th>Batches</th>
                            <th>Rejected</th>
                            <th>Avg Score</th>
                            <th>Threshold</th>
                            <th>Run At</th>
                          </tr>
                        </thead>
                        <tbody>
                          {history.length === 0 ? (
                            <tr>
                              <td colSpan="8" className="py-10 text-center text-brand-text-muted">
                                No analysis runs recorded yet. Run the engine to begin.
                              </td>
                            </tr>
                          ) : (
                            history.map((run) => (
                              <tr key={run.id}>
                                <td className="font-mono font-semibold text-brand-primary">#{run.id}</td>
                                <td>{run.total_pending}</td>
                                <td>{run.total_evaluated_pairs}</td>
                                <td className="font-semibold text-brand-success">{run.batches_created}</td>
                                <td className="font-semibold text-brand-danger">{run.rejected_count}</td>
                                <td className="font-mono font-semibold text-brand-warning">
                                  {run.avg_compatibility_score?.toFixed(1)}%
                                </td>
                                <td className="font-mono">≥{run.threshold_used}%</td>
                                <td className="font-mono text-[11px] text-brand-text-muted">{run.run_at}</td>
                              </tr>
                            ))
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
              </motion.div>
            </AnimatePresence>
          </div>
        </motion.div>
      </div>
    </div>
  );
}