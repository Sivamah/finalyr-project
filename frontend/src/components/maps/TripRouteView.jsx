import React, { useEffect, useState } from 'react';
import { Loader2, Route, Droplet, Clock } from 'lucide-react';
import routingService from '../../services/routingService';
import GoogleMapView from './GoogleMapView';
import toast from 'react-hot-toast';

export default function TripRouteView({ tripId }) {
  const [routeDetails, setRouteDetails] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchRoute = async () => {
      setLoading(true);
      try {
        const data = await routingService.getRouteDetails(tripId);
        setRouteDetails(data);
      } catch (err) {
        // If route not generated yet, try to generate it
        if (err.response?.status === 404) {
          try {
            const data = await routingService.optimizeRoute(tripId);
            setRouteDetails(data);
            toast.success("Route optimized successfully!");
          } catch (generateErr) {
            toast.error("Failed to optimize route for this trip.");
          }
        } else {
          toast.error("Failed to load route details.");
        }
      }
      setLoading(false);
    };

    if (tripId) fetchRoute();
  }, [tripId]);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-48 bg-gray-50 rounded-xl border border-gray-200">
        <Loader2 className="h-6 w-6 animate-spin text-violet-500" />
      </div>
    );
  }

  if (!routeDetails) {
    return (
      <div className="flex justify-center items-center h-48 bg-gray-50 rounded-xl border border-gray-200 text-gray-500 text-sm">
        No route data available for this trip.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Route Stats */}
      <div className="grid grid-cols-3 gap-3">
        <div className="bg-indigo-50 p-3 rounded-xl text-center">
          <Route className="h-5 w-5 text-indigo-500 mx-auto mb-1" />
          <p className="text-sm font-bold text-indigo-700">{routeDetails.total_distance_km.toFixed(1)} km</p>
          <p className="text-xs text-indigo-600/80 font-medium">Distance</p>
        </div>
        <div className="bg-emerald-50 p-3 rounded-xl text-center">
          <Clock className="h-5 w-5 text-emerald-500 mx-auto mb-1" />
          <p className="text-sm font-bold text-emerald-700">{Math.round(routeDetails.total_duration_mins)} min</p>
          <p className="text-xs text-emerald-600/80 font-medium">Est. Time</p>
        </div>
        <div className="bg-orange-50 p-3 rounded-xl text-center">
          <Droplet className="h-5 w-5 text-orange-500 mx-auto mb-1" />
          <p className="text-sm font-bold text-orange-700">{routeDetails.estimated_fuel_liters.toFixed(1)} L</p>
          <p className="text-xs text-orange-600/80 font-medium">Est. Fuel</p>
        </div>
      </div>

      {/* Map */}
      <div className="h-64 rounded-xl overflow-hidden border border-gray-200">
        <GoogleMapView 
          routeStops={routeDetails.stops || []} 
        />
      </div>
      
      {/* Stop Sequence */}
      <div className="mt-4">
        <h4 className="text-xs font-semibold uppercase text-gray-500 mb-2">Optimized Route Sequence</h4>
        <div className="space-y-2">
          {routeDetails.stops?.map((stop, idx) => (
            <div key={idx} className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg border border-gray-100">
              <div className="bg-white text-gray-800 w-6 h-6 rounded-full flex items-center justify-center font-bold text-xs shadow-sm">
                {stop.stop_sequence}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-900 truncate font-medium">{stop.address || `Lat: ${stop.lat.toFixed(4)}, Lng: ${stop.lng.toFixed(4)}`}</p>
                <p className="text-xs text-gray-500 capitalize">{stop.action} • ETA: +{Math.round(stop.eta_mins)} mins</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
