import openai
import speech_recognition as sr
import pyttsx3
import mysql.connector
from mysql.connector import Error
from gtts import gTTS
import os

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
# Initialize Text-to-Speech engine
engine = pyttsx3.init()

# Initialize Speech Recognizer
recognizer = sr.Recognizer()


# Database connection (use your credentials here)
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
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=150,
            temperature=0.7,
            n=1
        )
        return response.choices[0].message['content'].strip()
    except Exception as e:
        return f"Error fetching response: {str(e)}"


# Function to use voice recognition to get input
def listen_to_voice():
    with sr.Microphone() as source:
        print("Listening...")
        audio = recognizer.listen(source)

    try:
        text = recognizer.recognize_google(audio)
        print(f"You said: {text}")
        return text
    except sr.UnknownValueError:
        return "Sorry, I didn't catch that."
    except sr.RequestError as e:
        return f"Could not request results; {e}"


# Function to speak out text
def speak_text(text):
    tts = gTTS(text=text, lang='en')
    tts.save("response.mp3")
    os.system("start response.mp3")


# Main chatbot function
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


def main():
    print("Chatbot is ready! Type 'exit' to quit.")
    while True:
        # Ask if the user wants to input via text or voice
        input_type = input("Do you want to use voice or text? (v/t): ").strip().lower()

        if input_type == 'v':
            user_input = listen_to_voice()
        else:
            user_input = input("You: ")

        if user_input.lower() == 'exit':
            print("Exiting chatbot. Goodbye!")
            break

        # Get the response from the chatbot (either DB or Internet)
        response = chatbot(user_input)

        # Print the bot response
        print(f"Bot: {response}")

        # Ask if the user wants the response in voice as well
        output_voice = input("Do you want the response in voice? (y/n): ").strip().lower()
        if output_voice == 'y':
            speak_text(response)


if __name__ == "__main__":
    main()
