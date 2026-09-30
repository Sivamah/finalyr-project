import sqlite3
import os

db_path = 'dmfe_dev.db'

def alter_tables():
    if not os.path.exists(db_path):
        print("DB not found")
        return
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("PRAGMA foreign_keys=OFF;")
    cursor.execute("BEGIN TRANSACTION;")
    
    # 1. Alter assignments
    cursor.execute("""
    CREATE TABLE assignments_new (
        id INTEGER NOT NULL, 
        trip_id INTEGER, 
        driver_id INTEGER, 
        vehicle_id INTEGER, 
        driver_name VARCHAR,
        vehicle_name VARCHAR,
        assignment_type VARCHAR NOT NULL, 
        status VARCHAR NOT NULL, 
        assigned_at DATETIME, 
        completed_at DATETIME, 
        PRIMARY KEY (id), 
        FOREIGN KEY(driver_id) REFERENCES drivers (id), 
        FOREIGN KEY(trip_id) REFERENCES trips (id), 
        FOREIGN KEY(vehicle_id) REFERENCES vehicles (id)
    )
    """)
    cursor.execute("INSERT INTO assignments_new SELECT id, trip_id, driver_id, vehicle_id, driver_name, vehicle_name, assignment_type, status, assigned_at, completed_at FROM assignments")
    cursor.execute("DROP TABLE assignments")
    cursor.execute("ALTER TABLE assignments_new RENAME TO assignments")

    # 2. Alter driver_assignment_history
    cursor.execute("""
    CREATE TABLE driver_assignment_history_new (
        id INTEGER NOT NULL, 
        driver_id INTEGER, 
        vehicle_id INTEGER, 
        driver_name VARCHAR, 
        vehicle_name VARCHAR, 
        assignment_time DATETIME DEFAULT CURRENT_TIMESTAMP, 
        completion_time DATETIME, 
        status VARCHAR, 
        PRIMARY KEY (id), 
        FOREIGN KEY(driver_id) REFERENCES drivers (id), 
        FOREIGN KEY(vehicle_id) REFERENCES vehicles (id)
    )
    """)
    cursor.execute("INSERT INTO driver_assignment_history_new SELECT id, driver_id, vehicle_id, driver_name, vehicle_name, assignment_time, completion_time, status FROM driver_assignment_history")
    cursor.execute("DROP TABLE driver_assignment_history")
    cursor.execute("ALTER TABLE driver_assignment_history_new RENAME TO driver_assignment_history")
    
    conn.commit()
    conn.close()
    print("Done")

if __name__ == "__main__":
    alter_tables()
