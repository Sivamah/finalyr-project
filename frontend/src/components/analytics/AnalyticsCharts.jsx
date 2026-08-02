import React from 'react';
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import { TrendingUp, Layers, Building2, Activity, CheckCircle2 } from 'lucide-react';

const PIE_COLORS = ['#3b82f6', '#f97316', '#a855f7', '#10b981', '#ec4899', '#6366f1'];

export default function AnalyticsCharts({ charts = {} }) {
  const genTrend = charts.request_generation_trend || [];
  const typeDist = charts.request_type_distribution || [];
  const provDist = charts.provider_distribution || [];
  const queueTrend = charts.queue_size_trend || [];
  const compTrend = charts.completed_requests_trend || [];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
      {/* 1. Request Generation Trend (Line Chart) */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-5 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-indigo-400" />
            Request Generation Trend
          </h3>
          <span className="text-xs text-gray-400">Line Chart</span>
        </div>
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={genTrend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="time" stroke="#9ca3af" fontSize={11} />
              <YAxis stroke="#9ca3af" fontSize={11} allowDecimals={false} />
              <Tooltip contentStyle={{ backgroundColor: '#1f2937', borderColor: '#4b5563', color: '#fff', borderRadius: '8px' }} />
              <Line type="monotone" dataKey="count" name="Generated Requests" stroke="#6366f1" strokeWidth={2.5} dot={{ r: 3 }} activeDot={{ r: 6 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 2. Request Type Distribution (Pie / Donut Chart) */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-5 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <Layers className="h-4 w-4 text-blue-400" />
            Request Type Distribution
          </h3>
          <span className="text-xs text-gray-400">Ride / Food / Parcel</span>
        </div>
        <div className="h-64 w-full flex items-center justify-center">
          {typeDist.length === 0 ? (
            <p className="text-sm text-gray-500">No category data yet</p>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={typeDist}
                  dataKey="count"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={85}
                  paddingAngle={4}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                >
                  {typeDist.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ backgroundColor: '#1f2937', borderColor: '#4b5563', color: '#fff', borderRadius: '8px' }} />
                <Legend wrapperStyle={{ color: '#9ca3af', fontSize: '12px' }} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* 3. Provider Distribution (Bar Chart) */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-5 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <Building2 className="h-4 w-4 text-orange-400" />
            Provider Distribution
          </h3>
          <span className="text-xs text-gray-400">Bar Chart</span>
        </div>
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={provDist}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="name" stroke="#9ca3af" fontSize={11} />
              <YAxis stroke="#9ca3af" fontSize={11} allowDecimals={false} />
              <Tooltip contentStyle={{ backgroundColor: '#1f2937', borderColor: '#4b5563', color: '#fff', borderRadius: '8px' }} />
              <Bar dataKey="count" name="Requests Handled" fill="#f97316" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 4. Queue Size Trend (Area Chart) */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-5 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <Activity className="h-4 w-4 text-yellow-400" />
            Queue Size Trend
          </h3>
          <span className="text-xs text-gray-400">Area Chart</span>
        </div>
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={queueTrend}>
              <defs>
                <linearGradient id="queueGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#eab308" stopOpacity={0.8} />
                  <stop offset="95%" stopColor="#eab308" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="time" stroke="#9ca3af" fontSize={11} />
              <YAxis stroke="#9ca3af" fontSize={11} allowDecimals={false} />
              <Tooltip contentStyle={{ backgroundColor: '#1f2937', borderColor: '#4b5563', color: '#fff', borderRadius: '8px' }} />
              <Area type="monotone" dataKey="count" name="Queue Size" stroke="#eab308" strokeWidth={2} fillOpacity={1} fill="url(#queueGrad)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 5. Completed Requests Trend (Line Chart) */}
      <div className="bg-gray-800 border border-gray-700 rounded-xl p-5 shadow-sm lg:col-span-2">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-green-400" />
            Completed Requests Trend over Time
          </h3>
          <span className="text-xs text-gray-400">Throughput Analysis</span>
        </div>
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={compTrend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="time" stroke="#9ca3af" fontSize={11} />
              <YAxis stroke="#9ca3af" fontSize={11} allowDecimals={false} />
              <Tooltip contentStyle={{ backgroundColor: '#1f2937', borderColor: '#4b5563', color: '#fff', borderRadius: '8px' }} />
              <Line type="monotone" dataKey="count" name="Completed Requests" stroke="#10b981" strokeWidth={2.5} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
