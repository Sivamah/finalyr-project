import React, { useState } from 'react';
import { Layers, Plus, Trash2, Shield, CloudRain, Sun, Zap } from 'lucide-react';

export default function ScenarioManager({ scenarios = [], onCreateScenario, onDeleteScenario }) {
  const [showModal, setShowModal] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    traffic_multiplier: 1.2,
    demand_multiplier: 1.5,
    weather_condition: 'Clear',
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    onCreateScenario({
      ...formData,
      traffic_multiplier: parseFloat(formData.traffic_multiplier),
      demand_multiplier: parseFloat(formData.demand_multiplier),
    });
    setShowModal(false);
    setFormData({
      name: '',
      description: '',
      traffic_multiplier: 1.2,
      demand_multiplier: 1.5,
      weather_condition: 'Clear',
    });
  };

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 shadow-sm space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-700 pb-4">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <Layers className="h-5 w-5 text-indigo-400" />
            Scenario Presets & Custom Simulation Conditions ({scenarios.length})
          </h3>
          <p className="text-xs text-gray-400 mt-0.5">
            Manage traffic multipliers, weather conditions, and demand spurts for simulation testing
          </p>
        </div>

        <button
          type="button"
          onClick={() => setShowModal(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-lg transition-colors shadow-sm"
        >
          <Plus className="h-4 w-4" /> Add Custom Scenario
        </button>
      </div>

      {/* Grid of Scenarios */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {scenarios.map((sc) => (
          <div key={sc.id} className="bg-gray-900 border border-gray-700 rounded-xl p-4 flex flex-col justify-between space-y-3 hover:border-gray-600 transition-all">
            <div>
              <div className="flex items-center justify-between gap-2 mb-1">
                <h4 className="text-sm font-bold text-white leading-tight">{sc.name}</h4>
                <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                  sc.is_preset
                    ? 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20'
                    : 'bg-green-500/10 text-green-400 border-green-500/20'
                }`}>
                  {sc.is_preset ? 'System Preset' : 'Custom'}
                </span>
              </div>

              <p className="text-xs text-gray-400 leading-relaxed min-h-[36px]">{sc.description || 'Custom simulation scenario'}</p>
            </div>

            <div className="space-y-2 pt-2 border-t border-gray-800 text-xs">
              <div className="flex justify-between text-gray-300">
                <span>Traffic Multiplier:</span>
                <span className="font-mono font-bold text-indigo-400">{sc.traffic_multiplier}x</span>
              </div>

              <div className="flex justify-between text-gray-300">
                <span>Demand Multiplier:</span>
                <span className="font-mono font-bold text-green-400">{sc.demand_multiplier}x</span>
              </div>

              <div className="flex justify-between text-gray-300">
                <span>Weather Condition:</span>
                <span className="font-mono font-bold text-amber-400">{sc.weather_condition}</span>
              </div>
            </div>

            {!sc.is_preset && (
              <div className="pt-2 border-t border-gray-800 flex justify-end">
                <button
                  type="button"
                  onClick={() => onDeleteScenario(sc.id)}
                  className="text-xs text-red-400 hover:text-red-300 flex items-center gap-1 font-medium"
                >
                  <Trash2 className="h-3.5 w-3.5" /> Delete Scenario
                </button>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Add Custom Scenario Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 w-full max-w-md shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-4">Add Custom Scenario</h3>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-400 mb-1">Scenario Name</label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g. Festival Evening Rush"
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-400 mb-1">Description</label>
                <textarea
                  rows="2"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Brief description of traffic/demand conditions..."
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-gray-400 mb-1">Traffic Multiplier</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0.5"
                    max="5.0"
                    value={formData.traffic_multiplier}
                    onChange={(e) => setFormData({ ...formData, traffic_multiplier: e.target.value })}
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-400 mb-1">Demand Multiplier</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0.5"
                    max="5.0"
                    value={formData.demand_multiplier}
                    onChange={(e) => setFormData({ ...formData, demand_multiplier: e.target.value })}
                    className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-400 mb-1">Weather Condition</label>
                <select
                  value={formData.weather_condition}
                  onChange={(e) => setFormData({ ...formData, weather_condition: e.target.value })}
                  className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="Clear">Clear</option>
                  <option value="Rain">Rain</option>
                  <option value="Heavy Traffic">Heavy Traffic</option>
                </select>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-gray-700">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 text-xs font-bold rounded-lg"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold rounded-lg"
                >
                  Save Scenario
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
