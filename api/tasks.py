# tasks.py
from celery import shared_task
from django.conf import settings
import redis
from .models import LLMOutput, PatientData
from .serializer import PatientDeviceDataSerializer
from .prompt_jivi import (
    generate_system_prompt, generate_base_prompt,
    generate_diagnosis_prompt, generate_organ_prompt, generate_summary_prompt,
    generate_analysis_prompt, generate_alerts_prompt, generate_actions_prompt,
    generate_medication_prompt, generate_insights_prompt, generate_table_prompt,
    grok_image_prompt
)

from .generate_jivi import send_to_jivi, send_to_grok

REDIS_CONN = redis.Redis.from_url(settings.REDIS_URL)  # E.g. redis://localhost:6379/0

PROMPT_IDS = [2, 3, 4, 5, 6, 7, 8, 9, 10]  # Async prompts

def redis_key(output_id, prompt_id):
    return f"llm:output:{output_id}:prompt:{prompt_id}"

@shared_task
def generate_prompt_in_background(output_id, prompt_id):
    try:
        model_output = LLMOutput.objects.get(id=output_id)
        sensor_data = model_output.sensor_data
        patient = PatientData.objects.get(patient_mobile_number=model_output.patient_mobile_number)
        patient_device_data = PatientDeviceDataSerializer(sensor_data).data
        patient_data = {
            "patientName": patient.name,
            "age": patient.age,
            "gender": patient.gender,
            "symptoms": model_output.symptoms,
            "medicalHistory": model_output.history,
        }
        system_prompt = generate_system_prompt()
        base_prompt = generate_base_prompt(patient_data, patient_device_data)

        # Mark as "processing"
        REDIS_CONN.setex(redis_key(output_id, prompt_id), 300, "processing")  # Expires in 15 min

        if prompt_id == 2:
            val = send_to_jivi(system_prompt, generate_diagnosis_prompt(base_prompt))
            model_output.output_text_2 = val
        elif prompt_id == 3:
            val = send_to_jivi(system_prompt, generate_organ_prompt(base_prompt))
            model_output.output_text_3 = val
        elif prompt_id == 4:
            val = send_to_jivi(system_prompt, generate_summary_prompt(base_prompt))
            model_output.output_text_4 = val
        elif prompt_id == 5:
            val = send_to_jivi(system_prompt, generate_analysis_prompt(base_prompt))
            model_output.output_text_5 = val
        elif prompt_id == 6:
            val = send_to_jivi(system_prompt, generate_alerts_prompt(base_prompt))
            model_output.output_text_6 = val
        elif prompt_id == 7:
            val = send_to_jivi(system_prompt, generate_actions_prompt(base_prompt))
            model_output.output_text_7 = val
        elif prompt_id == 8:
            if model_output.medication_type:
                val = send_to_jivi(system_prompt, generate_medication_prompt(base_prompt, model_output.medication_type))
                model_output.output_text_8 = val
        elif prompt_id == 9:
            val = send_to_jivi(system_prompt, generate_insights_prompt(base_prompt))
            model_output.output_text_9 = val
        elif prompt_id == 10:
            if not model_output.file_urls:
                val = "No files were uploaded"
            else:
                val = send_to_grok(grok_image_prompt(base_prompt), model_output.file_urls)
            model_output.output_text_10 = val
        else:
            REDIS_CONN.setex(redis_key(output_id, prompt_id), 300, "invalid")
            return

        model_output.save()
        REDIS_CONN.setex(redis_key(output_id, prompt_id), 300, "done")  # Expire in 5min after done

    except Exception as e:
        REDIS_CONN.setex(redis_key(output_id, prompt_id), 300, f"error:{str(e)}")
