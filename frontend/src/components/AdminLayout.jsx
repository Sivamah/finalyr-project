import React, { useContext, useState, useEffect } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import {
  LayoutDashboard, Building2, Database, Cpu, LogOut, Menu, X, ChevronRight, Zap, MapPin, BarChart3, BrainCircuit, Bell, Users, Settings, Film, GitBranchPlus
} from 'lucide-react';
import api from '../services/api';

const NAV_ITEMS = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/providers', icon: Building2, label: 'Providers' },
  { to: '/datasets', icon: Database, label: 'Datasets' },
  { to: '/drivers', icon: Users, label: 'Drivers & Vehicles' },
  { to: '/simulation-monitor', icon: Zap, label: 'Simulation Monitor' },
  { to: '/analytics', icon: BarChart3, label: 'Analytics' },
  { to: '/xai', icon: BrainCircuit, label: 'Explainable AI' },
  { to: '/dmfe', icon: GitBranchPlus, label: 'DMFE Engine' },
  { to: '/playback', icon: Film, label: 'Playback & Scenarios' },
  { to: '/config', icon: Settings, label: 'System Config' },
  { to: '/notifications', icon: Bell, label: 'Notifications' },
  { to: '/live-map', icon: MapPin, label: 'Live Map' },
  { to: '/ai-orchestration', icon: Cpu, label: 'AI Orchestration' },
];

export default function AdminLayout() {
  const { user, logout } = useContext(AuthContext);
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

  // Poll unread notification count
  useEffect(() => {
    const fetchUnread = async () => {
      try {
        const res = await api.get('/notifications/stats');
        setUnreadCount(res.data?.unread_notifications || 0);
      } catch {
        // Silently catch error
      }
    };
    fetchUnread();
    const interval = setInterval(fetchUnread, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="flex h-screen bg-gray-900">
      {/* Sidebar */}
      <aside className={`fixed inset-y-0 left-0 z-50 w-64 bg-gray-800 border-r border-gray-700 transform transition-transform duration-200 lg:translate-x-0 lg:static lg:inset-auto ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex items-center justify-between h-16 px-6 border-b border-gray-700">
          <div className="flex items-center gap-3">
            <Cpu className="h-6 w-6 text-indigo-400" />
            <span className="font-bold text-lg text-white">AI Orchestrator</span>
          </div>
          <button onClick={() => setSidebarOpen(false)} className="lg:hidden text-gray-400 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>
        <nav className="p-4 space-y-1 overflow-y-auto max-h-[calc(100vh-8rem)]">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
                  isActive ? 'bg-indigo-600 text-white' : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                }`
              }
            >
              <item.icon className="h-5 w-5" />
              {item.label}
              {item.to === '/notifications' && unreadCount > 0 && (
                <span className="ml-auto px-2 py-0.5 rounded-full text-xs font-bold bg-indigo-500 text-white animate-pulse">
                  {unreadCount}
                </span>
              )}
              {item.to !== '/notifications' && <ChevronRight className="h-4 w-4 ml-auto opacity-50" />}
            </NavLink>
          ))}
        </nav>
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-700 bg-gray-800">
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-400 truncate">
              <p className="font-medium text-gray-300">{user?.full_name}</p>
              <p className="text-xs truncate">{user?.email}</p>
            </div>
            <button onClick={handleLogout} className="p-2 text-gray-400 hover:text-red-400 transition-colors" title="Logout">
              <LogOut className="h-5 w-5" />
            </button>
          </div>
        </div>
      </aside>

      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/50 z-40 lg:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Header */}
        <header className="h-16 border-b border-gray-700 bg-gray-800 flex items-center justify-between px-6">
          <div className="flex items-center gap-3">
            <button onClick={() => setSidebarOpen(true)} className="lg:hidden text-gray-400 hover:text-white">
              <Menu className="h-6 w-6" />
            </button>
            <div className="hidden lg:flex items-center gap-2">
              <Cpu className="h-5 w-5 text-indigo-400" />
              <span className="font-bold text-white">AI Orchestration Platform</span>
            </div>
          </div>

          {/* Top Header Actions (Notification Bell) */}
          <div className="flex items-center gap-4">
            <NavLink
              to="/notifications"
              className="relative p-2 text-gray-300 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
              title="Notifications & Activity Center"
            >
              <Bell className="h-5 w-5" />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white shadow">
                  {unreadCount > 99 ? '99+' : unreadCount}
                </span>
              )}
            </NavLink>
          </div>
        </header>

        <main className="flex-1 overflow-auto p-6 bg-gray-900">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
