from flask import Flask, render_template, request
from dotenv import load_dotenv
import os

app = Flask(__name__)

# Load environment variables from .env file
load_dotenv()

# Access the OpenAI API Key
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

## Home route
@app.route('/')
def home():
    # Retrieve the API key
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

    # Log the partial API key to the console for testing
    if OPENAI_API_KEY:
        print(f"Your API key is: {OPENAI_API_KEY[:4]}... (hidden)")
    else:
        print("API key not found.")

    # Render your existing welcome.html page
    return render_template('welcome.html')

## Options selection route
@app.route('/mode')
def options():
    return render_template('options.html')

# Global variables
questions_counter = 0
conversation = []

## Interview route
@app.route('/interview', methods=['GET', 'POST'])
def interview():
    global questions_counter, conversation

    # Get mode from query parameters (GET) or form data (POST)
    mode = request.args.get('mode') or request.form.get('mode', 'Full Interview Mode')

    if request.method == 'GET':
        # Initialize for a new session
        conversation = [{"role": "assistant", "content": "Welcome to the JTBD Interview Simulator!"}]
        questions_counter = 0

    elif request.method == 'POST':
        user_input = request.form['user_input']  # Get user input
        conversation.append({"role": "user", "content": user_input})

        # Simulate assistant response
        llm_response = f"Simulated response to: {user_input}"
        conversation.append({"role": "assistant", "content": llm_response})

        questions_counter += 1  # Increment questions counter

    # Render the interview template with mode and conversation data
    return render_template('interview.html', conversation=conversation, counter=questions_counter, mode=mode)



if __name__ == '__main__':
    app.run(debug=True)
