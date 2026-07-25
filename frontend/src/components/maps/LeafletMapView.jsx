import React, { useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import { Loader2 } from 'lucide-react';

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

const blueIcon = new L.Icon({
  iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-blue.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

const COIMBATORE = [11.0168, 76.9558];

function FitBounds({ markers, routeStops }) {
  const map = useMap();
  useEffect(() => {
    const points = [...(markers || []), ...(routeStops || [])].filter(p => p.lat != null && p.lng != null);
    if (points.length > 0) {
      const bounds = L.latLngBounds(points.map(p => [p.lat, p.lng]));
      map.fitBounds(bounds, { padding: [40, 40] });
    } else {
      map.setView(COIMBATORE, 12);
    }
  }, [markers, routeStops, map]);
  return null;
}

function getIcon(color) {
  if (color === 'green' || color === 'pickup') return greenIcon;
  if (color === 'red' || color === 'drop') return redIcon;
  if (color === 'blue' || color === 'driver') return blueIcon;
  return new L.Icon.Default();
}

export default function LeafletMapView({ markers = [], routeStops = [], onMapClick, polyline = [], center, zoom }) {
  const mapCenter = center || (markers.length > 0 ? [markers[0].lat, markers[0].lng] : COIMBATORE);
  const mapZoom = zoom || 13;

  const polylinePositions = polyline.length > 0
    ? polyline
    : routeStops.length >= 2
      ? routeStops.map(s => [s.lat, s.lng])
      : markers.length >= 2
        ? markers.map(m => [m.lat, m.lng])
        : [];

  return (
    <MapContainer
      center={mapCenter}
      zoom={mapZoom}
      className="h-full w-full rounded-xl z-0"
      whenReady={() => {}}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <FitBounds markers={markers} routeStops={routeStops} />

      {markers.map((m, i) => (
        <Marker
          key={`m-${i}`}
          position={[m.lat, m.lng]}
          icon={m.color ? getIcon(m.color) : undefined}
        >
          {m.label && <Popup>{m.label}</Popup>}
        </Marker>
      ))}

      {routeStops.map((s, i) => (
        <Marker
          key={`rs-${i}`}
          position={[s.lat, s.lng]}
          icon={i === 0 ? greenIcon : i === routeStops.length - 1 ? redIcon : blueIcon}
        >
          <Popup>
            {s.action || 'Stop'} #{i + 1}
            {s.address && <br />}
            {s.address}
          </Popup>
        </Marker>
      ))}

      {polylinePositions.length >= 2 && (
        <Polyline
          positions={polylinePositions}
          color="#7c3aed"
          weight={4}
          opacity={0.7}
        />
      )}

      {onMapClick && <MapClickHandler onClick={onMapClick} />}
    </MapContainer>
  );
}

function MapClickHandler({ onClick }) {
  const map = useMap();
  useEffect(() => {
    map.on('click', (e) => {
      onClick({ lat: e.latlng.lat, lng: e.latlng.lng });
    });
    return () => { map.off('click'); };
  }, [map, onClick]);
  return null;
}
