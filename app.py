import configparser
from flask import Flask, render_template, request, jsonify, redirect, url_for
import openai
import sqlite3


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

def search_medical_data(query):
    conn = sqlite3.connect("medical_data.db")
    cursor = conn.cursor()
    cursor.execute("SELECT answer FROM medical_info WHERE question LIKE ?", (f"%{query}%",))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

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

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message")
    voice = request.json.get("voice", False)  # Voice flag to decide response type
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": user_message}
    ]
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",  # Specify model version
            messages=messages,
            max_tokens=150
        )
        answer = response.choices[0].message['content'].strip()
        return jsonify({"response": answer, "voice": voice})
    except Exception as e:
        return jsonify({"response": f"Error: {str(e)}", "voice": voice})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)
