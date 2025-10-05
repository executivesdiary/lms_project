# executive_biographer/openai_utils.py
from openai import OpenAI
from django.conf import settings

def generate_biography_from_profile(prompt_text):
    try:
        # ✅ Correct way to initialize OpenAI client in v1.76.2
        client = OpenAI(api_key=settings.OPENAI_API_KEY)

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a professional executive biographer at Executives Diary. "
                        "Write polished, compelling, and structured biographies based on resume data, LinkedIn profiles, and internal comments. "
                        "Always maintain a respectful and inspiring tone, suitable for high-level professionals being featured in a digital magazine."
                    )
                },
                {"role": "user", "content": prompt_text},
            ],
            temperature=0.7,
            max_tokens=1000,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"❌ Error generating biography: {str(e)}"
