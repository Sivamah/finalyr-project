import React, { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AuthProvider } from './context/AuthContext';
import AdminLayout from './components/AdminLayout';
import ProtectedRoute from './components/ProtectedRoute';
import AnimatedBackground from './components/ui/AnimatedBackground';

const Login = lazy(() => import('./pages/Login'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const ProviderManagement = lazy(() => import('./pages/ProviderManagement'));
const DatasetManagement = lazy(() => import('./pages/DatasetManagement'));
const DriverDashboard = lazy(() => import('./pages/DriverDashboard'));
const SimulationMonitoring = lazy(() => import('./pages/SimulationMonitoring'));
const AnalyticsDashboard = lazy(() => import('./pages/AnalyticsDashboard'));
const ExplanationDashboard = lazy(() => import('./pages/ExplanationDashboard'));
const DMFEDashboard = lazy(() => import('./pages/DMFEDashboard'));
const SystemConfiguration = lazy(() => import('./pages/SystemConfiguration'));
const ScenarioDashboard = lazy(() => import('./pages/ScenarioDashboard'));
const NotificationCenter = lazy(() => import('./pages/NotificationCenter'));
const LiveSimulationMap = lazy(() => import('./pages/LiveSimulationMap'));
const AIDashboard = lazy(() => import('./pages/AIDashboard'));

const PageLoader = () => (
  <div className="flex h-screen w-full items-center justify-center bg-[#050816]">
    <div className="flex flex-col items-center gap-4">
      <div className="h-12 w-12 rounded-full border-2 border-white/10 border-t-brand-primary animate-spin shadow-[0_0_30px_rgba(59,130,246,0.25)]" />
      <p className="text-[10px] font-semibold tracking-[0.28em] text-brand-text-muted uppercase">A·DMFE</p>
    </div>
  </div>
);

function App() {
  return (
    <AuthProvider>
      <AnimatedBackground />
      <Router>
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              borderRadius: '14px',
              background: 'rgba(14, 22, 38, 0.92)',
              backdropFilter: 'blur(16px)',
              border: '1px solid rgba(255,255,255,0.1)',
              color: '#E4E9F2',
              fontSize: '13px',
              boxShadow: '0 16px 40px rgba(0,0,0,0.45)',
            },
          }}
        />
        <Suspense fallback={<PageLoader />}>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/" element={<ProtectedRoute><AdminLayout /></ProtectedRoute>}>
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="dashboard" element={<Dashboard />} />
              <Route path="providers" element={<ProviderManagement />} />
              <Route path="datasets" element={<DatasetManagement />} />
              <Route path="drivers" element={<DriverDashboard />} />
              <Route path="simulation-monitor" element={<SimulationMonitoring />} />
              <Route path="analytics" element={<AnalyticsDashboard />} />
              <Route path="xai" element={<ExplanationDashboard />} />
              <Route path="dmfe" element={<DMFEDashboard />} />
              <Route path="playback" element={<ScenarioDashboard />} />
              <Route path="config" element={<SystemConfiguration />} />
              <Route path="notifications" element={<NotificationCenter />} />
              <Route path="live-map" element={<LiveSimulationMap />} />
              <Route path="ai-orchestration" element={<AIDashboard />} />
            </Route>
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </Suspense>
      </Router>
    </AuthProvider>
  );
}

export default App;
