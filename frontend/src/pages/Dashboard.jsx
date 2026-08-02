import React, { useState, useEffect } from 'react';
import { Building2, Truck, FileText, Cpu, Route, Fuel, Leaf } from 'lucide-react';
import api from '../services/api';

const StatCard = ({ icon: Icon, label, value, color }) => (
  <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
    <div className="flex items-center justify-between">
      <div>
        <p className="text-sm text-gray-400">{label}</p>
        <p className="text-2xl font-bold text-white mt-1">{value}</p>
      </div>
      <div className={`p-3 rounded-lg ${color}`}>
        <Icon className="h-6 w-6 text-white" />
      </div>
    </div>
  </div>
);

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetch = async () => {
      try {
        const res = await api.get('/dashboard/stats');
        setStats(res.data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetch();
  }, []);

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-8 w-8 border-t-2 border-indigo-500" /></div>;
  if (!stats) return <p className="text-gray-400">Failed to load stats</p>;

  const cards = [
    { icon: Building2, label: 'Total Providers', value: stats.total_providers, color: 'bg-blue-600' },
    { icon: Truck, label: 'Total Vehicles', value: stats.total_vehicles, color: 'bg-green-600' },
    { icon: FileText, label: 'Total Requests', value: stats.total_requests, color: 'bg-amber-600' },
    { icon: Cpu, label: 'AI Optimizations', value: stats.total_optimizations, color: 'bg-purple-600' },
    { icon: Route, label: 'Avg Route Savings', value: `${stats.avg_route_savings} km`, color: 'bg-cyan-600' },
    { icon: Fuel, label: 'Fuel Saved', value: `${stats.fuel_saved} L`, color: 'bg-orange-600' },
    { icon: Leaf, label: 'CO₂ Reduction', value: `${stats.co2_reduction} kg`, color: 'bg-emerald-600' },
  ];

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="text-gray-400 mt-1">AI Orchestration Platform Overview</p>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {cards.map((card) => (
          <StatCard key={card.label} {...card} />
        ))}
      </div>
    </div>
  );
}
