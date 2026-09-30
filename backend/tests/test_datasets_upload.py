import pytest
import io
import os
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.api.deps import get_current_user
from app.db.database import SessionLocal
from app.db.models import User, Vehicle, Provider, Dataset

def override_get_current_user():
    return User(id=1, email="test@test.com", role="Admin")

app.dependency_overrides[get_current_user] = override_get_current_user

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_dataset_upload_imports_vehicles(client):
    db = SessionLocal()
    db.query(Vehicle).filter(Vehicle.name.like("CBE-V-90%")).delete(synchronize_session=False)
    db.commit()
    
    csv_content = """vehicle_id,vehicle_type,capacity,status,latitude,longitude,fuel_type\nCBE-V-901,Car,4,Available,11.0132,76.9558,Petrol\nCBE-V-902,Van,8,Busy,11.0216,76.9701,Diesel\n"""
    files = {'file': ('test_vehicles.csv', io.BytesIO(csv_content.encode("utf-8")), 'text/csv')}
    # Testing "Vehicles" data_type normalization
    data = {'name': 'test_vehicles', 'file_type': 'csv', 'data_type': 'Vehicles', 'description': 'Test vehicle import'}
    
    response = client.post('/api/orchestration/datasets/upload', files=files, data=data)
    assert response.status_code == 200
    
    dataset_data = response.json()
    dataset = db.query(Dataset).filter(Dataset.id == dataset_data['id']).first()
    assert dataset is not None
    assert dataset.file_path is not None
    assert os.path.exists(dataset.file_path)
    
    # Verify DB
    vehicles = db.query(Vehicle).filter(Vehicle.name.in_(["CBE-V-901", "CBE-V-902"])).all()
    assert len(vehicles) == 2
    
    v1 = next((v for v in vehicles if v.name == "CBE-V-901"), None)
    v2 = next((v for v in vehicles if v.name == "CBE-V-902"), None)
    
    assert v1 is not None and v1.capacity == 4 and v1.status == "Available"
    assert v2 is not None and v2.capacity == 8 and v2.status == "Busy"
    
    # Cleanup dataset
    client.delete(f'/api/orchestration/datasets/{dataset.id}')
    db.query(Vehicle).filter(Vehicle.name.like("CBE-V-90%")).delete(synchronize_session=False)
    db.commit()
    db.close()

def test_dataset_upload_valid_csv(client):
    db = SessionLocal()
    csv_content = "id,name\n1,Test\n"
    files = {'file': ('test.csv', io.BytesIO(csv_content.encode("utf-8")), 'text/csv')}
    data = {'name': 'test_csv', 'file_type': 'csv', 'data_type': 'Other'}
    response = client.post('/api/orchestration/datasets/upload', files=files, data=data)
    assert response.status_code == 200
    dataset = db.query(Dataset).filter(Dataset.id == response.json()['id']).first()
    assert dataset is not None
    assert dataset.row_count == 1
    client.delete(f'/api/orchestration/datasets/{dataset.id}')
    db.close()

def test_dataset_upload_valid_json(client):
    db = SessionLocal()
    json_content = '[{"id": 1, "name": "Test"}]'
    files = {'file': ('test.json', io.BytesIO(json_content.encode("utf-8")), 'application/json')}
    data = {'name': 'test_json', 'file_type': 'json', 'data_type': 'Other'}
    response = client.post('/api/orchestration/datasets/upload', files=files, data=data)
    assert response.status_code == 200
    dataset = db.query(Dataset).filter(Dataset.id == response.json()['id']).first()
    assert dataset is not None
    assert dataset.row_count == 1
    client.delete(f'/api/orchestration/datasets/{dataset.id}')
    db.close()

