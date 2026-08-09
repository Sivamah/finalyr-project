import React, { useState, useEffect } from 'react';
import { Cpu, Play, List, RefreshCw, Lightbulb, TrendingUp, DollarSign, Clock, Leaf, Route, Gauge } from 'lucide-react';
import api from '../services/api';
import toast from 'react-hot-toast';

import PageHeader from '../components/ui/PageHeader';

export default function AIDashboard() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [selected, setSelected] = useState(null);

  useEffect(() => { fetchResults(); }, []);

  const fetchResults = async () => {
    try {
      const res = await api.get('/orchestration/results?limit=20');
      setResults(res.data);
    } catch { toast.error('Failed to load results'); }
    finally { setLoading(false); }
  };

  const runOptimization = async () => {
    setRunning(true);
    try {
      await api.post('/orchestration/simulate?count=15');
      const res = await api.post('/orchestration/optimize');
      setResults(res.data);
      toast.success(`Optimization complete: ${res.data.length} batches`);
      setSelected(null);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Optimization failed. Ensure providers and vehicles exist.');
    }
    finally { setRunning(false); }
  };

  const scoreColor = (score) => {
    if (score >= 80) return 'text-green-400';
    if (score >= 60) return 'text-amber-400';
    return 'text-red-400';
  };

  return (
    <div className="pb-10 max-w-[1500px] mx-auto">
      <PageHeader
        eyebrow="Intelligence"
        title="Orchestration Engine"
        description="Dynamic Multi-Service Feasibility Engine — batch requests by compatibility and let OR-Tools route them."
        actions={
          <div className="flex gap-2.5">
            <button onClick={fetchResults} className="btn-glass">
              <RefreshCw className="h-4 w-4" /> Refresh
            </button>
            <button onClick={runOptimization} disabled={running} className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed">
              {running ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              {running ? 'Running…' : 'Run Optimization'}
            </button>
          </div>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 mb-6">
        <div className="lg:col-span-3 bg-gray-800 border border-gray-700 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2"><List className="h-5 w-5 text-indigo-400" /> Optimization Results</h2>
          {loading ? (
            <div className="flex items-center justify-center h-48"><div className="animate-spin rounded-full h-8 w-8 border-t-2 border-indigo-500" /></div>
          ) : results.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <Cpu className="h-12 w-12 mx-auto mb-3 opacity-50" />
              <p className="text-lg font-medium">No optimizations yet</p>
              <p className="text-sm">Click "Run Optimization" to start the AI engine</p>
            </div>
          ) : (
            <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
              {results.map((r) => (
                <div key={r.id} onClick={() => setSelected(selected?.id === r.id ? null : r)} className={`bg-gray-700/50 rounded-xl p-4 cursor-pointer transition-all border ${selected?.id === r.id ? 'border-indigo-500' : 'border-transparent hover:border-gray-600'}`}>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className={`text-lg font-bold ${scoreColor(r.optimization_score)}`}>{r.optimization_score}</span>
                      <span className="text-xs text-gray-500">score</span>
                    </div>
                    <div className="flex items-center gap-3 text-sm text-gray-400">
                      <span className="flex items-center gap-1"><DollarSign className="h-3.5 w-3.5" />₹{r.estimated_cost}</span>
                      <span className="flex items-center gap-1"><Clock className="h-3.5 w-3.5" />{r.eta_mins}min</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="px-2 py-0.5 rounded text-xs font-medium bg-blue-900 text-blue-300">{r.chosen_provider}</span>
                    <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-600 text-gray-300">{r.chosen_vehicle}</span>
                    <span className="text-xs text-gray-500">{r.request_count} requests</span>
                  </div>
                  <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                    <span className="flex items-center gap-1"><Route className="h-3 w-3" />{r.distance_saved_km}km saved</span>
                    <span className="flex items-center gap-1"><Leaf className="h-3 w-3" />{r.co2_saved_kg}kg CO₂</span>
                  </div>
                  {selected?.id === r.id && r.explanation_json && (
                    <div className="mt-3 pt-3 border-t border-gray-600 text-xs text-gray-400 space-y-1">
                      <p className="text-indigo-400 font-medium flex items-center gap-1"><Lightbulb className="h-3 w-3" /> Explanation</p>
                      {typeof r.explanation_json === 'object' ? (
                        Object.entries(r.explanation_json).map(([k, v]) => (
                          <p key={k}><span className="text-gray-500 capitalize">{k.replace(/_/g, ' ')}:</span> {String(v)}</p>
                        ))
                      ) : (
                        <p className="whitespace-pre-wrap">{String(r.explanation_json)}</p>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="lg:col-span-2 bg-gray-800 border border-gray-700 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2"><TrendingUp className="h-5 w-5 text-indigo-400" /> AI Engine Overview</h2>
          <div className="space-y-4">
            <div className="bg-gray-700/50 rounded-lg p-4">
              <div className="flex items-center gap-3 text-sm text-gray-300">
                <Gauge className="h-5 w-5 text-indigo-400" />
                <div>
                  <p className="font-medium text-white">Google OR-Tools VRP</p>
                  <p className="text-xs text-gray-500">Vehicle Routing Problem with Pickup & Delivery</p>
                </div>
              </div>
            </div>
            <div className="bg-gray-700/50 rounded-lg p-4">
              <div className="flex items-center gap-3 text-sm text-gray-300">
                <Route className="h-5 w-5 text-green-400" />
                <div>
                  <p className="font-medium text-white">Route Optimization</p>
                  <p className="text-xs text-gray-500">Haversine-based distance matrix + capacity constraints</p>
                </div>
              </div>
            </div>
            <div className="bg-gray-700/50 rounded-lg p-4">
              <div className="flex items-center gap-3 text-sm text-gray-300">
                <Leaf className="h-5 w-5 text-emerald-400" />
                <div>
                  <p className="font-medium text-white">Environmental Impact</p>
                  <p className="text-xs text-gray-500">CO₂ reduction & fuel savings calculation</p>
                </div>
              </div>
            </div>
            <div className="bg-gray-700/50 rounded-lg p-4">
              <div className="flex items-center gap-3 text-sm text-gray-300">
                <Lightbulb className="h-5 w-5 text-amber-400" />
                <div>
                  <p className="font-medium text-white">Explainable AI (XAI)</p>
                  <p className="text-xs text-gray-500">Weighted scoring with route similarity, delay, capacity, environmental, workload factors</p>
                </div>
              </div>
            </div>
            <div className="bg-gray-700/50 rounded-lg p-4">
              <div className="flex items-center gap-3 text-sm">
                <DollarSign className="h-5 w-5 text-green-400" />
                <div>
                  <p className="font-medium text-white">Cost Estimation</p>
                  <p className="text-xs text-gray-500">Per-vehicle cost per km with provider-specific pricing</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
