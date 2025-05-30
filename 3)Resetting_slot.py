import os.path
import datetime as dt
from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pytz
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

scheduler = BackgroundScheduler()

# Flag to track if scheduler is started
scheduler_started = False

def update_slots_after_meeting():
    print("Slots updated after meeting.")

# Schedule the task to check events and update slots every 30 minutes
scheduler.add_job(update_slots_after_meeting, 'interval', minutes=30)

@app.before_request
def start_scheduler():
    global scheduler_started
    if not scheduler_started:
        scheduler.start()
        scheduler_started = True

@app.route('/')
def index():
    return render_template('index.html')

# MongoDB connection setup
client = MongoClient("mongodb://localhost:27017/")
db = client["doctor_appointments"]
collection = db["appointments"]

# SCOPES for Google Calendar API
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Function to send email
def send_email(to_email, subject, body):
    from_email = "sparxvenom69@gmail.com"
    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(from_email, "dowg kvxj tkrn hxjh")  # App-specific password
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
        print(f"Email sent to {to_email}")
    except Exception as e:
        print(f"Failed to send email: {e}e")
        
@app.route('/get_doctors', methods=['GET'])
def get_doctors():
    doctors = list(collection.find({}, {"_id": 0, "doctor_name": 1, "qualification": 1, "specialization": 1}))
    return jsonify(doctors)

# Function to schedule Google Meet

# Function to fetch the latest patient information
def get_latest_patient_info():
    patient_db = client["patient_database"]
    patient_collection = patient_db["patients"]

    # Fetch the latest document based on `_id` timestamp
    latest_patient = patient_collection.find_one(sort=[("_id", -1)])
    return latest_patient

# Function to build diagnosis details with symptom evaluation
def build_diagnosis_details(diagnoses):
    details = []
    for diag in diagnoses:
        disease = diag.get("disease", "N/A")
        symptoms = "\n  ".join(diag.get("symptom_evaluation", [])) or "None"
        details.append(f"- {disease}\n  Symptom Evaluation:\n  {symptoms}")
    return "\n".join(details)

