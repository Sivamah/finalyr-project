import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Bell, CheckCheck, Trash2, Activity } from 'lucide-react';
import api from '../services/api';
import toast from 'react-hot-toast';

import NotificationStatistics from '../components/notifications/NotificationStatistics';
import NotificationFilters from '../components/notifications/NotificationFilters';
import NotificationCard from '../components/notifications/NotificationCard';
import ActivityTimeline from '../components/notifications/ActivityTimeline';
import PageHeader from '../components/ui/PageHeader';
import StatusBadge from '../components/ui/StatusBadge';

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
    }
  }, [search, filters]);

  // Polling: 2.5s
  useEffect(() => {
    fetchData();
    pollRef.current = setInterval(() => { if (document.visibilityState === 'visible') fetchData(); }, 2500);
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
    <div className="space-y-6 pb-10 max-w-[1500px] mx-auto">
      <PageHeader
        eyebrow="System"
        live
        title="Activity Center"
        description="Real-time simulation alerts, system events and the chronological activity stream."
        actions={
          <div className="flex flex-wrap items-center gap-2.5">
            <StatusBadge tone="success" label="Auto-refresh 2.5s" pulse />
            <button onClick={handleMarkAllRead} className="btn-primary">
              <CheckCheck className="h-4 w-4" /> Mark All as Read
            </button>
            <button onClick={handleClearAll} className="btn-glass !text-brand-danger">
              <Trash2 className="h-4 w-4" /> Clear All
            </button>
          </div>
        }
      />

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
        <div className="glass-panel rounded-[18px] p-1.5 flex items-center gap-1.5 w-fit overflow-x-auto custom-scrollbar">
          <button
            onClick={() => setActiveTab('notifications')}
            className={`tab-pill ${activeTab === 'notifications' ? 'tab-pill-active' : ''}`}
          >
            <Bell className="h-4 w-4" />
            Active Notifications
            <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-bold ${activeTab === 'notifications' ? 'bg-white/15 text-white' : 'bg-white/[0.06] text-brand-text-muted'}`}>
              {notifications.length}
            </span>
          </button>

          <button
            onClick={() => setActiveTab('timeline')}
            className={`tab-pill ${activeTab === 'timeline' ? 'tab-pill-active' : ''}`}
          >
            <Activity className="h-4 w-4" />
            Activity Timeline
            <span className={`px-1.5 py-0.5 rounded-full text-[10px] font-bold ${activeTab === 'timeline' ? 'bg-white/15 text-white' : 'bg-white/[0.06] text-brand-text-muted'}`}>
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
