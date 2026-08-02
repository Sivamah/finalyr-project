import React from 'react';
import { Truck, CheckCircle2, Navigation, Wrench } from 'lucide-react';

function StatCard({ label, value, icon: Icon, colorBg, borderColor, textColor }) {
  return (
    <div className={`bg-gray-800 border ${borderColor || 'border-gray-700'} rounded-xl p-4 shadow-sm hover:border-gray-600 transition-all`}>
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs text-gray-400 font-medium truncate">{label}</p>
          <p className={`text-2xl font-bold font-mono mt-1 ${textColor || 'text-white'}`}>{value}</p>
        </div>
        <div className={`p-3 rounded-lg ${colorBg}`}>
          <Icon className="h-5 w-5" />
        </div>
      </div>
    </div>
  );
}

export default function VehicleStatistics({ stats = {} }) {
  const cards = [
    {
      label: 'Total Vehicles',
      value: stats.total_vehicles ?? 0,
      icon: Truck,
      colorBg: 'bg-indigo-500/10 text-indigo-400',
      borderColor: 'border-indigo-500/20',
      textColor: 'text-white',
    },
    {
      label: 'Available Vehicles',
      value: stats.available_vehicles ?? 0,
      icon: CheckCircle2,
      colorBg: 'bg-green-500/10 text-green-400',
      borderColor: 'border-green-500/20',
      textColor: 'text-green-400',
    },
    {
      label: 'Vehicles in Service (Busy)',
      value: stats.vehicles_in_service ?? 0,
      icon: Navigation,
      colorBg: 'bg-blue-500/10 text-blue-400',
      borderColor: 'border-blue-500/20',
      textColor: 'text-blue-400',
    },
    {
      label: 'Under Maintenance',
      value: stats.maintenance_vehicles ?? 0,
      icon: Wrench,
      colorBg: 'bg-amber-500/10 text-amber-400',
      borderColor: 'border-amber-500/20',
      textColor: 'text-amber-400',
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
      {cards.map((c) => (
        <StatCard key={c.label} {...c} />
      ))}
    </div>
  );
}
