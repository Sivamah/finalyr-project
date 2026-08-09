import React, { useState, useCallback, useRef, useEffect } from 'react';
import { GoogleMap, useJsApiLoader } from '@react-google-maps/api';
import { MapContainer, TileLayer, Marker as LeafletMarker, Popup as LeafletPopup, useMap } from 'react-leaflet';
import L from 'leaflet';
import RequestMarkers, { MARKER_COLORS } from './RequestMarkers';
import MarkerPopup from './MarkerPopup';
import MapControls from './MapControls';
import 'leaflet/dist/leaflet.css';

const COIMBATORE_CENTER = { lat: 11.0168, lng: 76.9558 };
const DEFAULT_ZOOM = 12;

const containerStyle = {
  width: '100%',
  height: '100%',
  borderRadius: '0.75rem',
};

const darkMapStyles = [
  { elementType: 'geometry', stylers: [{ color: '#242f3e' }] },
  { elementType: 'labels.text.stroke', stylers: [{ color: '#242f3e' }] },
  { elementType: 'labels.text.fill', stylers: [{ color: '#746855' }] },
  {
    featureType: 'administrative.locality',
    elementType: 'labels.text.fill',
    stylers: [{ color: '#d59563' }],
  },
  {
    featureType: 'poi',
    elementType: 'labels.text.fill',
    stylers: [{ color: '#d59563' }],
  },
  {
    featureType: 'road',
    elementType: 'geometry',
    stylers: [{ color: '#38414e' }],
  },
  {
    featureType: 'road',
    elementType: 'geometry.stroke',
    stylers: [{ color: '#212a37' }],
  },
  {
    featureType: 'road',
    elementType: 'labels.text.fill',
    stylers: [{ color: '#9ca3af' }],
  },
  {
    featureType: 'water',
    elementType: 'geometry',
    stylers: [{ color: '#17263c' }],
  },
];

// Custom Leaflet DivIcons for fallback map
function createLeafletIcon(type = 'ride') {
  const color = MARKER_COLORS[type.toLowerCase()] || MARKER_COLORS.ride;
  return L.divIcon({
    className: 'custom-leaflet-marker',
    html: `<div style="background-color: ${color}; width: 24px; height: 24px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 6px rgba(0,0,0,0.4); display: flex; items-center; justify-content: center;"></div>`,
    iconSize: [24, 24],
    iconAnchor: [12, 12],
  });
}

// Leaflet Bounds Fitter Helper Component
function LeafletBoundsFitter({ requests, trigger }) {
  const map = useMap();
  useEffect(() => {
    if (trigger > 0 && requests && requests.length > 0) {
      const validPoints = requests.filter(r => r.pickup_lat && r.pickup_lng);
      if (validPoints.length > 0) {
        const bounds = L.latLngBounds(validPoints.map(r => [r.pickup_lat, r.pickup_lng]));
        map.fitBounds(bounds, { padding: [40, 40] });
      }
    }
  }, [trigger, requests, map]);
  return null;
}

