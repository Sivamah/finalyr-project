import React from 'react';
import { Play, Layers, Download, Trash2, Clock, CheckCircle2, CheckSquare, Square } from 'lucide-react';

export default function SavedSimulationsTable({
  simulations = [],
  selectedForCompare = [],
  onToggleCompare,
  onReplay,
  onExport,
  onDelete,
}) {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl shadow-sm overflow-hidden">
      <div className="flex items-center justify-between p-4 border-b border-gray-700">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            Saved Simulation Telemetry History ({simulations.length})
          </h3>
          <p className="text-xs text-gray-400">
            Select any 2 simulations using checkboxes to trigger side-by-side comparative analysis
          </p>
        </div>
        {selectedForCompare.length === 2 && (
          <span className="px-3 py-1 bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 rounded-lg text-xs font-bold animate-pulse">
            2 Simulations Selected for Comparison
          </span>
        )}
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-900/60 border-b border-gray-700 text-[11px] font-bold text-gray-400 uppercase tracking-wider">
              <th className="py-3 px-4 w-10">Compare</th>
              <th className="py-3 px-4">Simulation Name</th>
              <th className="py-3 px-4">Scenario Preset</th>
              <th className="py-3 px-4">Total Requests</th>
              <th className="py-3 px-4">Completion Rate</th>
              <th className="py-3 px-4">Avg Wait</th>
              <th className="py-3 px-4">Date Saved</th>
              <th className="py-3 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700 text-xs">
            {simulations.length === 0 ? (
              <tr>
                <td colSpan="8" className="text-center py-10 text-gray-500">
                  No saved simulations match current filters
                </td>
              </tr>
            ) : (
              simulations.map((sim) => {
                const isSelected = selectedForCompare.includes(sim.id);

                return (
                  <tr key={sim.id} className={`hover:bg-gray-750/50 transition-colors ${isSelected ? 'bg-indigo-950/20' : ''}`}>
                    <td className="py-3 px-4">
                      <button
                        type="button"
                        onClick={() => onToggleCompare(sim.id)}
                        className="text-indigo-400 hover:text-indigo-300 transition-colors"
                      >
                        {isSelected ? (
                          <CheckSquare className="h-4 w-4 text-indigo-400" />
                        ) : (
                          <Square className="h-4 w-4 text-gray-600" />
                        )}
                      </button>
                    </td>

                    <td className="py-3 px-4">
                      <div className="font-bold text-white flex items-center gap-2">
                        {sim.name}
                      </div>
                      <div className="text-[10px] text-gray-400 font-mono">
                        Duration: {Math.round(sim.duration_seconds)}s
                      </div>
                    </td>

                    <td className="py-3 px-4">
                      <span className="bg-gray-900 border border-gray-700 px-2 py-0.5 rounded text-[11px] font-medium text-gray-300">
                        {sim.scenario_name}
                      </span>
                    </td>

                    <td className="py-3 px-4 font-mono font-bold text-white">
                      {sim.total_requests} reqs
                    </td>

                    <td className="py-3 px-4">
                      <div className="flex items-center gap-2">
                        <span className={`font-mono font-bold ${
                          sim.completion_rate >= 80 ? 'text-green-400' : 'text-amber-400'
                        }`}>
                          {sim.completion_rate}%
                        </span>
                        <div className="w-16 bg-gray-700 h-1.5 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${sim.completion_rate >= 80 ? 'bg-green-500' : 'bg-amber-500'}`}
                            style={{ width: `${Math.min(100, sim.completion_rate)}%` }}
                          />
                        </div>
                      </div>
                    </td>

                    <td className="py-3 px-4 font-mono text-gray-300">
                      {sim.avg_waiting_time_sec}s
                    </td>

                    <td className="py-3 px-4 font-mono text-gray-400 text-[11px]">
                      {sim.created_at}
                    </td>

                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          type="button"
                          onClick={() => onReplay(sim)}
                          className="flex items-center gap-1 px-2.5 py-1 bg-indigo-600 hover:bg-indigo-700 text-white text-[11px] font-bold rounded transition-colors shadow-sm"
                        >
                          <Play className="h-3 w-3" /> Replay
                        </button>

                        <button
                          type="button"
                          onClick={() => onExport(sim)}
                          className="p-1.5 text-gray-400 hover:text-green-400 hover:bg-gray-700 rounded transition-colors"
                          title="Export Report CSV"
                        >
                          <Download className="h-3.5 w-3.5" />
                        </button>

                        <button
                          type="button"
                          onClick={() => onDelete(sim.id)}
                          className="p-1.5 text-gray-400 hover:text-red-400 hover:bg-gray-700 rounded transition-colors"
                          title="Delete Simulation Run"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
