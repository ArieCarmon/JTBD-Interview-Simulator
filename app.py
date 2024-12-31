from flask import Flask, render_template, request, session, render_template_string
from dotenv import load_dotenv
import openai
import threading
import time
import pandas as pd
import json
from copy import deepcopy
from flask import make_response
from flask import url_for, send_file
import os
import pdfkit



# Load environment variables from .env file
load_dotenv()

# Global variables
maxQuestions = 30  # Set to 5 for testing; change to 30 later

# Access the OpenAI API Key
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Global variables
questions_counter = 0
conversation = []
timer = 0  # Active timer during the interview
duration = 0  # Total duration of the interview
timer_active = False # Controls whether the timer is running
business_domain = None  # Will be set when domain is selected
print("Initial global business_domain:", business_domain)


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
            #session['timer'] = timer  # Persist timer in session
            print(f"Timer Active: {timer_active}, Timer: {timer} minutes")

subcategories = deepcopy({
    "Question Technique": {"MaxScore": 15},
    "JTBD Framework": {"MaxScore": 15},
    "Progress Forces": {"MaxScore": 10},
    "Interview Mgmt": {"MaxScore": 10},
    "Market Opportunity": {"MaxScore": 15},
    "Innovation": {"MaxScore": 15},
    "Customer Segment": {"MaxScore": 10},
    "Strategic": {"MaxScore": 10}
})

# Global DataFrame for storing scores
evaluation_df = pd.DataFrame(columns=[
    "Timestamp", "Q&A #",
    *[f"R - {sub}" for sub in subcategories.keys()],
    *[f"E - {sub}" for sub in subcategories.keys()],
    *[f"{sub} CalcScore" for sub in subcategories.keys()],
    *[f"{sub} AvgScore" for sub in subcategories.keys()],
    *[f"{sub} TotalScore" for sub in subcategories.keys()],
    "Interview Skills Score", "Business Insight Score", "Total Score",
    "Key Findings", "Interview Strengths", "Areas for Improvement", "Recommended Follow-Up Questions"
])

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

@app.route('/start_timer', methods=['POST'])
def start_timer():
    global timer, timer_active
    timer = 0  # Reset the timer for the new session
    timer_active = True  # Restart the timer thread
    print("Timer restarted for new session.")
    return '', 204

# Options selection route
@app.route('/mode')
def options():
    return render_template('options.html')

