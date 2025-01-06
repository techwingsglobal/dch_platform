import openai

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

def chatbot(messages):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # You can use "gpt-4" if you have access
            messages=messages,
            max_tokens=150,  # Adjust token limit as per your needs
            temperature=0.7,  # Adjust temperature to control randomness of responses
            n=1  # Number of responses to generate
        )

        return response.choices[0].message['content'].strip()

    except Exception as e:
        return f"Error: {str(e)}"


def main():
    print("Chatbot is ready! Type 'exit' to quit.")
    messages = [{"role": "system", "content": "You are a helpful assistant."}]  # Initial system prompt

    while True:
        user_input = input("You: ")
        if user_input.lower() == 'exit':
            print("Exiting chatbot. Goodbye!")
            break

        # Append user's input to the conversation history
        messages.append({"role": "user", "content": user_input})

        # Get bot's response
        response = chatbot(messages)

        # Append the bot's response to the conversation history
        messages.append({"role": "assistant", "content": response})

        print(f"Bot: {response}")


if __name__ == "__main__":
    main()