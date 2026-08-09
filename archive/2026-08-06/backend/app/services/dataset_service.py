import os
import json
import tempfile
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import UploadFile
from app.db.models import Dataset


def upload_dataset(
    db: Session,
    name: str,
    file_type: str,
    data_type: str,
    description: str,
    file: Optional[UploadFile] = None,
) -> Dataset:
    row_count = 0
    file_path = None

    if file:
        ext = os.path.splitext(file.filename)[1] if file.filename else ""
        fd, file_path = tempfile.mkstemp(suffix=ext, dir="datasets")
        os.close(fd)
        content = file.file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        if file_type == "csv":
            row_count = len(content.decode().splitlines()) - 1
        elif file_type == "json":
            data = json.loads(content)
            row_count = len(data) if isinstance(data, list) else 1

    dataset = Dataset(
        name=name,
        file_type=file_type,
        data_type=data_type,
        file_path=file_path,
        row_count=row_count,
        description=description,
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset


def delete_dataset(db: Session, dataset_id: int) -> bool:
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        return False
    if dataset.file_path and os.path.exists(dataset.file_path):
        os.remove(dataset.file_path)
    db.delete(dataset)
    db.commit()
    return True
