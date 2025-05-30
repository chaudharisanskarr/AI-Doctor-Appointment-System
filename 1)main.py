import re
from nltk.corpus import wordnet
import speech_recognition as sr
import pyttsx3
import webbrowser
from flask import Flask, render_template
from pymongo import MongoClient

# Initialize the Flask app for scheduling Google Meet
app = Flask(__name__)

# Initialize the text-to-speech engine
engine = pyttsx3.init()

# MongoDB client setup (assuming MongoDB is running locally)
client = MongoClient("mongodb://localhost:27017/")  # Connect to the MongoDB server
db = client["patient_database"]  # Create or use an existing database
patients_collection = db["patients"]  # Create or use an existing collection


# Function to speak a message
def speak(message):
    engine.say(message)
    engine.runAndWait()

# Function to print and speak a message
def print_and_speak(message):
    print(message)
    speak(message)

# Function to get synonyms from WordNet
def get_synonyms(word):
    synonyms = set()
    for syn in wordnet.synsets(word):
        for lemma in syn.lemmas():
            synonyms.add(lemma.name().replace('_', ' '))
    return synonyms

# Generate and expand symptom synonyms
def generate_synonyms_for_symptoms(symptoms_dict):
    for symptom, descriptions in symptoms_dict.items():
        synonyms = get_synonyms(symptom)
        symptoms_dict[symptom].extend(synonyms)

# Define symptoms for multiple diseases
disease_symptoms = {
    "fungal_infection": {
        "itching": ["itchy", "scratchy", "pruritus"],
        "skin rash": ["rash", "red spots", "lesions", "irritation"],
        "nodal skin eruptions": ["bumps", "lumps", "raised skin", "eruptions"],
        "dischromic patches": ["discolored skin", "light patches", "dark patches", "pigment changes"]
    },
    "allergy": {
        "sneezing": ["sneeze", "sneezes", "nasal irritation"],
        "runny nose": ["nasal discharge", "rhinorrhea", "dripping nose"],
        "itchy eyes": ["irritated eyes", "red eyes", "eye irritation"],
        "cough": ["coughing", "dry cough", "persistent cough"]
    }
}

# Symptom matrix for each disease
disease_matrix = {
    "fungal_infection": [
        [1, 1, 1, 1],
        [1, 1, 1, 0],
        [1, 1, 0, 0],
        [0, 0, 1, 0],
    ],
    "allergy": [
        [1, 1, 1, 1],
        [1, 1, 0, 0],
        [0, 0, 0, 0],
    ]
}

for disease in disease_symptoms:
    generate_synonyms_for_symptoms(disease_symptoms[disease])

# Function to recognize speech input
def recognize_speech():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        audio = recognizer.listen(source)
    try:
        speech = recognizer.recognize_google(audio)
        print(f"Recognized: {speech}")
        return speech.lower()
    except sr.UnknownValueError:
        print("Could not understand audio, please try again.")
        return ""
    except sr.RequestError:
        print("Could not request results from Google Speech Recognition service.")
        return ""

# Function to confirm or correct recognized speech
def confirm_or_correct(prompt):
    print_and_speak(prompt)
    recognized_text = recognize_speech()
    
    if not recognized_text:
        print_and_speak("I did not catch that. Can you please repeat?")
        return confirm_or_correct(prompt)

    return recognized_text

# Function to check if the response is affirmative
def is_affirmative(response):
    yes_synonyms = ["yes", "yeah", "yup", "sure", "absolutely", "affirmative", "certainly", "correct", "positive"]
    return any(phrase in response for phrase in yes_synonyms)

# Function to check if the response is negative
def is_negative(response):
    no_synonyms = ["no", "nah", "nope", "not at all", "never", "negative"]
    return any(phrase in response for phrase in no_synonyms)

# Function to extract symptoms from user input for multiple diseases
def extract_symptoms(user_input):
    detected_symptoms = {}
    for disease, symptoms in disease_symptoms.items():
        detected_symptoms[disease] = []
        for symptom, synonyms in symptoms.items():
            pattern = re.compile(r'\b(' + '|'.join(synonyms) + r')\b')
            if pattern.search(user_input):
                detected_symptoms[disease].append(symptom)
    return {disease: sym for disease, sym in detected_symptoms.items() if sym}

