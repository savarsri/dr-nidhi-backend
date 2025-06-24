def generate_base_prompt(patient_data, sensor_data):
    """
    Generates a structured prompt for real-time patient monitoring.
    Ignores any sensor data fields that are None or not provided.
    """
    # Get patient data with defaults in case a field is None
    name = patient_data.get('patientName', 'N/A')
    age = patient_data.get('age', 'N/A')
    gender = patient_data.get('gender', 'N/A')
    symptoms = patient_data.get('symptoms', 'N/A')
    medical_history = patient_data.get('medicalHistory', 'N/A')
    notes = patient_data.get('notes', 'N/A')
    
    # Define sensor parameters and units
    sensor_parameters = [
        ("NH3 (Ammonia)", sensor_data.get("nh3"), "ppm"),
        ("CO (Carbon Monoxide)", sensor_data.get("co"), "ppm"),
        ("O2 (Oxygen Level)", sensor_data.get("o2"), "%Vol"),
        ("CO2 (Carbon Dioxide)", sensor_data.get("co2"), "ppm"),
        ("SpO2", sensor_data.get("spo2"), "%"),
        ("Heart Rate", sensor_data.get("heart_rate"), "bpm"),
        ("Respiratory Quotient (RQ)", sensor_data.get("rq"), ""),
        ("Hydrogen (H2)", sensor_data.get("hydrogen"), ""),
        ("Formaldehyde", sensor_data.get("formaldehyde"), "")
    ]
    
    # Build table rows only for sensor values that are not None
    sensor_rows = ""
    for param, value, unit in sensor_parameters:
        if value is not None:
            space = " " if unit else ""
            sensor_rows += f"| {param} | {value}{space}{unit} |\n"
    
    base_prompt = f"""
### Real-Time Patient Monitoring Report
**Patient Info:**  
- Name: {name}  
- Age: {age}  
- Gender: {gender}
- Symptoms: {symptoms}    
- Medical History: {medical_history}  
- Doctor Notes: {notes}
**Vital Signs & Sensor Data:**  
| Parameter                | Value |
|--------------------------|-------|
{sensor_rows}
Normal Range:
● Carbon Monoxide (CO): 0.0 to 10 ppm
● Carbon Dioxide (CO2): 20,000 to 50,000 ppm
● Oxygen Level (O2): 13% to 18%
● Ammonia (NH3): 0.0 to 2 ppm
● Blood Oxygen Saturation (SpO2): Greater than 85%
● Heart Rate (BPM): 60 to 100 beats per minute
● Respiratory Quotient (RQ): 0.7 to 1.0
● Hydrogen (H2): 0.0 to 16 ppm
● Formaldehyde: 0.0 to 16 ppm
    """
            
    return base_prompt

def generate_medication_prompt(base, medication_type):
    medication_prompt = f"""
            {base}

            **Treatment Modalities:**
            (Treatment options based on the requested modality: {medication_type})
            Medication type selected by doctor: {medication_type}
            Please give treatment based on only medication type selected by the doctor.

            * Based on evidence-based guidelines, suggest **treatments, medications, and interventions**. 
            
            Cite sources or guidelines when giving Allopathy-based suggestions (e.g., IDSA, AHA, WHO protocols).

            Depending upon the user input put share one of the following:-
            **(A) Allopathy** 
            - Medications: [Dosage & Duration] 
            - ICU/ER Interventions: [Ventilation, dialysis, surgery] 
            - Supportive Care: [Pain management, physiotherapy] 
            
            **(B) Homeopathy** 
            - Remedy 1: [E.g., Nux Vomica for digestion, Arsenicum Album for weakness] 
            - Remedy 2: [E.g., Lycopodium for bloating, Belladonna for fever] 
            
            **(C) Ayurveda** 
            - Herbs: [E.g., Bhumi Amla for liver, Hing for digestion] 
            - Detox Therapies: [Panchakarma, Nasya] 
            - Lifestyle: [Meditation, Pranayama] 

            Please note:- 
            Ensure Homeopathic or Ayurvedic recommendations include dosage, frequency and contraindications.
            Outline medications, dosages, and supportive therapies (if known/available).
            Please note chatgpt: Don't share sensor value of sensor or range in the output. Simply tell the analysis.

        """
    
    return medication_prompt

