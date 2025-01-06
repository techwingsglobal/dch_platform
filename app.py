# app.py
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



@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message")
    voice = request.json.get("voice", False)  # Voice flag to decide response type
    messages = [{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": user_message}]
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",  # Change to gpt-4 or whichever is available to you
            messages=messages,
            max_tokens=150
        )
        answer = response.choices[0].message['content'].strip()
        return jsonify({"response": answer, "voice": voice})
    except Exception as e:
        return jsonify({"response": f"Error: {str(e)}", "voice": voice})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8000)

