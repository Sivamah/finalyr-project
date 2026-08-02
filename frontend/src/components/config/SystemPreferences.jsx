import React from 'react';
import { Sliders, Sun, Globe, Clock, Calendar, RefreshCw } from 'lucide-react';

export default function SystemPreferences({ config = {}, onChange }) {
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 shadow-sm space-y-6">
      <div className="border-b border-gray-700 pb-3">
        <h3 className="text-base font-bold text-white flex items-center gap-2">
          <Sliders className="h-5 w-5 text-indigo-400" />
          System Preferences & Display Localization
        </h3>
        <p className="text-xs text-gray-400 mt-0.5">
          Configure interface theme, locale language, date formatting, and live data polling frequencies
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Theme Preference */}
        <div>
          <label className="block text-xs font-semibold text-gray-300 mb-1 flex items-center gap-1.5">
            <Sun className="h-3.5 w-3.5 text-amber-400" />
            Interface Visual Theme
          </label>
          <select
            value={config.theme || 'Dark'}
            onChange={(e) => onChange('theme', e.target.value)}
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-medium"
          >
            <option value="Dark">Dark Mode (Default)</option>
            <option value="Light">Light Mode</option>
            <option value="System">Sync with System</option>
          </select>
          <p className="text-[11px] text-gray-500 mt-1">Application UI color scheme</p>
        </div>

        {/* Language */}
        <div>
          <label className="block text-xs font-semibold text-gray-300 mb-1 flex items-center gap-1.5">
            <Globe className="h-3.5 w-3.5 text-blue-400" />
            System Language
          </label>
          <select
            value={config.language || 'English'}
            onChange={(e) => onChange('language', e.target.value)}
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-medium"
          >
            <option value="English">English (US/UK)</option>
            <option value="Tamil">Tamil (தமிழ்)</option>
            <option value="Hindi">Hindi (हिन्दी)</option>
          </select>
          <p className="text-[11px] text-gray-500 mt-1">Primary language for dashboard labels and export reports</p>
        </div>

        {/* Time Zone */}
        <div>
          <label className="block text-xs font-semibold text-gray-300 mb-1 flex items-center gap-1.5">
            <Clock className="h-3.5 w-3.5 text-green-400" />
            Time Zone
          </label>
          <select
            value={config.time_zone || 'Asia/Kolkata (IST)'}
            onChange={(e) => onChange('time_zone', e.target.value)}
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-medium"
          >
            <option value="Asia/Kolkata (IST)">Asia/Kolkata (IST - UTC+5:30)</option>
            <option value="UTC">Coordinated Universal Time (UTC)</option>
            <option value="America/New_York (EST)">America/New_York (EST - UTC-5:00)</option>
          </select>
          <p className="text-[11px] text-gray-500 mt-1">Timezone reference for telemetry log timestamps</p>
        </div>

        {/* Date Format */}
        <div>
          <label className="block text-xs font-semibold text-gray-300 mb-1 flex items-center gap-1.5">
            <Calendar className="h-3.5 w-3.5 text-indigo-400" />
            Date Format
          </label>
          <select
            value={config.date_format || 'YYYY-MM-DD'}
            onChange={(e) => onChange('date_format', e.target.value)}
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-medium"
          >
            <option value="YYYY-MM-DD">YYYY-MM-DD (ISO 8601)</option>
            <option value="DD/MM/YYYY">DD/MM/YYYY (UK/India)</option>
            <option value="MM/DD/YYYY">MM/DD/YYYY (US Standard)</option>
          </select>
          <p className="text-[11px] text-gray-500 mt-1">Date display formatting across tables and audit logs</p>
        </div>

        {/* Live Refresh Interval */}
        <div>
          <label className="block text-xs font-semibold text-gray-300 mb-1 flex items-center gap-1.5">
            <RefreshCw className="h-3.5 w-3.5 text-indigo-400" />
            Live Telemetry Refresh Interval (Seconds)
          </label>
          <input
            type="number"
            min="1.0"
            max="60.0"
            step="0.5"
            value={config.refresh_interval ?? 2.5}
            onChange={(e) => onChange('refresh_interval', parseFloat(e.target.value) || 2.5)}
            className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono"
          />
          <p className="text-[11px] text-gray-500 mt-1">Frontend polling frequency for live simulation dashboards</p>
        </div>
      </div>
    </div>
  );
}