def generate_insights_prompt(base):

    prompt = f"""
        {base}

        - **Predicted 24-hour Mortality Risk:** [XX%] 
        - **Ventilator Weaning Probability:** [XX%] 
        - **Recovery Time Estimate:** [XX Days] 
        Please note chatgpt: Don't share sensor value of sensor or range in the output. Simply tell the analysis.
    """

    return prompt

def generate_summary_prompt(base):
    prompt = f"""
        {base}
        
        * Present a very short and concise case summary **overview of findings, urgency level, and suggested next steps**. 
        Please note chatgpt: Don't share sensor value of sensor or range in the output. Simply tell the analysis.
    """

    return prompt

def generate_actions_prompt(base):
    prompt = f"""
        {base}

        Share the analysis in paragraph form
        1. **Clinical Management:** [Adjust oxygen, fluids, drugs, etc.] 
        2. **Monitoring:** [ABG, imaging, vitals repeat schedule] 
        3. **Lifestyle Changes:** [Dietary & exercise recommendations] 
        Please note chatgpt: Don't share sensor value of sensor or range in the output. Simply tell the analysis.

    """

    return prompt

def generate_organ_prompt(base):
    prompt = f"""
        {base}

        Provide a **comprehensive diagnosis** with impact on all the organs one by one. Discuss potential organ system impacts for liver, Cardiovascular, renal, respiratory and nervous.
        How much is the risk of being diabetic for this patient.  
        * Suggest **potential diseases** based on symptoms & sensor data. 

        Add a special note recommendation in case the patient is diabetic.

        Please note chatgpt: Don't share sensor value of sensor or range in the output. Simply tell the analysis.
    """

    return prompt

def generate_initial_prompt(base):
    prompt = f"""
        {base}

        This is Respiratory Quotient (RQ). Please do analysis of Respiratory Quotient. 
        Please note chatgpt: Don't share sensor value of sensor or range in the output. Simply tell the analysis. 
    """

    return prompt

def generate_alerts_prompt(base):
    prompt = f"""
        {base}

        **[Brief description in paragraph about Condition Alert]** 
        **[Brief description in paragraph about Critical Value Alert]** 
        Please note chatgpt: Don't share sensor value of sensor or range in the output. Simply tell the analysis.
    """

    return prompt

def generate_analysis_prompt(base):
    prompt = f"""
        {base}
        
        * **Assess patient's respiratory and metabolic status** based on real-time sensor readings. 
        * **Detect early warning signs** of toxicity, hypoxia, or metabolic disorders. 
        * **Predict potential organ dysfunction** based on sensor and vital sign trends. 
        Please note chatgpt: Don't share sensor value of sensor or range in the output. Simply tell the analysis.
        
    """

    return prompt

def generate_diagnosis_prompt(base):
    prompt = f"""
        {base}
        
        Real-Time Patient Monitoring
        Continuously analyze and interpret vital signs, lab results, imaging, and patient-reported symptoms.
        Detect early signs of deterioration or improvement.
        Generate timely alerts for critical parameters (e.g., sepsis risk, respiratory failure, hypotension).a
        Please note chatgpt: Don't share sensor value of sensor or range in the output. Simply tell the analysis.

    """

    return prompt

def grok_image_prompt(base):
    prompt = f"""
    {base}
    - When the user shares an **MRI, CT, X-ray, or Ultrasound attachment**, generate a **separate structured analysis**: 
    1. **Imaging Type** (MRI, CT, Ultrasound, X-ray) 
    2. **Key Observations** (e.g., tumor presence, fractures, hemorrhage, fluid accumulation) 
    3. **Preliminary Interpretation** (without replacing radiologist evaluation) 
    4. **Clinical Relevance** (How findings correlate with symptoms and lab values) 
    5. **Suggested Follow-Up** (Need for biopsy, specialist referral, repeat scan)
    Please note:-
    All the sensor data is the human exhales breath reading using CO, CO2, O2 and NH3 sensors and also consider Respiratory Quotient, SpO2 and Heart rate. Share the analysis on the basis of the above 7 sensor data.
    Please note grok: Don't share sensor value of sensor or range in the output. Simply tell the analysis.
    """
    return prompt

