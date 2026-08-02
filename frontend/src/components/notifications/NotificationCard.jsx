import React from 'react';
import { Info, CheckCircle2, AlertTriangle, AlertOctagon, Check, Trash2, Clock } from 'lucide-react';

const CATEGORY_STYLE = {
  Information: {
    icon: Info,
    colorClass: 'text-blue-400',
    bgClass: 'bg-blue-500/10 border-blue-500/30',
    badgeClass: 'bg-blue-600 text-white',
  },
  Success: {
    icon: CheckCircle2,
    colorClass: 'text-green-400',
    bgClass: 'bg-green-500/10 border-green-500/30',
    badgeClass: 'bg-green-600 text-white',
  },
  Warning: {
    icon: AlertTriangle,
    colorClass: 'text-amber-400',
    bgClass: 'bg-amber-500/10 border-amber-500/30',
    badgeClass: 'bg-amber-600 text-white',
  },
  Error: {
    icon: AlertOctagon,
    colorClass: 'text-red-400',
    bgClass: 'bg-red-500/10 border-red-500/30',
    badgeClass: 'bg-red-600 text-white',
  },
};

export default function NotificationCard({ notification, onMarkRead, onDelete }) {
  if (!notification) return null;

  const style = CATEGORY_STYLE[notification.category] || CATEGORY_STYLE.Information;
  const Icon = style.icon;

  const dateStr = notification.created_at
    ? new Date(notification.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    : '—';

  return (
    <div
      className={`border rounded-xl p-4 transition-all shadow-sm flex items-start gap-4 ${
        notification.is_read
          ? 'bg-gray-800/60 border-gray-700/60 opacity-85'
          : 'bg-gray-800 border-indigo-500/40 ring-1 ring-indigo-500/10'
      }`}
    >
      {/* Category Icon Badge */}
      <div className={`p-2.5 rounded-xl border shrink-0 ${style.bgClass}`}>
        <Icon className={`h-5 w-5 ${style.colorClass}`} />
      </div>

      {/* Content Body */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2 mb-1">
          <div className="flex items-center gap-2 flex-wrap">
            <h4 className="text-sm font-bold text-white leading-tight">{notification.title}</h4>
            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${style.badgeClass}`}>
              {notification.category}
            </span>
            {!notification.is_read && (
              <span className="flex items-center gap-1 text-[10px] font-bold text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded-full border border-indigo-500/20">
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-ping" /> Unread
              </span>
            )}
          </div>

          <span className="text-xs font-mono text-gray-400 flex items-center gap-1 shrink-0">
            <Clock className="h-3 w-3 text-gray-500" />
            {dateStr}
          </span>
        </div>

        <p className="text-xs text-gray-300 leading-relaxed mb-2">{notification.description}</p>

        {/* Metadata Tags */}
        <div className="flex items-center gap-3 text-[11px] text-gray-400">
          {notification.request_id && (
            <span className="font-mono text-gray-400 bg-gray-900 px-2 py-0.5 rounded border border-gray-700">
              Request #{notification.request_id}
            </span>
          )}
          {notification.provider_name && (
            <span className="text-gray-400 bg-gray-900 px-2 py-0.5 rounded border border-gray-700">
              {notification.provider_name}
            </span>
          )}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex items-center gap-1 shrink-0 pt-0.5">
        {!notification.is_read && (
          <button
            onClick={() => onMarkRead(notification.id)}
            className="p-1.5 text-gray-400 hover:text-green-400 hover:bg-green-500/10 rounded-lg transition-colors"
            title="Mark as Read"
          >
            <Check className="h-4 w-4" />
          </button>
        )}

        <button
          onClick={() => onDelete(notification.id)}
          className="p-1.5 text-gray-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
          title="Delete Notification"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
