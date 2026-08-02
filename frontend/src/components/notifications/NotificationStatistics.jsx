import React from 'react';
import { Bell, MailOpen, Calendar, AlertTriangle, AlertOctagon } from 'lucide-react';

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

export default function NotificationStatistics({ stats = {} }) {
  const cards = [
    {
      label: 'Total Notifications',
      value: stats.total_notifications ?? 0,
      icon: Bell,
      colorBg: 'bg-indigo-500/10 text-indigo-400',
      borderColor: 'border-indigo-500/20',
      textColor: 'text-white',
    },
    {
      label: 'Unread Notifications',
      value: stats.unread_notifications ?? 0,
      icon: MailOpen,
      colorBg: 'bg-blue-500/10 text-blue-400',
      borderColor: 'border-blue-500/20',
      textColor: 'text-blue-400',
    },
    {
      label: "Today's Activities",
      value: stats.today_activities ?? 0,
      icon: Calendar,
      colorBg: 'bg-green-500/10 text-green-400',
      borderColor: 'border-green-500/20',
      textColor: 'text-green-400',
    },
    {
      label: 'Warnings Count',
      value: stats.warnings_count ?? 0,
      icon: AlertTriangle,
      colorBg: 'bg-amber-500/10 text-amber-400',
      borderColor: 'border-amber-500/20',
      textColor: 'text-amber-400',
    },
    {
      label: 'System Errors',
      value: stats.errors_count ?? 0,
      icon: AlertOctagon,
      colorBg: 'bg-red-500/10 text-red-400',
      borderColor: 'border-red-500/20',
      textColor: 'text-red-400',
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
      {cards.map((c) => (
        <StatCard key={c.label} {...c} />
      ))}
    </div>
  );
}
