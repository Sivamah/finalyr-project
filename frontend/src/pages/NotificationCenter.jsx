import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Bell, CheckCheck, Trash2, RefreshCw, Activity, ListFilter, AlertCircle } from 'lucide-react';
import api from '../services/api';
import toast from 'react-hot-toast';

import NotificationStatistics from '../components/notifications/NotificationStatistics';
import NotificationFilters from '../components/notifications/NotificationFilters';
import NotificationCard from '../components/notifications/NotificationCard';
import ActivityTimeline from '../components/notifications/ActivityTimeline';

export default function NotificationCenter() {
  const [search, setSearch] = useState('');
  const [filters, setFilters] = useState({
    category: 'All',
    readStatus: 'All',
    date: 'All',
  });

  const [notifications, setNotifications] = useState([]);
  const [stats, setStats] = useState({});
  const [timeline, setTimeline] = useState([]);
  const [activeTab, setActiveTab] = useState('notifications'); // 'notifications' | 'timeline'
  const [loading, setLoading] = useState(true);

  const pollRef = useRef(null);

  // Fetch all notification data
  const fetchData = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (search) params.append('search', search);
      if (filters.category !== 'All') params.append('category', filters.category);
      if (filters.readStatus !== 'All') params.append('read_status', filters.readStatus);
      if (filters.date !== 'All') params.append('date', filters.date);

      const [listRes, statsRes, timelineRes] = await Promise.all([
        api.get(`/notifications?${params.toString()}`),
        api.get('/notifications/stats'),
        api.get('/notifications/timeline?limit=100'),
      ]);

      setNotifications(listRes.data.items || []);
      setStats(statsRes.data || {});
      setTimeline(timelineRes.data || []);
    } catch (err) {
      console.error('Failed to fetch notification data:', err);
    } finally {
      setLoading(false);
    }
  }, [search, filters]);

  // Polling: 2.5s
  useEffect(() => {
    fetchData();
    pollRef.current = setInterval(fetchData, 2500);
    return () => clearInterval(pollRef.current);
  }, [fetchData]);

  // Filter change handlers
  const handleFilterChange = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const handleResetFilters = () => {
    setSearch('');
    setFilters({ category: 'All', readStatus: 'All', date: 'All' });
  };

  // Notification Actions
  const handleMarkRead = async (id) => {
    try {
      await api.patch(`/notifications/${id}/read`);
      fetchData();
      toast.success('Marked as read');
    } catch {
      toast.error('Failed to mark notification as read');
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await api.patch('/notifications/read-all');
      fetchData();
      toast.success('All notifications marked as read');
    } catch {
      toast.error('Failed to mark all as read');
    }
  };

  const handleDelete = async (id) => {
    try {
      await api.delete(`/notifications/${id}`);
      fetchData();
      toast.success('Notification deleted');
    } catch {
      toast.error('Failed to delete notification');
    }
  };

  const handleClearAll = async () => {
    if (!confirm('Are you sure you want to clear all notifications?')) return;
    try {
      await api.delete('/notifications/clear-all');
      fetchData();
      toast.success('All notifications cleared');
    } catch {
      toast.error('Failed to clear notifications');
    }
  };

  return (
    <div className="space-y-6 pb-12">
      {/* ── Page Header ────────────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Bell className="h-6 w-6 text-indigo-400" />
            Notification & Activity Center
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Real-time simulation alerts, system event telemetry, and chronological activity logs
          </p>
        </div>

        {/* Actions Toolbar */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Live Indicator */}
          <div className="flex items-center gap-1.5 px-3 py-2 bg-green-500/10 border border-green-500/30 rounded-lg text-xs font-semibold text-green-400 mr-1">
            <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
            Live Auto-Refresh (2.5s)
          </div>

          <button
            onClick={handleMarkAllRead}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg text-xs transition-colors shadow-sm"
          >
            <CheckCheck className="h-4 w-4" /> Mark All as Read
          </button>

          <button
            onClick={handleClearAll}
            className="flex items-center gap-1.5 px-3.5 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 text-red-400 font-medium rounded-lg text-xs transition-colors"
          >
            <Trash2 className="h-4 w-4" /> Clear All
          </button>
        </div>
      </div>

      {/* ── 1. Statistics Metric Cards ────────────────────────────────────────── */}
      <NotificationStatistics stats={stats} />

      {/* ── 2. Search & Filter Bar ───────────────────────────────────────────── */}
      <NotificationFilters
        search={search}
        onSearchChange={setSearch}
        filters={filters}
        onFilterChange={handleFilterChange}
        onResetFilters={handleResetFilters}
      />

      {/* ── 3. Tabbed View: Notifications Panel vs Activity Timeline ──────────── */}
      <div className="space-y-4">
        {/* Tabs Bar */}
        <div className="flex items-center border-b border-gray-700">
          <button
            onClick={() => setActiveTab('notifications')}
            className={`flex items-center gap-2 py-3 px-4 font-bold text-sm border-b-2 transition-colors ${
              activeTab === 'notifications'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            <Bell className="h-4 w-4" />
            Active Notifications
            <span className="px-2 py-0.5 rounded-full text-xs bg-indigo-500/20 text-indigo-400 font-bold">
              {notifications.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('timeline')}
            className={`flex items-center gap-2 py-3 px-4 font-bold text-sm border-b-2 transition-colors ${
              activeTab === 'timeline'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-gray-400 hover:text-gray-200'
            }`}
          >
            <Activity className="h-4 w-4" />
            Activity Timeline Log
            <span className="px-2 py-0.5 rounded-full text-xs bg-green-500/20 text-green-400 font-bold">
              {timeline.length}
            </span>
          </button>
        </div>

        {/* Tab 1: Notifications List */}
        {activeTab === 'notifications' && (
          <div className="space-y-3">
            {notifications.length === 0 ? (
              <div className="bg-gray-800 border border-gray-700 rounded-xl p-16 text-center text-gray-500">
                <Bell className="h-10 w-10 mx-auto mb-2 opacity-40" />
                <p className="text-base font-medium">No notifications found</p>
                <p className="text-xs text-gray-600 mt-1">Start the simulation or clear your filters to view new alerts</p>
              </div>
            ) : (
              notifications.map((item) => (
                <NotificationCard
                  key={item.id}
                  notification={item}
                  onMarkRead={handleMarkRead}
                  onDelete={handleDelete}
                />
              ))
            )}
          </div>
        )}

        {/* Tab 2: Activity Timeline */}
        {activeTab === 'timeline' && (
          <ActivityTimeline timeline={timeline} />
        )}
      </div>
    </div>
  );
}
