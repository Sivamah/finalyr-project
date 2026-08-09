import React, { useContext, useState, useEffect } from 'react';
import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutDashboard, Radio, GitBranchPlus, Users, BarChart3, BrainCircuit,
  Film, Activity, Building2, Database, Settings, LogOut, Menu, X, Bell,
  Cpu, ChevronRight,
} from 'lucide-react';
import api from '../services/api';

const NAV_GROUPS = [
  {
    label: 'Operations',
    items: [
      { to: '/dashboard', icon: LayoutDashboard, label: 'Overview' },
      { to: '/live-map', icon: Radio, label: 'Live Operations' },
      { to: '/dmfe', icon: GitBranchPlus, label: 'Requests' },
      { to: '/drivers', icon: Users, label: 'Fleet' },
    ],
  },
  {
    label: 'Intelligence',
    items: [
      { to: '/analytics', icon: BarChart3, label: 'Analytics' },
      { to: '/xai', icon: BrainCircuit, label: 'AI Insights' },
      { to: '/playback', icon: Film, label: 'Reports' },
    ],
  },
  {
    label: 'System',
    items: [
      { to: '/simulation-monitor', icon: Activity, label: 'Simulation Monitor' },
      { to: '/providers', icon: Building2, label: 'Providers' },
      { to: '/datasets', icon: Database, label: 'Datasets' },
      { to: '/config', icon: Settings, label: 'Settings' },
    ],
  },
];

const ROUTE_TITLES = {
  '/dashboard': 'Overview',
  '/live-map': 'Live Operations',
  '/dmfe': 'Requests',
  '/drivers': 'Fleet',
  '/analytics': 'Analytics',
  '/xai': 'AI Insights',
  '/playback': 'Reports',
  '/simulation-monitor': 'Simulation Monitor',
  '/providers': 'Providers',
  '/datasets': 'Datasets',
  '/config': 'Settings',
  '/notifications': 'Activity Center',
};

function LiveClock() {
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);
  return (
    <div className="hidden md:flex items-center gap-2.5 pl-5 text-[12px] text-brand-text-secondary font-medium tabular-nums">
      <span>{now.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}</span>
      <span className="h-1 w-1 rounded-full bg-white/20" />
      <span className="text-white/90">
        {now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
      </span>
    </div>
  );
}

