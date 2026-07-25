import React, { useContext, useEffect, useState } from 'react';
import { WebSocketContext } from '../../context/WebSocketContext';
import { Navigation2, Loader2 } from 'lucide-react';
import LeafletMapView from '../../components/maps/LeafletMapView';

export default function LiveTracking({ tripId, pickup, drop, status }) {
  const { liveLocation } = useContext(WebSocketContext) || { liveLocation: null };
  const [driverLoc, setDriverLoc] = useState(null);

  useEffect(() => {
    if (liveLocation && liveLocation.trip_id === tripId) {
      setDriverLoc({ lat: liveLocation.lat, lng: liveLocation.lng });
    }
  }, [liveLocation, tripId]);

  const getTimelineSteps = () => [
    { label: 'Booking Confirmed', completed: true },
    { label: 'Driver Assigned',   completed: ['Accepted', 'In_Progress', 'Completed'].includes(status) },
    { label: 'Driver En Route',   completed: ['In_Progress', 'Completed'].includes(status) },
    { label: 'Completed',         completed: status === 'Completed' }
  ];

  const markers = [];
  if (pickup) markers.push({ lat: pickup.lat, lng: pickup.lng, color: 'green', label: 'Pickup' });
  if (drop) markers.push({ lat: drop.lat, lng: drop.lng, color: 'red', label: 'Drop' });
  if (driverLoc) markers.push({ lat: driverLoc.lat, lng: driverLoc.lng, color: 'blue', label: 'Driver' });

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

        <div className="md:col-span-2 h-72 bg-gray-50 rounded-xl overflow-hidden border border-gray-200 relative">
          <LeafletMapView markers={markers} />
        </div>
      </div>
    </div>
  );
}
