import React from 'react';
import { Clock, CheckCircle2, Activity, Info, AlertTriangle, AlertOctagon } from 'lucide-react';

const CATEGORY_ICON = {
  Information: Info,
  Success: CheckCircle2,
  Warning: AlertTriangle,
  Error: AlertOctagon,
};

const CATEGORY_COLOR = {
  Information: 'text-blue-400 border-blue-500/30 bg-blue-500/10',
  Success: 'text-green-400 border-green-500/30 bg-green-500/10',
  Warning: 'text-amber-400 border-amber-500/30 bg-amber-500/10',
  Error: 'text-red-400 border-red-500/30 bg-red-500/10',
};

export default function ActivityTimeline({ timeline = [] }) {
  if (timeline.length === 0) {
    return (
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-12 text-center text-gray-500">
        <Activity className="h-10 w-10 mx-auto mb-2 opacity-40" />
        <p className="text-base font-medium">No activity log events recorded</p>
        <p className="text-xs text-gray-600 mt-1">System events will appear here chronologically</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-5 shadow-sm">
      <div className="flex items-center justify-between border-b border-gray-700 pb-3 mb-5">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <Activity className="h-4 w-4 text-indigo-400" />
          Chronological Activity Log Timeline
        </h3>
        <span className="text-xs text-gray-400 font-mono">{timeline.length} events logged</span>
      </div>

      <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-gray-700">
        {timeline.map((item, idx) => {
          const Icon = CATEGORY_ICON[item.category] || Info;
          const color = CATEGORY_COLOR[item.category] || CATEGORY_COLOR.Information;

          return (
            <div key={item.id || idx} className="relative flex items-start justify-between gap-4">
              {/* Dot Icon */}
              <div className={`absolute -left-6 top-0.5 w-5 h-5 rounded-full flex items-center justify-center border ${color}`}>
                <Icon className="h-3 w-3" />
              </div>

              <div>
                <p className="text-sm font-bold text-white leading-tight">{item.title}</p>
                {item.description && (
                  <p className="text-xs text-gray-400 mt-0.5 leading-relaxed">{item.description}</p>
                )}
              </div>

              <span className="text-xs font-mono font-semibold text-indigo-400 shrink-0 bg-gray-900 px-2.5 py-1 rounded border border-gray-700">
                {item.time_str}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
