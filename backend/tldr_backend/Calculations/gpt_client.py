import os
from openai import OpenAI
from django.conf import settings
from .models import cvImage

class GPTClient:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def get_response(self, text):
        prompt = (
            "Please analyze this text from an image and provide a clear summary: \n\n"
            f"{text}"
        )
        
        try:
            response = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model="gpt-3.5-turbo",
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"GPT Error: {str(e)}")
            return f"Error processing text: {str(e)}"