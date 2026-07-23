import React, { createContext, useContext, useEffect, useState, useRef } from 'react';
import { AuthContext } from './AuthContext';
import toast from 'react-hot-toast';

export const WebSocketContext = createContext(null);

export function WebSocketProvider({ children }) {
  const { user, token } = useContext(AuthContext);
  const [socket, setSocket] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [liveLocation, setLiveLocation] = useState(null);
  const ws = useRef(null);

  useEffect(() => {
    if (!token) {
      if (ws.current) {
        ws.current.close();
        ws.current = null;
      }
      return;
    }

    const connectWs = () => {
      // Assuming backend runs on port 8000
      const wsUrl = `ws://localhost:8000/api/ws/track?token=${token}`;
      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        console.log('WebSocket connected');
        setSocket(ws.current);
      };

      ws.current.onmessage = (event) => {
        const payload = JSON.parse(event.data);
        if (payload.event === 'NOTIFICATION') {
          setNotifications(prev => [payload.data, ...prev]);
          toast.success(payload.data.title + ": " + payload.data.message, {
            icon: '🔔',
            duration: 4000,
            position: 'top-right'
          });
        } else if (payload.event === 'LOCATION_UPDATE') {
          setLiveLocation(payload.data);
        }
      };

      ws.current.onclose = () => {
        console.log('WebSocket disconnected. Reconnecting in 3s...');
        setSocket(null);
        setTimeout(connectWs, 3000);
      };
    };

    connectWs();

    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [token]);

  return (
    <WebSocketContext.Provider value={{ socket, notifications, setNotifications, liveLocation }}>
      {children}
    </WebSocketContext.Provider>
  );
}
