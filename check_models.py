import google.generativeai as genai

api_key = ""

genai.configure(api_key=api_key)

try:
    models = genai.list_models()
    print("Available models and supported methods:")
    for model in models:
        print(f"- {model.name}: {model.supported_generation_methods}")
except Exception as e:
    print(f"Error listing models: {e}")