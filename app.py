import configparser
from flask import Flask, render_template, request, jsonify, redirect, url_for
import openai
import sqlite3
import snowflake.connector

# Initialize config parser
config = configparser.ConfigParser()
config.read('config.ini')

app = Flask(__name__)

# Fetch sensitive data from config
api_key = config['DEFAULT']['api_key']
admin_user = config['DEFAULT']['admin_user']
admin_password = config['DEFAULT']['admin_password']

# Set OpenAI API key
openai.api_key = api_key

# User credentials
users = {admin_user: admin_password}
def query_snowflake(query):
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
    cursor.execute(query)
    results = cursor.fetchall()
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



@app.route("/")
def login():
    return render_template("login.html")

@app.route("/validate", methods=["POST"])
def validate():
    username = request.form.get("username")
    password = request.form.get("password")
    if username in users and users[username] == password:
        return redirect(url_for("chat_screen"))
    else:
        return render_template("login.html", error="Invalid Credentials")

@app.route("/chat_screen")
def chat_screen():
    return render_template("index.html")


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

    # Step 1: Determine if the query is database-related
    if is_database_related(user_message):
        db_answers = search_medical_data(user_message)
        if db_answers:
            formatted_response = "Here is what I found from the database:\n"
            for table_data in db_answers:
                for table_name, rows in table_data.items():
                    formatted_response += f"\n**{table_name}**:\n"
                    for row in rows:
                        formatted_response += " | ".join(map(str, row)) + "\n"
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
        return jsonify({"response": f"(AI): {answer}", "voice": voice})
    except Exception as e:
        return jsonify({"response": f"Error: Unable to process your request. {str(e)}", "voice": voice})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)