# Function to ask follow-up questions for all symptoms of a disease
def ask_follow_up(disease):
    follow_up_questions = {
        "fungal_infection": {
            "itching": ["Is the itching localized to one area? (yes/no)", "Does the itching worsen at night? (yes/no)"],
            "skin rash": ["Does the rash appear red and irritated? (yes/no)", "Is the rash spreading? (yes/no)"],
            "nodal skin eruptions": ["Are the eruptions painful? (yes/no)", "Are the bumps filled with fluid? (yes/no)"],
            "dischromic patches": ["Are the patches lighter or darker than your skin? (yes/no)", "Are the patches well-defined or blurred? (yes/no)"]
        },
        "allergy": {
            "sneezing": ["Is the sneezing frequent? (yes/no)", "Is it worse in the morning? (yes/no)"],
            "runny nose": ["Is your nose constantly runny? (yes/no)", "Is nasal discharge clear? (yes/no)"],
            "itchy eyes": ["Are your eyes red and itchy? (yes/no)", "Do your eyes water frequently? (yes/no)"],
            "cough": ["Is the cough dry? (yes/no)", "Does the cough worsen at night? (yes/no)"]
        }
    }
    
    confirmed_symptoms = []
    symptom_names = []
    for symptom in disease_symptoms[disease].keys():
        confirmed = False
        while not confirmed:
            response = confirm_or_correct(f"Do you have {symptom}? (yes/no)")
            print(f"User response for {symptom}: {response}")
            if is_affirmative(response):
                confirmed = True
                follow_ups = follow_up_questions.get(disease, {}).get(symptom, [])
                yes_count = 0
                for question in follow_ups:
                    print_and_speak(question)
                    answer = confirm_or_correct("")
                    print(f"User answer for '{question}': {answer}")
                    if is_affirmative(answer):
                        yes_count += 1
                if yes_count > len(follow_ups) / 2:
                    confirmed_symptoms.append(1)
                    symptom_names.append(f"+{symptom}")
                else:
                    confirmed_symptoms.append(0)
                    symptom_names.append(f"-{symptom}")
                break
            elif is_negative(response):
                confirmed_symptoms.append(0)
                symptom_names.append(f"-{symptom}")
                confirmed = True
            else:
                print_and_speak("I didn't catch that. Can you please say yes or no?")
    return confirmed_symptoms, symptom_names

# Function to evaluate all diseases based on symptom patterns
def evaluate_diseases(symptom_patterns):
    confirmed_prognoses = []
    not_confirmed_prognoses = []

    for disease, (symptom_pattern, symptom_names) in symptom_patterns.items():
        pattern = ''.join(map(str, symptom_pattern))
        if list(map(int, pattern)) in disease_matrix[disease]:
            confirmed_prognoses.append((disease, symptom_names))
        else:
            not_confirmed_prognoses.append((disease, symptom_names))

    return confirmed_prognoses, not_confirmed_prognoses

# Function to ask for patient details and store in patient_info.txt
def get_patient_details():
    patient_info = {}
    name_confirmed = False
    attempts = 0
    while not name_confirmed and attempts < 2:
        recognized_name = confirm_or_correct("What is your name?")
        print_and_speak(f"You said your name is {recognized_name}. Is that correct? (yes/no)")
        
        confirmation = confirm_or_correct("")
        if is_affirmative(confirmation):
            patient_info['name'] = recognized_name
            name_confirmed = True
        else:
            print_and_speak("Please input your name manually.")
            patient_info['name'] = input("Enter name manually: ")
            name_confirmed = True

    age_confirmed = False
    attempts = 0
    while not age_confirmed and attempts < 2:
        age_input = confirm_or_correct("How old are you?")
        if age_input.isdigit() and 0 < int(age_input) < 120:
            patient_info['age'] = age_input
            age_confirmed = True
        else:
            print_and_speak("Please provide a valid age (a number between 1 and 120).")
            attempts += 1
    
    if not age_confirmed:
        print_and_speak("Unable to confirm age, please input manually.")
        patient_info['age'] = input("Enter age manually: ")

    sex_confirmed = False
    attempts = 0
    while not sex_confirmed and attempts < 2:
        sex_input = confirm_or_correct("What is your Gender? (male/female)")
        
        # Handling common misrecognitions
        if sex_input in ["male", "m", "mail"]:
            patient_info['sex'] = "male"
            sex_confirmed = True
        elif sex_input in ["female", "f", "female"]:
            patient_info['sex'] = "female"
            sex_confirmed = True
        else:
            print_and_speak("Please specify male or female.")
            attempts += 1

    if not sex_confirmed:
        print_and_speak("Unable to confirm sex, please input manually.")
        patient_info['sex'] = input("Enter sex manually (male/female): ")

    return patient_info

# Function to write patient details and evaluation to a file with spacing between entries
def write_patient_info_to_file(patient_info, confirmed_prognoses, not_confirmed_prognoses):
    with open("./patient_info.txt", "a") as file:
        # Add a newline between entries if the file isn't empty
        file.write("\n" + "="*30 + "\n")  # Add a separator for clarity between entries
        file.write(f"Name: {patient_info['name']}\n")
        file.write(f"Age: {patient_info['age']}\n")
        file.write(f"Sex: {patient_info['sex']}\n")
        file.write(f"Symptom Description: {patient_symptoms}\n")
        file.write("Symptoms and Final Evaluation:\n")
        
        if confirmed_prognoses:
            file.write("\nConfirmed Diagnoses:\n")
            for disease, symptoms in confirmed_prognoses:
                file.write(f"- {disease} with symptom evaluation as: {', '.join(symptoms)}\n")
        else:
            file.write("\nNo confirmed diseases based on symptoms.\n")
        
        if not_confirmed_prognoses:
            file.write("\nUnconfirmed Diagnoses:\n")
            for disease, symptoms in not_confirmed_prognoses:
                file.write(f"- {disease} with symptom evaluation as: {', '.join(symptoms)}\n")
        else:
            file.write("\nAll potential diagnoses were considered based on symptoms.\n")
            