# Interview route
@app.route('/interview', methods=['GET', 'POST'])
def interview():
    global questions_counter, conversation, evaluation_df, timer, duration, timer_active, subcategories, business_domain
    print("Interview route - Start - business_domain:", business_domain)

    # Get mode and business domain
    mode = request.args.get('mode') or request.form.get('mode', 'Full Interview Mode')
    resume = request.args.get('resume', 'false').lower() == 'true'

    if not resume:
        # Only update business_domain if not resuming
        business_domain = request.args.get('business_domain') or request.form.get('business_domain',
                                                                                  'Airline Operations')
    print("After setting - Global business_domain:", business_domain)

    #resume = request.args.get('resume', 'false').lower() == 'true'

    # Load persona details based on business domain
    persona = personas.get(business_domain, {})



    if request.method == 'GET':
        if not resume:
            timer = 0  # Reset timer
            if mode == 'Guided Interview Mode':  # Specific to Guided Mode
                print("Starting a new session. Timer reset to 0.")
            timer_active = True
            questions_counter = 0
            conversation = []
            evaluation_df = pd.DataFrame(columns=[
                "Timestamp", "Q&A #",
                *[f"R - {sub}" for sub in subcategories.keys()],
                *[f"E - {sub}" for sub in subcategories.keys()],
                *[f"{sub} CalcScore" for sub in subcategories.keys()],
                *[f"{sub} AvgScore" for sub in subcategories.keys()],
                *[f"{sub} TotalScore" for sub in subcategories.keys()],
                "Interview Skills Score", "Business Insight Score", "Total Score",
                "Key Findings", "Interview Strengths", "Areas for Improvement", "Recommended Follow-Up Questions"
            ])
            print("Evaluation DataFrame reset for new interview.")
        else:  # Resuming session
            timer_active = True
            print(f"Resuming session with timer at {timer} minutes.")

        if resume and mode == 'Guided Interview Mode':
        #if resume and mode == 'Guided Interview Mode':
            print("Resuming Guided Interview session...")
        else:
            # Start a new session
            opening_message = (
                f"Hello, I'm {persona['name']}, {persona['position']} at {persona['company']}. "
                f"{persona['introduction']} I have about an hour to 90 minutes for this conversation. "
                "I am ready to answer your questions."
            )

            #timer = session.get('timer', 0)  # Fetch timer from session (default to 0 if not set)
            conversation = [{"role": "assistant", "content": opening_message}]
            questions_counter = 0
            timer = 0  # Reset timer
            duration = 0  # Reset duration

        #if not resume:  # New session
        #    timer_active = True
        #    session['timer'] = 0  # Reset timer for new session
        #    print("Starting a new session. Timer reset to 0.")
        #else:  # Resuming session
        #    timer_active = True  # Ensure timer continues running
        #    print(f"Resuming session with timer at {timer} minutes.")

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

        if mode == "Guided Interview Mode" and not timer_active:
            timer_active = True  # Ensure timer continues running
            print("Continuing guided mode timer:", timer)

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

        # Debugging Subcategories Before Feedback Processing
        print("Subcategories Before Processing:", subcategories)

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
            "       1. Question Technique (clarity, follow-ups, open-ended).\n"
            "       2. JTBD Framework (job discovery, context, timeline).\n"
            "       3. Progress Forces (push, pull, anxiety, habits).\n"
            "       4. Interview Mgmt (flow, rapport, time).\n"
            "     • Business Insights:\n"
            "       1. Market Opportunity (needs, gaps, competition).\n"
            "       2. Innovation (solutions, value propositions).\n"
            "       3. Customer Segment (characteristics, behavior).\n"
            "       4. Strategic (actions, implications, priorities).\n"
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
            "      \"Question Technique\": {\"relevance\": 0.9, \"effectiveness\": 4.5},\n"
            "      \"JTBD Framework\": {\"relevance\": 0.8, \"effectiveness\": 4.0},\n"
            "      \"Progress Forces\": {\"relevance\": 0.7, \"effectiveness\": 3.5},\n"
            "      \"Interview Mgmt\": {\"relevance\": 0.6, \"effectiveness\": 4.0}\n"
            "    },\n"
            "    \"Business Insights\": {\n"
            "      \"Market Opportunity\": {\"relevance\": 0.7, \"effectiveness\": 4.0},\n"
            "      \"Innovation\": {\"relevance\": 0.9, \"effectiveness\": 4.5},\n"
            "      \"Customer Segment\": {\"relevance\": 0.8, \"effectiveness\": 4.0},\n"
            "      \"Strategic\": {\"relevance\": 0.6, \"effectiveness\": 3.5}\n"
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

            feedback_data = json.loads(raw_response)
            numerical_feedback = feedback_data['numerical_feedback']
            raw_scores = {}
            for category, subs in numerical_feedback.items():
                for sub, scores in subs.items():
                    raw_scores[f"R - {sub}"] = scores["relevance"]
                    raw_scores[f"E - {sub}"] = scores["effectiveness"]

            # Extract verbal feedback
            verbal_feedback = feedback_data['verbal_feedback']
            key_findings = "; ".join(verbal_feedback.get("Key Findings", []))
            strengths = "; ".join(verbal_feedback.get("Interview Strengths", []))
            improvements = "; ".join(verbal_feedback.get("Areas for Improvement", []))
            follow_up_questions = "; ".join(verbal_feedback.get("Recommended Follow-Up Questions", []))

            new_row = {
                "Timestamp": pd.Timestamp.now(),
                "Q&A #": questions_counter,
                **raw_scores,
                "Key Findings": key_findings,
                "Interview Strengths": strengths,
                "Areas for Improvement": improvements,
                "Recommended Follow-Up Questions": follow_up_questions
            }
            evaluation_df = pd.concat([evaluation_df, pd.DataFrame([new_row])], ignore_index=True)
            print("Evaluation DataFrame after appending new row:")
            print(evaluation_df.info())

            # Normalize subcategories dictionary
            normalized_subcategories = {
                key.strip().lower().replace(" ", "_"): value for key, value in subcategories.items()
            }

            # Debugging: Print expected and actual subcategories
            print("Expected Subcategories:", list(subcategories.keys()))
            print("Raw Response Subcategories:", list(numerical_feedback["Business Insights"].keys()))

            # Verify the subcategories dictionary is structured properly
            print("Subcategories Dictionary:", subcategories)

            # Calculate Derived Scores
            for sub in subcategories.keys():
                print(f"Processing sub-category: {sub}")
                relevance_col = f"R - {sub}"
                effectiveness_col = f"E - {sub}"
                calc_col = f"{sub} CalcScore"
                avg_col = f"{sub} AvgScore"
                total_col = f"{sub} TotalScore"

                if relevance_col not in evaluation_df or effectiveness_col not in evaluation_df:
                    print(f"Missing columns for sub-category: {sub}")
                    continue

                # Normalize subcategory name and fetch MaxScore
                normalized_sub = sub.strip().lower().replace(" ", "_")
                if normalized_sub not in normalized_subcategories:
                    print(f"Error: Sub-category '{sub}' not found in normalized subcategories.")
                    continue

                # Debug MaxScore access
                print(f"Accessing MaxScore for sub-category: {sub}")
                if sub not in subcategories:
                    print(f"Sub-category '{sub}' not found in subcategories.")
                    continue

                try:
                    max_score = subcategories[sub]["MaxScore"]
                    print(f"MaxScore for '{sub}': {max_score}")

                    if relevance_col in evaluation_df and effectiveness_col in evaluation_df:
                        # Set CalcScore to NaN if Relevance < 0.3
                        evaluation_df[calc_col] = evaluation_df.apply(
                            lambda row: row[relevance_col] * row[effectiveness_col]
                            if row[relevance_col] >= 0.3 else float('NaN'),
                            axis=1
                        )
                    evaluation_df[avg_col] = evaluation_df[calc_col].expanding().mean()
                    evaluation_df[total_col] = (
                        evaluation_df[avg_col] / 5 * normalized_subcategories[normalized_sub]["MaxScore"]
                    )
                except KeyError as e:
                    print(f"Error accessing MaxScore for sub-category: {sub}")
                    raise

            # Calculate Overall Scores
            evaluation_df["Interview Skills Score"] = evaluation_df[
                [f"{sub} TotalScore" for sub in
                 ["Question Technique", "JTBD Framework", "Progress Forces", "Interview Mgmt"]]
            ].sum(axis=1)

            evaluation_df["Business Insight Score"] = evaluation_df[
                [f"{sub} TotalScore" for sub in ["Market Opportunity", "Innovation", "Customer Segment", "Strategic"]]
            ].sum(axis=1)

            evaluation_df["Total Score"] = evaluation_df["Interview Skills Score"] + evaluation_df[
                "Business Insight Score"]

            # Save to Excel AFTER calculations
            print("Saving evaluation DataFrame to Excel...")
            evaluation_df.to_excel("evaluation_debug.xlsx", index=False)
            print("File saved.")

            print("Last Row of Evaluation DataFrame:")
            print(evaluation_df.tail(1))

        except Exception as e:
            print(f"Error processing feedback: {e}")

        # Debugging Subcategories After Feedback Processing
        print("Subcategories After Processing:", subcategories)

        # Persist Timer After Processing
        #session['timer'] = timer  # Save the current timer value in session
        print(f"Timer value after processing question: {timer} minutes")

        # Render the updated interview screen
        return render_template(
            'interview.html',
            conversation=conversation,
            counter=questions_counter,
            mode=mode,
            maxQuestions=maxQuestions,
            persona=persona,
            timer=timer,
            business_domain = business_domain,
            auto_scroll = True
        )


