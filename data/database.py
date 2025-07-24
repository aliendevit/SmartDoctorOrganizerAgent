# database.py
import os
import sqlite3

DATABASE = os.path.join(os.path.dirname(__file__), "clients_database.db")

def init_db():
    """Initialize the database and create the clients table if it doesn't exist."""
    db_dir = os.path.dirname(DATABASE)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)

    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            age INTEGER,
            symptoms TEXT,
            notes TEXT,
            date TEXT,
            appointment_date TEXT,
            summary TEXT,
            followup_date TEXT,
            appointment_time TEXT
        )
    ''')
    conn.commit()
    conn.close()

def insert_client(data):
    """
    Inserts a client record into the database.
    Data is a dictionary with keys:
      - Name, Age, Symptoms (list), Notes, Date, Appointment Date, Summary, Follow-Up Date, Appointment Time.
    """
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO clients (name, age, symptoms, notes, date, appointment_date, summary, followup_date, appointment_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        data.get("Name", ""),
        data.get("Age", None),
        ", ".join(data.get("Symptoms", [])),
        data.get("Notes", ""),
        data.get("Date", ""),
        data.get("Appointment Date", ""),
        data.get("Summary", ""),
        data.get("Follow-Up Date", ""),
        data.get("Appointment Time", "")
    ))
    conn.commit()
    conn.close()

def load_all_clients():
    """
    Loads all client records from the database.
    Returns a list of dictionaries containing the following keys:
      "Name", "Age", "Symptoms", "Appointment Date", "Appointment Time"
    """
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()
    # Select name, age, symptoms, appointment_date, and appointment_time.
    c.execute("SELECT name, age, symptoms, appointment_date, appointment_time FROM clients")
    rows = c.fetchall()
    conn.close()
    appointments = []
    for row in rows:
        appointments.append({
            "Name": row[0],
            "Age": row[1] if row[1] is not None else "",
            "Symptoms": row[2] if row[2] is not None else "",
            "Appointment Date": row[3] if row[3] is not None else "Not Specified",
            "Appointment Time": row[4] if row[4] is not None else "Not Specified"
        })
    return appointments

# Initialize the database when the module is imported.
init_db()