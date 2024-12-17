from flask import Flask, render_template, request
from dotenv import load_dotenv
import os

app = Flask(__name__)

# Load environment variables from .env file
load_dotenv()

# Global variables
maxQuestions = 20  # Set to 5 for testing; change to 30 later

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
# Define personas for each business domain
personas = {
    "Airline Operations": {
        "name": "David Cohen",
        "position": "CEO",
        "company": "SkyRegional Airlines",
        "introduction": "Leads a regional airline with 5 aircraft serving destinations within a 3-4 hour flight radius from Tel Aviv.",
        "style": "Direct and pragmatic, typical Israeli approach.",
        "focus": "Cost management, customer service, route optimization."
    }
}

@app.route('/interview', methods=['GET', 'POST'])
def interview():
    global questions_counter, conversation

    # Get mode and business domain
    mode = request.args.get('mode') or request.form.get('mode', 'Full Interview Mode')
    business_domain = request.args.get('business_domain') or request.form.get('business_domain', 'Airline Operations')

    # Load persona details based on business domain
    persona = personas.get(business_domain, {})

    if request.method == 'GET':
        # Set opening message dynamically
        opening_message = (
            f"Hello, I'm {persona['name']}, {persona['position']} at {persona['company']}. "
            f"{persona['introduction']} I have about an hour to 90 minutes for this conversation. "
            "I am ready to answer your questions."
        )
        conversation = [{"role": "assistant", "content": opening_message}]
        questions_counter = 0

    elif request.method == 'POST':
        user_input = request.form['user_input']
        conversation.append({"role": "user", "content": user_input})

        llm_response = f"Simulated response to: {user_input}"
        conversation.append({"role": "assistant", "content": llm_response})

        questions_counter += 1

    return render_template('interview.html',
                           conversation=conversation,
                           counter=questions_counter,
                           mode=mode,
                           maxQuestions=maxQuestions,
                           persona=persona)


if __name__ == '__main__':
    app.run(debug=True)
