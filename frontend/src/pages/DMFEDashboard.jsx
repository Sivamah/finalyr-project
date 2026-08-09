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
      const res = await api.get('/simulation/queue?limit=50');
      setPending(res.data?.items || []);
    } catch {
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
      if (!lastResult) {
        setCompatBatches(compatRes.data || []);
        setRejectedBatches(rejRes.data || []);
      }
    } catch { /* silent */ }
  }, [lastResult]);

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
    { id: 'batches', label: 'Compatible Batches', icon: Layers, count: compatBatches.length },
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