export default function LiveMapContainer({
  requests = [],
  selectedRequest,
  onSelectRequest,
  onClosePopup,
  className = 'relative w-full h-[600px] rounded-xl overflow-hidden shadow-2xl border border-white/[0.08] bg-white/[0.02]',
}) {
  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY || '';
  const isGoogleKeyPresent = Boolean(apiKey && apiKey !== 'your_google_maps_api_key_here');

  const { isLoaded, loadError } = useJsApiLoader({
    googleMapsApiKey: isGoogleKeyPresent ? apiKey : '',
    id: 'google-map-script',
  });

  const mapRef = useRef(null);
  const wrapperRef = useRef(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [leafletFitTrigger, setLeafletFitTrigger] = useState(0);

  const onLoad = useCallback((map) => {
    mapRef.current = map;
  }, []);

  const onUnmount = useCallback(() => {
    mapRef.current = null;
  }, []);

  // Fit bounds handler
  const handleFitBounds = useCallback(() => {
    const validPoints = requests.filter(r => r.pickup_lat && r.pickup_lng);
    if (validPoints.length === 0) return;

    if (mapRef.current && window.google) {
      const bounds = new window.google.maps.LatLngBounds();
      validPoints.forEach(r => {
        bounds.extend({ lat: r.pickup_lat, lng: r.pickup_lng });
      });
      mapRef.current.fitBounds(bounds);
    } else {
      setLeafletFitTrigger(prev => prev + 1);
    }
  }, [requests]);

  // Recenter handler
  const handleRecenter = useCallback(() => {
    if (mapRef.current) {
      mapRef.current.panTo(COIMBATORE_CENTER);
      mapRef.current.setZoom(DEFAULT_ZOOM);
    }
  }, []);

  // Zoom handlers
  const handleZoomIn = useCallback(() => {
    if (mapRef.current) {
      mapRef.current.setZoom(mapRef.current.getZoom() + 1);
    }
  }, []);

  const handleZoomOut = useCallback(() => {
    if (mapRef.current) {
      mapRef.current.setZoom(mapRef.current.getZoom() - 1);
    }
  }, []);

  // Fullscreen handler
  const toggleFullscreen = useCallback(() => {
    if (!wrapperRef.current) return;
    if (!document.fullscreenElement) {
      wrapperRef.current.requestFullscreen().then(() => setIsFullscreen(true)).catch(() => {});
    } else {
      document.exitFullscreen().then(() => setIsFullscreen(false)).catch(() => {});
    }
  }, []);

  // ── Render Google Map if loaded and valid ──────────────────────────────────
  const canUseGoogleMap = isGoogleKeyPresent && isLoaded && !loadError;

  return (
    <div ref={wrapperRef} className={className}>
      {canUseGoogleMap ? (
        <GoogleMap
          mapContainerStyle={containerStyle}
          center={COIMBATORE_CENTER}
          zoom={DEFAULT_ZOOM}
          onLoad={onLoad}
          onUnmount={onUnmount}
          options={{
            styles: darkMapStyles,
            disableDefaultUI: false,
            zoomControl: false,
            mapTypeControl: false,
            streetViewControl: false,
            fullscreenControl: false,
          }}
        >
          <RequestMarkers
            requests={requests}
            selectedRequest={selectedRequest}
            onSelectRequest={onSelectRequest}
            onClosePopup={onClosePopup}
          />
        </GoogleMap>
      ) : (
        /* Fallback Interactive Leaflet / OpenStreetMap when Google Maps key is missing */
        <MapContainer
          center={[COIMBATORE_CENTER.lat, COIMBATORE_CENTER.lng]}
          zoom={DEFAULT_ZOOM}
          style={{ width: '100%', height: '100%', borderRadius: '0.75rem' }}
          zoomControl={false}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <LeafletBoundsFitter requests={requests} trigger={leafletFitTrigger} />

          {requests.map((req) => {
            if (!req.pickup_lat || !req.pickup_lng) return null;
            const reqType = req.request_type?.toLowerCase() || 'ride';
            return (
              <LeafletMarker
                key={req.id}
                position={[req.pickup_lat, req.pickup_lng]}
                icon={createLeafletIcon(reqType)}
                eventHandlers={{
                  click: () => onSelectRequest(req),
                }}
              >
                <LeafletPopup>
                  <MarkerPopup request={req} />
                </LeafletPopup>
              </LeafletMarker>
            );
          })}
        </MapContainer>
      )}

      {/* Floating Map Controls Overlay */}
      <div className="absolute bottom-6 right-6 z-20">
        <MapControls
          onFitBounds={handleFitBounds}
          onRecenter={handleRecenter}
          onZoomIn={handleZoomIn}
          onZoomOut={handleZoomOut}
          isFullscreen={isFullscreen}
          onToggleFullscreen={toggleFullscreen}
        />
      </div>
    </div>
  );
}
