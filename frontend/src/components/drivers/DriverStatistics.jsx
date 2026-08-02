import React from 'react';
import { Users, UserCheck, UserX, UserMinus } from 'lucide-react';

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

export default function DriverStatistics({ stats = {} }) {
  const cards = [
    {
      label: 'Total Drivers',
      value: stats.total_drivers ?? 0,
      icon: Users,
      colorBg: 'bg-indigo-500/10 text-indigo-400',
      borderColor: 'border-indigo-500/20',
      textColor: 'text-white',
    },
    {
      label: 'Available Drivers',
      value: stats.available_drivers ?? 0,
      icon: UserCheck,
      colorBg: 'bg-green-500/10 text-green-400',
      borderColor: 'border-green-500/20',
      textColor: 'text-green-400',
    },
    {
      label: 'Busy Drivers',
      value: stats.busy_drivers ?? 0,
      icon: UserMinus,
      colorBg: 'bg-amber-500/10 text-amber-400',
      borderColor: 'border-amber-500/20',
      textColor: 'text-amber-400',
    },
    {
      label: 'Offline Drivers',
      value: stats.offline_drivers ?? 0,
      icon: UserX,
      colorBg: 'bg-gray-500/10 text-gray-400',
      borderColor: 'border-gray-500/20',
      textColor: 'text-gray-400',
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
