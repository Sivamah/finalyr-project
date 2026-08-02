import React from 'react';
import { Scale, Trophy, CheckCircle2, Clock, Layers, ArrowRight } from 'lucide-react';

export default function ScenarioComparison({ comparison = null, onClose }) {
  if (!comparison) return null;

  const { simulation_1: sim1, simulation_2: sim2, delta_completion_rate: deltaRate, delta_waiting_time_sec: deltaWait, winner_simulation_id: winnerId } = comparison;

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 shadow-sm space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-gray-700 pb-4">
        <div>
          <h3 className="text-lg font-bold text-white flex items-center gap-2">
            <Scale className="h-5 w-5 text-indigo-400" />
            Side-by-Side Scenario Comparison
          </h3>
          <p className="text-xs text-gray-400 mt-0.5">
            Comparative performance telemetry delta between two historical simulation runs
          </p>
        </div>

        {onClose && (
          <button
            onClick={onClose}
            className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg text-xs font-bold transition-colors"
          >
            Close Comparison
          </button>
        )}
      </div>

      {/* Winners Badge Banner */}
      <div className="bg-indigo-950/40 border border-indigo-500/30 rounded-xl p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-green-500/10 border border-green-500/30 rounded-xl text-green-400">
            <Trophy className="h-6 w-6" />
          </div>
          <div>
            <h4 className="text-sm font-bold text-white">
              Higher Efficiency Winner: <span className="text-green-400">{winnerId === sim1.id ? sim1.name : sim2.name}</span>
            </h4>
            <p className="text-xs text-gray-400 mt-0.5">
              Completion Rate Delta: <span className="font-mono text-green-400 font-bold">{Math.abs(deltaRate)}% higher</span>
            </p>
          </div>
        </div>
      </div>

      {/* Comparison Matrix Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Simulation 1 Card */}
        <div className={`bg-gray-900 border rounded-xl p-5 space-y-4 ${
          winnerId === sim1.id ? 'border-green-500/50 ring-1 ring-green-500/20' : 'border-gray-700'
        }`}>
          <div className="flex items-center justify-between border-b border-gray-700 pb-3">
            <div>
              <h4 className="text-base font-bold text-white flex items-center gap-2">
                {sim1.name}
                {winnerId === sim1.id && (
                  <span className="bg-green-500/20 text-green-400 text-[10px] px-2 py-0.5 rounded font-bold border border-green-500/30">
                    Winner
                  </span>
                )}
              </h4>
              <p className="text-xs text-indigo-300 font-medium mt-0.5">{sim1.scenario_name}</p>
            </div>
            <span className="text-[11px] font-mono text-gray-500">{sim1.created_at}</span>
          </div>

          <div className="space-y-3">
            <div className="flex justify-between items-center text-xs">
              <span className="text-gray-400">Total Requests:</span>
              <span className="font-mono font-bold text-white">{sim1.total_requests} reqs</span>
            </div>

            <div className="flex justify-between items-center text-xs">
              <span className="text-gray-400">Completion Rate:</span>
              <span className="font-mono font-bold text-green-400">{sim1.completion_rate}%</span>
            </div>

            <div className="flex justify-between items-center text-xs">
              <span className="text-gray-400">Average Waiting Time:</span>
              <span className="font-mono font-bold text-amber-400">{sim1.avg_waiting_time_sec}s</span>
            </div>

            <div className="flex justify-between items-center text-xs">
              <span className="text-gray-400">Duration:</span>
              <span className="font-mono font-bold text-gray-300">{Math.round(sim1.duration_seconds)}s</span>
            </div>
          </div>

          {/* Provider Breakdown */}
          <div className="pt-2 border-t border-gray-800">
            <h5 className="text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-2">Provider Usage</h5>
            <div className="space-y-1">
              {Object.entries(sim1.provider_stats || {}).map(([pName, count]) => (
                <div key={pName} className="flex justify-between text-xs text-gray-300">
                  <span>{pName}:</span>
                  <span className="font-mono font-bold text-indigo-300">{count} reqs</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Simulation 2 Card */}
        <div className={`bg-gray-900 border rounded-xl p-5 space-y-4 ${
          winnerId === sim2.id ? 'border-green-500/50 ring-1 ring-green-500/20' : 'border-gray-700'
        }`}>
          <div className="flex items-center justify-between border-b border-gray-700 pb-3">
            <div>
              <h4 className="text-base font-bold text-white flex items-center gap-2">
                {sim2.name}
                {winnerId === sim2.id && (
                  <span className="bg-green-500/20 text-green-400 text-[10px] px-2 py-0.5 rounded font-bold border border-green-500/30">
                    Winner
                  </span>
                )}
              </h4>
              <p className="text-xs text-indigo-300 font-medium mt-0.5">{sim2.scenario_name}</p>
            </div>
            <span className="text-[11px] font-mono text-gray-500">{sim2.created_at}</span>
          </div>

          <div className="space-y-3">
            <div className="flex justify-between items-center text-xs">
              <span className="text-gray-400">Total Requests:</span>
              <span className="font-mono font-bold text-white">{sim2.total_requests} reqs</span>
            </div>

            <div className="flex justify-between items-center text-xs">
              <span className="text-gray-400">Completion Rate:</span>
              <span className="font-mono font-bold text-green-400">{sim2.completion_rate}%</span>
            </div>

            <div className="flex justify-between items-center text-xs">
              <span className="text-gray-400">Average Waiting Time:</span>
              <span className="font-mono font-bold text-amber-400">{sim2.avg_waiting_time_sec}s</span>
            </div>

            <div className="flex justify-between items-center text-xs">
              <span className="text-gray-400">Duration:</span>
              <span className="font-mono font-bold text-gray-300">{Math.round(sim2.duration_seconds)}s</span>
            </div>
          </div>

          {/* Provider Breakdown */}
          <div className="pt-2 border-t border-gray-800">
            <h5 className="text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-2">Provider Usage</h5>
            <div className="space-y-1">
              {Object.entries(sim2.provider_stats || {}).map(([pName, count]) => (
                <div key={pName} className="flex justify-between text-xs text-gray-300">
                  <span>{pName}:</span>
                  <span className="font-mono font-bold text-indigo-300">{count} reqs</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
