# 🏥 AI Doctor Appointment System

An intelligent voice-based doctor appointment system that captures patient details through speech, determines symptoms, analyzes severity, and schedules a Google Meet consultation with a doctor automatically.

---

## 🧠 Project Description

In today's fast-paced world, access to timely and accurate medical advice is crucial, yet often limited by geographical barriers and mobility constraints. The **AI Personalized Doctor Project** aims to revolutionize healthcare by developing a virtual health assistant that offers personalized medical advice, disease prediction, and seamless telemedicine consultations—making quality healthcare accessible to all.

## 🎯 Key Objectives

- ✅ Develop an **AI-powered virtual health assistant**
- ✅ Integrate **Natural Language Processing (NLP)** and **Text-to-Speech (TTS)** technologies
- ✅ Train **Machine Learning models** for disease prediction
- ✅ Implement a **dynamic scheduling system**
- ✅ Build a secure, **web-based telemedicine platform**
- ✅ Seamlessly integrate **Google Meet** for real-time virtual consultations

---

## 🧪 Methodology

1. **User Onboarding**  
   - Collect user details (name, age, sex) via voice or form  
   - Store securely in MongoDB

2. **Symptom Collection**  
   - Use an intelligent Q&A engine to collect symptom-related data

3. **Disease Prediction**  
   - Apply rule-based or ML/NLP models to infer likely conditions

4. **Doctor Selection**  
   - Display list of available doctors based on specialization and availability

5. **Appointment Booking**  
   - Automatically schedule appointment  
   - Generate and send Google Meet link  
   - Store all relevant details in MongoDB

---

## 📁 Project Structure

```
AI Doctor Appointment System/
├── Dataset/                  # Contains training/lookup data (e.g., symptoms, diseases)
├── Key/                      # API keys and credentials (e.g., Google API)
├── static/                   # Static assets (CSS, JS, images)
├── templates/                # HTML templates for frontend
├── 1)main.py                 # Entry point: Handles voice input, symptom processing, and slot display
├── 2)GoogleMeet_Schedule.py # Schedules Google Meet based on appointment logic
├── 3)Resetting_slot.py       # Resets the appointment slots daily
```

---

## 🚀 How to Run

1. **Clone the Repository**
   ```bash
   git clone https://github.com/chaudharisanskarr/AI-Doctor-Appointment-System.git
   cd ai-doctor-appointment-system
   ```

2. **Set Up Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   - Flask  
   - SpeechRecognition  
   - gTTS  
   - google-api-python-client  
   - google-auth  
   - google-auth-oauthlib  
   - pyaudio  
   - nltk  
   - pymongo

4. **Add API Keys**
   - Place your **Google API credentials** in the `Key/` directory.

5. **Run the Application**
   ```bash
   python "1)main.py"
   ```

---

## 🔁 Slot Reset (Optional Cron Job)

To reset slots daily, schedule the script using a cron job or Task Scheduler:

```bash
python "3)Resetting_slot.py"
```

---

## 🌐 Future Enhancements

- Deep learning-based symptom classification  
- Support for multiple specializations and departments  
- Voice-based prescription management  
- Multilingual interface for wider accessibility  

---

## 🙌 Acknowledgments

Thanks to open-source communities and tools including Google API, Flask, MongoDB, SpeechRecognition, gTTS, and more for enabling this project.