export default function AdminLayout() {
  const { user, logout } = useContext(AuthContext);
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const fetchUnread = async () => {
      try {
        const res = await api.get('/notifications/stats');
        if (!cancelled) setUnreadCount(res.data?.unread_notifications || 0);
      } catch { /* silent */ }
    };
    fetchUnread();
    const interval = setInterval(() => {
      if (document.visibilityState === 'visible') fetchUnread();
    }, 15000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const sectionTitle = ROUTE_TITLES[location.pathname] || 'Operations Platform';

  return (
    <div className="flex h-screen overflow-hidden text-brand-text font-sans">
      {/* ── Floating Sidebar ─────────────────────────────────────────────── */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}
      </AnimatePresence>

      <aside
        className={`fixed top-4 bottom-4 left-4 z-50 w-[272px] flex flex-col glass-panel-strong rounded-[28px] transition-transform duration-500 ease-[cubic-bezier(0.22,1,0.36,1)] lg:translate-x-0 lg:top-5 lg:bottom-5 lg:left-6 ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-[120%]'
        }`}
      >
        {/* Brand */}
        <div className="flex items-center gap-3.5 px-6 pt-7 pb-5">
          <div className="relative">
            <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-brand-primary/60 to-brand-accent/60 blur-md opacity-60" />
            <div className="relative h-11 w-11 rounded-2xl bg-gradient-to-br from-brand-primary to-brand-accent border border-white/20 flex items-center justify-center shadow-lg">
              <Cpu className="h-5 w-5 text-white drop-shadow" />
            </div>
          </div>
          <div className="flex flex-col">
            <span className="font-display font-semibold text-[16px] tracking-tight text-white leading-none">A·DMFE</span>
            <span className="text-[10px] text-brand-text-muted uppercase tracking-[0.18em] mt-1.5 font-medium">Operations Platform</span>
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden ml-auto text-brand-text-muted hover:text-white transition-colors"
            aria-label="Close menu"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto custom-scrollbar px-4 pb-4 space-y-6">
          {NAV_GROUPS.map((group) => (
            <div key={group.label}>
              <p className="px-3 mb-2 text-[10px] font-bold uppercase tracking-[0.16em] text-brand-text-muted">
                {group.label}
              </p>
              <div className="space-y-1">
                {group.items.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    onClick={() => setSidebarOpen(false)}
                    className="relative block"
                  >
                    {({ isActive }) => (
                      <span
                        className={`relative flex items-center gap-3 px-3.5 py-2.5 rounded-2xl text-[13px] font-medium transition-all duration-300 ${
                          isActive ? 'text-white' : 'text-brand-text-secondary hover:text-white hover:bg-white/[0.04]'
                        }`}
                      >
                        {isActive && (
                          <motion.span
                            layoutId="nav-active"
                            className="absolute inset-0 rounded-2xl bg-white/[0.08] border border-white/[0.12]"
                            transition={{ type: 'spring', stiffness: 350, damping: 30 }}
                          />
                        )}
                        {isActive && (
                          <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-full bg-gradient-to-b from-brand-primary to-brand-accent shadow-[0_0_12px_rgba(59,130,246,0.7)]" />
                        )}
                        <item.icon
                          className={`relative z-10 h-[18px] w-[18px] ${
                            isActive
                              ? 'text-brand-primary drop-shadow-[0_0_8px_rgba(59,130,246,0.6)]'
                              : 'text-brand-text-muted group-hover:text-white'
                          }`}
                        />
                        <span className="relative z-10 tracking-wide">{item.label}</span>
                        {isActive && (
                          <ChevronRight className="relative z-10 ml-auto h-3.5 w-3.5 text-brand-text-muted" />
                        )}
                      </span>
                    )}
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </nav>

        {/* System state */}
        <div className="px-5 pb-4">
          <div className="rounded-2xl border border-white/[0.07] bg-white/[0.03] p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-[11px] font-semibold text-brand-text-secondary tracking-wide">System Health</span>
              <span className="flex items-center gap-1.5">
                <span className="relative flex h-2 w-2">
                  <span className="absolute inline-flex h-full w-full rounded-full bg-brand-success opacity-60 animate-ping" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-brand-success shadow-[0_0_8px_rgba(16,185,129,0.8)]" />
                </span>
                <span className="text-[10px] font-semibold text-brand-success tracking-widest uppercase">Nominal</span>
              </span>
            </div>
            <div className="flex items-center justify-between text-[10.5px] text-brand-text-muted">
              <span>Adaptive engine</span>
              <span className="text-brand-text-secondary font-medium">98.4%</span>
            </div>
            <div className="mt-1.5 h-1 w-full rounded-full bg-white/[0.06] overflow-hidden">
              <div className="h-full rounded-full bg-gradient-to-r from-brand-primary to-brand-accent" style={{ width: '98.4%' }} />
            </div>
          </div>
        </div>

        {/* User */}
        <div className="px-5 pb-5">
          <div className="flex items-center gap-3 rounded-2xl border border-white/[0.07] bg-white/[0.03] p-3.5 group">
            <div className="relative h-9 w-9 shrink-0 rounded-full bg-gradient-to-br from-brand-primary to-brand-accent border border-white/20 flex items-center justify-center text-white text-[13px] font-semibold">
              {user?.full_name?.charAt(0) || 'A'}
              <span className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full bg-brand-success border-2 border-[#0E1626]" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-[13px] font-semibold text-white truncate">{user?.full_name || 'Admin User'}</p>
              <p className="text-[10.5px] text-brand-text-muted truncate">{user?.email || 'admin@admfe.io'}</p>
            </div>
            <button
              onClick={handleLogout}
              className="p-2 rounded-xl text-brand-text-muted hover:text-white hover:bg-white/[0.08] transition-all opacity-60 group-hover:opacity-100"
              title="Sign out"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* ── Main Column ──────────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 h-full lg:pl-[312px] p-4 md:p-5">
        {/* Floating Top Navigation */}
        <header className="h-14 shrink-0 glass-panel rounded-[20px] flex items-center justify-between px-4 md:px-6 mb-4 md:mb-6">
          <div className="flex items-center gap-3 min-w-0">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden btn-icon !h-9 !w-9"
              aria-label="Open menu"
            >
              <Menu className="h-4.5 w-4.5" />
            </button>
            <div className="min-w-0">
              <p className="text-[10px] text-brand-text-muted uppercase tracking-[0.16em] font-semibold hidden sm:block">
                Operations Platform
              </p>
              <h1 className="text-[15px] font-semibold text-white truncate leading-tight">{sectionTitle}</h1>
            </div>
          </div>

          <div className="flex items-center gap-2.5 md:gap-3">
            <LiveClock />

            <NavLink
              to="/notifications"
              className="relative btn-icon"
              title="Activity Center"
            >
              <Bell className="h-[17px] w-[17px]" />
              {unreadCount > 0 && (
                <span className="absolute -top-1 -right-1 h-3.5 w-3.5 rounded-full bg-brand-danger border-2 border-[#0E1626] shadow-[0_0_10px_rgba(239,68,68,0.8)] flex items-center justify-center">
                  <span className="text-[8px] font-bold text-white leading-none">{unreadCount > 9 ? '9+' : unreadCount}</span>
                </span>
              )}
            </NavLink>

            <div className="hidden sm:flex items-center gap-2.5 pl-2.5 border-l border-white/[0.08]">
              <div className="h-8 w-8 rounded-full bg-gradient-to-br from-brand-primary to-brand-accent border border-white/20 flex items-center justify-center text-white text-[12px] font-semibold">
                {user?.full_name?.charAt(0) || 'A'}
              </div>
              <div className="hidden xl:block leading-tight">
                <p className="text-[12px] font-semibold text-white">{user?.full_name || 'Admin User'}</p>
                <p className="text-[10px] text-brand-text-muted">Operator · System</p>
              </div>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto custom-scrollbar -mx-1 px-1">
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 14, filter: 'blur(4px)' }}
              animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
              exit={{ opacity: 0, y: -8, filter: 'blur(4px)' }}
              transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
              className="min-h-full pb-10"
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
}