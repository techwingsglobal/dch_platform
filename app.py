import configparser
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import openai
import sqlite3
import snowflake.connector
from werkzeug.security import check_password_hash, generate_password_hash



# Initialize config parser
config = configparser.ConfigParser()
config.read('config.ini')

app = Flask(__name__)

app.secret_key = "your_secret_key"
# Fetch sensitive data from config
api_key = config['DEFAULT']['api_key']
# Set OpenAI API key
openai.api_key = api_key

# User credentials
users = {
    "doctor_user": {"password": "doctor_pass", "role": "doctor"},
    "staff_user": {"password": "staff_pass", "role": "staff"},
    "individual_user": {"password": "indiv_pass", "role": "individual"}
}
def query_snowflake(query, params=None):
    """
    Executes a parameterized query on Snowflake.
    :param query: The SQL query with placeholders
    :param params: Tuple of parameters to be substituted into the query
    :return: Query results
    """
    config = configparser.ConfigParser()
    config.read('config.ini')

    conn = snowflake.connector.connect(
        user=config['SNOWFLAKE']['user'],
        password=config['SNOWFLAKE']['password'],
        account=config['SNOWFLAKE']['account'],
        database=config['SNOWFLAKE']['database'],
        schema=config['SNOWFLAKE']['schema'],
        warehouse=config['SNOWFLAKE']['warehouse'],
        role=config['SNOWFLAKE']['role']
    )

    cursor = conn.cursor()
    try:
        # Execute query with or without parameters
        cursor.execute(query, params or ())
        results = cursor.fetchall()
    except Exception as e:
        print(f"Error executing Snowflake query: {e}")
        results = []
    finally:
        cursor.close()
        conn.close()

    return results

def search_medical_data(query):
    # Map table names to columns that might be relevant for the search
    table_column_map = {
        "ANATOMICAL_REFERENCES": ["title", "details"],
        "APPOINTMENTS": ["reason_for_visit"],
        "CASE_HISTORIES": ["condition", "procedure", "outcome", "notes"],
        "CHECKLISTS_AND_PROTOCOLS": ["title", "description"],
        "DOCTORS": ["name", "specialization"],
        "DRUG_REFERENCES": ["name", "usage", "side_effects"],
        "EQUIPMENT_MANUALS": ["equipment_name", "usage_summary"],
        "HOSPITALS": ["hospital_name", "departments"],
        "MEDICAL_LITERATURE": ["title", "summary"],
        "PATIENTS": ["name", "contact"],
        "SURGICAL_VIDEOS": ["title", "description"],
        "TREATMENT_HISTORY": ["diagnosis", "prescription", "procedure"],
    }

    # Query each table for the user's query
    results = []
    for table, columns in table_column_map.items():
        conditions = " OR ".join([f"{col} LIKE '%{query}%'" for col in columns])
        sql_query = f"SELECT * FROM HOSPITAL_SCHEMA.{table} WHERE {conditions}"
        table_results = query_snowflake(sql_query)
        if table_results:
            results.append({table: table_results})

    return results


# User Registration Route
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        role = request.form.get("role")

        if password != confirm_password:
            return render_template("register.html", error="Passwords do not match.")

        hashed_password = generate_password_hash(password)

        try:
            # Check if the username already exists
            check_query = "SELECT username FROM USERS WHERE username = %s"
            existing_user = query_snowflake(check_query, (username,))
            if existing_user:
                return render_template("register.html", error="Username already taken.")

            # Insert new user into database
            insert_query = "INSERT INTO USERS (username, password_hash, role) VALUES (%s, %s, %s)"
            query_snowflake(insert_query, (username, hashed_password, role))

            return redirect(url_for("login"))
        except Exception as e:
            return render_template("register.html", error=f"Error: {e}")

    return render_template("register.html")
@app.route("/")
def login():
    return render_template("login.html")


