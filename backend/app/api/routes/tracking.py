from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.api.deps import get_current_user
from app.db import models
from pydantic import BaseModel
from app.services.websocket_manager import manager
from app.services import notification_service

router = APIRouter()

class LocationUpdate(BaseModel):
    lat: float
    lng: float
    trip_id: int

@router.post("/location")
async def update_location(data: LocationUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    if current_user.role != "Driver":
        raise HTTPException(status_code=403, detail="Only drivers can post locations")

    # Update driver location in DB
    loc = db.query(models.DriverLocation).filter(models.DriverLocation.driver_id == current_user.id).first()
    if loc:
        loc.lat = data.lat
        loc.lng = data.lng
    else:
        loc = models.DriverLocation(driver_id=current_user.id, lat=data.lat, lng=data.lng)
        db.add(loc)
    db.commit()

    # Find the trip and the customer(s) involved to broadcast the location
    trip = db.query(models.Trip).filter(models.Trip.id == data.trip_id).first()
    if trip and trip.batch:
        customer_ids = set()
        # Find all associated bookings from the batch
        # Wait, Batch model has `ride_bookings`, `food_bookings`, `parcel_bookings`
        for b in trip.batch.ride_bookings: customer_ids.add(b.customer_id)
        for b in trip.batch.food_bookings: customer_ids.add(b.customer_id)
        for b in trip.batch.parcel_bookings: customer_ids.add(b.customer_id)

        payload = {
            "event": "LOCATION_UPDATE",
            "data": {
                "driver_id": current_user.id,
                "lat": data.lat,
                "lng": data.lng,
                "trip_id": data.trip_id
            }
        }

        # Broadcast location to all relevant customers
        for cid in customer_ids:
            await manager.send_personal_message(payload, cid)
            
    return {"status": "ok"}
