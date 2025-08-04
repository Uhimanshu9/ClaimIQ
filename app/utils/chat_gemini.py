

import os
from google import genai
from google.genai import types

# Secure API key handling
def chat_gemini(image_path: str) -> str:

    client = genai.Client(api_key="AIzaSyALKw7su4WoLec6v-4vEHponzPHMUCcWpQ")

    with open(image_path, 'rb') as f:
        image_bytes = f.read()

    # Comprehensive data extraction prompt
    extraction_prompt = """
    Extract ALL data from this image including:
    1. All readable text content
    2. Tables and structured data
    3. Numbers, measurements, statistics
    4. Charts/graphs and their data points
    5. Dates, contact information, addresses
    6. Mathematical formulas or equations
    7. Visual elements descriptions

    Organize the output with clear sections for each type of data found.
    """

    response = client.models.generate_content(
        model='gemini-2.0-flash-exp',
        contents=[
            types.Part.from_bytes(
                data=image_bytes,
                mime_type='image/jpg',
            ),
            extraction_prompt
        ]
    )

    return response.text
