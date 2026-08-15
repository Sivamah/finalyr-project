import React from 'react';
import { CheckCircle2, Activity, Info, AlertTriangle, AlertOctagon } from 'lucide-react';

const CATEGORY_ICON = {
  Information: Info,
  Success: CheckCircle2,
  Warning: AlertTriangle,
  Error: AlertOctagon,
};

const CATEGORY_COLOR = {
  Information: 'text-brand-primary border-brand-primary/30 bg-brand-primary/10',
  Success: 'text-brand-success border-brand-success/30 bg-brand-success/10',
  Warning: 'text-brand-warning border-brand-warning/30 bg-brand-warning/10',
  Error: 'text-brand-danger border-brand-danger/30 bg-brand-danger/10',
};

export default function ActivityTimeline({ timeline = [] }) {
  if (timeline.length === 0) {
    return (
      <div className="p-4 text-center">
        <Activity className="h-10 w-10 mx-auto mb-2 opacity-40 text-brand-text-muted" />
        <p className="text-sm font-medium text-brand-text-secondary">No activity events recorded</p>
        <p className="text-[11px] text-brand-text-muted mt-1">System events will appear here chronologically</p>
      </div>
    );
  }

  return (
    <div className="w-full">
      <div className="relative pl-7 space-y-5 before:absolute before:left-[9px] before:top-2 before:bottom-2 before:w-px before:bg-gradient-to-b before:from-brand-primary/40 before:via-white/[0.08] before:to-transparent">
        {timeline.map((item, idx) => {
          const Icon = CATEGORY_ICON[item.category] || Info;
          const color = CATEGORY_COLOR[item.category] || CATEGORY_COLOR.Information;

          return (
            <div key={item.id || idx} className="relative flex items-start gap-3.5">
              <div className={`absolute -left-7 top-0 h-[18px] w-[18px] rounded-full border flex items-center justify-center backdrop-blur-md ${color}`}>
                <Icon className="h-[10px] w-[10px]" />
              </div>

              <div className="min-w-0 flex-1">
                <p className="text-[13px] font-semibold text-white leading-snug">{item.title}</p>
                {item.description && (
                  <p className="text-[12px] text-brand-text-secondary mt-0.5 leading-relaxed line-clamp-2">{item.description}</p>
                )}
              </div>

              <span className="text-[10.5px] font-mono font-medium text-brand-text-muted shrink-0 mt-0.5">
                {item.time_str}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}