import requests

def generate_prompt(patient_data, sensor_data):
    return f"""
    A {patient_data['age']}-year-old {patient_data['gender']} patient presents to a rural clinic with complaints of {patient_data['symptoms']}.
    Your diagnostic device records the following parameters in real time:

    Input Data from Sensors
    Parameter        Value        Normal Range
    NH3 (Ammonia)    {sensor_data['nh3']} µg/dL    15-45 µg/dL
    CO (Carbon Monoxide)    {sensor_data['co']} ppm    <9 ppm
    O2 (Oxygen Level)    {sensor_data['o2']} mmHg    75-100 mmHg
    CO2 (Carbon Dioxide)    {sensor_data['co2']} mmHg    35-45 mmHg
    SpO2    {sensor_data['spo2']}%    >95%
    Heart Rate    {sensor_data['heart_rate']} bpm    60-100 bpm

    Suggest the most comprehensive diagnosis along with organ impact.
    """

def send_to_grok_ai(prompt, medication_type):
    grok_ai_endpoint = "https://api.x.ai/v1/chat/completions"
    api_key = "xai-VbNaEN6CwvpioKVa0dmlCVZWhe4mlpDqP4yGuTcpE3xnlqL0IV2I4Jx33x2vtTX5OyNMRDDZgscD3jTG"

    try:
        response = requests.post(
            grok_ai_endpoint,
            json={"model": "grok-2-1212", "messages": [
                {
                    "role": "user", 
                    "content": prompt
                },
                {
                    "role": "user",
                    "content": '''give at last the executive summary of all'''
                },
                {
                    "role": "user",
                    "content": f'''Treatments and medicines in {medication_type}'''
                },

                ]
            },
            headers={"Authorization": f"Bearer {api_key}"}
        )
        response_data = response.json()
        return response_data.get('choices', [])[0].get('message', {}).get('content', "")
        # return response_data.choices[0].message
    except Exception as e:
        return {"error": str(e)}
