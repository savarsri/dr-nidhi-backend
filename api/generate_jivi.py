from django.conf import settings
from openai import OpenAI

client = OpenAI(api_key=settings.GPT_KEY)

grok_client = OpenAI(
  api_key=settings.GROK_KEY,
  base_url=settings.GROK_URL,
)

def send_to_jivi(system_prompt, user_prompt, images=None):
    """
    Sends the generated prompt to OpenAI's ChatGPT API and retrieves the response.
    """
    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        if images:
            for image in images:
                image_message = {"role": "user", "content": {"type": "image_url", "image_url": image["image_url"]}}
                if "description" in image:
                    messages.append({"role": "user", "content": image["description"]})
                messages.append(image_message)

        completion = client.chat.completions.create(
            model=settings.GPT_MODEL,
            messages=messages,
            stream=False
        )

        if not completion.choices or not completion.choices[0].message or not completion.choices[0].message.content:
            raise ValueError("Invalid response received from OpenAI API.")

        return completion.choices[0].message.content

    except Exception as e:
        raise RuntimeError(f"ChatGPT API error: {str(e)}")

def send_to_grok(user_prompt, images=None):
    """
    Sends the generated prompt along with optional images to Grok 3 API built by xAI.
    
    Args:
        user_prompt (str): The text prompt from the user
        images (dict, optional): Dictionary of category:image_url pairs
        
    Returns:
        str: Grok's response content
        
    Raises:
        ValueError: If input parameters are invalid
        RuntimeError: If API call fails
    """
    try:
        # Input validation
        if not isinstance(user_prompt, str) or not user_prompt.strip():
            raise ValueError("User prompt must be a non-empty string")
            
        if images is not None and not isinstance(images, dict):
            raise ValueError("Images must be provided as a dictionary")

        # Initialize messages list with proper structure
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": user_prompt
                    }
                ]
            }
        ]

        # Attach images if provided
        if images:
            for category, image_url in images.items():
                if not isinstance(image_url, str) or not image_url.strip():
                    raise ValueError(f"Invalid image URL for category {category}")
                    
                messages[0]["content"].append({
                    "type": "image_url",
                    "image_url": {
                        "url": image_url,
                        "detail": "auto"  # Optional: can be "low", "high", or "auto"
                    }
                })

        # Call Grok API (assuming grok_client is properly initialized elsewhere)
        completion = grok_client.chat.completions.create(
            model=settings.GROK_MODEL,  # Updated to match current version
            messages=messages,
            stream=False,
        )

        # Validate response structure
        if not hasattr(completion, 'choices') or not completion.choices:
            raise ValueError("No choices received in API response")
            
        if not hasattr(completion.choices[0], 'message') or not completion.choices[0].message:
            raise ValueError("No message in API response")
            
        if not hasattr(completion.choices[0].message, 'content') or not completion.choices[0].message.content:
            raise ValueError("No content in API response")

        return completion.choices[0].message.content.strip()

    except ValueError as ve:
        raise ValueError(f"Validation error: {str(ve)}")
    except AttributeError as ae:
        raise RuntimeError(f"Unexpected API response structure: {str(ae)}")
    except Exception as e:
        raise RuntimeError(f"Grok API error: {str(e)}")