def test_dataset_upload_imports_vehicles_xlsx(client):
    db = SessionLocal()
    db.query(Vehicle).filter(Vehicle.name.like("CBE-X-90%")).delete(synchronize_session=False)
    db.commit()

    from openpyxl import Workbook
    from io import BytesIO
    wb = Workbook()
    ws = wb.active
    ws.append(["vehicle_id", "vehicle_type", "capacity", "status", "latitude", "longitude", "fuel_type"])
    ws.append(["CBE-X-901", "Car", 4, "Available", 11.0132, 76.9558, "Petrol"])
    ws.append(["CBE-X-902", "Van", 8, "Busy", 11.0216, 76.9701, "Diesel"])
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    files = {'file': ('test_vehicles.xlsx', buffer, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
    data = {'name': 'test_vehicles_xlsx', 'file_type': 'xlsx', 'data_type': 'Vehicles', 'description': 'Test XLSX vehicle import'}

    response = client.post('/api/orchestration/datasets/upload', files=files, data=data)
    assert response.status_code == 200
    assert response.json()['row_count'] == 2

    dataset = db.query(Dataset).filter(Dataset.id == response.json()['id']).first()
    assert dataset is not None
    assert dataset.file_path is not None
    assert os.path.exists(dataset.file_path)

    vehicles = db.query(Vehicle).filter(Vehicle.name.in_(["CBE-X-901", "CBE-X-902"])).all()
    assert len(vehicles) == 2
    v1 = next(v for v in vehicles if v.name == "CBE-X-901")
    v2 = next(v for v in vehicles if v.name == "CBE-X-902")
    assert v1.capacity == 4 and v1.status == "Available"
    assert v2.capacity == 8 and v2.status == "Busy"

    client.delete(f'/api/orchestration/datasets/{dataset.id}')
    db.query(Vehicle).filter(Vehicle.name.like("CBE-X-90%")).delete(synchronize_session=False)
    db.commit()
    db.close()

def test_dataset_upload_rejects_malformed_xlsx(client):
    db = SessionLocal()
    files = {'file': ('test_bad.xlsx', io.BytesIO(b"dummy"), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
    data = {'name': 'test_bad_xlsx', 'file_type': 'xlsx', 'data_type': 'Other'}
    response = client.post('/api/orchestration/datasets/upload', files=files, data=data)
    assert response.status_code == 400
    dataset = db.query(Dataset).filter(Dataset.name == 'test_bad_xlsx').first()
    assert dataset is None
    db.close()

def test_dataset_upload_malformed_csv(client):
    db = SessionLocal()
    files = {'file': ('test.csv', io.BytesIO(b"\xff\xfe\x00\x00"), 'text/csv')}
    data = {'name': 'test_malformed', 'file_type': 'csv', 'data_type': 'Other'}
    response = client.post('/api/orchestration/datasets/upload', files=files, data=data)
    assert response.status_code == 400
    dataset = db.query(Dataset).filter(Dataset.name == 'test_malformed').first()
    assert dataset is None
    db.close()

def test_dataset_upload_failed_vehicle_import(client):
    db = SessionLocal()
    csv_content = "vehicle_id,vehicle_type\nCBE-V-FAIL1,Car\nCBE-V-FAIL2,Van"
    files = {'file': ('test_fail.csv', io.BytesIO(csv_content.encode("utf-8")), 'text/csv')}
    data = {'name': 'test_fail', 'file_type': 'csv', 'data_type': 'vehicle'}
    
    with patch("sqlalchemy.orm.session.Session.commit", side_effect=Exception("Simulated DB Failure")):
        response = client.post('/api/orchestration/datasets/upload', files=files, data=data)
        
    assert response.status_code == 500
    dataset = db.query(Dataset).filter(Dataset.name == 'test_fail').first()
    assert dataset is None
    
    vehicles = db.query(Vehicle).filter(Vehicle.name.in_(["CBE-V-FAIL1", "CBE-V-FAIL2"])).all()
    assert len(vehicles) == 0
    db.close()

def test_dataset_delete(client):
    db = SessionLocal()
    csv_content = "id,name\n1,Test\n"
    files = {'file': ('test_delete.csv', io.BytesIO(csv_content.encode("utf-8")), 'text/csv')}
    data = {'name': 'test_delete', 'file_type': 'csv', 'data_type': 'Other'}
    response = client.post('/api/orchestration/datasets/upload', files=files, data=data)
    assert response.status_code == 200
    dataset_id = response.json()['id']
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    file_path = dataset.file_path
    
    assert os.path.exists(file_path)
    
    del_response = client.delete(f'/api/orchestration/datasets/{dataset_id}')
    assert del_response.status_code == 200
    
    assert db.query(Dataset).filter(Dataset.id == dataset_id).first() is None
    assert not os.path.exists(file_path)
    db.close()