@app.route("/validate", methods=["POST"])
def validate():
    username = request.form.get("username")
    password = request.form.get("password")

    try:
        # Fetch user from the database
        query = "SELECT password_hash, role FROM USERS WHERE username = %s"
        result = query_snowflake(query, (username,))

        if result:
            password_hash, role = result[0]

            # Verify the password
            if check_password_hash(password_hash, password):
                session["username"] = username
                session["role"] = role
                return redirect(url_for("chat_screen", role=role))
            else:
                return render_template("login.html", error="Invalid Credentials")
        else:
            return render_template("login.html", error="User not found")
    except Exception as e:
        print(f"Error during login: {e}")
        return render_template("login.html", error="An error occurred. Please try again.")
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/chat_screen")
def chat_screen():
    role = session.get("role")  # Use session.get() to avoid KeyError
    if not role:
        return redirect(url_for("login"))  # Redirect to login if the session is invalid

    if role == 'doctor':
        return render_template("doctor_chat.html")
    elif role == 'staff':
        return render_template("staff_chat.html")
    else:
        return render_template("individual_chat.html")


def is_database_related(user_message):
    """
    Check if the user's message is related to the database using a keyword-based approach or GPT classification.
    """
    # Keyword-based relevance detection
    database_keywords = ["doctor", "treatment", "surgery", "drug", "protocol", "case history", "equipment", "appointment"]
    for keyword in database_keywords:
        if keyword.lower() in user_message.lower():
            return True

    # (Optional) Use GPT-4 to classify relevance
    messages = [
        {"role": "system", "content": "You are a classifier. Respond 'yes' if the question is related to a medical database (e.g., about doctors, treatments, drugs, or surgeries). Respond 'no' otherwise."},
        {"role": "user", "content": user_message}
    ]

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=messages,
            max_tokens=5  # Keep it concise
        )
        classification = response.choices[0].message['content'].strip().lower()
        return classification == "yes"
    except Exception as e:
        print(f"Error in GPT-4 classification: {e}")
        return False

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message")
    voice = request.json.get("voice", False)  # Voice flag to decide response type
    role = session.get("role", "individual")
    # Step 1: Determine if the query is database-related
    if is_database_related(user_message):
        db_answers = search_medical_data(user_message)
        if db_answers:
            formatted_response = "<div style='font-family: Arial, sans-serif;'>"
            formatted_response += "<strong>Here is what I found from the database:</strong><br>"
            for table_data in db_answers:
                for table_name, rows in table_data.items():
                    formatted_response += f"<h4 style='color: #0056b3;'>{table_name.replace('_', ' ').title()}</h4>"
                    formatted_response += "<ul>"
                    for row in rows:
                        formatted_response += "<li>" + " | ".join([f"<strong>{col}:</strong> {val}" for col, val in zip(row.keys(), row)]) + "</li>"
                    formatted_response += "</ul>"
            formatted_response += "</div>"
            return jsonify({"response": f"(Database): {formatted_response.strip()}", "voice": voice})

    # Step 2: Use GPT-4 for general questions
    messages = [
        {"role": "system", "content": "You are a knowledgeable assistant providing concise, accurate, and professional answers tailored for doctors."},
        {"role": "user", "content": f"Doctor's Query: {user_message}. Please provide a detailed and accurate response."}
    ]

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=messages,
            max_tokens=500  # Allow more detailed responses
        )
        answer = response.choices[0].message['content'].strip()
        structured_answer = format_gpt_response(answer)
        return jsonify({"response": f"(AI): {structured_answer}", "voice": voice})
    except Exception as e:
        return jsonify({"response": f"Error: Unable to process your request. {str(e)}", "voice": voice})


def format_gpt_response(answer):
    """
    Format GPT-4 responses for better readability using HTML.
    """
    formatted = "<div style='font-family: Arial, sans-serif;'>"
    for line in answer.split("\n"):
        if line.strip():
            formatted += f"<p style='margin: 5px 0;'>{line.strip()}</p>"
    formatted += "</div>"
    return formatted
def add_user(username, password, role):
    hashed_password = generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)
    query = "INSERT INTO USERS (username, password_hash, role) VALUES (%s, %s, %s)"
    query_snowflake(query, (username, hashed_password, role))

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)
