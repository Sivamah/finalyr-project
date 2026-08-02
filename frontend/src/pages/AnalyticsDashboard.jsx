import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { BarChart3, RefreshCw, Zap, ShieldCheck } from 'lucide-react';
import api from '../services/api';
import toast from 'react-hot-toast';

import AnalyticsFilters from '../components/analytics/AnalyticsFilters';
import KPICards from '../components/analytics/KPICards';
import AnalyticsCharts from '../components/analytics/AnalyticsCharts';
import RequestAnalytics from '../components/analytics/RequestAnalytics';
import ProviderAnalytics from '../components/analytics/ProviderAnalytics';
import TimeAnalytics from '../components/analytics/TimeAnalytics';
import ReportExport from '../components/analytics/ReportExport';

export default function AnalyticsDashboard() {
  const [filters, setFilters] = useState({
    preset: 'all', // 'all' | 'today' | 'hour'
    requestType: 'All', // 'All' | 'ride' | 'food' | 'parcel'
    providerId: '0', // '0' or provider ID string
    status: 'All', // 'All' | 'Pending' | 'Completed'
  });

  const [analyticsData, setAnalyticsData] = useState({
    kpi: {},
    charts: {},
    request_analytics: {},
    provider_analytics: {},
    time_analytics: {},
    timestamp: '',
  });

  const [providers, setProviders] = useState([]);
  const [loading, setLoading] = useState(true);
  const pollRef = useRef(null);

  // Fetch Providers List once for filter dropdown
  useEffect(() => {
    const fetchProviders = async () => {
      try {
        const res = await api.get('/providers/');
        setProviders(res.data || []);
      } catch (err) {
        console.error('Failed to load providers:', err);
      }
    };
    fetchProviders();
  }, []);

  // Fetch Analytics Data
  const fetchAnalytics = useCallback(async () => {
    try {
      // Build query params
      const params = new URLSearchParams();
      if (filters.requestType !== 'All') params.append('request_type', filters.requestType);
      if (filters.providerId !== '0') params.append('provider_id', filters.providerId);
      if (filters.status !== 'All') params.append('status', filters.status);

      if (filters.preset === 'today') {
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        params.append('start_date', today.toISOString());
      } else if (filters.preset === 'hour') {
        const oneHourAgo = new Date(Date.now() - 3600 * 1000);
        params.append('start_date', oneHourAgo.toISOString());
      }

      const res = await api.get(`/simulation/advanced-analytics?${params.toString()}`);
      setAnalyticsData(res.data || {});
    } catch (err) {
      console.error('Failed to fetch advanced analytics:', err);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  // Polling setup: 2.5s interval
  useEffect(() => {
    fetchAnalytics();
    pollRef.current = setInterval(fetchAnalytics, 2500);
    return () => clearInterval(pollRef.current);
  }, [fetchAnalytics]);

  // Filter Change Handlers
  const handleFilterChange = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const handleResetFilters = () => {
    setFilters({
      preset: 'all',
      requestType: 'All',
      providerId: '0',
      status: 'All',
    });
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <BarChart3 className="h-6 w-6 text-indigo-400" />
            Advanced Analytics & Reporting
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Real-time operational insights, provider throughput, and transportation request metrics
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Live Auto-Refresh Indicator */}
          <div className="flex items-center gap-1.5 px-3 py-1.5 bg-green-500/10 border border-green-500/30 rounded-lg text-xs font-semibold text-green-400">
            <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
            Live Auto-Refresh (2.5s)
          </div>

          {/* Export Report Component */}
          <ReportExport analyticsData={analyticsData} filters={filters} />
        </div>
      </div>

      {/* 1. Filters */}
      <AnalyticsFilters
        filters={filters}
        onFilterChange={handleFilterChange}
        onResetFilters={handleResetFilters}
        providerOptions={providers}
      />

      {loading && !analyticsData.timestamp ? (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-indigo-500" />
        </div>
      ) : (
        <>
          {/* 2. KPI Cards */}
          <KPICards kpi={analyticsData.kpi} />

          {/* 3. Interactive Charts */}
          <AnalyticsCharts charts={analyticsData.charts} />

          {/* 4. Request Analytics Breakdown */}
          <RequestAnalytics data={analyticsData.request_analytics} />

          {/* 5. Provider Analytics */}
          <ProviderAnalytics data={analyticsData.provider_analytics} />

          {/* 6. Time & Temporal Analytics */}
          <TimeAnalytics data={analyticsData.time_analytics} />
        </>
      )}
    </div>
  );
}
