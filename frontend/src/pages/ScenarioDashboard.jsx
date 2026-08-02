import React, { useState, useEffect, useCallback } from 'react';
import { Film, Save, Play, Scale, Layers, Search, Filter, RotateCcw, Download } from 'lucide-react';
import api from '../services/api';
import toast from 'react-hot-toast';

import ScenarioDashboardOverview from '../components/playback/ScenarioDashboardOverview';
import SavedSimulationsTable from '../components/playback/SavedSimulationsTable';
import SimulationReplayPlayer from '../components/playback/SimulationReplayPlayer';
import ScenarioComparison from '../components/playback/ScenarioComparison';
import ScenarioManager from '../components/playback/ScenarioManager';

export default function ScenarioDashboard() {
  const [activeTab, setActiveTab] = useState('saved'); // 'saved' | 'comparison' | 'scenarios'

  const [search, setSearch] = useState('');
  const [filterScenario, setFilterScenario] = useState('All');

  const [overview, setOverview] = useState({});
  const [simulations, setSimulations] = useState([]);
  const [scenarios, setScenarios] = useState([]);
  const [selectedForCompare, setSelectedForCompare] = useState([]); // array of 2 sim IDs
  const [comparisonResult, setComparisonResult] = useState(null);

  const [replaySimulation, setReplaySimulation] = useState(null);
  const [showSaveModal, setShowSaveModal] = useState(false);
  const [saveName, setSaveName] = useState('');
  const [saveScenario, setSaveScenario] = useState('Standard Baseline Run');

  // Fetch all playback data
  const fetchData = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (search) params.append('search', search);
      if (filterScenario !== 'All') params.append('scenario', filterScenario);

      const [overviewRes, simListRes, scenRes] = await Promise.all([
        api.get('/simulation/saved/dashboard'),
        api.get(`/simulation/saved?${params.toString()}`),
        api.get('/scenarios'),
      ]);

      setOverview(overviewRes.data || {});
      setSimulations(simListRes.data || []);
      setScenarios(scenRes.data || []);
    } catch (err) {
      console.error('Failed to fetch playback data:', err);
    }
  }, [search, filterScenario]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Checkbox toggle for comparison (max 2 items)
  const handleToggleCompare = (simId) => {
    if (selectedForCompare.includes(simId)) {
      setSelectedForCompare((prev) => prev.filter((id) => id !== simId));
    } else {
      if (selectedForCompare.length >= 2) {
        toast.error('You can select a maximum of 2 simulations for side-by-side comparison');
        return;
      }
      setSelectedForCompare((prev) => [...prev, simId]);
    }
  };

  // Perform Side-by-Side Comparison
  const handleCompareClick = async () => {
    if (selectedForCompare.length !== 2) {
      toast.error('Please select exactly 2 simulations from the table to compare');
      return;
    }

    try {
      const res = await api.get(`/simulation/compare?sim_id_1=${selectedForCompare[0]}&sim_id_2=${selectedForCompare[1]}`);
      setComparisonResult(res.data);
      setActiveTab('comparison');
      toast.success('Generated side-by-side comparison matrix');
    } catch {
      toast.error('Failed to generate comparison result');
    }
  };

  // Save Current Live Run
  const handleOpenSaveModal = () => {
    setSaveName(`Simulation Run #${Math.floor(100 + Math.random() * 900)}`);
    setSaveScenario(scenarios[0]?.name || 'Standard Baseline Run');
    setShowSaveModal(true);
  };

  const handleConfirmSave = async (e) => {
    e.preventDefault();
    try {
      await api.post('/simulation/save-current', {
        name: saveName,
        scenario_name: saveScenario,
      });
      setShowSaveModal(false);
      fetchData();
      toast.success(`Simulation run '${saveName}' saved successfully`);
    } catch {
      toast.error('Failed to save current simulation run');
    }
  };

  // Delete saved simulation
  const handleDeleteSimulation = async (simId) => {
    if (!confirm('Are you sure you want to delete this saved simulation run?')) return;
    try {
      await api.delete(`/simulation/saved/${simId}`);
      setSelectedForCompare((prev) => prev.filter((id) => id !== simId));
      fetchData();
      toast.success('Saved simulation run deleted');
    } catch {
      toast.error('Failed to delete simulation run');
    }
  };

  // Create / Delete Custom Scenario
  const handleCreateScenario = async (scData) => {
    try {
      await api.post('/scenarios', scData);
      fetchData();
      toast.success('Custom scenario created');
    } catch {
      toast.error('Failed to create scenario');
    }
  };

  const handleDeleteScenario = async (scId) => {
    if (!confirm('Are you sure you want to delete this custom scenario?')) return;
    try {
      await api.delete(`/scenarios/${scId}`);
      fetchData();
      toast.success('Custom scenario deleted');
    } catch {
      toast.error('Failed to delete scenario');
    }
  };

  // Export CSV
  const handleExportCSV = (sim) => {
    const csvContent = "data:text/csv;charset=utf-8," +
      "Field,Value\n" +
      `Simulation Name,"${sim.name}"\n` +
      `Scenario,"${sim.scenario_name}"\n` +
      `Duration Seconds,${sim.duration_seconds}\n` +
      `Total Requests,${sim.total_requests}\n` +
      `Completed Requests,${sim.completed_requests}\n` +
      `Completion Rate,${sim.completion_rate}%\n` +
      `Avg Waiting Time,${sim.avg_waiting_time_sec}s\n` +
      `Created At,"${sim.created_at}"\n`;

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `${sim.name.replace(/\s+/g, '_')}_report.csv`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    toast.success('CSV report exported');
  };

  return (
    <div className="space-y-6 pb-12">
      {/* ── Page Header ────────────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Film className="h-6 w-6 text-indigo-400" />
            Simulation Playback & Scenario Testing
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Save historical simulation telemetry runs, replay events, compare scenarios side-by-side, and manage presets
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          {selectedForCompare.length === 2 && (
            <button
              onClick={handleCompareClick}
              className="flex items-center gap-1.5 px-3.5 py-2 bg-green-600 hover:bg-green-700 text-white font-bold text-xs rounded-lg transition-colors shadow-sm animate-bounce"
            >
              <Scale className="h-4 w-4" /> Compare Selected (2)
            </button>
          )}

          <button
            onClick={handleOpenSaveModal}
            className="flex items-center gap-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-lg text-xs transition-colors shadow-sm"
          >
            <Save className="h-4 w-4" /> Save Live Simulation Run
          </button>
        </div>
      </div>

      {/* ── 1. Overview Metric Cards ────────────────────────────────────────── */}
      <ScenarioDashboardOverview overview={overview} />

      {/* ── 2. Search & Filter Bar ───────────────────────────────────────────── */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 shadow-sm">
        <div className="flex flex-col sm:flex-row gap-4 items-stretch sm:items-center justify-between">
          <div className="relative flex-1 min-w-[280px]">
            <Search className="absolute left-3.5 top-2.5 h-4 w-4 text-gray-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search saved runs by Simulation Name or Scenario..."
              className="w-full pl-10 pr-4 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 bg-gray-900 border border-gray-700 rounded-lg px-3 py-1.5">
              <Filter className="h-3.5 w-3.5 text-indigo-400" />
              <select
                value={filterScenario}
                onChange={(e) => setFilterScenario(e.target.value)}
                className="bg-transparent text-gray-200 text-xs font-medium focus:outline-none cursor-pointer"
              >
                <option value="All" className="bg-gray-800 text-white">All Scenarios</option>
                {scenarios.map((s) => (
                  <option key={s.id} value={s.name} className="bg-gray-800 text-white">{s.name}</option>
                ))}
              </select>
            </div>

            <button
              onClick={() => { setSearch(''); setFilterScenario('All'); }}
              className="flex items-center gap-1 px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg text-xs font-medium transition-colors"
            >
              <RotateCcw className="h-3.5 w-3.5" /> Reset
            </button>
          </div>
        </div>
      </div>

      {/* ── 3. Navigation Tabs & Content Views ───────────────────────────────── */}
      <div className="space-y-4">
        {/* Tabs Bar */}
        <div className="flex items-center border-b border-gray-700">
          <button
            onClick={() => setActiveTab('saved')}
            className={`flex items-center gap-2 py-3 px-5 font-bold text-sm border-b-2 transition-colors ${
              activeTab === 'saved'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            <Film className="h-4 w-4" /> Saved Simulations
            <span className="px-2 py-0.5 rounded-full text-xs bg-indigo-500/20 text-indigo-400 font-bold">
              {simulations.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('comparison')}
            className={`flex items-center gap-2 py-3 px-5 font-bold text-sm border-b-2 transition-colors ${
              activeTab === 'comparison'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            <Scale className="h-4 w-4" /> Scenario Comparison Matrix
          </button>

          <button
            onClick={() => setActiveTab('scenarios')}
            className={`flex items-center gap-2 py-3 px-5 font-bold text-sm border-b-2 transition-colors ${
              activeTab === 'scenarios'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            <Layers className="h-4 w-4" /> Scenario Presets Manager
            <span className="px-2 py-0.5 rounded-full text-xs bg-green-500/20 text-green-400 font-bold">
              {scenarios.length}
            </span>
          </button>
        </div>

        {/* Tab 1: Saved Simulations Table */}
        {activeTab === 'saved' && (
          <SavedSimulationsTable
            simulations={simulations}
            selectedForCompare={selectedForCompare}
            onToggleCompare={handleToggleCompare}
            onReplay={(sim) => setReplaySimulation(sim)}
            onExport={handleExportCSV}
            onDelete={handleDeleteSimulation}
          />
        )}

        {/* Tab 2: Scenario Comparison */}
        {activeTab === 'comparison' && (
          <ScenarioComparison
            comparison={comparisonResult}
            onClose={() => setActiveTab('saved')}
          />
        )}

        {/* Tab 3: Scenario Presets Manager */}
        {activeTab === 'scenarios' && (
          <ScenarioManager
            scenarios={scenarios}
            onCreateScenario={handleCreateScenario}
            onDeleteScenario={handleDeleteScenario}
          />
        )}
      </div>

      {/* Replay Player Modal */}
      {replaySimulation && (
        <SimulationReplayPlayer
          simulation={replaySimulation}
          onClose={() => setReplaySimulation(null)}
        />
      )}

      {/* Save Live Simulation Modal */}
      {showSaveModal && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 w-full max-w-md shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-4">Save Live Simulation Snapshot</h3>
            <form onSubmit={handleConfirmSave} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-400 mb-1">Simulation Run Name</label>
                <input
                  type="text"
                  required
                  value={saveName}
                  onChange={(e) => setSaveName(e.target.value)}
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-400 mb-1">Scenario Tag</label>
                <select
                  value={saveScenario}
                  onChange={(e) => setSaveScenario(e.target.value)}
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  {scenarios.map((s) => (
                    <option key={s.id} value={s.name}>{s.name}</option>
                  ))}
                </select>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-gray-700">
                <button
                  type="button"
                  onClick={() => setShowSaveModal(false)}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 text-xs font-bold rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-lg"
                >
                  Save Simulation
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
