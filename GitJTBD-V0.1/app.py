from flask import Flask, render_template, request, session
from dotenv import load_dotenv
import os
import openai
import threading
import time
from datetime import datetime



# Load environment variables from .env file
load_dotenv()

# Global variables
maxQuestions = 20  # Set to 5 for testing; change to 30 later

# Access the OpenAI API Key
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Global variables
questions_counter = 0
conversation = []
timer = 0  # Active timer during the interview
duration = 0  # Total duration of the interview
timer_active = False # Controls whether the timer is running

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

# Background Timer Function
def background_timer():
    global timer, timer_active
    while True:
        if timer_active:
            time.sleep(60)  # Increment every minute
            if not timer_active:  # Check if the timer was deactivated during the wait
                break
            timer += 1
            print(f"Timer Active: {timer_active}, Timer: {timer} minutes")

# Initialize Flask App
app = Flask(__name__)

# Start Background Timer Loop
threading.Thread(target=background_timer, daemon=True).start()

# Home route
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

# Options selection route
@app.route('/mode')
def options():
    return render_template('options.html')

# Interview route
@app.route('/interview', methods=['GET', 'POST'])
def interview():
    global questions_counter, conversation, timer, duration, timer_active

    # Get mode and business domain
    mode = request.args.get('mode') or request.form.get('mode', 'Full Interview Mode')
    business_domain = request.args.get('business_domain') or request.form.get('business_domain', 'Airline Operations')
    resume = request.args.get('resume', 'false').lower() == 'true'

    # Load persona details based on business domain
    persona = personas.get(business_domain, {})

    def increment_timer():
        global timer
        while True:
            time.sleep(60)  # Increment every minute
            timer += 1
            print(f"Timer: {timer} minutes")  # Debugging log

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
            timer = 0  # Reset timer for new session
            duration = 0  # Reset duration for new session

        timer_active = True  # Start the timer

        # Render the interview screen for GET requests
        return render_template(
            'interview.html',
            conversation=conversation,
            counter=questions_counter,
            mode=mode,
            maxQuestions=maxQuestions,
            persona=persona,
            timer = timer
        )

    elif request.method == 'POST':
        user_input = request.form['user_input']
        business_domain = request.args.get('business_domain') or request.form.get('business_domain',
                                                                                  'Airline Operations')
        persona = personas.get(business_domain, {})  # Reload persona details
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
            persona=persona,
            timer=timer
        )

# Evaluation route
@app.route('/evaluation', methods=['GET'])
def evaluation():
    global questions_counter, conversation, timer, duration, timer_active

    mode = request.args.get('mode', 'Full Interview Mode')
    duration_to_display = timer if mode == 'Guided Interview Mode' else duration

    print(f"Time passed to evaluation: {duration_to_display} minutes")  # Debugging log

    return render_template(
        'evaluation.html',
        mode=mode,
        conversation=conversation,
        counter=questions_counter,
        duration=duration_to_display  # Pass appropriate value
    )


@app.route('/stop_timer', methods=['POST'])
def stop_timer():
    global timer, duration, timer_active

    # Capture the final duration
    duration = timer
    print(f"Final duration: {duration} minutes")

    # Reset the timer
    timer = 0

    timer_active = False  # Stop the timer
    print(f"Final duration: {duration} minutes")
    print(f"Timer Active: {timer_active}, Timer: {timer} minutes")
    print("Timer reset and thread cleared.")
    return '', 204  # No content response


if __name__ == '__main__':
    app.run(debug=True)
