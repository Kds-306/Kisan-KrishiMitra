from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3, os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret123"


# --- Database Setup ---
def get_db():
    conn = sqlite3.connect("agri_drain.db")
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS farmers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            mobile TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS farmer_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            soil_type TEXT,
            water_level TEXT,
            crop TEXT,
            farm_address TEXT,
            latitude REAL,
            longitude REAL,
            created_at TEXT,
            feedback TEXT,
            recommendation TEXT
        )
    """)
    conn.commit()
    conn.close()


# Initialize database
init_db()


# --- Home ---
@app.route('/')
def home():
    return render_template('index.html')


# --- Farmer Registration ---
@app.route('/farmer_register', methods=['GET', 'POST'])
def farmer_register():
    if request.method == 'POST':
        name = request.form['name']
        mobile = request.form['mobile']
        password = request.form['password']

        conn = get_db()
        try:
            conn.execute("INSERT INTO farmers (name, mobile, password) VALUES (?, ?, ?)",
                         (name, mobile, password))
            conn.commit()
            message = "✅ Registration successful! Please log in."
        except sqlite3.IntegrityError:
            message = "⚠️ Mobile number already registered!"
        finally:
            conn.close()

        return render_template('farmer_register.html', message=message)
    return render_template('farmer_register.html')


# --- Farmer Login ---
@app.route('/farmer_login', methods=['GET', 'POST'])
def farmer_login():
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']

        conn = get_db()
        farmer = conn.execute("SELECT * FROM farmers WHERE name=? AND password=?",
                              (name, password)).fetchone()
        conn.close()

        if farmer:
            session['farmer_logged_in'] = True
            session['farmer_name'] = farmer['name']
            return redirect(url_for('farmer'))
        else:
            return render_template('farmer_login.html', error="Invalid credentials")

    return render_template('farmer_login.html')


# --- Admin Registration ---
@app.route('/admin_register', methods=['GET', 'POST'])
def admin_register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db()
        try:
            conn.execute("INSERT INTO admins (username, password) VALUES (?, ?)",
                         (username, password))
            conn.commit()
            message = "✅ Admin registered successfully!"
        except sqlite3.IntegrityError:
            message = "⚠️ Username already exists!"
        finally:
            conn.close()

        return render_template('admin_register.html', message=message)
    return render_template('admin_register.html')


# --- Admin Login ---
@app.route('/admin_login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db()
        admin = conn.execute("SELECT * FROM admins WHERE username=? AND password=?",
                             (username, password)).fetchone()
        conn.close()

        if admin:
            session['admin_logged_in'] = True
            session['admin_name'] = admin['username']
            return redirect(url_for('dashboard'))
        else:
            return render_template('admin_login.html', error="Invalid credentials")

    return render_template('admin_login.html')


# -- Farmer Data ---
@app.route("/farmer_data")
def farmer_data():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = get_db()
    farmers = conn.execute("SELECT id, name, mobile, password FROM farmers").fetchall()
    conn.close()
    return render_template("farmer_data.html", farmers=farmers)

@app.route("/farmer", methods=["GET", "POST"])
def farmer():
    conn = get_db()

    # 🚫 Admin should never access this page
    if session.get("admin_logged_in"):
        conn.close()
        return redirect(url_for("dashboard"))

    # 🚫 Guests must log in first
    if not session.get("farmer_logged_in"):
        conn.close()
        return redirect(url_for("farmer_login"))

    # ✅ If farmer logged in, show the page
    farmer_name = session["farmer_name"]
    message = None
    soil = ''
    water = ''
    crop = ''

    if request.method == "POST":
        soil = request.form["soil"]
        water = request.form["water"]
        crop = request.form["crop"]
        farm_address = request.form.get("farm_address", "")
        latitude = request.form.get("latitude", "")
        longitude = request.form.get("longitude", "")
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Store in session for the suggestion page
        session['soil_type'] = soil
        session['water_level'] = water
        session['selected_crop'] = crop
        session['farm_address'] = farm_address
        session['latitude'] = latitude
        session['longitude'] = longitude

        conn.execute("""
            INSERT INTO farmer_data (name, soil_type, water_level, crop, farm_address, latitude, longitude, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (farmer_name, soil, water, crop, farm_address, latitude, longitude, created_at))
        conn.commit()
        message = "✅ Data submitted successfully!"

    conn.close()
    return render_template(
        "farmer.html",
        message=message,
        name=farmer_name,
        soil=soil,
        water=water,
        crop=crop
    )