# Evaluation route
@app.route('/evaluation', methods=['GET'])
def evaluation():
    global questions_counter, conversation, timer, duration, timer_active, evaluation_df, subcategories, business_domain
    print("Evaluation route - business_domain:", business_domain)

    #business_domain = request.args.get('business_domain', 'Airline Operations')

    # Determine if this is the final or progress evaluation
    mode = request.args.get('mode', 'Full Interview Mode')
    is_final = request.args.get('final', 'true').lower() == 'true'

    # Use the session's timer value for progress evaluation, or duration for the final evaluation
    duration_to_display = timer if not is_final else duration
    print(f"Timer passed to evaluation screen: {duration_to_display} minutes")  # Debugging log

    # Get the latest row from the evaluation DataFrame
    latest_row = evaluation_df.iloc[-1] if not evaluation_df.empty else None

    # Extract numerical scores
    scores = {}
    if latest_row is not None:
        scores = {
            "Interview Skills Score": latest_row["Interview Skills Score"],
            "Business Insight Score": latest_row["Business Insight Score"],
            "Total Score": latest_row["Total Score"]
        }

    # Add subcategory scores dynamically
    for sub in subcategories.keys():
        scores[sub] = latest_row.get(f"{sub} TotalScore", "N/A")

    # Extract verbal feedback
    feedback = {}
    if latest_row is not None:
        feedback = {
            "Key Findings": latest_row["Key Findings"],
            "Interview Strengths": latest_row["Interview Strengths"],
            "Areas for Improvement": latest_row["Areas for Improvement"],
            "Recommended Follow-Up Questions": latest_row["Recommended Follow-Up Questions"]
        }

    # Include the transcript only for final evaluations
    #transcript = conversation if is_final else None
    transcript = [
        {
            "role": "Executive" if message["role"] == "assistant" else "You",
            "content": message["content"]
        }
        for message in conversation
    ] if is_final else None

    # Persist the current timer value in the session
    #session['timer'] = session.get('timer', 0)  # Ensure the latest value is saved
    print(f"Timer saved for evaluation: {timer} minutes")  # Debugging log
    print(f"Duration displayed: {duration_to_display}")

    return render_template(
        'evaluation.html',
        business_domain=business_domain,
        mode=mode,
        is_final=is_final,
        subcategories=subcategories,
        scores=scores,
        feedback=feedback,
        transcript=transcript,
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


@app.route('/download_report', methods=['GET'])
def download_report():
    global business_domain
    print("Business Domain is:", business_domain)
    output_path = 'temp_report.pdf'

    try:
        print("Starting download_report function")
        print(f"Using global business domain: {business_domain}")

        # Use global business_domain directly
        current_persona = personas[business_domain]
        print(f"Found persona: {current_persona}")

        timestamp = pd.Timestamp.now()

        # Debugging evaluation_df
        print("Evaluation DF empty?", evaluation_df.empty)
        if not evaluation_df.empty:
            print("Last row keys:", list(evaluation_df.iloc[-1].keys()))

        # Handle scores
        if not evaluation_df.empty:
            latest_row = evaluation_df.iloc[-1]
            scores = {
                "Interview Skills Score": int(
                    latest_row["Interview Skills Score"] if pd.notnull(latest_row["Interview Skills Score"]) else 0),
                "Business Insight Score": int(
                    latest_row["Business Insight Score"] if pd.notnull(latest_row["Business Insight Score"]) else 0),
                "Total Score": int(latest_row["Total Score"] if pd.notnull(latest_row["Total Score"]) else 0)
            }

            for sub in subcategories.keys():
                score_value = latest_row.get(f"{sub} TotalScore", 0)
                scores[sub] = int(score_value if pd.notnull(score_value) else 0)
        else:
            print("No evaluation data, using default scores")
            scores = {
                "Interview Skills Score": 0,
                "Business Insight Score": 0,
                "Total Score": 0,
                **{sub: 0 for sub in subcategories.keys()}
            }

        print("Scores prepared:", scores)

        # Render template
        print("Starting template rendering")
        html = render_template(
            'final_report.html',
            timestamp=timestamp,
            #mode=mode,
            subcategories=subcategories,
            scores=scores,
            feedback={
                "Key Findings": latest_row["Key Findings"] if not evaluation_df.empty else "",
                "Interview Strengths": latest_row["Interview Strengths"] if not evaluation_df.empty else "",
                "Areas for Improvement": latest_row["Areas for Improvement"] if not evaluation_df.empty else "",
                "Recommended Follow-Up Questions": latest_row[
                    "Recommended Follow-Up Questions"] if not evaluation_df.empty else ""
            } if not evaluation_df.empty else {},
            transcript=[
                {
                    "role": "Executive" if message["role"] == "assistant" else "You",
                    "content": message["content"]
                }
                for message in conversation
            ],
            counter=questions_counter,
            duration=duration,
            persona=current_persona
        )
        print("Template rendered successfully")

        # Generate PDF
        print("Starting PDF generation")
        options = {
            'page-size': 'Letter',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': 'UTF-8',
            'enable-local-file-access': True,
            'quiet': ''
        }

        config = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')
        pdfkit.from_string(html, output_path, options=options, configuration=config)
        print("PDF generated successfully")

        return send_file(
            output_path,
            as_attachment=True,
            download_name="JTBD_Interview_Analysis_Report.pdf",
            mimetype='application/pdf'
        )

    except Exception as e:
        print(f"Error generating report: {e}")
        import traceback
        traceback.print_exc()
        return make_response(f"Failed to generate report: {str(e)}", 500)

    finally:
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception as e:
                print(f"Error removing temporary file: {e}")

@app.route('/thank-you')
def thank_you():
    return render_template('thank-you.html')

if __name__ == '__main__':
    app.run(debug=True)
