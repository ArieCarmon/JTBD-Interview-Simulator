from flask import Flask, render_template, request, session
from dotenv import load_dotenv
import os
import openai
import threading
import time

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
interview_timer = 0

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
    },

    "Education Technology": {
        "name": "Sarah Martinez",
        "position": "Chief Innovation Officer",
        "company": "EduTech Solutions",
        "introduction": "Manages digital transformation for a growing EdTech company serving over 200+ institutions with learning technology solutions.",
        "style": "Collaborative and forward-thinking.",
        "focus": "Digital learning, institutional partnerships, student engagement."
    }
}

@app.route('/interview', methods=['GET', 'POST'])
def interview():
    global questions_counter, conversation, interview_timer

    # Get mode and business domain
    mode = request.args.get('mode') or request.form.get('mode', 'Full Interview Mode')
    business_domain = request.args.get('business_domain') or request.form.get('business_domain', 'Airline Operations')
    resume = request.args.get('resume', 'false').lower() == 'true'

    # Load persona details based on business domain
    persona = personas.get(business_domain, {})

    if request.method == 'GET':
        if resume and mode == 'Guided Interview Mode':
            # Resume the current session
            print("Resuming Guided Interview session...")
        else:
            # Start a new session
            opening_message = (
                f"Hello, I'm {persona['name']}, {persona['position']} at {persona['company']}. "
                f"{persona['introduction']} I have about an hour to 90 minutes for this conversation. "
                "I am ready to answer your questions."
            )
            conversation = [{"role": "assistant", "content": opening_message}]
            questions_counter = 0
            interview_timer = 0  # Initialize timer for new session

        # Render the interview screen for GET requests
        return render_template(
            'interview.html',
            conversation=conversation,
            counter=questions_counter,
            mode=mode,
            maxQuestions=maxQuestions,
            persona=persona
        )

    elif request.method == 'POST':
        user_input = request.form['user_input']
        timer_value = int(request.form.get('timer', 0))  # Retrieve timer from the form
        interview_timer = timer_value  # Update global timer

        conversation.append({"role": "user", "content": user_input})

        # Prepare the GPT-4 prompt
        prompt = (
            f"You are {persona['name']}, {persona['position']} at {persona['company']}. "
            f"{persona['introduction']} Your style is: {persona['style']} Your focus is: {persona['focus']}.\n\n"
            f"User's Question: {user_input}\n\n"
            "Respond in your persona's voice, and include non-verbal behavioral signs (e.g., [smiling], [nodding]) where appropriate."
        )

        try:
            # Call the GPT-4 API
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": prompt}
                ]
            )
            llm_response = response['choices'][0]['message']['content']
        except Exception as e:
            print(f"Error connecting to OpenAI API: {e}")
            llm_response = "There was an error connecting to the LLM. Please try again."

        # Append the assistant's response to the conversation
        conversation.append({"role": "assistant", "content": llm_response})

        questions_counter += 1

        # Render the updated interview screen
        return render_template(
            'interview.html',
            conversation=conversation,
            counter=questions_counter,
            mode=mode,
            maxQuestions=maxQuestions,
            persona=persona
        )

@app.route('/evaluation', methods=['GET'])
def evaluation():
    global questions_counter, conversation, interview_timer

    # Get the mode
    mode = request.args.get('mode', 'Full Interview Mode')

    # Pass counters and data to the template
    return render_template(
        'evaluation.html',
        mode=mode,
        conversation=conversation,
        counter=questions_counter,
        duration=interview_timer  # Pass the timer value to the template
    )


if __name__ == '__main__':
    app.run(debug=True)