# --- Admin Dashboard (Shows all farmer data including location) ---
@app.route('/dashboard')
def dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = get_db()

    # Join farmer_data with farmers table to get registration ID
    farmers = conn.execute("""
        SELECT fd.*, f.id as farmer_registration_id 
        FROM farmer_data fd
        LEFT JOIN farmers f ON fd.name = f.name
        WHERE fd.crop IS NOT NULL AND fd.crop != ''
        ORDER BY fd.id DESC
    """).fetchall()

    # Convert to list of dictionaries and format dates
    farmers_list = []
    for farmer in farmers:
        farmer_dict = dict(farmer)
        # Format the created_at date if it exists
        if farmer_dict['created_at']:
            try:
                # Parse the datetime string and format it nicely
                dt = datetime.strptime(farmer_dict['created_at'], '%Y-%m-%d %H:%M:%S')
                farmer_dict['formatted_date'] = dt.strftime('%d %b %Y')
                farmer_dict['formatted_time'] = dt.strftime('%I:%M %p')
            except:
                farmer_dict['formatted_date'] = farmer_dict['created_at'][:10]
                farmer_dict['formatted_time'] = farmer_dict['created_at'][11:16]
        else:
            farmer_dict['formatted_date'] = 'N/A'
            farmer_dict['formatted_time'] = ''

        farmers_list.append(farmer_dict)

    conn.close()
    return render_template('dashboard.html', farmers=farmers_list)


