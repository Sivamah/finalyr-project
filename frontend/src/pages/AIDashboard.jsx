import React, { useState, useEffect, useCallback } from 'react';
import {
  Cpu, Play, List, RefreshCw, IndianRupee, Clock, Leaf, Route,
  Gauge, ShieldCheck, CheckCircle2, XCircle, ArrowRight,
  Info
} from 'lucide-react';
import api from '../services/api';
import toast from 'react-hot-toast';

import PageHeader from '../components/ui/PageHeader';
import OrchestrationDetailsDrawer from '../components/orchestration/OrchestrationDetailsDrawer';
import { formatINR } from '../utils/currencyUtils';

export default function AIDashboard() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [activeFilter, setActiveFilter] = useState('all'); // 'all' | 'accepted' | 'rejected'
  const [selectedResult, setSelectedResult] = useState(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const fetchResults = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get(`/orchestration/results?limit=50&status_filter=${activeFilter}`);
      setResults(res.data || []);
    } catch {
      toast.error('Failed to load orchestration results');
    } finally {
      setLoading(false);
    }
  }, [activeFilter]);

  useEffect(() => {
    fetchResults();
  }, [fetchResults]);

  /**
   * Runs the A-DMFE pipeline — rule-based & adaptive multi-service feasibility
   * analysis followed by OR-Tools route optimization.
   */
  const runOptimization = async () => {
    setRunning(true);
    try {
      // Seed queue only if empty
      const queue = await api.get('/simulation/queue?limit=1');
      if ((queue.data?.items?.length ?? 0) === 0) {
        await api.post('/orchestration/simulate?count=15');
      }

      const res = await api.post('/dmfe/analyze');
      const created = res.data?.batches_created ?? 0;
      const rejected = res.data?.rejected_count ?? 0;

      await fetchResults();
      toast.success(
        `A-DMFE run complete: ${created} batch${created !== 1 ? 'es' : ''} created, ${rejected} rejected`
      );
    } catch (err) {
      toast.error(
        err.response?.data?.detail || 'A-DMFE run failed. Ensure providers, vehicles and drivers exist.'
      );
    } finally {
      setRunning(false);
    }
  };

  const scoreColor = (score) => {
    if (score >= 80) return 'text-brand-success';
    if (score >= 60) return 'text-brand-warning';
    return 'text-brand-danger';
  };

  const handleOpenDetails = (r) => {
    setSelectedResult(r);
    setIsDrawerOpen(true);
  };

  const acceptedCount = results.filter((r) => r.decision !== 'Rejected' && r.status !== 'Rejected').length;
  const rejectedCount = results.filter((r) => r.decision === 'Rejected' || r.status === 'Rejected').length;

  return (
    <div className="pb-10 max-w-[1500px] mx-auto">
      <PageHeader
        eyebrow="Intelligence"
        title="Orchestration Engine"
        description="Routing output of the A-DMFE engine — compatible requests batched, then routed by OR-Tools. Scoring decisions are shown on the Feasibility Engine page."
        actions={
          <div className="flex gap-2.5">
            <button onClick={fetchResults} className="btn-glass">
              <RefreshCw className="h-4 w-4" /> Refresh
            </button>
            <button
              onClick={runOptimization}
              disabled={running}
              className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {running ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              {running ? 'Running…' : 'Run Optimization'}
            </button>
          </div>
        }
      />

      {/* COMPACT INFORMATIONAL SECTION: HOW A-DMFE WORKS */}
      <div className="mb-6 glass-card rounded-2xl p-5 shadow-sm border border-brand-primary/20">
        <div className="flex items-start gap-3.5">
          <div className="p-2 rounded-xl bg-brand-primary/10 border border-brand-primary/20 text-brand-primary shrink-0 mt-0.5">
            <Info className="h-5 w-5" />
          </div>
          <div className="space-y-1">
            <h3 className="text-sm font-bold text-white tracking-tight flex items-center gap-2">
              How A-DMFE Orchestration Works
              <span className="text-[10px] px-2 py-0.5 rounded font-mono font-medium bg-brand-primary/15 text-brand-primary border border-brand-primary/30">
                Rule-Based Feasibility & OR-Tools Routing
              </span>
            </h3>
            <p className="text-xs text-gray-300 leading-relaxed">
              A-DMFE first checks whether service requests are feasible to combine based on compatibility factors
              such as pickup proximity, route similarity, time compatibility, capacity, and priority. Feasible requests
              are grouped into a batch. The resulting batch is then assigned to an available driver/vehicle and routed
              using OR-Tools.
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-5 mb-6">
        {/* LEFT COLUMN: OPTIMIZATION RESULTS LIST */}
        <div className="lg:col-span-3 glass-panel shadow-[0_10px_40px_rgba(5,8,22,0.6)] border border-white/[0.1] rounded-2xl p-6 flex flex-col">
          {/* Header & Filter Tabs */}
          <div className="flex items-center justify-between gap-4 mb-4 flex-wrap">
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <List className="h-5 w-5 text-brand-primary" />
              Optimization Results
              <span className="text-xs px-2 py-0.5 rounded-full bg-white/10 text-brand-text-muted font-mono font-bold">
                {results.length}
              </span>
            </h2>

            {/* Filter Buttons */}
            <div className="flex items-center gap-1.5 bg-black/20 p-1 rounded-xl border border-white/5 text-xs">
              <button
                onClick={() => setActiveFilter('all')}
                className={`px-3 py-1 rounded-lg font-medium transition-all ${
                  activeFilter === 'all'
                    ? 'bg-brand-primary/20 text-brand-primary shadow-sm border border-brand-primary/30'
                    : 'text-brand-text-muted hover:text-white border border-transparent'
                }`}
              >
                All Results
              </button>
              <button
                onClick={() => setActiveFilter('accepted')}
                className={`px-3 py-1 rounded-lg font-medium transition-all ${
                  activeFilter === 'accepted'
                    ? 'bg-brand-success/20 text-brand-success shadow-sm border border-brand-success/30'
                    : 'text-brand-text-muted hover:text-white border border-transparent'
                }`}
              >
                Accepted ({acceptedCount})
              </button>
              <button
                onClick={() => setActiveFilter('rejected')}
                className={`px-3 py-1 rounded-lg font-medium transition-all ${
                  activeFilter === 'rejected'
                    ? 'bg-brand-danger/20 text-brand-danger shadow-sm border border-brand-danger/30'
                    : 'text-brand-text-muted hover:text-white border border-transparent'
                }`}
              >
                Rejected ({rejectedCount})
              </button>
            </div>
          </div>

          {/* Results List */}
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-indigo-500" />
            </div>
          ) : results.length === 0 ? (
            <div className="text-center py-16 text-gray-500">
              <Cpu className="h-12 w-12 mx-auto mb-3 opacity-40" />
              <p className="text-base font-medium text-gray-400">No optimizations found</p>
              <p className="text-xs mt-1">
                {activeFilter !== 'all'
                  ? `No ${activeFilter} results in current view. Switch filter or run optimization.`
                  : 'Click "Run Optimization" above to process pending requests.'}
              </p>
            </div>
          ) : (
            <div className="space-y-3 overflow-y-auto max-h-[640px] pr-1.5 custom-scrollbar">
              {results.map((r) => {
                const isAccepted = r.decision !== 'Rejected' && r.status !== 'Rejected';

                return (
                    <div
                      key={r.id}
                      className={`glass-card rounded-xl p-4 transition-all border ${
                        isAccepted
                          ? 'border-white/10 hover:border-white/20'
                          : 'border-brand-danger/25 bg-brand-danger/10 hover:border-brand-danger/40'
                      }`}
                    >
                      {/* Card Top Row: Score + Decision + Cost + Duration */}
                      <div className="flex items-center justify-between gap-3 mb-2.5">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className={`text-lg font-bold font-mono ${scoreColor(r.optimization_score)}`}>
                            {r.optimization_score !== undefined ? Number(r.optimization_score).toFixed(0) : '—'}
                          </span>
                          <span className="text-[11px] text-brand-text-muted font-medium">score</span>

                          {isAccepted ? (
                            <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded font-bold bg-brand-success/15 text-brand-success border border-brand-success/30">
                              <CheckCircle2 className="h-3 w-3" /> Feasible
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded font-bold bg-brand-danger/15 text-brand-danger border border-brand-danger/30">
                              <XCircle className="h-3 w-3" /> Rejected
                            </span>
                          )}

                          <span className="text-[11px] font-mono text-brand-text-muted">
                            {r.batch_id}
                          </span>
                        </div>

                        <div className="flex items-center gap-3 text-xs font-mono">
                          {isAccepted ? (
                            <>
                              <span className="flex items-center gap-0.5 text-brand-success font-bold">
                                {formatINR(r.estimated_cost)}
                              </span>
                              <span className="flex items-center gap-1 text-white/80">
                                <Clock className="h-3.5 w-3.5 text-brand-text-muted" />
                                {r.eta_mins}min
                              </span>
                            </>
                          ) : (
                            <span className="text-brand-text-muted text-[11px]">Not dispatched</span>
                          )}
                        </div>
                      </div>

                    {/* Card Middle Row: Provider, Vehicle, Requests */}
                    <div className="flex items-center justify-between gap-2 flex-wrap">
                      <div className="flex items-center gap-2 flex-wrap">
                        {isAccepted ? (
                          <>
                            <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-brand-primary/20 text-brand-primary border border-brand-primary/40">
                              {r.chosen_provider || 'Default Provider'}
                            </span>
                            <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-white/10 text-white border border-white/20">
                              {r.chosen_vehicle || 'Vehicle Assigned'}
                            </span>
                          </>
                        ) : (
                          <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-brand-danger/20 text-brand-danger border border-brand-danger/30">
                            Failed Gate
                          </span>
                        )}

                        <span className="text-xs text-brand-text-muted">
                          {r.request_count} request{r.request_count !== 1 ? 's' : ''}
                        </span>
                      </div>

                      {/* Explicit "Details →" Action Button */}
                      <button
                        type="button"
                        onClick={() => handleOpenDetails(r)}
                        className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold text-brand-primary hover:text-white bg-brand-primary/10 hover:bg-brand-primary/20 border border-brand-primary/30 transition-all ml-auto"
                      >
                        Details
                        <ArrowRight className="h-3.5 w-3.5" />
                      </button>
                    </div>

                    {/* Card Bottom Row: Savings / Rejection snippet */}
                    {isAccepted ? (
                      <div className="flex items-center gap-4 mt-2.5 pt-2 border-t border-white/5 text-[11px] text-brand-text-muted">
                        <span className="flex items-center gap-1">
                          <Route className="h-3 w-3 text-brand-primary" />
                          {r.distance_saved_km}km saved
                        </span>
                        <span className="flex items-center gap-1">
                          <Leaf className="h-3 w-3 text-brand-success" />
                          {r.co2_saved_kg}kg CO₂
                        </span>
                      </div>
                    ) : (
                      <div className="mt-2.5 pt-2 border-t border-brand-danger/20 text-[11px] text-brand-danger/80 truncate">
                        Reason: {r.failed_gate || 'Incompatible constraints'}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* RIGHT COLUMN: A-DMFE ENGINE ARCHITECTURE & PIPELINE */}
        <div className="lg:col-span-2 space-y-4">
          <div className="glass-panel shadow-[0_10px_40px_rgba(5,8,22,0.6)] border border-white/[0.1] rounded-2xl p-6">
            <h2 className="text-base font-bold text-white mb-4 flex items-center gap-2">
              <ShieldCheck className="h-5 w-5 text-brand-primary" />
              A-DMFE Decision Pipeline
            </h2>

            {/* Accurate 7-stage flowchart */}
            <div className="space-y-2 mb-6">
              {[
                { title: '1. Incoming Requests', desc: 'Ride, Food, and Parcel bookings enter pending pool' },
                { title: '2. A-DMFE Feasibility Analysis', desc: 'Pairwise geometric, temporal & capacity gating' },
                { title: '3. Compatibility Scoring', desc: 'Weighted scoring across proximity, route, and time' },
                { title: '4. Batch Formation', desc: 'Optimal grouping of compatible service requests' },
                { title: '5. Driver & Vehicle Selection', desc: 'Availability, vehicle capacity and proximity match' },
                { title: '6. OR-Tools Route Optimization', desc: 'VRP stop sequencing for minimum detour' },
                { title: '7. Final Orchestration Result', desc: 'Dispatched trip with cost in ₹ & CO₂ savings' },
              ].map((step, idx) => (
                <div key={idx} className="flex items-start gap-3 glass-card rounded-xl p-3 border border-white/5">
                  <div className="h-6 w-6 rounded-full bg-brand-primary/20 text-brand-primary border border-brand-primary/30 flex items-center justify-center text-xs font-mono font-bold shrink-0 mt-0.5">
                    {idx + 1}
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-semibold text-white">{step.title}</p>
                    <p className="text-[11px] text-brand-text-muted mt-0.5">{step.desc}</p>
                  </div>
                </div>
              ))}
            </div>

            <div className="border-t border-white/10 pt-4 space-y-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-brand-text-muted">
                Core Engine Technologies
              </h3>

              <div className="bg-white/5 rounded-xl p-3 border border-white/5 flex items-start gap-3">
                <Gauge className="h-4 w-4 text-brand-primary mt-0.5 shrink-0" />
                <div className="text-xs">
                  <p className="font-semibold text-white">Google OR-Tools VRP</p>
                  <p className="text-[11px] text-brand-text-muted mt-0.5">
                    Vehicle Routing Problem with Pickup & Delivery solving optimal stop order.
                  </p>
                </div>
              </div>

              <div className="bg-white/5 rounded-xl p-3 border border-white/5 flex items-start gap-3">
                <IndianRupee className="h-4 w-4 text-brand-success mt-0.5 shrink-0" />
                <div className="text-xs">
                  <p className="font-semibold text-white">Indian Rupee (₹) Cost Tariffs</p>
                  <p className="text-[11px] text-brand-text-muted mt-0.5">
                    Configured per-kilometer tariffs with provider-specific commission rates.
                  </p>
                </div>
              </div>

              <div className="bg-white/5 rounded-xl p-3 border border-white/5 flex items-start gap-3">
                <Leaf className="h-4 w-4 text-brand-success mt-0.5 shrink-0" />
                <div className="text-xs">
                  <p className="font-semibold text-white">Environmental Footprint Model</p>
                  <p className="text-[11px] text-brand-text-muted mt-0.5">
                    2.3 kg CO₂ saved per litre of fuel saved through shared multi-modal batching.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* INTERACTIVE DETAILS DRAWER */}
      <OrchestrationDetailsDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        result={selectedResult}
      />
    </div>
  );
}