def generate_system_prompt():
    prompt = f"""
        You are a Medical AI specializing in real-time patient monitoring, diagnosis, prognosis, and treatment recommendation. You are optimized for Indian clinical conditions, diagnostic standards, and medical practices. You assist healthcare professionals by analyzing multimodal patient data including sensor inputs, vital signs, lab investigations, clinical notes, and imaging findings. All assessments must follow evidence-based medical reasoning, prioritize patient safety, and adhere to ethical and regulatory norms applicable in India.

        You must follow the specified normal ranges and sensor calibration standards strictly, as defined below. These values are validated for use in Indian test environments and are to be treated as the only acceptable reference for interpretation.

        Ethical and Legal Compliance:
        ● Always include a disclaimer that AI-generated output is not a substitute for professional medical judgment.
        ● Emphasize the necessity of clinical correlation and referral to qualified physicians or specialists where appropriate.
        ● Ensure complete confidentiality of patient data and compliance with Indian data privacy laws and ethical guidelines.
        ● Follow best practices as per National Medical Commission (NMC) and Central Drugs Standard Control Organisation (CDSCO).

        Input Guidelines:
        You accept the following multimodal inputs:

        1. Vital Signs and Sensor Data from exhaled breath and wearable sensors. Strictly use the following normal ranges for interpretation. Do not refer to general physiological ranges. These ranges are calibrated specifically for the device and environment:
        ● Carbon Monoxide (CO): 0 to 10 ppm
        ● Carbon Dioxide (CO2): 20,000 to 50,000 ppm
        ● Oxygen Level (O2): 13% to 16%
        ● Ammonia (NH3): 0 to 1.5 ppm
        ● Hydrogen (H2): 0 to 16 ppm
        ● Blood Oxygen Saturation (SpO2): Greater than 85%
        ● Heart Rate (BPM): 60 to 100 beats per minute
        ● Respiratory Quotient (RQ): 0.7 to 1.0

        All diagnostic interpretation must be strictly based on these ranges only. You must not deviate from these defined thresholds under any condition. These values represent the normal range for sensor data collected from the designated test area and device configuration.
        Do not display or repeat raw sensor values to the user. Only provide medical interpretation of these values.

        2. Laboratory Parameters (optional inputs): Complete Blood Count (CBC), metabolic panels, arterial blood gas (ABG), ammonia levels, lactate, troponin, liver function tests, electrolytes, etc.

        3. Imaging Data: Interpret data from X-ray, CT scan, MRI, ultrasound, sonogram, and other imaging modalities. Imaging data may be provided in DICOM format or as textual summaries. Imaging findings must be correlated with vital signs and sensor data to enhance diagnostic accuracy.

        4. Symptoms and Medical History: This includes chief complaints, symptom onset, duration, comorbidities, allergy history, medication history.

        Presentation Guidelines:
        ● All output must use a fixed font size.
        ● Ensure that the entire response is presented in a consistent font size with no variation in text size throughout the output.
    """
    return prompt

def generate_table_prompt(base):
    prompt = f"""
        {base}
        Clinical Alerts:
        Based on the sensors data and a set of metabolic or physiological test results 
        (Respiratory Quotient, Metabolic Efficiency Index, Detox Load Ratio, Oxygen Ultilization Factor, Stress Load Index), 
        identify and list any immediate or significant clinical alerts. These should be short, high-priority bullet points indicating potential health risks or red flags. 
        Do not include the values or detailed interpretation — just the alerts.
        
        Clinical Interpretation
        Interpret the following metabolic or physiological test results by providing 1–3 bullet points that explain the implications of the findings. 
        Focus on what the data suggests about metabolic efficiency, detoxification burden, oxygen usage, or stress response. 
        Do not include raw metric values or status colors — just the clinical meaning and implications.

        Suggested Actions:
        Based on metabolic or physiological test results, provide 1–3 clinically appropriate and actionable suggestions. 
        These may include further evaluations, lab tests, lifestyle changes, dietary adjustments, or referrals. 
        Avoid restating the test values — focus only on clear, evidence-based recommendations suitable for follow-up care or management.
        
        KEEP IT SHORT AND GIVE OUTPUT IN POINTS ONLY AND NOT PARAGRAPHS
        MAKE THE OUTPUT ELEGANT AND USE PROPER FORMATTING, AND DO NOT GIVE DISCLAIMER AS IT IS ALREADY SHOWN
        MAKE SURE YOU DO NOT MIX FORMATTING LIKE USING **## TOGETHER AS IN FRONTEND IT MESSES UP WITH THE PARSER
        """
    return prompt
