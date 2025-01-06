import openai
import mysql.connector
from mysql.connector import Error

import configparser
from flask import Flask, render_template, request, jsonify
import openai
# Initialize config parser
config = configparser.ConfigParser()
config.read('config.ini')

app = Flask(__name__)

#FETCH SENSITIVE DATA FROM COFIG
api_key = config['DEFAULT']['api_key']
admin_user = config['DEFAULT']['admin_user']
admin_password = config['DEFAULT']['admin_password']

# Set your OpenAI API key
openai.api_key = api_key
# Database connection (replace with your database credentials)
def connect_to_db():
    try:
        return mysql.connector.connect(
            host="your-database-host",
            user="your-database-username",
            password="your-database-password",
            database="your-database-name"
        )
    except Error as e:
        print(f"Error connecting to database: {e}")
        return None


# Search the database for a relevant answer
def search_db_for_answer(question):
    db_connection = connect_to_db()
    if db_connection is None:
        return None  # Skip if DB connection failed

    try:
        cursor = db_connection.cursor()
        query = "SELECT answer FROM faqs WHERE question LIKE %s LIMIT 1"
        cursor.execute(query, ("%" + question + "%",))
        result = cursor.fetchone()
        cursor.close()
        db_connection.close()

        if result:
            return result[0]
        else:
            return None
    except Error as e:
        print(f"Database error: {e}")
        return None


# Fetch data from an external API if no database result is found
def fetch_generic_answer_from_internet(question):
    try:
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": question}
        ]
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Use "gpt-4" if available
            messages=messages,
            max_tokens=150,
            temperature=0.7,
            n=1
        )
        return response.choices[0].message['content'].strip()
    except Exception as e:
        return f"Error fetching response: {str(e)}"


# Main chatbot function that integrates DB and OpenAI
def chatbot(question):
    # Attempt to retrieve an answer from the database
    db_answer = search_db_for_answer(question)

    # Fetch a generic response from the internet
    internet_answer = fetch_generic_answer_from_internet(question)

    # If there's a database answer, combine both
    if db_answer:
        return f"Database Answer: {db_answer}\n\nAdditional Info: {internet_answer}"
    else:
        return f"Generic Answer: {internet_answer}"
