import os
import io
import json
from flask import Flask, render_template, request, redirect, session, url_for, send_file
from fpdf import FPDF
import mysql.connector
from mysql.connector import Error
import config

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = config.SECRET_KEY


# ================= DATABASE CONFIG =================
DB_CONFIG = config.DB_CONFIG


# ================= DATABASE HELPERS =================
def get_db_connection():
    """Return a MySQL connection with dict-style row access."""
    conn = mysql.connector.connect(**DB_CONFIG)
    return conn


def fetchone_as_dict(cursor):
    row = cursor.fetchone()
    if row is None:
        return None
    cols = [d[0] for d in cursor.description]
    return dict(zip(cols, row))


def fetchall_as_dict(cursor):
    rows = cursor.fetchall()
    cols = [d[0] for d in cursor.description]
    return [dict(zip(cols, row)) for row in rows]


# ================= INIT DB =================
def init_db():
    try:
        # Connect without specifying DB first to create it if needed
        base_conn = mysql.connector.connect(
            host=DB_CONFIG["host"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            charset=DB_CONFIG["charset"]
        )
        base_cursor = base_conn.cursor()
        base_cursor.execute(
            "CREATE DATABASE IF NOT EXISTS `tour_booking` "
            "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        base_conn.commit()
        base_cursor.close()
        base_conn.close()
    except Error as e:
        print(f"[init_db] Could not create database: {e}")
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    # --- Create tables ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT NOT NULL AUTO_INCREMENT,
            name LONGTEXT,
            email LONGTEXT,
            password LONGTEXT,
            is_admin TINYINT(1) DEFAULT 0,
            PRIMARY KEY (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS destinations (
            id INT NOT NULL AUTO_INCREMENT,
            state LONGTEXT,
            name LONGTEXT,
            hotel_cost DOUBLE,
            food_cost DOUBLE,
            sightseeing_cost DOUBLE,
            image_url LONGTEXT,
            itinerary LONGTEXT,
            PRIMARY KEY (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trips (
            id INT NOT NULL AUTO_INCREMENT,
            user_id INT,
            destination LONGTEXT,
            days INT,
            total_cost DOUBLE,
            start_date LONGTEXT,
            PRIMARY KEY (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cars (
            id INT NOT NULL AUTO_INCREMENT,
            name LONGTEXT,
            price DOUBLE,
            image_url LONGTEXT,
            PRIMARY KEY (id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    conn.commit()

    # --- Seed destinations ---
    cursor.execute("SELECT COUNT(*) FROM destinations")
    count = cursor.fetchone()[0]

    if count == 0:
        def make_itin(days):
            return json.dumps(days)

        sample_destinations = [
            ("Tamil Nadu", "Ooty", 2500, 800, 500,
             "https://images.unsplash.com/photo-1609766856923-7e0a7a3b1b5a?w=600&q=80",
             make_itin([
                 {"day": 1, "title": "Arrival & City Tour", "desc": "Visit Ooty Botanical Gardens and Ooty Lake. Enjoy an evening boat ride.", "image": "https://images.unsplash.com/photo-1549479404-51e944111352?w=400&q=80"},
                 {"day": 2, "title": "Peaks & Valleys", "desc": "Doddabetta Peak for sunrise, followed by the Tea Museum and Rose Garden.", "image": "https://images.unsplash.com/photo-1590050731038-f86aeccd95b2?w=400&q=80"},
                 {"day": 3, "title": "Toy Train Ride", "desc": "Take the Nilgiri Mountain Railway to Coonoor. Visit Sim's Park and Dolphin's Nose.", "image": "https://images.unsplash.com/photo-1616053303666-ac288b58406f?w=400&q=80"}
             ])),
            ("Tamil Nadu", "Kodaikanal", 2200, 700, 400,
             "https://images.unsplash.com/photo-1589308078059-be1415eab4c3?w=600&q=80",
             make_itin([
                 {"day": 1, "title": "Lakes & Walks", "desc": "Kodai Lake boating and a stroll along Coaker's Walk. Visit Bryant Park.", "image": "https://images.unsplash.com/photo-1596489399873-1002237eb5f4?w=400&q=80"},
                 {"day": 2, "title": "Waterfalls Tour", "desc": "Visit Silver Cascade Falls, Bear Shola Falls, and Pillar Rocks.", "image": "https://images.unsplash.com/photo-1574069806497-6a45749aeb04?w=400&q=80"},
                 {"day": 3, "title": "Trekking & Viewpoints", "desc": "Trek to Dolphin's Nose and Echo Point. Shopping in the evening.", "image": "https://images.unsplash.com/photo-1605416954271-e5d4dcb12d93?w=400&q=80"}
             ])),
            ("Kerala", "Munnar", 2800, 900, 600,
             "https://images.unsplash.com/photo-1602216056096-3b40cc0c9944?w=600&q=80",
             make_itin([
                 {"day": 1, "title": "Tea Gardens", "desc": "Visit the Tata Tea Museum and wide stretches of tea plantations. Eravikulam National Park.", "image": "https://images.unsplash.com/photo-1595167732049-2eeb2be7e076?w=400&q=80"},
                 {"day": 2, "title": "Waterfalls & Dams", "desc": "Mattupetty Dam, Echo Point, and Attukal Waterfalls.", "image": "https://images.unsplash.com/photo-1593693397365-c3c1374582f3?w=400&q=80"}
             ])),
            ("Himachal Pradesh", "Manali", 3000, 850, 700,
             "https://images.unsplash.com/photo-1626621341517-bbf3d9990a23?w=600&q=80",
             make_itin([
                 {"day": 1, "title": "Local Sightseeing", "desc": "Hadimba Temple, Manu Temple, and Mall Road.", "image": "https://images.unsplash.com/photo-1593644310574-8846c4f9f74a?w=400&q=80"},
                 {"day": 2, "title": "Solang Valley", "desc": "Full day at Solang Valley for adventure sports (paragliding, zorbing).", "image": "https://images.unsplash.com/photo-1592329348981-cd54fd3ae9b1?w=400&q=80"},
                 {"day": 3, "title": "Rohtang Pass", "desc": "Snow activities at Rohtang Pass (subject to opening).", "image": "https://images.unsplash.com/photo-1563865436874-ce921ad2dbdc?w=400&q=80"}
             ])),
            ("Goa", "Goa Beaches", 3500, 1000, 800,
             "https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?w=600&q=80",
             make_itin([
                 {"day": 1, "title": "North Goa Beaches", "desc": "Baga Beach, Calangute, and Anjuna Beach. Night market.", "image": "https://images.unsplash.com/photo-1560179406-1bc09c6cd7b9?w=400&q=80"},
                 {"day": 2, "title": "South Goa & Churches", "desc": "Basilica of Bom Jesus, Colva Beach, and Dona Paula.", "image": "https://images.unsplash.com/photo-1587595431973-160d0d94add1?w=400&q=80"}
             ])),
            ("Rajasthan", "Jaipur", 2000, 600, 500,
             "https://images.unsplash.com/photo-1477587458883-47145ed94245?w=600&q=80",
             make_itin([
                 {"day": 1, "title": "Forts Tour", "desc": "Amber Fort elephant ride, Jaigarh Fort, and Nahargarh Fort sunset.", "image": "https://images.unsplash.com/photo-1599661559684-d7dc34f9a061?w=400&q=80"},
                 {"day": 2, "title": "City Palaces", "desc": "City Palace, Hawa Mahal, and Jantar Mantar.", "image": "https://images.unsplash.com/photo-1581403673570-5b51239c0862?w=400&q=80"}
             ])),
            ("Rajasthan", "Udaipur", 2800, 750, 550,
             "https://images.unsplash.com/photo-1595658658481-d53d3f999875?w=600&q=80",
             make_itin([
                 {"day": 1, "title": "City of Lakes", "desc": "City Palace, Lake Pichola boat ride, and Jag Mandir.", "image": "https://images.unsplash.com/photo-1557088714-38cdeb6110f0?w=400&q=80"},
                 {"day": 2, "title": "Culture & Views", "desc": "Sajjangarh Monsoon Palace, Saheliyon-ki-Bari, and Bagore Ki Haveli show.", "image": "https://images.unsplash.com/photo-1628126235206-5260b9ea6441?w=400&q=80"}
             ])),
            ("Himachal Pradesh", "Shimla", 2600, 800, 500,
             "https://images.unsplash.com/photo-1597074866923-dc0589150458?w=600&q=80",
             make_itin([
                 {"day": 1, "title": "Mall Road & Ridge", "desc": "The Ridge, Christ Church, and shopping at Mall Road.", "image": "https://images.unsplash.com/photo-1596395270119-915f013bd0df?w=400&q=80"},
                 {"day": 2, "title": "Kufri", "desc": "Excursion to Kufri for horse riding and Himalayan Nature Park.", "image": "https://images.unsplash.com/photo-1610408542918-ad1f190eec26?w=400&q=80"}
             ])),
            ("West Bengal", "Darjeeling", 2400, 700, 450,
             "https://images.unsplash.com/photo-1622308644420-b20142dc993c?w=600&q=80",
             make_itin([
                 {"day": 1, "title": "Tiger Hill Sunrise", "desc": "Early morning Tiger Hill sunrise over Kanchenjunga. Batasia Loop and Ghoom Monastery.", "image": "https://images.unsplash.com/photo-1566858273678-bdacd873cb95?w=400&q=80"},
                 {"day": 2, "title": "Tea & Zoo", "desc": "Happy Valley Tea Estate, Himalayan Mountaineering Institute, and Zoo.", "image": "https://images.unsplash.com/photo-1627918512591-23cb49a46f7c?w=400&q=80"}
             ])),
            ("Puducherry", "Pondicherry", 2200, 750, 400,
             "https://images.unsplash.com/photo-1582510003544-4d00b7f74220?w=600&q=80",
             make_itin([
                 {"day": 1, "title": "French Quarter", "desc": "Promenade Beach, Aurobindo Ashram, and exploring White Town cafes.", "image": "https://images.unsplash.com/photo-1583002674391-7db8a0b0058b?w=400&q=80"},
                 {"day": 2, "title": "Auroville", "desc": "Visit Auroville and Matrimandir. Paradise Beach in the afternoon.", "image": "https://images.unsplash.com/photo-1614088927063-e4d588506169?w=400&q=80"}
             ]))
        ]

        cursor.executemany("""
            INSERT INTO destinations (state, name, hotel_cost, food_cost, sightseeing_cost, image_url, itinerary)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, sample_destinations)

    # --- Ensure admin user exists ---
    cursor.execute("SELECT * FROM users WHERE email='admin@tour.com'")
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO users (name, email, password, is_admin)
            VALUES (%s, %s, %s, %s)
        """, ('Admin', 'admin@tour.com', 'admin123', 1))

    # --- Seed cars ---
    cursor.execute("SELECT COUNT(*) FROM cars")
    if cursor.fetchone()[0] == 0:
        sample_cars = [
            ("Hatchback", 2000, json.dumps([
                "https://images.unsplash.com/photo-1549317661-bd32c8ce0db2?w=1600&q=80",
                "https://images.unsplash.com/photo-1544258925-fb355b25ee4b?w=1600&q=80",
                "https://images.unsplash.com/photo-1590362891991-f776e747a588?w=1600&q=80"
            ])),
            ("Sedan", 3000, json.dumps([
                "https://images.unsplash.com/photo-1550355291-bbee04a92027?w=1600&q=80",
                "https://images.unsplash.com/photo-1503376762369-07f2aebf9bad?w=1600&q=80",
                "https://images.unsplash.com/photo-1541899481282-d53bffe3c35d?w=1600&q=80"
            ])),
            ("SUV", 5000, json.dumps([
                "https://images.unsplash.com/photo-1533473359331-0135ef1b58bf?w=1600&q=80",
                "https://images.unsplash.com/photo-1506015391300-4152f4192446?w=1600&q=80",
                "https://images.unsplash.com/photo-1519641471654-76ce0107ad1b?w=1600&q=80"
            ]))
        ]
        cursor.executemany("""
            INSERT INTO cars (name, price, image_url)
            VALUES (%s, %s, %s)
        """, sample_cars)

    conn.commit()
    cursor.close()
    conn.close()


init_db()


# ================= HOME =================
@app.route("/")
def home():
    return redirect("/login")


# ================= REGISTER =================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (name, email, password)
            VALUES (%s, %s, %s)
        """, (
            request.form["name"],
            request.form["email"],
            request.form["password"]
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect("/login")

    return render_template("register.html")


# ================= LOGIN =================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=%s",
                       (request.form["email"],))
        user = fetchone_as_dict(cursor)
        cursor.close()
        conn.close()

        if user and user["password"] == request.form["password"]:
            if user["is_admin"] == 1:
                return redirect("/admin/login")

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["is_admin"] = user["is_admin"]
            return redirect("/dashboard")

        return "Invalid Credentials"

    return render_template("login.html")


# ================= ADMIN LOGIN =================
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=%s",
                       (request.form["email"],))
        user = fetchone_as_dict(cursor)
        cursor.close()
        conn.close()

        if user and user["password"] == request.form["password"] and user["is_admin"] == 1:
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["is_admin"] = user["is_admin"]
            return redirect("/admin")

        return "Invalid Admin Credentials"

    return render_template("admin_login.html")


# ================= DASHBOARD =================
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    return render_template("dashboard.html", name=session["user_name"])


# ================= BUDGET PAGE =================
@app.route("/budget")
def budget():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM destinations")
    destinations = fetchall_as_dict(cursor)
    cursor.close()
    conn.close()

    return render_template("budget.html", destinations=destinations)


# ================= DESTINATION =================
@app.route("/destination/<int:id>", methods=["GET", "POST"])
def destination(id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM destinations WHERE id=%s", (id,))
    place = fetchone_as_dict(cursor)

    if not place:
        cursor.close()
        conn.close()
        return "Destination not found"

    itinerary = []
    if place["itinerary"]:
        try:
            itinerary = json.loads(place["itinerary"])
        except json.JSONDecodeError:
            pass

    if request.method == "POST":
        days = int(request.form["days"])
        total = (place["hotel_cost"] +
                 place["food_cost"] +
                 place["sightseeing_cost"]) * days

        cursor.execute("""
            INSERT INTO trips (user_id, destination, days, total_cost)
            VALUES (%s, %s, %s, %s)
        """, (
            session["user_id"],
            place["name"],
            days,
            total
        ))
        conn.commit()
        trip_id = cursor.lastrowid
        cursor.close()
        conn.close()

        return redirect(url_for("booking_success", trip_id=trip_id))

    cursor.close()
    conn.close()
    return render_template("destination.html", place=place, itinerary=itinerary)


# ================= BOOKING SUCCESS =================
@app.route("/booking-success/<int:trip_id>")
def booking_success(trip_id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trips WHERE id=%s", (trip_id,))
    trip = fetchone_as_dict(cursor)
    cursor.close()
    conn.close()

    if not trip:
        return "Booking not found"

    return render_template("booking_success.html", trip=trip)


# ================= CAR RENTAL =================
@app.route("/car-rental", methods=["GET", "POST"])
def car_rental():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        car_id = request.form["car_id"]
        days = int(request.form["days"])

        cursor.execute("SELECT * FROM cars WHERE id=%s", (car_id,))
        car = fetchone_as_dict(cursor)

        if car:
            total = days * car["price"]
            cursor.execute("""
                INSERT INTO trips (user_id, destination, days, total_cost)
                VALUES (%s, %s, %s, %s)
            """, (
                session["user_id"],
                f"Car Rental: {car['name']}",
                days,
                total
            ))
            conn.commit()

            cursor.execute("SELECT * FROM cars")
            cars = fetchall_as_dict(cursor)
            cursor.close()
            conn.close()

            return render_template("car_rental.html",
                                   result=True, total=total, cars=cars)

    cursor.execute("SELECT * FROM cars")
    cars = fetchall_as_dict(cursor)
    cursor.close()
    conn.close()

    return render_template("car_rental.html", cars=cars)


# ================= SAVED TRIPS =================
@app.route("/saved-trips")
def saved_trips():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trips WHERE user_id=%s",
                   (session["user_id"],))
    trips = fetchall_as_dict(cursor)
    cursor.close()
    conn.close()

    return render_template("saved_trips.html", trips=trips)


# ================= ADMIN DASHBOARD =================
@app.route("/admin")
def admin_dashboard():
    if "user_id" not in session or not session.get("is_admin"):
        return "Access Denied"

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM destinations")
    destinations = fetchall_as_dict(cursor)
    cursor.close()
    conn.close()

    return render_template("admin_dashboard.html", destinations=destinations)


# ================= ADMIN ADD DESTINATION =================
@app.route("/admin/add", methods=["GET", "POST"])
def admin_add():
    if "user_id" not in session or not session.get("is_admin"):
        return "Access Denied"

    if request.method == "POST":
        itinerary_data = []
        days = request.form.getlist("itin_day[]")
        titles = request.form.getlist("itin_title[]")
        descs = request.form.getlist("itin_desc[]")
        images = request.form.getlist("itin_image[]")

        for i in range(len(days)):
            if i < len(titles) and i < len(descs) and titles[i].strip() and descs[i].strip():
                item = {
                    "day": int(days[i]),
                    "title": titles[i].strip(),
                    "desc": descs[i].strip()
                }
                if i < len(images) and images[i].strip():
                    item["image"] = images[i].strip()
                itinerary_data.append(item)

        itinerary_str = json.dumps(itinerary_data) if itinerary_data else ""

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO destinations
            (state, name, hotel_cost, food_cost, sightseeing_cost, image_url, itinerary)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            request.form["state"],
            request.form["name"],
            request.form["hotel"],
            request.form["food"],
            request.form["sight"],
            request.form["image"],
            itinerary_str
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect("/admin")

    return render_template("add_destination.html")


# ================= ADMIN EDIT DESTINATION =================
@app.route("/admin/edit/<int:id>", methods=["GET", "POST"])
def admin_edit(id):
    if "user_id" not in session or not session.get("is_admin"):
        return "Access Denied"

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        itinerary_data = []
        days = request.form.getlist("itin_day[]")
        titles = request.form.getlist("itin_title[]")
        descs = request.form.getlist("itin_desc[]")
        images = request.form.getlist("itin_image[]")

        for i in range(len(days)):
            if i < len(titles) and i < len(descs) and titles[i].strip() and descs[i].strip():
                item = {
                    "day": int(days[i]),
                    "title": titles[i].strip(),
                    "desc": descs[i].strip()
                }
                if i < len(images) and images[i].strip():
                    item["image"] = images[i].strip()
                itinerary_data.append(item)

        itinerary_str = json.dumps(itinerary_data) if itinerary_data else ""

        cursor.execute("""
            UPDATE destinations
            SET state=%s, name=%s, hotel_cost=%s, food_cost=%s,
                sightseeing_cost=%s, image_url=%s, itinerary=%s
            WHERE id=%s
        """, (
            request.form["state"],
            request.form["name"],
            request.form["hotel"],
            request.form["food"],
            request.form["sight"],
            request.form["image"],
            itinerary_str,
            id
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect("/admin")

    cursor.execute("SELECT * FROM destinations WHERE id=%s", (id,))
    destination = fetchone_as_dict(cursor)
    cursor.close()
    conn.close()

    if not destination:
        return "Destination not found"

    return render_template("edit_destination.html", destination=destination)


# ================= ADMIN DELETE DESTINATION =================
@app.route("/admin/delete/<int:id>")
def admin_delete(id):
    if "user_id" not in session or not session.get("is_admin"):
        return "Access Denied"

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM destinations WHERE id=%s", (id,))
    conn.commit()
    cursor.close()
    conn.close()

    return redirect("/admin")


# ================= ADMIN TRIPS =================
@app.route("/admin/trips")
def admin_trips():
    if "user_id" not in session or not session.get("is_admin"):
        return "Access Denied"

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT trips.id, trips.destination, trips.days, trips.total_cost,
               users.name AS user_name
        FROM trips
        JOIN users ON trips.user_id = users.id
        ORDER BY trips.id DESC
    """)
    trips = fetchall_as_dict(cursor)
    cursor.close()
    conn.close()

    return render_template("admin_trips.html", trips=trips)


@app.route("/admin/delete_trip/<int:id>")
def admin_delete_trip(id):
    if "user_id" not in session or not session.get("is_admin"):
        return "Access Denied"

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM trips WHERE id=%s", (id,))
    conn.commit()
    cursor.close()
    conn.close()

    return redirect("/admin/trips")


# ================= ADMIN CARS =================
@app.route("/admin/cars")
def admin_cars():
    if "user_id" not in session or not session.get("is_admin"):
        return "Access Denied"

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cars ORDER BY id ASC")
    cars = fetchall_as_dict(cursor)
    cursor.close()
    conn.close()

    return render_template("admin_cars.html", cars=cars)


@app.route("/admin/cars/add", methods=["GET", "POST"])
def admin_add_car():
    if "user_id" not in session or not session.get("is_admin"):
        return "Access Denied"

    if request.method == "POST":
        raw_urls = request.form["image_url"].strip().split("\n")
        urls = [url.strip() for url in raw_urls if url.strip()]
        images_json = json.dumps(urls)

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO cars (name, price, image_url)
            VALUES (%s, %s, %s)
        """, (
            request.form["name"],
            request.form["price"],
            images_json
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect("/admin/cars")

    return render_template("admin_add_car.html")


@app.route("/admin/cars/edit/<int:id>", methods=["GET", "POST"])
def admin_edit_car(id):
    if "user_id" not in session or not session.get("is_admin"):
        return "Access Denied"

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        raw_urls = request.form["image_url"].strip().split("\n")
        urls = [url.strip() for url in raw_urls if url.strip()]
        images_json = json.dumps(urls)

        cursor.execute("""
            UPDATE cars
            SET name=%s, price=%s, image_url=%s
            WHERE id=%s
        """, (
            request.form["name"],
            request.form["price"],
            images_json,
            id
        ))
        conn.commit()
        cursor.close()
        conn.close()
        return redirect("/admin/cars")

    cursor.execute("SELECT * FROM cars WHERE id=%s", (id,))
    car = fetchone_as_dict(cursor)
    cursor.close()
    conn.close()

    if not car:
        return "Car not found"

    try:
        urls = json.loads(car["image_url"])
        car["image_url_text"] = "\n".join(urls) if isinstance(urls, list) else car["image_url"]
    except Exception:
        car["image_url_text"] = car["image_url"]

    return render_template("admin_edit_car.html", car=car)


@app.route("/admin/cars/delete/<int:id>")
def admin_delete_car(id):
    if "user_id" not in session or not session.get("is_admin"):
        return "Access Denied"

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cars WHERE id=%s", (id,))
    conn.commit()
    cursor.close()
    conn.close()

    return redirect("/admin/cars")


# ================= DOWNLOAD RECEIPT =================
@app.route("/download-receipt/<int:trip_id>")
def download_receipt(trip_id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trips WHERE id=%s AND user_id=%s",
                   (trip_id, session["user_id"]))
    trip = fetchone_as_dict(cursor)
    cursor.close()
    conn.close()

    if not trip:
        return "Trip not found", 404

    # Generate PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    pdf.set_fill_color(15, 23, 42)
    pdf.rect(0, 0, 210, 50, 'F')

    pdf.set_text_color(56, 189, 248)
    pdf.set_font("Helvetica", "B", 24)
    pdf.set_y(12)
    pdf.cell(0, 12, "Tour Planner", ln=True, align="C")
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 8, "Trip Receipt", ln=True, align="C")

    pdf.ln(20)
    pdf.set_text_color(30, 41, 59)

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, f"Booking #{trip['id']}", ln=True, align="C")
    pdf.ln(5)

    pdf.set_draw_color(200, 200, 200)
    pdf.line(30, pdf.get_y(), 180, pdf.get_y())
    pdf.ln(8)

    details = [
        ("Destination", str(trip["destination"])),
        ("Duration", f"{trip['days']} day{'s' if trip['days'] != 1 else ''}"),
        ("Total Cost", f"Rs. {trip['total_cost']:,.2f}"),
        ("Traveller", session.get("user_name", "N/A")),
    ]

    for label, value in details:
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(60, 10, label, align="R")
        pdf.cell(10, 10, "")
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(30, 41, 59)
        pdf.cell(0, 10, value, ln=True)

    pdf.ln(10)
    pdf.line(30, pdf.get_y(), 180, pdf.get_y())
    pdf.ln(10)

    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(0, 8, "Thank you for booking with Tour Planner!", ln=True, align="C")
    pdf.cell(0, 6, "This is a computer-generated receipt.", ln=True, align="C")

    pdf_bytes = pdf.output()
    buffer = io.BytesIO(pdf_bytes)
    buffer.seek(0)

    filename = f"TourPlanner_Receipt_{trip['id']}.pdf"
    return send_file(buffer, as_attachment=True,
                     download_name=filename,
                     mimetype="application/pdf")


# ================= LOGOUT =================
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


if __name__ == "__main__":
    # Use FLASK_DEBUG=true in .env for local development
    app.run(debug=config.DEBUG, port=int(os.environ.get("PORT", 5000)))