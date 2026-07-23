import React, { useContext, useEffect, useState } from 'react';
import { WebSocketContext } from '../../context/WebSocketContext';
import { MapPin, Navigation2, CheckCircle2, Clock, Map as MapIcon, Loader2 } from 'lucide-react';
import { GoogleMap, useJsApiLoader, Marker } from '@react-google-maps/api';

const containerStyle = {
  width: '100%',
  height: '100%'
};

export default function LiveTracking({ tripId, pickup, drop, status }) {
  const { liveLocation } = useContext(WebSocketContext) || { liveLocation: null };
  const [driverLoc, setDriverLoc] = useState(null);

  const { isLoaded } = useJsApiLoader({
    id: 'google-map-script',
    googleMapsApiKey: import.meta.env.VITE_GOOGLE_MAPS_API_KEY || ''
  });

  // Default to Bangalore
  const [center, setCenter] = useState({ lat: 12.9716, lng: 77.5946 });

  useEffect(() => {
    if (liveLocation && liveLocation.trip_id === tripId) {
      setDriverLoc({ lat: liveLocation.lat, lng: liveLocation.lng });
      setCenter({ lat: liveLocation.lat, lng: liveLocation.lng });
    }
  }, [liveLocation, tripId]);

  // Set initial bounds to fit pickup and drop
  const onLoad = (map) => {
    if (pickup && drop) {
      const bounds = new window.google.maps.LatLngBounds();
      bounds.extend({ lat: pickup.lat, lng: pickup.lng });
      bounds.extend({ lat: drop.lat, lng: drop.lng });
      map.fitBounds(bounds);
    }
  };

  const getTimelineSteps = () => [
    { label: 'Booking Confirmed', completed: true },
    { label: 'Driver Assigned',   completed: ['Accepted', 'In_Progress', 'Completed'].includes(status) },
    { label: 'Driver En Route',   completed: ['In_Progress', 'Completed'].includes(status) },
    { label: 'Completed',         completed: status === 'Completed' }
  ];

  return (
    <div className="bg-white rounded-2xl shadow-xl border border-gray-100 overflow-hidden mt-6">
      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 p-4 text-white flex items-center justify-between">
        <div className="flex items-center gap-2 font-bold">
          <Navigation2 className="h-5 w-5" />
          Live Tracking (Trip #{tripId})
        </div>
        <div className="text-xs font-semibold bg-white/20 px-2 py-1 rounded-md">
          {status.replace('_', ' ')}
        </div>
      </div>
      
      <div className="p-4 grid md:grid-cols-3 gap-6">
        {/* Timeline */}
        <div className="md:col-span-1 space-y-6">
          <h4 className="font-semibold text-gray-800 mb-4">Trip Progress</h4>
          <div className="relative border-l-2 border-gray-200 ml-3 space-y-6">
            {getTimelineSteps().map((step, idx) => (
              <div key={idx} className="relative pl-6">
                <div className={`absolute -left-[9px] top-0 w-4 h-4 rounded-full border-2 bg-white
                  ${step.completed ? 'border-emerald-500 bg-emerald-500' : 'border-gray-300'}`} 
                />
                <h5 className={`text-sm font-semibold ${step.completed ? 'text-gray-900' : 'text-gray-400'}`}>
                  {step.label}
                </h5>
                {step.completed && idx === getTimelineSteps().findIndex(s => !s.completed) - 1 && (
                  <p className="text-xs text-emerald-600 font-medium mt-1 animate-pulse flex items-center gap-1">
                    <Loader2 className="h-3 w-3 animate-spin" /> In progress...
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Map */}
        <div className="md:col-span-2 h-72 bg-gray-50 rounded-xl overflow-hidden border border-gray-200 relative">
          {!isLoaded ? (
            <div className="flex items-center justify-center h-full">
              <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
            </div>
          ) : (
            <GoogleMap
              mapContainerStyle={containerStyle}
              center={center}
              zoom={13}
              onLoad={onLoad}
              options={{ disableDefaultUI: true, zoomControl: true }}
            >
              {pickup && (
                <Marker position={{ lat: pickup.lat, lng: pickup.lng }} icon="http://maps.google.com/mapfiles/ms/icons/green-dot.png" />
              )}
              {drop && (
                <Marker position={{ lat: drop.lat, lng: drop.lng }} icon="http://maps.google.com/mapfiles/ms/icons/red-dot.png" />
              )}
              {driverLoc && (
                <Marker position={driverLoc} icon="http://maps.google.com/mapfiles/ms/icons/blue-dot.png" />
              )}
            </GoogleMap>
          )}
        </div>
      </div>
    </div>
  );
}
