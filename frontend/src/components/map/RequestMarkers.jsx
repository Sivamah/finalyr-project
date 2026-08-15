import React from 'react';
import { Marker, InfoWindow } from '@react-google-maps/api';
import MarkerPopup from './MarkerPopup';

// Color definitions:
// Ride  -> Cyan (#22D3EE)
// Food  -> Delivery Orange (#F97316)
// Parcel-> Success Green (#22C55E)

export const MARKER_COLORS = {
  ride: '#22D3EE',
  food: '#F97316',
  parcel: '#22C55E',
};

// SVG custom marker generator for Google Maps
export function createGoogleMarkerSvg(type = 'ride') {
  const color = MARKER_COLORS[type.toLowerCase()] || MARKER_COLORS.ride;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" viewBox="0 0 24 24" fill="${color}" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3" fill="#ffffff"/></svg>`;
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}

export default function RequestMarkers({
  requests = [],
  selectedRequest,
  onSelectRequest,
  onClosePopup,
}) {
  return (
    <>
      {requests.map((req) => {
        if (!req.pickup_lat || !req.pickup_lng) return null;

        const reqType = req.request_type?.toLowerCase() || 'ride';
        const iconUrl = createGoogleMarkerSvg(reqType);

        return (
          <Marker
            key={req.id}
            position={{ lat: req.pickup_lat, lng: req.pickup_lng }}
            icon={{
              url: iconUrl,
              scaledSize: new window.google.maps.Size(32, 32),
              anchor: new window.google.maps.Point(16, 32),
            }}
            onClick={() => onSelectRequest(req)}
            title={`Request #${req.id} (${req.request_type}) - ${req.pickup_address}`}
          />
        );
      })}

      {selectedRequest && selectedRequest.pickup_lat && selectedRequest.pickup_lng && (
        <InfoWindow
          position={{ lat: selectedRequest.pickup_lat, lng: selectedRequest.pickup_lng }}
          onCloseClick={onClosePopup}
        >
          <MarkerPopup request={selectedRequest} onClose={onClosePopup} />
        </InfoWindow>
      )}
    </>
  );
}