# Function to store patient info in MongoDB
def store_patient_info_in_mongo(patient_info, confirmed_prognoses, not_confirmed_prognoses):
    patient_data = {
        "name": patient_info['name'],
        "age": patient_info['age'],
        "sex": patient_info['sex'],
        "confirmed_diagnoses": [{
            "disease": disease,
            "symptom_evaluation": symptoms
        } for disease, symptoms in confirmed_prognoses],
        "unconfirmed_diagnoses": [{
            "disease": disease,
            "symptom_evaluation": symptoms
        } for disease, symptoms in not_confirmed_prognoses]
    }
    # Insert the patient info into MongoDB
    patients_collection.insert_one(patient_data)
            
# Function to extract relevant diseases based on detected symptoms
def extract_relevant_diseases(user_input):
    detected_symptoms = {}
    relevant_diseases = set()
    
    # Detect symptoms for each disease and determine relevance
    for disease, symptoms in disease_symptoms.items():
        detected_symptoms[disease] = []
        for symptom, synonyms in symptoms.items():
            pattern = re.compile(r'\b(' + '|'.join(synonyms) + r')\b')
            if pattern.search(user_input):
                detected_symptoms[disease].append(symptom)
                relevant_diseases.add(disease)  # Add disease to relevant list if any symptom matches
    
    return relevant_diseases, {disease: sym for disease, sym in detected_symptoms.items() if sym}

# Function to print and voice out the final evaluation
def display_final_evaluation(confirmed, not_confirmed):
    if confirmed:
        print_and_speak("Based on your responses, the following conditions may be present:")
        for disease in confirmed:
            print_and_speak(f"- {disease}")
    else:
        print_and_speak("No specific conditions were confirmed based on the symptoms provided.")
    
    if not_confirmed:
        print_and_speak("The following conditions were considered but not confirmed:")
        for disease in not_confirmed:
            print_and_speak(f"- {disease}")
            
# Function to run Flask app for scheduling Google Meet
@app.route('/')
def index():
    return render_template('index.html')  # Assuming you have an index.html for scheduling

# Function to start the Flask app in a separate thread
def start_flask_app():
    from threading import Thread
    thread = Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': 5000})
    thread.daemon = True
    thread.start()

# Main code execution update
if __name__ == "__main__":
    print_and_speak("Welcome to the health assessment program.")
    
    # Step 1: Collect patient details
    patient_info = get_patient_details()
    
    # Step 2: Ask for an initial symptom description
    patient_symptoms = confirm_or_correct("Please describe your symptoms.")
    
    # Step 3: Extract relevant diseases and symptom patterns
    relevant_diseases, symptom_patterns = extract_relevant_diseases(patient_symptoms)
    print(f"Relevant diseases based on initial input: {relevant_diseases}")
    
    # Step 4: For each relevant disease, ask follow-up questions and store the confirmed symptoms
    for disease in relevant_diseases:
        confirmed_symptoms, symptom_names = ask_follow_up(disease)
        symptom_patterns[disease] = (confirmed_symptoms, symptom_names)
    
    # Step 5: Evaluate based on confirmed symptom patterns
    confirmed_prognoses, not_confirmed_prognoses = evaluate_diseases(symptom_patterns)
    
    # Step 6: Display the final evaluation to the user
    display_final_evaluation([d[0] for d in confirmed_prognoses], [d[0] for d in not_confirmed_prognoses])
    
    # Step 7: Save in MongoDB
    try:
        store_patient_info_in_mongo(patient_info, confirmed_prognoses, not_confirmed_prognoses)
        print_and_speak("Patient information stored successfully in the database.")
    except Exception as e:
        print(f"Error while saving patient information: {e}")
        print_and_speak("An error occurred while saving your information.")
    
    # Step 8: Write the patient information and evaluation to a file
    try:
        write_patient_info_to_file(patient_info, confirmed_prognoses, not_confirmed_prognoses)
        print_and_speak("Thank you for using the health assessment program.")
    except Exception as e:
        print(f"Error while saving patient information: {e}")
        print_and_speak("An error occurred while saving your information.")
    
     # Now, launch the Flask server for scheduling
    print_and_speak("Redirecting to the scheduling system...")
    start_flask_app()

    # Automatically open the browser to localhost:5000
    webbrowser.open("http://localhost:5000")