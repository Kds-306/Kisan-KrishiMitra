import sqlite3
from datetime import datetime

# Connect to database (creates file if it doesn't exist)
conn = sqlite3.connect('agri_drain.db')
cur = conn.cursor()

# --- Create farmers table ---
cur.execute('''
CREATE TABLE IF NOT EXISTS farmers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    mobile TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)
''')

# --- Create admins table ---
cur.execute('''
CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)
''')

# --- Create farmer_data table with new columns ---
cur.execute('''
CREATE TABLE IF NOT EXISTS farmer_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    soil_type TEXT,
    water_level TEXT,
    crop TEXT,
    farm_address TEXT,
    latitude REAL,
    longitude REAL,
    submission_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    feedback TEXT,
    recommendation TEXT
)
''')

# Insert default admin
cur.execute('INSERT OR IGNORE INTO admins (username, password) VALUES (?, ?)', ('admin', 'admin123'))

# Insert sample farmer data with location (optional - for testing)
cur.execute('''
INSERT OR IGNORE INTO farmer_data 
(name, soil_type, water_level, crop, farm_address, latitude, longitude, submission_date) 
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
''', (
    'Sample Farmer',
    'Black Soil',
    'Moderate (2m - 5m)',
    'Cotton',
    'Sample Farm, Maharashtra',
    19.7515,
    75.7139,
    datetime.now()
))

conn.commit()
conn.close()

print("✅ Database initialized successfully!")
print("✅ Tables created: farmers, admins, farmer_data")
print("✅ New columns added: farm_address, latitude, longitude, submission_date")