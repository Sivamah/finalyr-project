import React, { useState, useCallback, useEffect } from 'react';
import { GoogleMap, useJsApiLoader, Marker, DirectionsRenderer } from '@react-google-maps/api';
import { Loader2 } from 'lucide-react';

const containerStyle = {
  width: '100%',
  height: '100%'
};

const defaultCenter = {
  lat: 12.9716, // Bangalore default
  lng: 77.5946
};

// markers: [{ lat, lng, label, color }]
export default function GoogleMapView({ markers = [], routeStops = [], onMapClick }) {
  const { isLoaded } = useJsApiLoader({
    id: 'google-map-script',
    googleMapsApiKey: import.meta.env.VITE_GOOGLE_MAPS_API_KEY || ''
  });

  const [map, setMap] = useState(null);
  const [directions, setDirections] = useState(null);

  const onLoad = useCallback(function callback(map) {
    if (markers.length > 0) {
      const bounds = new window.google.maps.LatLngBounds();
      markers.forEach(({ lat, lng }) => bounds.extend({ lat, lng }));
      routeStops.forEach(({ lat, lng }) => bounds.extend({ lat, lng }));
      map.fitBounds(bounds);
    }
    setMap(map);
  }, [markers, routeStops]);

  const onUnmount = useCallback(function callback(map) {
    setMap(null);
  }, []);

  useEffect(() => {
    if (isLoaded && routeStops.length >= 2) {
      const directionsService = new window.google.maps.DirectionsService();
      
      const origin = { lat: routeStops[0].lat, lng: routeStops[0].lng };
      const destination = { lat: routeStops[routeStops.length - 1].lat, lng: routeStops[routeStops.length - 1].lng };
      
      const waypoints = routeStops.slice(1, -1).map(stop => ({
        location: { lat: stop.lat, lng: stop.lng },
        stopover: true
      }));

      directionsService.route(
        {
          origin,
          destination,
          waypoints,
          optimizeWaypoints: false, // We pre-optimized on the backend
          travelMode: window.google.maps.TravelMode.DRIVING
        },
        (result, status) => {
          if (status === window.google.maps.DirectionsStatus.OK) {
            setDirections(result);
          } else {
            console.error(`error fetching directions ${result}`);
          }
        }
      );
    }
  }, [isLoaded, routeStops]);

  const handleMapClick = (e) => {
    if (onMapClick) {
      onMapClick({ lat: e.latLng.lat(), lng: e.latLng.lng() });
    }
  };

  if (!isLoaded) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-gray-50 rounded-2xl">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <GoogleMap
      mapContainerStyle={containerStyle}
      center={markers.length > 0 ? { lat: markers[0].lat, lng: markers[0].lng } : defaultCenter}
      zoom={12}
      onLoad={onLoad}
      onUnmount={onUnmount}
      onClick={handleMapClick}
      options={{
        disableDefaultUI: false,
        zoomControl: true,
      }}
    >
      {markers.map((marker, index) => (
        <Marker
          key={index}
          position={{ lat: marker.lat, lng: marker.lng }}
          label={marker.label}
        />
      ))}

      {directions && (
        <DirectionsRenderer
          directions={directions}
          options={{
            suppressMarkers: true,
            polylineOptions: { strokeColor: '#4f46e5', strokeWeight: 5 }
          }}
        />
      )}
    </GoogleMap>
  );
}
