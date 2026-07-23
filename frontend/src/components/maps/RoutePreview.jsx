import { useEffect, useState, useCallback } from 'react';
import { GoogleMap, useJsApiLoader, Marker, DirectionsRenderer } from '@react-google-maps/api';
import { Navigation, Clock, IndianRupee, Loader2 } from 'lucide-react';

const containerStyle = {
  width: '100%',
  height: '100%'
};

export default function RoutePreview({ pickup, drop, onRouteData }) {
  const { isLoaded } = useJsApiLoader({
    id: 'google-map-script',
    googleMapsApiKey: import.meta.env.VITE_GOOGLE_MAPS_API_KEY || ''
  });

  const [map, setMap] = useState(null);
  const [directions, setDirections] = useState(null);
  const [info, setInfo] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const onLoad = useCallback(function callback(map) {
    setMap(map);
    if (pickup && drop) {
      const bounds = new window.google.maps.LatLngBounds();
      bounds.extend({ lat: pickup.lat, lng: pickup.lng });
      bounds.extend({ lat: drop.lat, lng: drop.lng });
      map.fitBounds(bounds);
    }
  }, [pickup, drop]);

  const onUnmount = useCallback(function callback(map) {
    setMap(null);
  }, []);

  useEffect(() => {
    if (!pickup || !drop || !isLoaded) { 
      setDirections(null); 
      setInfo(null); 
      return; 
    }

    const fetchRoute = () => {
      setLoading(true);
      setError(null);
      
      const directionsService = new window.google.maps.DirectionsService();
      directionsService.route(
        {
          origin: { lat: pickup.lat, lng: pickup.lng },
          destination: { lat: drop.lat, lng: drop.lng },
          travelMode: window.google.maps.TravelMode.DRIVING
        },
        (result, status) => {
          setLoading(false);
          if (status === window.google.maps.DirectionsStatus.OK) {
            setDirections(result);
            
            const route = result.routes[0].legs[0];
            const distKm = route.distance.value / 1000;
            const etaMin = Math.round(route.duration.value / 60);
            const fare = Math.round(25 + distKm * 12);
            
            const routeData = { distanceKm: distKm.toFixed(2), etaMinutes: etaMin, fare };
            setInfo(routeData);
            if (onRouteData) onRouteData(routeData);
          } else {
            // Fallback for API failure or straight line
            setError('Google Maps routing failed. Using straight-line estimate.');
            const distKm = haversineKm(pickup.lat, pickup.lng, drop.lat, drop.lng);
            const etaMin = Math.round((distKm / 30) * 60);
            const fare   = Math.round(25 + distKm * 12);
            const routeData = { distanceKm: distKm.toFixed(2), etaMinutes: etaMin, fare };
            setInfo(routeData);
            if (onRouteData) onRouteData(routeData);
          }
        }
      );
    };

    fetchRoute();
  }, [pickup, drop, isLoaded, onRouteData]);

  // Simple Haversine distance formula
  function haversineKm(lat1, lng1, lat2, lng2) {
    const R = 6371;
    const dLat = ((lat2 - lat1) * Math.PI) / 180;
    const dLng = ((lng2 - lng1) * Math.PI) / 180;
    const a =
      Math.sin(dLat / 2) ** 2 +
      Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLng / 2) ** 2;
    return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }

  if (!pickup && !drop) return null;

  const center = pickup ? { lat: pickup.lat, lng: pickup.lng } : { lat: 12.9716, lng: 77.5946 };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Navigation className="h-4 w-4 text-violet-600" />
        <span className="text-sm font-semibold text-gray-700">Route Preview</span>
        {loading && <Loader2 className="h-4 w-4 text-violet-400 animate-spin" />}
      </div>

      {/* Stats */}
      {info && (
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-violet-50 rounded-xl p-3 text-center">
            <p className="text-xs text-violet-600 font-medium">Distance</p>
            <p className="text-lg font-bold text-violet-800">{info.distanceKm} km</p>
          </div>
          <div className="bg-sky-50 rounded-xl p-3 text-center">
            <p className="text-xs text-sky-600 font-medium">Est. ETA</p>
            <p className="text-lg font-bold text-sky-800 flex items-center justify-center gap-0.5">
              <Clock className="h-4 w-4" /> {info.etaMinutes} min
            </p>
          </div>
          <div className="bg-emerald-50 rounded-xl p-3 text-center">
            <p className="text-xs text-emerald-600 font-medium">Est. Fare</p>
            <p className="text-lg font-bold text-emerald-800 flex items-center justify-center gap-0.5">
              <IndianRupee className="h-4 w-4" /> {info.fare}
            </p>
          </div>
        </div>
      )}

      {error && <p className="text-xs text-amber-600 bg-amber-50 px-3 py-1.5 rounded-lg">⚠️ {error}</p>}

      {/* Map */}
      <div className="h-56 rounded-xl overflow-hidden border border-gray-200 relative">
        {!isLoaded ? (
           <div className="w-full h-full flex items-center justify-center bg-gray-50">
             <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
           </div>
        ) : (
          <GoogleMap
            mapContainerStyle={containerStyle}
            center={center}
            zoom={12}
            onLoad={onLoad}
            onUnmount={onUnmount}
            options={{
              disableDefaultUI: true,
              zoomControl: true,
            }}
          >
            {pickup && !directions && (
              <Marker position={{ lat: pickup.lat, lng: pickup.lng }} icon="http://maps.google.com/mapfiles/ms/icons/green-dot.png" />
            )}
            {drop && !directions && (
              <Marker position={{ lat: drop.lat, lng: drop.lng }} icon="http://maps.google.com/mapfiles/ms/icons/red-dot.png" />
            )}
            {directions && (
              <DirectionsRenderer 
                directions={directions} 
                options={{
                  polylineOptions: { strokeColor: '#7c3aed', strokeWeight: 5 }
                }}
              />
            )}
          </GoogleMap>
        )}
      </div>
    </div>
  );
}
