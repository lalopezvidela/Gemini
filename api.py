import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=API_KEY)

# Inicializar modelos
model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-06-17')
##vision_model = genai.GenerativeModel('gemini-pro-vision')
