import React from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';
import { Clock, Timer, Zap, Calendar, TrendingUp } from 'lucide-react';

export default function TimeAnalytics({ data = {} }) {
  const avgWait = data.avg_queue_waiting_time_sec ?? 0;
  const avgCompletion = data.avg_completion_time_sec ?? 0;
  const peakHour = data.peak_request_hour || 'N/A';
  const hourlyData = data.hourly_distribution || [];
  const dailyData = data.daily_distribution || [];

  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-5 shadow-sm mb-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 border-b border-gray-700 pb-3">
        <h3 className="text-base font-bold text-white flex items-center gap-2">
          <Clock className="h-5 w-5 text-yellow-400" />
          Time & Temporal Analytics
        </h3>
        <span className="text-xs bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 px-2.5 py-1 rounded-full font-semibold">
          Latency & Hourly Load
        </span>
      </div>

      {/* Top 3 Summary Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {/* Avg Queue Waiting Time */}
        <div className="bg-gray-900/60 border border-gray-700/60 rounded-xl p-4 flex items-center justify-between">
          <div>
            <p className="text-xs text-gray-400 font-medium">Avg Queue Waiting Time</p>
            <p className="text-2xl font-bold text-yellow-400 font-mono mt-1">
              {avgWait} <span className="text-xs font-normal text-gray-400">sec</span>
            </p>
          </div>
          <div className="p-3 bg-yellow-500/10 rounded-lg text-yellow-400">
            <Clock className="h-6 w-6" />
          </div>
        </div>

        {/* Avg Completion Time */}
        <div className="bg-gray-900/60 border border-gray-700/60 rounded-xl p-4 flex items-center justify-between">
          <div>
            <p className="text-xs text-gray-400 font-medium">Avg Completion Time</p>
            <p className="text-2xl font-bold text-green-400 font-mono mt-1">
              {avgCompletion} <span className="text-xs font-normal text-gray-400">sec</span>
            </p>
          </div>
          <div className="p-3 bg-green-500/10 rounded-lg text-green-400">
            <Timer className="h-6 w-6" />
          </div>
        </div>

        {/* Peak Request Generation Hour */}
        <div className="bg-gray-900/60 border border-gray-700/60 rounded-xl p-4 flex items-center justify-between">
          <div>
            <p className="text-xs text-gray-400 font-medium">Peak Generation Hour</p>
            <p className="text-xl font-bold text-indigo-400 font-mono mt-1 truncate max-w-[180px]" title={peakHour}>
              {peakHour}
            </p>
          </div>
          <div className="p-3 bg-indigo-500/10 rounded-lg text-indigo-400">
            <Zap className="h-6 w-6" />
          </div>
        </div>
      </div>

      {/* Hourly Request Distribution Chart */}
      <div>
        <h4 className="text-xs font-semibold text-gray-300 uppercase tracking-wider mb-3 flex items-center gap-2">
          <Calendar className="h-4 w-4 text-indigo-400" /> Hourly Request Distribution (24 Hours)
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
