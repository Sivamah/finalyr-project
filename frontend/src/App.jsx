import React, { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AuthProvider } from './context/AuthContext';
import AdminLayout from './components/AdminLayout';
import ProtectedRoute from './components/ProtectedRoute';

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
  <div className="flex h-screen w-full items-center justify-center bg-gray-900">
    <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"></div>
  </div>
);

function App() {
  return (
    <AuthProvider>
      <Router>
        <Toaster position="top-right" toastOptions={{ duration: 4000, style: { borderRadius: '12px' } }} />
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