def schedule_google_meet(doctor_email, patient_email, time_slot, day, doctor_name):
    today = dt.datetime.now(pytz.timezone("Asia/Kolkata"))
    weekday_map = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6}
    
    if day not in weekday_map:
        return None, "Invalid day provided."
    
    day_index = weekday_map[day]
    days_ahead = (day_index - today.weekday() + 7) % 7
    
    if days_ahead == 0 and today.time() > dt.datetime.strptime(time_slot.split(" - ")[0], "%I:%M %p").time():
        days_ahead = 7
    
    appointment_date = today + dt.timedelta(days=days_ahead)
    
    if days_ahead > 7:
        return None, "Appointments can only be scheduled within the next 7 days."
    
    start_time = dt.datetime.strptime(time_slot.split(" - ")[0], "%I:%M %p").time()
    start_datetime = dt.datetime.combine(appointment_date.date(), start_time)
    local_start = pytz.timezone("Asia/Kolkata").localize(start_datetime)
    start_datetime_utc = local_start.astimezone(pytz.utc)
    end_datetime_utc = start_datetime_utc + dt.timedelta(hours=1)

    creds = None
    if os.path.exists("./Key/token.json"):
        creds = Credentials.from_authorized_user_file("./Key/token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("./Key/Credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("./Key/token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("calendar", "v3", credentials=creds)
        event = {
            "summary": "Doctor Appointment",
            "location": "Online (Google Meet)",
            "description": f"Doctor appointment scheduled.",
            "start": {
                "dateTime": start_datetime_utc.isoformat(),
                "timeZone": "UTC",
            },
            "end": {
                "dateTime": end_datetime_utc.isoformat(),
                "timeZone": "UTC",
            },
            "attendees": [
                {"email": patient_email},
                {"email": doctor_email},
            ],
            "conferenceData": {
                "createRequest": {
                    "requestId": f"meet-{start_datetime_utc.isoformat()}",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                },
            },
        }

        event = service.events().insert(
            calendarId="primary", body=event, conferenceDataVersion=1, sendUpdates="all"
        ).execute()

        meet_link = event.get("htmlLink")
        google_meet_link = (
            event.get("conferenceData", {})
            .get("entryPoints", [{}])[0]
            .get("uri", "Google Meet link not available")
        )

        # Store the event_id and mark the slot as unavailable
        collection.update_one(
            {"doctor_name": doctor_name},
            {"$push": {
                f"appointments.{day}": {
                    "time_slot": time_slot,
                    "event_id": event['id'],
                    "available": False  # Mark slot as unavailable
                }
            }}
        )

        return meet_link, google_meet_link
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None, None
    
def update_slots_after_meeting():
    # Get the current UTC time
    now = dt.datetime.now(pytz.timezone("Asia/Kolkata"))
    current_time_utc = pytz.utc.localize(now)

    # Fetch all appointments with event IDs that are currently unavailable
    doctors = collection.find({"appointments": {"$exists": True}})
    
    for doctor in doctors:
        for day, appointments in doctor.get("appointments", {}).items():
            for appointment in appointments:
                if not appointment["available"]:  # Only check unavailable slots
                    event_id = appointment.get("event_id")
                    if event_id:
                        # Fetch the event details from Google Calendar API
                        try:
                            creds = None
                            if os.path.exists("./Key/token.json"):
                                creds = Credentials.from_authorized_user_file("./Key/token.json", SCOPES)
                            if not creds or not creds.valid:
                                if creds and creds.expired and creds.refresh_token:
                                    creds.refresh(Request())
                                else:
                                    flow = InstalledAppFlow.from_client_secrets_file("./Key/Credentials.json", SCOPES)
                                    creds = flow.run_local_server(port=0)
                                with open("./Key/token.json", "w") as token:
                                    token.write(creds.to_json())
                            
                            service = build("calendar", "v3", credentials=creds)
                            event = service.events().get(
                                calendarId="primary", eventId=event_id
                            ).execute()
                            
                            event_end_time = event["end"]["dateTime"]
                            event_end_time_utc = dt.datetime.fromisoformat(event_end_time).astimezone(pytz.utc)

                            # Check if the event has ended
                            if event_end_time_utc <= current_time_utc:
                                # Update the slot to available
                                collection.update_one(
                                    {"doctor_name": doctor["doctor_name"]},
                                    {"$set": {
                                        f"appointments.{day}.$[slot].available": True
                                    }},
                                    array_filters=[{"slot.event_id": event_id}]
                                )
                                print(f"Slot for {doctor['doctor_name']} on {day} at {appointment['time_slot']} is now available.")
                        except HttpError as error:
                            print(f"An error occurred while checking event: {error}")


# Fetch available slots for a specific doctor on a given day
@app.route("/get_slots", methods=["POST"])
def get_slots():
    doctor_name = request.json.get("doctor_name")
    day = request.json.get("day")
    doctor_info = collection.find_one({"doctor_name": doctor_name})

    if doctor_info:
        slots = doctor_info["available_slots"].get(day, [])
        available_slots = [slot for slot in slots if slot["available"]]
        return jsonify({"available_slots": available_slots})
    else:
        return jsonify({"message": "Doctor not found or no available slots for the selected day."}), 400

# Book an appointment
@app.route('/book_appointment', methods=['POST'])
def book_appointment():
    data = request.json
    doctor_name = data['doctor_name']
    day = data['day']
    time_slot = data['time_slot']
    patient_email = data['patient_email']
    patient_name = data['patient_name']

    # Fetch doctor information
    doctor_info = collection.find_one({'doctor_name': doctor_name})

    if not doctor_info:
        return jsonify({'message': 'Doctor not found.'}), 400

    # Search for the patient by exact name
    patient_db = client["patient_database"]
    patient_collection = patient_db["patients"]

    patient_records = list(patient_collection.find({'name': {'$regex': f'^{patient_name}$', '$options': 'i'}}))

    if not patient_records:
        return jsonify({'message': f"No patient found with the name '{patient_name}'. Please ensure the name matches exactly."}), 400

    if len(patient_records) > 1:
        # Fetch the latest record if multiple records exist
        latest_patient = sorted(patient_records, key=lambda x: x["_id"], reverse=True)[0]
    else:
        latest_patient = patient_records[0]

    # Check the slot availability
    slots = doctor_info['available_slots'].get(day, [])
    slot = next((slot for slot in slots if slot['time'] == time_slot), None)

    if not slot or not slot['available']:
        return jsonify({'message': 'The selected time slot is already booked.'}), 400

    # Update the slot to mark it as unavailable
    collection.update_one(
        {'doctor_name': doctor_name, f'available_slots.{day}.time': time_slot},
        {'$set': {'available_slots.' + day + '.$.available': False}}
    )

    # Build patient information string for description
    confirmed_diagnoses_details = build_diagnosis_details(latest_patient.get("confirmed_diagnoses", [])) or "None"
    unconfirmed_diagnoses_details = build_diagnosis_details(latest_patient.get("unconfirmed_diagnoses", [])) or "None"
    patient_info = (
        f"Patient Name: {latest_patient.get('name', 'N/A')}\n"
        f"Age: {latest_patient.get('age', 'N/A')}\n"
        f"Sex: {latest_patient.get('sex', 'N/A')}\n\n"
        f"Confirmed Diagnoses:\n{confirmed_diagnoses_details}\n\n"
        f"Unconfirmed Diagnoses:\n{unconfirmed_diagnoses_details}"
    )

    # Schedule Google Meet and get the link
    meet_link, google_meet_link = schedule_google_meet(
    doctor_info['doctor_email'], 
    patient_email, 
    time_slot, 
    day, 
    doctor_name  # Add this missing argument
)

    # Send confirmation emails
    doctor_subject = f"New Appointment Scheduled with {latest_patient.get('name', 'N/A')}"
    doctor_body = f"Dear {doctor_name},\n\nYou have a new appointment.\n\n{patient_info}\n\nTime: {time_slot}\nMeet Link: {google_meet_link}\n\nRegards,\nAppointment System"
    send_email(doctor_info['doctor_email'], doctor_subject, doctor_body)

    patient_subject = f"Appointment Confirmation with {doctor_name}"
    patient_body = f"Dear {latest_patient.get('name', 'N/A')},\n\nYour appointment with {doctor_name} is confirmed.\nTime: {time_slot}\nMeet Link: {google_meet_link}\n\nRegards,\nAppointment System"
    send_email(patient_email, patient_subject, patient_body)

    return jsonify({'message': 'Appointment successfully booked!', 'meet_link': google_meet_link})

if __name__ == "__main__":
    app.run(debug=True, host="localhost", port=5000)