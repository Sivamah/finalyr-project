import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.api.deps import get_current_user
from app.db.database import SessionLocal
from app.db.models import User, Provider, Driver, Vehicle, Trip, DriverAssignment, DriverAssignmentHistory

def override_get_current_user():
    return User(id=1, email="test@test.com", role="Admin")

app.dependency_overrides[get_current_user] = override_get_current_user

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="function")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Helper to create test data
def create_provider(db):
    p = Provider(name="Test Prov", provider_type="Ride")
    db.add(p)
    db.commit()
    return p

def create_vehicle(db, provider_id):
    v = Vehicle(provider_id=provider_id, name="Test Veh", vehicle_type="Car")
    db.add(v)
    db.commit()
    return v

def create_driver(db, provider_id):
    d = Driver(provider_id=provider_id, name="Test Drv")
    db.add(d)
    db.commit()
    return d

def test_delete_empty_provider(client, db_session):
    p = create_provider(db_session)
    res = client.delete(f'/api/providers/{p.id}')
    assert res.status_code == 200
    assert db_session.query(Provider).filter(Provider.id == p.id).first() is None

def test_delete_provider_with_drivers(client, db_session):
    p = create_provider(db_session)
    d = create_driver(db_session, p.id)
    p_id, d_id = p.id, d.id
    res = client.delete(f'/api/providers/{p_id}')
    assert res.status_code == 200
    assert db_session.query(Provider).filter(Provider.id == p_id).first() is None
    assert db_session.query(Driver).filter(Driver.id == d_id).first() is None

def test_delete_provider_with_vehicles(client, db_session):
    p = create_provider(db_session)
    v = create_vehicle(db_session, p.id)
    p_id, v_id = p.id, v.id
    res = client.delete(f'/api/providers/{p_id}')
    assert res.status_code == 200
    assert db_session.query(Provider).filter(Provider.id == p_id).first() is None
    assert db_session.query(Vehicle).filter(Vehicle.id == v_id).first() is None

def test_delete_driver_no_deps(client, db_session):
    p = create_provider(db_session)
    d = create_driver(db_session, p.id)
    p_id, d_id = p.id, d.id
    res = client.delete(f'/api/drivers/{d_id}')
    assert res.status_code == 200
    assert db_session.query(Driver).filter(Driver.id == d_id).first() is None
    # Cleanup
    client.delete(f'/api/providers/{p_id}')

def test_delete_driver_with_active_assignment(client, db_session):
    p = create_provider(db_session)
    d = create_driver(db_session, p.id)
    v = create_vehicle(db_session, p.id)
    
    trip = Trip(trip_code="T-TEST", status="Planned")
    db_session.add(trip)
    db_session.commit()
    
    assignment = DriverAssignment(trip_id=trip.id, driver_id=d.id, vehicle_id=v.id, status="Active")
    db_session.add(assignment)
    db_session.commit()
    
    res = client.delete(f'/api/drivers/{d.id}')
    assert res.status_code == 409
    
    # Cleanup
    db_session.delete(assignment)
    db_session.delete(trip)
    db_session.commit()
    client.delete(f'/api/providers/{p.id}')

def test_delete_driver_with_planned_trip(client, db_session):
    p = create_provider(db_session)
    d = create_driver(db_session, p.id)
    
    trip = Trip(trip_code="T-TEST2", driver_id=d.id, status="Planned")
    db_session.add(trip)
    db_session.commit()
    
    res = client.delete(f'/api/drivers/{d.id}')
    assert res.status_code == 409
    
    # Cleanup
    db_session.delete(trip)
    db_session.commit()
    client.delete(f'/api/providers/{p.id}')

def test_delete_vehicle_no_deps(client, db_session):
    p = create_provider(db_session)
    v = create_vehicle(db_session, p.id)
    p_id, v_id = p.id, v.id
    res = client.delete(f'/api/vehicles/{v_id}')
    assert res.status_code == 200
    assert db_session.query(Vehicle).filter(Vehicle.id == v_id).first() is None
    # Cleanup
    client.delete(f'/api/providers/{p_id}')

def test_delete_vehicle_with_active_trip(client, db_session):
    p = create_provider(db_session)
    v = create_vehicle(db_session, p.id)
    
    trip = Trip(trip_code="T-TEST3", vehicle_id=v.id, status="Active")
    db_session.add(trip)
    db_session.commit()
    
    res = client.delete(f'/api/vehicles/{v.id}')
    assert res.status_code == 409
    
    # Cleanup
    db_session.delete(trip)
    db_session.commit()
    client.delete(f'/api/providers/{p.id}')

def test_delete_vehicle_with_assigned_driver_safe(client, db_session):
    p = create_provider(db_session)
    v = create_vehicle(db_session, p.id)
    d = create_driver(db_session, p.id)
    d.assigned_vehicle_id = v.id
    v.current_driver_id = d.id
    db_session.commit()
    
    p_id, v_id, d_id = p.id, v.id, d.id
    
    # delete vehicle
    res = client.delete(f'/api/vehicles/{v_id}')
    assert res.status_code == 200
    
    # Verify driver is updated and vehicle is deleted
    db_session.expire_all()
    assert db_session.query(Vehicle).filter(Vehicle.id == v_id).first() is None
    d = db_session.query(Driver).filter(Driver.id == d_id).first()
    assert d.assigned_vehicle_id is None
    
    # Cleanup
    client.delete(f'/api/providers/{p_id}')

def test_safe_handling_of_historical_records(client, db_session):
    p = create_provider(db_session)
    d = create_driver(db_session, p.id)
    v = create_vehicle(db_session, p.id)
    
    history = DriverAssignmentHistory(driver_id=d.id, vehicle_id=v.id, status="Completed")
    db_session.add(history)
    db_session.commit()
    
    trip = Trip(trip_code="T-COMPLETED", driver_id=d.id, vehicle_id=v.id, status="Completed")
    db_session.add(trip)
    db_session.commit()
    
    assignment = DriverAssignment(trip_id=trip.id, driver_id=d.id, vehicle_id=v.id, status="Completed")
    db_session.add(assignment)
    db_session.commit()
    
    p_id, d_id, v_id, h_id, t_id, a_id = p.id, d.id, v.id, history.id, trip.id, assignment.id
    
    # Delete driver -> should succeed and nullify references
    res = client.delete(f'/api/drivers/{d_id}')
    assert res.status_code == 200
    
    # Verify historical records remain but references are nulled
    db_session.expire_all()
    history = db_session.query(DriverAssignmentHistory).get(h_id)
    trip = db_session.query(Trip).get(t_id)
    assignment = db_session.query(DriverAssignment).get(a_id)
    
    assert history.driver_id is None
    assert history.vehicle_id == v_id
    
    assert trip.driver_id is None
    assert trip.vehicle_id == v_id
    
    assert assignment.driver_id is None
    assert assignment.vehicle_id == v_id
    
    # Cleanup
    db_session.delete(assignment)
    db_session.delete(trip)
    db_session.delete(history)
    db_session.commit()
    client.delete(f'/api/providers/{p_id}')


def test_rollback_on_simulated_failure(client, db_session):
    p = create_provider(db_session)
    p_id = p.id
    
    with patch("sqlalchemy.orm.session.Session.commit", side_effect=Exception("Simulated Failure")):
        try:
            client.delete(f'/api/providers/{p_id}')
        except Exception as e:
            assert str(e) == "Simulated Failure"
        
    # Verify transaction rollback
    db_session.rollback()
    assert db_session.query(Provider).filter(Provider.id == p_id).first() is not None
    
    # Cleanup properly
    client.delete(f'/api/providers/{p_id}')
