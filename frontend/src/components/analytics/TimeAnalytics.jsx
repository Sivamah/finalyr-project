import React from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';
import { Clock, Timer, Zap, Calendar } from 'lucide-react';

export default function TimeAnalytics({ data = {} }) {
  const avgWait = data.avg_queue_waiting_time_sec ?? 0;
  const avgCompletion = data.avg_completion_time_sec ?? 0;
  const peakHour = data.peak_request_hour || 'N/A';
  const hourlyData = data.hourly_distribution || [];

  return (
    <div className="glass-panel rounded-[20px] p-5 lg:p-6 shadow-sm mb-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-5 border-b border-white/10 pb-4">
        <h3 className="text-base font-display font-semibold text-white flex items-center gap-2">
          <Clock className="h-5 w-5 text-yellow-400" />
          Time & Temporal Analytics
        </h3>
        <span className="text-[10px] bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 px-3 py-1.5 rounded-full font-bold uppercase tracking-wider">
          Latency & Hourly Load
        </span>
      </div>

      {/* Top 3 Summary Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 lg:gap-5 mb-8">
        {/* Avg Queue Waiting Time */}
        <div className="glass-card bg-black/20 border border-white/5 rounded-[16px] p-4 lg:p-5 flex items-center justify-between">
          <div>
            <p className="text-[10px] text-brand-text-muted font-bold uppercase tracking-wider">Avg Queue Waiting Time</p>
            <p className="text-2xl font-bold text-yellow-400 font-mono mt-1">
              {avgWait} <span className="text-xs font-medium text-brand-text-muted">sec</span>
            </p>
          </div>
          <div className="p-3 bg-yellow-500/10 rounded-[12px] text-yellow-400">
            <Clock className="h-5 w-5" />
          </div>
        </div>

        {/* Avg Completion Time */}
        <div className="glass-card bg-black/20 border border-white/5 rounded-[16px] p-4 lg:p-5 flex items-center justify-between">
          <div>
            <p className="text-[10px] text-brand-text-muted font-bold uppercase tracking-wider">Avg Completion Time</p>
            <p className="text-2xl font-bold text-brand-success font-mono mt-1">
              {avgCompletion} <span className="text-xs font-medium text-brand-text-muted">sec</span>
            </p>
          </div>
          <div className="p-3 bg-brand-success/10 rounded-[12px] text-brand-success">
            <Timer className="h-5 w-5" />
          </div>
        </div>

        {/* Peak Request Generation Hour */}
        <div className="glass-card bg-black/20 border border-white/5 rounded-[16px] p-4 lg:p-5 flex items-center justify-between">
          <div>
            <p className="text-[10px] text-brand-text-muted font-bold uppercase tracking-wider">Peak Generation Hour</p>
            <p className="text-xl font-bold text-brand-primary font-mono mt-1 truncate max-w-[180px]" title={peakHour}>
              {peakHour}
            </p>
          </div>
          <div className="p-3 bg-brand-primary/10 rounded-[12px] text-brand-primary">
            <Zap className="h-5 w-5" />
          </div>
        </div>
      </div>

      {/* Hourly Request Distribution Chart */}
      <div>
        <h4 className="text-[10px] font-bold text-brand-text-muted uppercase tracking-wider mb-4 flex items-center gap-2">
          <Calendar className="h-3.5 w-3.5 text-brand-primary" /> Hourly Request Distribution (24 Hours)
        </h4>
        <div className="h-56 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={hourlyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="name" stroke="#9ca3af" fontSize={10} interval={1} />
              <YAxis stroke="#9ca3af" fontSize={11} allowDecimals={false} />
              <Tooltip contentStyle={{ backgroundColor: '#1f2937', borderColor: '#4b5563', color: '#fff', borderRadius: '8px' }} />
              <Bar dataKey="count" name="Request Volume" fill="#6366f1" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
