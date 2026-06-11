import google.generativeai as genai

# Coloque sua chave aqui para testar
genai.configure(api_key="AIzaSyCGRpk5LoL3ZOVHyFjXcqTdnHwLhNUSAL4")

print("Modelos disponíveis para sua chave:")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(f"Nome: {m.name} | Descrição: {m.description}")