import React, { useState, useCallback, useEffect, useRef } from 'react';
import { GoogleMap, useJsApiLoader, Marker, Autocomplete } from '@react-google-maps/api';
import { MapPin, Loader2 } from 'lucide-react';

const containerStyle = {
  width: '100%',
  height: '100%'
};

export default function LocationPicker({ label, color = 'green', value, onChange }) {
  const { isLoaded } = useJsApiLoader({
    id: 'google-map-script',
    googleMapsApiKey: import.meta.env.VITE_GOOGLE_MAPS_API_KEY || '',
    libraries: ['places']
  });

  const [map, setMap] = useState(null);
  const [autocomplete, setAutocomplete] = useState(null);
  
  const center = value ? { lat: value.lat, lng: value.lng } : { lat: 12.9716, lng: 77.5946 };
  
  const onLoad = useCallback(function callback(map) {
    setMap(map);
  }, []);

  const onUnmount = useCallback(function callback(map) {
    setMap(null);
  }, []);

  const onMapClick = useCallback((e) => {
    const lat = e.latLng.lat();
    const lng = e.latLng.lng();
    
    // Reverse geocode
    if (window.google) {
      const geocoder = new window.google.maps.Geocoder();
      geocoder.geocode({ location: { lat, lng } }, (results, status) => {
        if (status === "OK" && results[0]) {
          onChange({ lat, lng, address: results[0].formatted_address });
        } else {
          onChange({ lat, lng, address: `${lat.toFixed(5)}, ${lng.toFixed(5)}` });
        }
      });
    } else {
      onChange({ lat, lng, address: `${lat.toFixed(5)}, ${lng.toFixed(5)}` });
    }
  }, [onChange]);

  const onLoadAutocomplete = (autocomplete) => {
    setAutocomplete(autocomplete);
  };

  const onPlaceChanged = () => {
    if (autocomplete !== null) {
      const place = autocomplete.getPlace();
      if (place.geometry && place.geometry.location) {
        const lat = place.geometry.location.lat();
        const lng = place.geometry.location.lng();
        const address = place.formatted_address;
        onChange({ lat, lng, address });
        
        if (map) {
          map.panTo({ lat, lng });
          map.setZoom(15);
        }
      }
    }
  };

  return (
    <div className="space-y-2">
      <label className="block text-sm font-semibold text-gray-700">
        <MapPin className={`inline h-4 w-4 mr-1 ${color === 'green' ? 'text-emerald-600' : 'text-red-500'}`} />
        {label}
      </label>

      {/* Search box using Google Places Autocomplete */}
      {isLoaded ? (
        <Autocomplete
          onLoad={onLoadAutocomplete}
          onPlaceChanged={onPlaceChanged}
        >
          <input
            type="text"
            placeholder={`Search or click map to set ${label.toLowerCase()}`}
            className="w-full p-2.5 text-sm border border-gray-200 rounded-xl bg-white focus:outline-none focus:border-violet-400 focus:ring-2 focus:ring-violet-100"
            defaultValue={value?.address || ""}
            key={value?.address} // force re-render if address changes via map click
          />
        </Autocomplete>
      ) : (
        <div className="w-full p-2.5 text-sm border border-gray-200 rounded-xl bg-gray-50 flex items-center text-gray-500">
          <Loader2 className="h-4 w-4 animate-spin mr-2" /> Loading Maps...
        </div>
      )}

      {/* Selected address chip */}
      {value && (
        <p className="text-xs text-gray-500 truncate px-1">📍 {value.address}</p>
      )}

      {/* Map */}
      <div className="h-48 rounded-xl overflow-hidden border border-gray-200 relative">
        {!isLoaded ? (
           <div className="w-full h-full flex items-center justify-center bg-gray-50">
             <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
           </div>
        ) : (
          <GoogleMap
            mapContainerStyle={containerStyle}
            center={center}
            zoom={value ? 15 : 12}
            onLoad={onLoad}
            onUnmount={onUnmount}
            onClick={onMapClick}
            options={{
              disableDefaultUI: true,
              zoomControl: true,
            }}
          >
            {value && (
              <Marker
                position={{ lat: value.lat, lng: value.lng }}
                icon={color === 'green' ? 'http://maps.google.com/mapfiles/ms/icons/green-dot.png' : 'http://maps.google.com/mapfiles/ms/icons/red-dot.png'}
              />
            )}
          </GoogleMap>
        )}
      </div>
    </div>
  );
}
