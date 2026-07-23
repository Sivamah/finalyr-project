import { Outlet, Link, useNavigate } from 'react-router-dom';
import { useContext, useState } from 'react';
import { AuthContext } from '../context/AuthContext';
import { WebSocketContext } from '../context/WebSocketContext';
import { LogOut, User, Zap, LayoutDashboard, Bell } from 'lucide-react';
import NotificationPanel from './notifications/NotificationPanel';

const DASHBOARD_ROUTES = {
  Admin:    '/admin',
  Driver:   '/driver',
  Customer: '/customer',
};

export default function Layout() {
  const { user, logout } = useContext(AuthContext);
  const { notifications } = useContext(WebSocketContext) || { notifications: [] };
  const navigate = useNavigate();
  const [showNotifications, setShowNotifications] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const dashRoute = user ? DASHBOARD_ROUTES[user.role] : null;

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <nav className="bg-white border-b border-gray-100 sticky top-0 z-40 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            {/* Brand */}
            <div className="flex items-center">
              <Link to="/" className="flex items-center gap-2 text-xl font-bold text-violet-700">
                <div className="p-1.5 bg-violet-600 rounded-lg">
                  <Zap className="h-5 w-5 text-white" />
                </div>
                <span>DMFE System</span>
              </Link>
            </div>

            {/* Right */}
            <div className="flex items-center gap-3">
              {user ? (
                <>
                  <div className="hidden sm:flex items-center gap-2 text-sm text-gray-600">
                    <div className="w-7 h-7 rounded-full bg-violet-100 flex items-center justify-center">
                      <User className="h-4 w-4 text-violet-600" />
                    </div>
                    <span className="font-medium">{user.full_name}</span>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-semibold
                      ${user.role === 'Admin'  ? 'bg-red-100 text-red-700' :
                        user.role === 'Driver' ? 'bg-violet-100 text-violet-700' :
                                                  'bg-blue-100 text-blue-700'}`}>
                      {user.role}
                    </span>
                  </div>

                  {dashRoute && (
                    <Link
                      to={dashRoute}
                      className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-medium text-violet-700 hover:bg-violet-50 transition-colors"
                    >
                      <LayoutDashboard className="h-4 w-4" />
                      <span className="hidden sm:inline">Dashboard</span>
                    </Link>
                  )}
                  
                  {/* Notification Bell */}
                  <div className="relative">
                    <button
                      onClick={() => setShowNotifications(!showNotifications)}
                      className="relative p-2 rounded-xl text-gray-500 hover:bg-gray-100 transition-colors"
                    >
                      <Bell className="h-5 w-5" />
                      {notifications?.filter(n => !n.is_read).length > 0 && (
                        <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full"></span>
                      )}
                    </button>
                    {showNotifications && (
                      <NotificationPanel onClose={() => setShowNotifications(false)} />
                    )}
                  </div>

                  <button
                    onClick={handleLogout}
                    className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-medium text-white
                      bg-violet-600 hover:bg-violet-700 transition-colors shadow-sm"
                  >
                    <LogOut className="h-4 w-4" />
                    <span className="hidden sm:inline">Logout</span>
                  </button>
                </>
              ) : (
                <>
                  <Link to="/login" className="text-gray-600 hover:text-violet-700 px-3 py-2 text-sm font-medium transition-colors">
                    Login
                  </Link>
                  <Link to="/register"
                    className="bg-violet-600 text-white hover:bg-violet-700 px-4 py-2 rounded-xl text-sm font-semibold transition-colors shadow-sm">
                    Register
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>
      </nav>

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 flex flex-col">
        <Outlet />
      </main>

      <footer className="border-t border-gray-100 py-4 text-center text-xs text-gray-400 bg-white">
        DMFE System — AI-Powered Unified Mobility & Delivery · Phase 2
      </footer>
    </div>
  );
}
