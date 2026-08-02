import React from 'react';
import { Truck, MapPin, Clock, Wrench } from 'lucide-react';

export default function VehicleRules({ config = {}, onChange }) {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 shadow-sm space-y-6">
      <div className="border-b border-gray-700 pb-3">
        <h3 className="text-base font-bold text-white flex items-center gap-2">
          <Truck className="h-5 w-5 text-indigo-400" />
          Vehicle Safety & Operational Constraints
        </h3>
        <p className="text-xs text-gray-400 mt-0.5">
          Establish fleet limits for vehicle payload, max trip distance, driver shift duration, and maintenance alerts
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Max Vehicle Capacity */}
        <div>
          <label className="block text-xs font-semibold text-gray-300 mb-1 flex items-center gap-1.5">
            <Truck className="h-3.5 w-3.5 text-indigo-400" />
            Maximum Allowed Vehicle Capacity (Passengers / Items)
          </label>
          <input
            type="number"
            min="1"
            max="50"
            value={config.max_vehicle_capacity ?? 6}
            onChange={(e) => onChange('max_vehicle_capacity', parseInt(e.target.value) || 1)}
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono"
          />
          <p className="text-[11px] text-gray-500 mt-1">Upper limit payload constraint for vehicle batching</p>
        </div>

        {/* Max Route Distance */}
        <div>
          <label className="block text-xs font-semibold text-gray-300 mb-1 flex items-center gap-1.5">
            <MapPin className="h-3.5 w-3.5 text-red-400" />
            Maximum Route Distance (KM per trip)
          </label>
          <input
            type="number"
            min="1.0"
            max="500.0"
            step="1.0"
            value={config.max_route_distance_km ?? 50.0}
            onChange={(e) => onChange('max_route_distance_km', parseFloat(e.target.value) || 10.0)}
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono"
          />
          <p className="text-[11px] text-gray-500 mt-1">Maximum allowed single trip coverage radius</p>
        </div>

        {/* Max Working Hours */}
        <div>
          <label className="block text-xs font-semibold text-gray-300 mb-1 flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5 text-green-400" />
            Maximum Shift Duration (Hours per day)
          </label>
          <input
            type="number"
            min="1.0"
            max="24.0"
            step="0.5"
            value={config.max_working_hours ?? 8.0}
            onChange={(e) => onChange('max_working_hours', parseFloat(e.target.value) || 4.0)}
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono"
          />
          <p className="text-[11px] text-gray-500 mt-1">Driver safety shift limit before mandating rest</p>
        </div>

        {/* Maintenance Threshold */}
        <div>
          <label className="block text-xs font-semibold text-gray-300 mb-1 flex items-center gap-1.5">
            <Wrench className="h-3.5 w-3.5 text-amber-400" />
            Maintenance Trigger Threshold (KM traveled)
          </label>
          <input
            type="number"
            min="500"
            max="50000"
            step="500"
            value={config.maintenance_threshold_km ?? 5000.0}
            onChange={(e) => onChange('maintenance_threshold_km', parseFloat(e.target.value) || 1000.0)}
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono"
          />
          <p className="text-[11px] text-gray-500 mt-1">Cumulative distance triggering automatic service inspection</p>
        </div>
      </div>
    </div>
  );
}
