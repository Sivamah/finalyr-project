import React from 'react';
import { Building2, Layers } from 'lucide-react';

export default function ProviderConfiguration({ config = {}, providers = [], onChange }) {
  const enabledMap = config.provider_enabled_map || { '1': true, '2': true, '3': true };
  const priorityMap = config.provider_priority_map || { '1': 'High', '2': 'Medium', '3': 'Medium' };
  const supportedServices = config.supported_services || ['Ride', 'Food', 'Parcel'];

  const handleToggleProvider = (pid) => {
    const updated = { ...enabledMap, [pid]: !enabledMap[pid] };
    onChange('provider_enabled_map', updated);
  };

  const handleChangePriority = (pid, prio) => {
    const updated = { ...priorityMap, [pid]: prio };
    onChange('provider_priority_map', updated);
  };

  const handleToggleService = (srv) => {
    let updated = [...supportedServices];
    if (updated.includes(srv)) {
      updated = updated.filter((s) => s !== srv);
    } else {
      updated.push(srv);
    }
    onChange('supported_services', updated);
  };

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 shadow-sm space-y-6">
      <div className="border-b border-gray-700 pb-3">
        <h3 className="text-base font-bold text-white flex items-center gap-2">
          <Building2 className="h-5 w-5 text-indigo-400" />
          Provider Integration & Priority Rules
        </h3>
        <p className="text-xs text-gray-400 mt-0.5">
          Enable/disable participating providers, adjust dispatch priorities, and daily request quotas
        </p>
      </div>

      {/* Global Quota & Service Types */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label className="block text-xs font-semibold text-gray-300 mb-1">
            Maximum Daily Platform Capacity
          </label>
          <input
            type="number"
            min="100"
            max="100000"
            step="100"
            value={config.max_daily_capacity ?? 1000}
            onChange={(e) => onChange('max_daily_capacity', parseInt(e.target.value) || 500)}
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono"
          />
          <p className="text-[11px] text-gray-500 mt-1">Total daily simulation requests limit across all providers</p>
        </div>

        <div>
          <label className="block text-xs font-semibold text-gray-300 mb-2 flex items-center gap-1.5">
            <Layers className="h-3.5 w-3.5 text-blue-400" />
            Supported Platform Service Types
          </label>
          <div className="flex flex-wrap gap-3">
            {['Ride', 'Food', 'Parcel'].map((srv) => {
              const checked = supportedServices.includes(srv);
              return (
                <button
                  key={srv}
                  type="button"
                  onClick={() => handleToggleService(srv)}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-bold transition-all border ${
                    checked
                      ? 'bg-indigo-600 border-indigo-500 text-white'
                      : 'bg-gray-900 border-gray-700 text-gray-400 hover:text-white'
                  }`}
                >
                  <span className={`w-2 h-2 rounded-full ${checked ? 'bg-white' : 'bg-gray-600'}`} />
                  {srv} Delivery
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Provider Roster Enable / Priority Table */}
      <div className="border border-gray-700 rounded-xl overflow-hidden">
        <div className="bg-gray-900/60 px-4 py-2.5 border-b border-gray-700 text-xs font-bold text-gray-300 uppercase tracking-wider">
          Individual Provider Status & Dispatch Priority
        </div>
        <div className="divide-y divide-gray-700">
          {providers.length === 0 ? (
            <div className="p-4 text-center text-xs text-gray-500">No registered providers</div>
          ) : (
            providers.map((p) => {
              const isEnabled = enabledMap[p.id] !== false;
              const priority = priorityMap[p.id] || 'Medium';

              return (
                <div key={p.id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-gray-750/30 transition-colors">
                  <div className="flex items-center gap-3">
                    <button
                      type="button"
                      onClick={() => handleToggleProvider(p.id)}
                      className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out ${
                        isEnabled ? 'bg-green-600' : 'bg-gray-700'
                      }`}
                    >
                      <span
                        className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                          isEnabled ? 'translate-x-5' : 'translate-x-0'
                        }`}
                      />
                    </button>

                    <div>
                      <h4 className="text-sm font-bold text-white flex items-center gap-2">
                        {p.name}
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          isEnabled ? 'bg-green-500/10 text-green-400 border border-green-500/30' : 'bg-red-500/10 text-red-400 border border-red-500/30'
                        }`}>
                          {isEnabled ? 'Enabled' : 'Disabled'}
                        </span>
                      </h4>
                      <p className="text-xs text-gray-400">{p.provider_type} • {p.operating_area}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <span className="text-xs text-gray-400 font-medium">Dispatch Priority:</span>
                    <select
                      value={priority}
                      onChange={(e) => handleChangePriority(p.id, e.target.value)}
                      className="bg-gray-900 border border-gray-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-medium"
                    >
                      <option value="High">High Priority</option>
                      <option value="Medium">Medium Priority</option>
                      <option value="Low">Low Priority</option>
                    </select>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
