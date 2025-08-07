from ..db.collections.files import files_collection
from bson import ObjectId
import os
from pdf2image import convert_from_path
from google import genai
from google.genai import types

# Configure Gemini client
client = genai.Client(api_key="AIzaSyALKw7su4WoLec6v-4vEHponzPHMUCcWpQ")


async def process_file(id: str, file_path: str):
    await files_collection.update_one({"_id": ObjectId(id)}, {
        "$set": {
            "status": "processing"
        }
    })

    await files_collection.update_one({"_id": ObjectId(id)}, {
        "$set": {
            "status": "converting to images"
        }
    })

    # Step 1: Convert the PDF to Images
    pages = convert_from_path(file_path)
    images = []

    for i, page in enumerate(pages):
        image_save_path = f"/mnt/uploads/images/{id}/image-{i}.jpg"
        os.makedirs(os.path.dirname(image_save_path), exist_ok=True)
        page.save(image_save_path, 'JPEG')
        images.append(image_save_path)

    await files_collection.update_one({"_id": ObjectId(id)}, {
        "$set": {
            "status": "converting to images success"
        }
    })

    # Step 2: Process with Gemini using new SDK
    try:
        # Read the first image as bytes
        with open(images[0], 'rb') as f:
            image_bytes = f.read()

        # Resume roasting prompt
        roast_prompt = """
        Based on the resume below, Roast this resume. Be witty,
        constructive, and point out:
        1. Formatting issues and design problems
        2. Content gaps or weaknesses
        3. Overused buzzwords or clichés
        4. Missing important information
        5. Areas for improvement
        Make it entertaining but helpful for the candidate 
        to improve their resume.
        """

        # Generate content using the new SDK
        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=[
                types.Part.from_bytes(
                    data=image_bytes,
                    mime_type='image/jpeg', 
                ),
                roast_prompt
            ]
        )
        
        # Update database with results
        await files_collection.update_one({"_id": ObjectId(id)}, {
            "$set": {
                "status": "processed",
                "result": response.text
            }
        })
        
    except Exception as e:
        # Handle errors
        await files_collection.update_one({"_id": ObjectId(id)}, {
            "$set": {
                "status": "error",
                "error": str(e)
            }
        })
        raise e

    # queue: Email Queue - Your file is ready


# rq worker --with-scheduler --url redis://valkey:6379
