export const COIMBATORE_BOUNDS = {
  minLat: 10.95,
  maxLat: 11.15,
  minLng: 76.85,
  maxLng: 77.05,
};

export const COIMBATORE_CENTER = { lat: 11.0168, lng: 76.9558 };

export function isInCoimbatore(lat, lng) {
  return (
    lat >= COIMBATORE_BOUNDS.minLat &&
    lat <= COIMBATORE_BOUNDS.maxLat &&
    lng >= COIMBATORE_BOUNDS.minLng &&
    lng <= COIMBATORE_BOUNDS.maxLng
  );
}

export function validateCoimbatore(lat, lng, label) {
  if (!isInCoimbatore(lat, lng)) {
    throw new Error(`${label} is outside Coimbatore. Service is currently available only in Coimbatore.`);
  }
}
