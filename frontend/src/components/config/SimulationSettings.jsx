import React from 'react';
import { Sliders, Zap, Database, Clock, RefreshCw, Trash2 } from 'lucide-react';

export default function SimulationSettings({ config = {}, onChange }) {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 shadow-sm space-y-6">
      <div className="border-b border-gray-700 pb-3">
        <h3 className="text-base font-bold text-white flex items-center gap-2">
          <Zap className="h-5 w-5 text-indigo-400" />
          Simulation Engine Settings
        </h3>
        <p className="text-xs text-gray-400 mt-0.5">
          Configure telemetry generation speed, queue limits, and auto-cleanup behavior
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Request Generation Speed */}
        <div>
          <label className="block text-xs font-semibold text-gray-300 mb-1 flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5 text-indigo-400" />
            Request Generation Speed (Seconds per tick)
          </label>
          <input
            type="number"
            min="1"
            max="30"
            value={config.simulation_speed ?? 3}
            onChange={(e) => onChange('simulation_speed', parseInt(e.target.value) || 1)}
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono"
          />
          <p className="text-[11px] text-gray-500 mt-1">Lower value accelerates request generation frequency</p>
        </div>

        {/* Max Queue Size */}
        <div>
          <label className="block text-xs font-semibold text-gray-300 mb-1 flex items-center gap-1.5">
            <Database className="h-3.5 w-3.5 text-blue-400" />
            Maximum Queue Capacity
          </label>
          <input
            type="number"
            min="50"
            max="5000"
            step="50"
            value={config.max_queue_size ?? 500}
            onChange={(e) => onChange('max_queue_size', parseInt(e.target.value) || 100)}
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono"
          />
          <p className="text-[11px] text-gray-500 mt-1">Maximum active pending requests allowed in memory queue</p>
        </div>

        {/* Simulation Duration */}
        <div>
          <label className="block text-xs font-semibold text-gray-300 mb-1 flex items-center gap-1.5">
            <Sliders className="h-3.5 w-3.5 text-green-400" />
            Max Simulation Run Duration (Minutes)
          </label>
          <input
            type="number"
            min="5"
            max="1440"
            step="5"
            value={config.simulation_duration ?? 60}
            onChange={(e) => onChange('simulation_duration', parseInt(e.target.value) || 10)}
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono"
          />
          <p className="text-[11px] text-gray-500 mt-1">Automatic shutdown timer for continuous simulation runs</p>
        </div>

        {/* Checkbox Toggles */}
        <div className="space-y-4 pt-2">
          {/* Auto Restart */}
          <label className="flex items-center gap-3 cursor-pointer p-3 bg-gray-900 border border-gray-700 rounded-lg hover:border-gray-600 transition-colors">
            <input
              type="checkbox"
              checked={!!config.auto_restart}
              onChange={(e) => onChange('auto_restart', e.target.checked)}
              className="w-4 h-4 text-indigo-600 bg-gray-800 border-gray-700 rounded focus:ring-indigo-500"
            />
            <div>
              <span className="text-xs font-bold text-white flex items-center gap-1.5">
                <RefreshCw className="h-3.5 w-3.5 text-indigo-400" /> Auto Restart Engine
              </span>
              <p className="text-[11px] text-gray-400">Automatically resume background ticks after server restart</p>
            </div>
          </label>

          {/* Auto Cleanup */}
          <label className="flex items-center gap-3 cursor-pointer p-3 bg-gray-900 border border-gray-700 rounded-lg hover:border-gray-600 transition-colors">
            <input
              type="checkbox"
              checked={!!config.auto_cleanup}
              onChange={(e) => onChange('auto_cleanup', e.target.checked)}
              className="w-4 h-4 text-indigo-600 bg-gray-800 border-gray-700 rounded focus:ring-indigo-500"
            />
            <div>
              <span className="text-xs font-bold text-white flex items-center gap-1.5">
                <Trash2 className="h-3.5 w-3.5 text-amber-400" /> Auto Cleanup Completed History
              </span>
              <p className="text-[11px] text-gray-400">Automatically purge completed requests older than 24 hours</p>
            </div>
          </label>
        </div>
      </div>
    </div>
  );
}
