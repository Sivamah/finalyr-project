import React, { useContext, useState, useEffect } from 'react';
import { Bell, CheckCircle2, XCircle, Info, Loader2 } from 'lucide-react';
import { WebSocketContext } from '../../context/WebSocketContext';
import api from '../../services/api';

export default function NotificationPanel({ onClose }) {
  const { notifications, setNotifications } = useContext(WebSocketContext);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Fetch historical notifications
    const fetchHistory = async () => {
      setLoading(true);
      try {
        const res = await api.get('/notifications');
        // Merge with existing real-time notifications to avoid duplicates
        const existingIds = new Set(notifications.map(n => n.id));
        const newHistory = res.data.filter(n => !existingIds.has(n.id));
        if (newHistory.length > 0) {
          setNotifications(prev => [...prev, ...newHistory].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)));
        }
      } catch (err) {
        console.error('Failed to load notifications', err);
      }
      setLoading(false);
    };

    fetchHistory();
  }, []);

  const markAsRead = async (id) => {
    try {
      await api.put(`/notifications/${id}/read`);
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
    } catch (err) {
      console.error('Failed to mark as read', err);
    }
  };

  const getIcon = (type) => {
    switch (type) {
      case 'SUCCESS': return <CheckCircle2 className="h-5 w-5 text-emerald-500" />;
      case 'WARNING': return <Info className="h-5 w-5 text-amber-500" />;
      case 'ERROR':   return <XCircle className="h-5 w-5 text-red-500" />;
      default:        return <Info className="h-5 w-5 text-blue-500" />;
    }
  };

  const unreadCount = notifications.filter(n => !n.is_read).length;

  return (
    <div className="absolute right-0 top-12 w-80 bg-white rounded-2xl shadow-2xl border border-gray-100 z-50 overflow-hidden flex flex-col max-h-[500px]">
      <div className="bg-slate-800 p-4 text-white flex justify-between items-center">
        <h3 className="font-bold flex items-center gap-2">
          <Bell className="h-4 w-4" /> Notifications
          {unreadCount > 0 && (
            <span className="bg-red-500 text-white text-[10px] font-bold px-2 py-0.5 rounded-full">
              {unreadCount} New
            </span>
          )}
        </h3>
        {onClose && (
          <button onClick={onClose} className="text-slate-400 hover:text-white">
            <XCircle className="h-4 w-4" />
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {loading && notifications.length === 0 ? (
          <div className="flex justify-center p-8">
            <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
          </div>
        ) : notifications.length === 0 ? (
          <div className="p-8 text-center text-gray-500 text-sm">
            <Bell className="h-8 w-8 text-gray-200 mx-auto mb-2" />
            No new notifications
          </div>
        ) : (
          <div className="space-y-1">
            {notifications.map(n => (
              <div 
                key={n.id} 
                className={`p-3 rounded-xl border ${n.is_read ? 'bg-gray-50 border-transparent opacity-60' : 'bg-white border-blue-100 shadow-sm'} transition-colors cursor-pointer`}
                onClick={() => !n.is_read && markAsRead(n.id)}
              >
                <div className="flex gap-3">
                  <div className="mt-0.5 shrink-0">{getIcon(n.type)}</div>
                  <div>
                    <h4 className={`text-sm font-bold ${n.is_read ? 'text-gray-700' : 'text-gray-900'}`}>{n.title}</h4>
                    <p className="text-xs text-gray-500 mt-1">{n.message}</p>
                    <p className="text-[10px] text-gray-400 mt-2">
                      {new Date(n.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