# --- Delete Submission ---
@app.route('/delete_submission/<int:submission_id>')
def delete_submission(submission_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = get_db()
    try:
        # Get submission details for the message
        submission = conn.execute("SELECT name FROM farmer_data WHERE id = ?", (submission_id,)).fetchone()

        conn.execute("DELETE FROM farmer_data WHERE id = ?", (submission_id,))
        conn.commit()

        # Check if we need to reset auto-increment (if table is empty)
        remaining_submissions = conn.execute("SELECT COUNT(*) as count FROM farmer_data").fetchone()['count']

        if submission:
            message = f'✅ Submission from {submission["name"]} (ID: {submission_id}) deleted successfully!'
        else:
            message = '✅ Submission deleted successfully!'

        # If no submissions left, reset auto-increment to start from 1
        if remaining_submissions == 0:
            conn.execute("DELETE FROM sqlite_sequence WHERE name='farmer_data'")
            conn.execute("INSERT INTO sqlite_sequence (name, seq) VALUES ('farmer_data', 0)")
            conn.commit()
            message += ' Auto-increment reset to start from 1.'
        else:
            message += ' ID will be reused for new submissions.'

        flash(message, 'success')

    except sqlite3.Error as e:
        flash(f'❌ Error deleting submission: {str(e)}', 'error')
    finally:
        conn.close()

    return redirect(url_for('dashboard'))


# --- Delete Farmer ---
@app.route('/delete_farmer/<int:farmer_id>')
def delete_farmer(farmer_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = get_db()
    try:
        # First get farmer details
        farmer = conn.execute("SELECT name FROM farmers WHERE id = ?", (farmer_id,)).fetchone()

        if farmer:
            farmer_name = farmer['name']

            # Count how many submissions this farmer has
            submission_count = \
            conn.execute("SELECT COUNT(*) FROM farmer_data WHERE name = ?", (farmer_name,)).fetchone()[0]

            # Delete related data from farmer_data table
            conn.execute("DELETE FROM farmer_data WHERE name = ?", (farmer_name,))

            # Then delete the farmer
            conn.execute("DELETE FROM farmers WHERE id = ?", (farmer_id,))

            conn.commit()

            # Check if we need to reset auto-increment (if table is empty)
            remaining_farmers = conn.execute("SELECT COUNT(*) as count FROM farmers").fetchone()['count']

            # Prepare success message
            if submission_count > 0:
                message = f'✅ Farmer {farmer_name} (ID: {farmer_id}) and their {submission_count} submission(s) deleted successfully!'
            else:
                message = f'✅ Farmer {farmer_name} (ID: {farmer_id}) deleted successfully!'

            # If no farmers left, reset auto-increment to start from 1
            if remaining_farmers == 0:
                conn.execute("DELETE FROM sqlite_sequence WHERE name='farmers'")
                conn.execute("INSERT INTO sqlite_sequence (name, seq) VALUES ('farmers', 0)")
                conn.commit()
                message += ' Auto-increment reset to start from 1.'
            else:
                message += ' ID will be reused for new registrations.'

            flash(message, 'success')

        else:
            flash('❌ Farmer not found!', 'error')

    except sqlite3.Error as e:
        flash(f'❌ Error deleting farmer: {str(e)}', 'error')
    finally:
        conn.close()

    return redirect(url_for('farmer_data'))


# --- Reset All IDs (Manual Reset) ---
@app.route('/reset_ids')
def reset_ids():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = get_db()
    try:
        # Reset both tables' auto-increment
        conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('farmers', 'farmer_data')")
        conn.execute("INSERT INTO sqlite_sequence (name, seq) VALUES ('farmers', 0)")
        conn.execute("INSERT INTO sqlite_sequence (name, seq) VALUES ('farmer_data', 0)")
        conn.commit()

        flash('✅ Auto-increment counters reset successfully! New records will start from ID 1.', 'success')
    except sqlite3.Error as e:
        flash(f'❌ Error resetting IDs: {str(e)}', 'error')
    finally:
        conn.close()

    return redirect(url_for('dashboard'))


# --- Send Recommendation (Optional - if you still want to keep this feature) ---
@app.route('/send_recommendation', methods=['POST'])
def send_recommendation():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = get_db()

    # Loop through all form fields to find recommendations
    for key, value in request.form.items():
        if key.startswith('recommendation_') and value:  # Only process selected recommendations
            farmer_id = key.split('_')[1]  # Extract farmer ID from field name
            conn.execute(
                "UPDATE farmer_data SET recommendation=? WHERE id=?",
                (value, farmer_id)
            )

    conn.commit()
    conn.close()

    return redirect(url_for('dashboard'))


# --- Reports ---
@app.route('/reports')
def reports():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = get_db()

    # Fetch data safely
    soil_rows = conn.execute("""
        SELECT soil_type, COUNT(*) as count 
        FROM farmer_data 
        WHERE soil_type IS NOT NULL AND soil_type != '' 
        GROUP BY soil_type
    """).fetchall()

    crop_rows = conn.execute("""
        SELECT crop, COUNT(*) as count 
        FROM farmer_data 
        WHERE crop IS NOT NULL AND crop != '' 
        GROUP BY crop
    """).fetchall()

    water_rows = conn.execute("""
        SELECT water_level, COUNT(*) as count 
        FROM farmer_data 
        WHERE water_level IS NOT NULL AND water_level != '' 
        GROUP BY water_level
    """).fetchall()

    conn.close()

    # Convert rows to dictionaries
    soil_data = [{'soil_type': row['soil_type'], 'count': row['count']} for row in soil_rows if row['soil_type']]
    crop_data = [{'crop': row['crop'], 'count': row['count']} for row in crop_rows if row['crop']]
    water_data = [{'water_level': row['water_level'], 'count': row['count']} for row in water_rows if row['water_level']]

    # ✅ Safe debug logging for Windows (avoids OSError)
    try:
        print("=== REPORT DATA ===")
        print("Soil Data:", soil_data)
        print("Crop Data:", crop_data)
        print("Water Data:", water_data)
        print("===================")
    except Exception as e:
        # Prevent crash if console can't display characters
        pass

    return render_template(
        'reports.html',
        soil_data=soil_data,
        crop_data=crop_data,
        water_data=water_data
    )

# --- About ---
@app.route('/about')
def about():
    return render_template('about.html')


# --- Irrigation ---
@app.route('/irrigation')
def irrigation():
    return render_template('irrigation.html')


@app.route('/crop')
def crop():
    return render_template('crop.html')


@app.route('/rice')
def rice():
    return render_template('rice.html')


@app.route('/wheat')
def wheat():
    return render_template('wheat.html')


@app.route('/maize')
def maize():
    return render_template('maize.html')


@app.route('/sugarcane')
def sugarcane():
    return render_template('sugarcane.html')


@app.route('/cotton')
def cotton():
    return render_template('cotton.html')


# --- Contact Page (Feedback system only) ---
@app.route('/contact', methods=['GET', 'POST'])
def contact():
    conn = get_db()

    # --- If Admin is logged in: show feedback only ---
    if session.get('admin_logged_in'):
        feedbacks = conn.execute("""
            SELECT name, feedback 
            FROM farmer_data
            WHERE feedback IS NOT NULL AND feedback != ''
            ORDER BY id DESC
        """).fetchall()
        conn.close()
        return render_template('contact.html', role='admin', feedbacks=feedbacks)

    # --- If Farmer or Guest (Can send feedback) ---
    if request.method == 'POST':
        name = session.get('farmer_name', request.form.get('name', 'Guest User'))
        email = request.form.get('email', None)
        feedback = request.form['feedback']

        conn.execute("""
            INSERT INTO farmer_data (name, feedback)
            VALUES (?, ?)
        """, (f"{name} ({email})", feedback))
        conn.commit()
        conn.close()
        return render_template('contact.html', role='farmer', message="✅ Feedback received successfully!")

    conn.close()
    return render_template('contact.html', role='farmer')


@app.route('/suggestion')
def suggestion():
    # Check if farmer is logged in
    if not session.get('farmer_logged_in'):
        return redirect(url_for('farmer_login'))

    # Check if farmer has submitted data
    if not session.get('soil_type') or not session.get('selected_crop'):
        flash('Please submit your farm data first to get crop suggestions.', 'info')
        return redirect(url_for('farmer'))

    # Get crop recommendations based on soil and water conditions
    soil_type = session.get('soil_type', '')
    water_level = session.get('water_level', '')
    selected_crop = session.get('selected_crop', '')

    # Generate recommendations
    recommended_crops = get_crop_recommendations(soil_type, water_level)
    crop_guide = get_crop_guide(selected_crop)
    additional_suggestions = get_additional_suggestions(soil_type, water_level)

    return render_template(
        'suggestion.html',
        farmer_name=session.get('farmer_name'),
        soil_type=soil_type,
        water_level=water_level,
        selected_crop=selected_crop,
        farm_address=session.get('farm_address', ''),
        recommended_crops=recommended_crops,
        crop_guide=crop_guide,
        additional_suggestions=additional_suggestions
    )


# Helper functions for crop recommendations
def get_crop_recommendations(soil_type, water_level):
    # Crop suggestions database
    crop_suggestions = {
        "Black Soil": {
            "Low (Below 2m)": ["Cotton", "Groundnut", "Jowar (Sorghum)", "Soybean"],
            "Moderate (2m - 5m)": ["Cotton", "Soybean", "Jowar (Sorghum)", "Wheat", "Sunflower"],
            "High (Above 5m)": ["Sugarcane", "Rice", "Turmeric", "Banana"],
            "Waterlogged Area": ["Rice", "Sugarcane"]
        },
        "Laterite Soil": {
            "Low (Below 2m)": ["Cashew", "Groundnut", "Bajra (Pearl Millet)"],
            "Moderate (2m - 5m)": ["Cashew", "Sugarcane", "Turmeric", "Mango"],
            "High (Above 5m)": ["Rice", "Sugarcane", "Banana"],
            "Waterlogged Area": ["Rice"]
        },
        "Alluvial Soil": {
            "Low (Below 2m)": ["Wheat", "Gram (Chana)", "Barley", "Mustard"],
            "Moderate (2m - 5m)": ["Wheat", "Rice", "Sugarcane", "Cotton", "Maize"],
            "High (Above 5m)": ["Rice", "Sugarcane", "Banana", "Turmeric"],
            "Waterlogged Area": ["Rice", "Jute"]
        },
        "Red Soil": {
            "Low (Below 2m)": ["Groundnut", "Bajra (Pearl Millet)", "Ragi", "Gram (Chana)"],
            "Moderate (2m - 5m)": ["Groundnut", "Jowar (Sorghum)", "Cotton", "Maize"],
            "High (Above 5m)": ["Rice", "Sugarcane"],
            "Waterlogged Area": ["Rice"]
        },
        "Marshy and Peaty Soil": {
            "Low (Below 2m)": ["Rice", "Jute", "Sugarcane"],
            "Moderate (2m - 5m)": ["Rice", "Sugarcane", "Banana"],
            "High (Above 5m)": ["Rice", "Sugarcane", "Aquaculture"],
            "Waterlogged Area": ["Rice", "Aquaculture", "Jute"]
        }
    }

    if soil_type in crop_suggestions and water_level in crop_suggestions[soil_type]:
        return crop_suggestions[soil_type][water_level]
    return []


def get_crop_guide(crop_name):
    # Crop database with detailed information
    crop_database = {
        "Rice": {
            "season": "Kharif (June-October)",
            "icon": "🌾",
            "timing": "Sow: June-July, Harvest: October-November. Best time for sowing is with onset of monsoon.",
            "soil": "Clayey loam with good water retention. pH: 5.5-6.5. Requires puddling for better growth.",
            "water": "Requires standing water (5-10cm depth). Ideal for high water level areas. Total water requirement: 1200-1500mm.",
            "care": "Transplant 25-30 day old seedlings. Control weeds, manage water levels, watch for blast and stem borer."
        },
        "Wheat": {
            "season": "Rabi (November-March)",
            "icon": "🌾",
            "timing": "Sow: November-December, Harvest: March-April. Ideal temperature: 20-25°C during growing period.",
            "soil": "Well-drained loamy soil. pH: 6.0-7.5. Avoid waterlogged conditions.",
            "water": "Moderate water requirements (4-6 irrigations). Critical stages: crown root, tillering, flowering.",
            "care": "Seed rate: 100-125 kg/ha. Fertilizer: N:P:K - 120:60:40 kg/ha. Control rust and aphids."
        },
        "Cotton": {
            "season": "Kharif (June-December)",
            "icon": "🧵",
            "timing": "Sow: June-July, Harvest: December-January. Requires warm temperature (25-35°C).",
            "soil": "Black soil preferred, well-drained. pH: 6.0-8.0. Good for water moderate areas.",
            "water": "Moderate water requirements. Drought tolerant but needs irrigation during flowering and boll formation.",
            "care": "Regular weeding, pest control for bollworms. Spacing: 60-90 cm between plants."
        },
        "Sugarcane": {
            "season": "Year-round (12-18 months)",
            "icon": "🎋",
            "timing": "Plant: February-March or October-November. Harvest: After 12-18 months.",
            "soil": "Deep, well-drained loamy soil. pH: 6.5-7.5. Requires good organic matter.",
            "water": "High water requirements. Needs regular irrigation. Total water: 1500-2500mm.",
            "care": "Planting: 3-budded setts. Fertilizer: 200-300 kg N/ha. Control red rot and borers."
        },
        "Groundnut": {
            "season": "Kharif (June-September)",
            "icon": "🥜",
            "timing": "Sow: June-July, Harvest: September-October. Requires warm climate.",
            "soil": "Well-drained sandy loam. pH: 6.0-7.0. Avoid heavy soils.",
            "water": "Low to moderate water needs. Sensitive to waterlogging.",
            "care": "Seed rate: 100-120 kg/ha. Inoculate with Rhizobium. Control leaf spot and root rot."
        }
        # Add more crops as needed...
    }

    return crop_database.get(crop_name, {
        "season": "Information not available",
        "icon": "🌱",
        "timing": "Seasonal information not available for this crop.",
        "soil": "Soil preparation details not available.",
        "water": "Water management information not available.",
        "care": "Crop care instructions not available."
    })


def get_additional_suggestions(soil_type, water_level):
    suggestions = {
        "rotation": get_rotation_suggestion(soil_type),
        "intercropping": get_intercropping_suggestion(soil_type),
        "irrigation": get_irrigation_suggestion(water_level)
    }
    return suggestions


def get_rotation_suggestion(soil):
    suggestions = {
        "Black Soil": "Rotate cotton with legumes like soybean or pigeon pea to improve soil nitrogen and break pest cycles.",
        "Red Soil": "Rotate millets with pulses like green gram or black gram. Include oilseeds in rotation.",
        "Alluvial Soil": "Rice-wheat rotation or add legumes in rotation. Include mustard or maize for diversification.",
        "Laterite Soil": "Include groundnut and pulses in rotation with cashew. Practice mixed cropping with legumes.",
        "Marshy and Peaty Soil": "Rice-fish rotation or include jute. Practice integrated farming system."
    }
    return suggestions.get(soil, "Include legume crops in your rotation cycle to maintain soil health and fertility.")


def get_intercropping_suggestion(soil):
    suggestions = {
        "Black Soil": "Cotton with groundnut or soybean. Sorghum with pigeon pea.",
        "Red Soil": "Pearl millet with cluster bean. Groundnut with pearl millet.",
        "Alluvial Soil": "Wheat with chickpea. Rice with fish culture.",
        "Laterite Soil": "Cashew with pineapple or legumes. Coconut with pepper or cocoa.",
        "Marshy and Peaty Soil": "Rice with fish or prawns. Include aquatic plants."
    }
    return suggestions.get(soil,
                           "Consider intercropping with compatible crops for better land utilization and risk management.")


def get_irrigation_suggestion(water):
    suggestions = {
        "Low (Below 2m)": "Use drip irrigation and mulching to conserve water. Grow drought-resistant crops and practice rainwater harvesting.",
        "Moderate (2m - 5m)": "Schedule irrigation based on crop growth stages. Use sprinkler irrigation for efficient water use.",
        "High (Above 5m)": "Ensure proper drainage to prevent waterlogging. Practice controlled irrigation and grow water-loving crops.",
        "Waterlogged Area": "Install drainage systems. Grow aquatic crops or practice integrated fish farming with crops."
    }
    return suggestions.get(water, "Optimize irrigation based on crop requirements and soil moisture conditions.")

# --- Logout ---
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


if __name__ == '__main__':
    import webbrowser
    from threading import Timer


    # --- Automatically open the browser ---
    def open_browser():
        webbrowser.open_new("http://127.0.0.1:5000/")


    # Open browser after 1 second
    Timer(1, open_browser).start()

    # Run the Flask app
    app.run(debug=True)