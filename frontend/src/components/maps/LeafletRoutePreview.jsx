import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import { Navigation, Clock, IndianRupee, Loader2 } from 'lucide-react';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

const greenIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const redIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const COIMBATORE = [11.0168, 76.9558];

function FitBounds({ pickup, drop }) {
  const map = useMap();
  useEffect(() => {
    if (pickup && drop) {
      const bounds = L.latLngBounds([
        [pickup.lat, pickup.lng],
        [drop.lat, drop.lng],
      ]);
      map.fitBounds(bounds, { padding: [40, 40] });
    } else if (pickup) {
      map.setView([pickup.lat, pickup.lng], 13);
    }
  }, [pickup, drop, map]);
  return null;
}

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

export default function LeafletRoutePreview({ pickup, drop, onRouteData }) {
  const [info, setInfo] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!pickup || !drop) { setInfo(null); return; }

    // Use OSRM for actual road routing (free, no API key needed)
    const fetchRoute = async () => {
      try {
        const res = await fetch(
          `https://router.project-osrm.org/route/v1/driving/${pickup.lng},${pickup.lat};${drop.lng},${drop.lat}?overview=full&geometries=geojson`
        );
        const data = await res.json();
        if (data.code === 'Ok' && data.routes.length > 0) {
          const route = data.routes[0];
          const distKm = route.distance / 1000;
          const etaMin = Math.round(route.duration / 60);
          const fare = Math.round(25 + distKm * 12);
          const routeData = { distanceKm: distKm.toFixed(2), etaMinutes: etaMin, fare };
          setInfo(routeData);
          setError(null);
          if (onRouteData) onRouteData(routeData);
        } else {
          throw new Error('OSRM routing failed');
        }
      } catch {
        setError('Routing service unavailable. Using straight-line estimate.');
        const distKm = haversineKm(pickup.lat, pickup.lng, drop.lat, drop.lng);
        const etaMin = Math.round((distKm / 30) * 60);
        const fare   = Math.round(25 + distKm * 12);
        const routeData = { distanceKm: distKm.toFixed(2), etaMinutes: etaMin, fare };
        setInfo(routeData);
        if (onRouteData) onRouteData(routeData);
      }
    };
    fetchRoute();
  }, [pickup, drop, onRouteData]);

  if (!pickup && !drop) return null;

  const center = pickup ? [pickup.lat, pickup.lng] : COIMBATORE;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Navigation className="h-4 w-4 text-violet-600" />
        <span className="text-sm font-semibold text-gray-700">Route Preview</span>
      </div>

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

      <div className="h-56 rounded-xl overflow-hidden border border-gray-200 relative">
        <MapContainer center={center} zoom={12} className="h-full w-full">
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <FitBounds pickup={pickup} drop={drop} />
          {pickup && <Marker position={[pickup.lat, pickup.lng]} icon={greenIcon} />}
          {drop && <Marker position={[drop.lat, drop.lng]} icon={redIcon} />}
          {pickup && drop && (
            <Polyline
              positions={[[pickup.lat, pickup.lng], [drop.lat, drop.lng]]}
              color="#7c3aed"
              weight={4}
              opacity={0.7}
              dashArray="10, 10"
            />
          )}
        </MapContainer>
      </div>
    </div>
  );
}
