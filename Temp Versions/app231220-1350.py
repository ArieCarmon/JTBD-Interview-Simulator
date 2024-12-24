from flask import Flask, render_template, request, session
from dotenv import load_dotenv
import os
import openai
import threading
import time
from datetime import datetime
import pandas as pd
import numpy as np
import json



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
    },

    "Hospitality Services": {
        "name": "James Chen",
        "position": 'Operations Director',
        "company": 'Urban Hotels Group',
        "introduction": 'Oversees operations for a boutique hotel chain with 12 properties across major cities.',
        "style": 'customer-focused and detail-oriented',
        "focus": ['guest experience', 'operational efficiency', 'staff management'],
    },

    "Healthcare Services": {
        "name": 'Dr. Emily Thompson',
        "position": 'Medical Director',
        "company": 'HealthFirst Network',
        "introduction": 'Leads a network of primary care clinics serving over 50,000 patients annually.',
        "style": 'professional and empathetic',
        "focus": ['patient care', 'healthcare innovation', 'clinical efficiency'],
    },

    "Retail & E-commerce": {
        "name": 'Michael Roberts',
        "position": 'VP of Digital',
        "company": 'RetailNext',
        "introduction": 'Directs omnichannel strategy for a mid-size retail chain with 200+ stores and growing e-commerce presence.',
        "style": 'innovative and customer-centric',
        "focus": ['digital transformation', 'customer experience', 'market expansion'],
    },

    "Financial Services": {
        "name": 'Lisa Wong',
        "position": 'Head of Innovation',
        "company": 'FinServ Solutions',
        "introduction": 'Leads digital transformation for a regional financial services provider serving small to medium businesses.',
        "style": 'analytical and strategic',
        "focus": ['digital banking', 'business solutions', 'risk management'],
    },

    "Software & Technology": {
        "name": 'Alex Kumar',
        "position": 'Product Director',
        "company": 'CloudTech Systems',
        "introduction": 'Manages enterprise software solutions used by over 1000 companies globally.',
        "style": 'technical and solution-oriented',
        "focus": ['product development', 'enterprise solutions', 'technical innovation'],
    },

      "Manufacturing": {
        "name": 'Robert Schmidt',
        "position": 'Operations Manager',
        "company": 'PrecisionMake Industries',
        "introduction": 'Oversees smart manufacturing facilities producing precision components for various industries.',
        "style": 'methodical and quality-focused',
        "focus": ['production efficiency', 'quality control', 'process automation'],
    },

    "Logistics & Supply Chain": {
        "name": 'Maria Garcia',
        "position": 'Supply Chain Director',
        "company": 'GlobalMove Logistics',
        "introduction": 'Manages end-to-end supply chain operations across 15 countries with 1000+ vehicles.',
        "style": 'organized and efficiency-driven',
        "focus": ['supply chain optimization', 'fleet management', 'international operations'],
    },

    "Telecommunications": {
        "name": 'John Parker',
        "position": 'Strategy Director',
        "company": 'CommTech Solutions',
        "introduction": 'Leads strategic initiatives for a telecommunications provider serving 2 million customers.',
        "style": 'strategic and technology-focused',
        "focus": ['network expansion', 'service innovation', 'customer retention'],
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

# Global DataFrame for storing scores
evaluation_df = pd.DataFrame(columns=[
    "Index", "Timestamp", "Q&A#",
    "R - Question Technique Relevance", "E - Question Technique Effectiveness", "Question Technique CalcScore", "Question Technique AvgScore", "Question Technique TolScore",
    "JTBD Framework Relevance", "JTBD Framework Effectiveness", "JTBD Framework CalcScore", "JTBD Framework AvgScore", "JTBD Framework TolScore",
    "Progress Forces Relevance", "Progress Forces Effectiveness", "Progress Forces CalcScore", "Progress Forces AvgScore", "Progress Forces TolScore",
    "Interview Mgmt Relevance", "Interview Mgmt Effectiveness", "Interview Mgmt CalcScore", "Interview Mgmt AvgScore", "Interview Mgmt TolScore",
    "Market Opportunity Relevance", "Market Opportunity Effectiveness", "Market Opportunity CalcScore", "Market Opportunity AvgScore", "Market Opportunity TolScore",
    "Innovation Relevance", "Innovation Effectiveness", "Innovation CalcScore", "Innovation AvgScore", "Innovation TolScore",
    "Customer Segment Relevance", "Customer Segment Effectiveness", "Customer Segment CalcScore", "Customer Segment AvgScore", "Customer Segment TolScore",
    "Strategic Relevance", "Strategic Effectiveness", "Strategic CalcScore", "Strategic AvgScore", "Strategic TolScore",
    "Business Insight Score", "Interview Skills Score", "Total Score"
])

max_scores = {
    "Question Technique": 15,
    "JTBD Framework": 15,
    "Progress Forces": 10,
    "Interview Mgmt": 10,
    "Market Opportunity": 15,
    "Innovation": 15,
    "Customer Segment": 10,
    "Strategic": 10
}

# Define subcategories and their max scores
subcategories = {
    "Question Technique": {"MaxScore": 15},
    "JTBD Framework": {"MaxScore": 15},
    "Progress Forces": {"MaxScore": 10},
    "Interview Mgmt": {"MaxScore": 10},
    "Market Opportunity": {"MaxScore": 15},
    "Innovation": {"MaxScore": 15},
    "Customer Segment": {"MaxScore": 10},
    "Strategic": {"MaxScore": 10}
}


# Reset the DataFrame for each new interview
def reset_scores():
    global evaluation_df
    evaluation_df = pd.DataFrame(columns=evaluation_df.columns)
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
    global questions_counter, conversation, evaluation_df, timer, duration, timer_active

    # Get mode and business domain
    mode = request.args.get('mode') or request.form.get('mode', 'Full Interview Mode')
    business_domain = request.args.get('business_domain') or request.form.get('business_domain', 'Airline Operations')
    resume = request.args.get('resume', 'false').lower() == 'true'

    # Load persona details based on business domain
    persona = personas.get(business_domain, {})

    # Initialize the evaluation DataFrame if it doesn't exist
    if evaluation_df is None or len(evaluation_df) == 0:
        evaluation_df = pd.DataFrame(columns=[
            "Index", "Timestamp", "Q&A #",
            *[f"R - {sub}" for sub in subcategories.keys()],
            *[f"E - {sub}" for sub in subcategories.keys()],
            *[f"{sub} CalcScore" for sub in subcategories.keys()],
            *[f"{sub} AvgScore" for sub in subcategories.keys()],
            *[f"{sub} TotalScore" for sub in subcategories.keys()],
            "Interview Skills Score", "Business Insight Score", "Total Score",
            "Key Findings", "Interview Strengths", "Areas for Improvement", "Recommended Follow-Up Questions"
        ])

    if request.method == 'GET':
        if resume and mode == 'Guided Interview Mode':
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
            timer = 0  # Reset timer
            duration = 0  # Reset duration

        timer_active = True

        # Render the interview screen
        return render_template(
            'interview.html',
            conversation=conversation,
            counter=questions_counter,
            mode=mode,
            maxQuestions=maxQuestions,
            persona=persona,
            timer=timer
        )

    elif request.method == 'POST':
        user_input = request.form['user_input']
        conversation.append({"role": "user", "content": user_input})

        # Step 1: Generate Persona's Answer
        persona_prompt = (
            f"You are {persona['name']}, {persona['position']} at {persona['company']}. "
            f"{persona['introduction']} Your style is: {persona['style']} Your focus is: {persona['focus']}.\n\n"
            f"User's Question: {user_input}\n\n"
            "Respond in your persona's voice, and include non-verbal behavioral signs (e.g., [smiling], [nodding])."
        )
        try:
            persona_response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": persona_prompt}]
            )
            persona_answer = persona_response['choices'][0]['message']['content']
        except Exception as e:
            print(f"Error generating persona response: {e}")
            persona_answer = "Error generating response. Please try again."

        # Append Persona's Answer
        conversation.append({"role": "assistant", "content": persona_answer})
        print("Persona's Answer:", persona_answer)

        questions_counter += 1

        # Step 2: Generate Feedback for the Q&A Pair
        prompt = (
            "You are a JTBD (Jobs-To-Be-Done) expert evaluator trained in the methodologies of Christensen, Moesta, and Klement. "
            "Your evaluation is based on the following principles:\n"
            "• Christensen: Customers 'hire' products/services to fulfill specific jobs in their lives.\n"
            "• Moesta: Focus on progress-making forces—push, pull, anxieties, and habits.\n"
            "• Klement: Understand demand generation as customers' struggles for progress.\n"
            "\n"
            "Your task is to analyze Q&A pairs in an interview and provide structured feedback.\n"
            "Evaluation Outputs:\n"
            "1. Numerical Feedback:\n"
            "   o Relevance (0–1): How relevant the Q&A is to the following sub-categories.\n"
            "   o Effectiveness (0–5): How well the Q&A supports each relevant sub-category.\n"
            "   o Sub-Categories:\n"
            "     • Interview Skills:\n"
            "       1. Question Technique & Structure (clarity, follow-ups, open-ended).\n"
            "       2. JTBD Framework Application (job discovery, context, timeline).\n"
            "       3. Progress Forces Exploration (push, pull, anxiety, habits).\n"
            "       4. Interview Management (flow, rapport, time).\n"
            "     • Business Insights:\n"
            "       1. Market Opportunity (needs, gaps, competition).\n"
            "       2. Product/Service Innovation (solutions, value propositions).\n"
            "       3. Customer Segment (characteristics, behavior).\n"
            "       4. Strategic Recommendations (actions, implications, priorities).\n"
            "\n"
            "2. Verbal Feedback:\n"
            "   o For all completed Q&A pairs, summarize in four sections (no more than 5 points per section):\n"
            "     • Key Findings\n"
            "     • Interview Strengths\n"
            "     • Areas for Improvement\n"
            "     • Recommended Follow-up Questions\n"
            "\n"
            "Expected Output Format (strict JSON):\n"
            "{\n"
            "  \"numerical_feedback\": {\n"
            "    \"Interview Skills\": {\n"
            "      \"Question Technique & Structure\": {\"relevance\": 0.9, \"effectiveness\": 4.5},\n"
            "      \"JTBD Framework Application\": {\"relevance\": 0.8, \"effectiveness\": 4.0},\n"
            "      ...\n"
            "    },\n"
            "    \"Business Insights\": {\n"
            "      \"Market Opportunity\": {\"relevance\": 0.7, \"effectiveness\": 4.0},\n"
            "      \"Product/Service Innovation\": {\"relevance\": 0.9, \"effectiveness\": 4.5},\n"
            "      ...\n"
            "    }\n"
            "  },\n"
            "  \"verbal_feedback\": {\n"
            "    \"Key Findings\": [\"Point 1\", \"Point 2\"],\n"
            "    \"Interview Strengths\": [\"Strength 1\", \"Strength 2\"],\n"
            "    \"Areas for Improvement\": [\"Improvement 1\", \"Improvement 2\"],\n"
            "    \"Recommended Follow-Up Questions\": [\"Question 1\", \"Question 2\"]\n"
            "  }\n"
            "}\n"
            "\n"
            "Focus on clarity, conciseness, and actionable insights."
            f"\n\nQ&A Pair:\nUser's Question: {user_input}\nPersona's Answer: {persona_answer}"
        )

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}]
            )
            raw_response = response['choices'][0]['message']['content']
            print("Raw API Response:", raw_response)  # Debugging

            # Split Numerical and Verbal Feedback
            numerical_feedback_section = raw_response.split("Verbal Feedback:")[0].strip()
            verbal_feedback_section = raw_response.split("Verbal Feedback:")[1].strip()

            print("Numerical Feedback Section:", numerical_feedback_section)
            print("Verbal Feedback Section:", verbal_feedback_section)

            # Parse Numerical Feedback
            numerical_feedback = json.loads(numerical_feedback_section)

            raw_scores = {}
            for sub, scores in numerical_feedback.items():
                print(f"Parsing sub-category: {sub}, scores: {scores}")
                raw_scores[f"R - {sub}"] = scores.get("relevance", 0)  # Default relevance to 0 if missing
                raw_scores[f"E - {sub}"] = scores.get("effectiveness", 0)  # Default effectiveness to 0 if missing

            # Parse Verbal Feedback
            verbal_feedback = json.loads(verbal_feedback_section)
            print("Parsed Verbal Feedback:", verbal_feedback)

            key_findings = "; ".join(verbal_feedback.get("Key Findings", []))
            strengths = "; ".join(verbal_feedback.get("Interview Strengths", []))
            improvements = "; ".join(verbal_feedback.get("Areas for Improvement", []))
            follow_up_questions = "; ".join(verbal_feedback.get("Recommended Follow-Up Questions", []))

            # Append to Evaluation DataFrame
            new_row = {
                "Index": questions_counter,
                "Timestamp": pd.Timestamp.now(),
                "Q&A #": questions_counter + 1,
                **raw_scores,
                "Key Findings": key_findings,
                "Interview Strengths": strengths,
                "Areas for Improvement": improvements,
                "Recommended Follow-Up Questions": follow_up_questions
            }
            evaluation_df = pd.concat([evaluation_df, pd.DataFrame([new_row])], ignore_index=True)

            # Calculate Derived Scores
            for sub in subcategories.keys():
                relevance_col = f"R - {sub}"
                effectiveness_col = f"E - {sub}"
                calc_col = f"{sub} CalcScore"
                avg_col = f"{sub} AvgScore"
                total_col = f"{sub} TotalScore"

                evaluation_df[calc_col] = evaluation_df[relevance_col] * evaluation_df[effectiveness_col]
                evaluation_df[avg_col] = evaluation_df[calc_col].expanding().mean()
                evaluation_df[total_col] = (evaluation_df[avg_col] / 5 * subcategories[sub]["MaxScore"]).round(0)

            evaluation_df["Interview Skills Score"] = evaluation_df[
                [f"{sub} TotalScore" for sub in
                 ["Question Technique", "JTBD Framework", "Progress Forces", "Interview Mgmt"]]
            ].sum(axis=1)

            evaluation_df["Business Insight Score"] = evaluation_df[
                [f"{sub} TotalScore" for sub in ["Market Opportunity", "Innovation", "Customer Segment", "Strategic"]]
            ].sum(axis=1)

            evaluation_df["Total Score"] = evaluation_df["Interview Skills Score"] + evaluation_df["Business Insight Score"]

            # Save to Excel AFTER calculations
            print("Saving evaluation DataFrame to Excel...")
            evaluation_df.to_excel("evaluation_debug.xlsx", index=False)
            print("File saved.")

        except Exception as e:
            print(f"Error processing feedback: {e}")

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
