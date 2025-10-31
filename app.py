from flask import Flask, request, jsonify, render_template
import os
import requests
import fitz  # PyMuPDF
import re

app = Flask(__name__)

# ================================
# CONFIGURACIÓN IA GRATUITA
# ================================
OLLAMA_API_URL = "https://api.deepinfra.com/v1/openai/chat/completions"
# Alternativas gratuitas: Hugging Face, OpenRouter, etc.

def extraer_texto_relevante(pregunta, texto_completo):
    """Extrae las partes más relevantes del PDF para la pregunta"""
    # Buscar párrafos que contengan palabras clave de la pregunta
    palabras_clave = set(re.findall(r'\b[a-záéíóúñ]{4,}\b', pregunta.lower()))
    
    parrafos = texto_completo.split('\n\n')
    parrafos_relevantes = []
    
    for parrafo in parrafos:
        parrafo_limpio = parrafo.lower()
        coincidencias = sum(1 for palabra in palabras_clave if palabra in parrafo_limpio)
        if coincidencias > 0:
            parrafos_relevantes.append((coincidencias, parrafo))
    
    # Ordenar por relevancia y tomar los más importantes
    parrafos_relevantes.sort(reverse=True, key=lambda x: x[0])
    contexto = "\n\n".join([p[1] for p in parrafos_relevantes[:3]])  # Top 3 párrafos
    
    return contexto[:3000]  # Limitar tamaño para la IA

def consultar_ia(pregunta, contexto):
    """Consulta un modelo de IA gratuito"""
    try:
        # Usar DeepInfra (gratuito con límites)
        headers = {
            "Authorization": "Bearer YOUR_API_KEY",  # Necesitarás una API key gratuita
            "Content-Type": "application/json"
        }
        
        prompt = f"""
        Eres un asistente especializado en el Sistema de Gestión Documental Digital (GDE).
        Responde la pregunta del usuario basándote ÚNICAMENTE en el siguiente contexto del manual oficial:

        CONTEXTO DEL MANUAL:
        {contexto}

        PREGUNTA DEL USUARIO:
        {pregunta}

        Responde de manera clara y concisa. Si la información no está en el contexto, di que no la tienes.
        """
        
        payload = {
            "model": "meta-llama/Meta-Llama-3-70B-Instruct",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500,
            "temperature": 0.3
        }
        
        response = requests.post(OLLAMA_API_URL, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return f"❌ Error con la IA: {response.status_code}"
            
    except Exception as e:
        return f"❌ Error consultando IA: {str(e)}"

def cargar_manual():
    """Carga y extrae texto del manual PDF"""
    try:
        for archivo in os.listdir("documents"):
            if archivo.lower().endswith('.pdf'):
                ruta_pdf = os.path.join("documents", archivo)
                doc = fitz.open(ruta_pdf)
                texto_completo = ""
                
                for pagina in doc:
                    texto_completo += pagina.get_text() + "\n\n"
                
                doc.close()
                return texto_completo
        return None
    except Exception as e:
        print(f"Error cargando PDF: {e}")
        return None

# Cargar el manual al iniciar (una sola vez)
MANUAL_COMPLETO = cargar_manual()

def procesar_con_ia(pregunta):
    """Procesa la pregunta usando IA con el manual"""
    pregunta = pregunta.strip()
    
    # 🚨 Una sola palabra = No entiendo
    if len(pregunta.split()) <= 1:
        return "❌ No entiendo la pregunta. Por favor haz una pregunta completa como: '¿Cómo ingreso al sistema?'"
    
    # Respuestas rápidas para conversación (sin IA)
    if any(saludo in pregunta.lower() for saludo in ['hola', 'buenos días', 'buenas tardes']):
        return "¡Hola! 👋 Soy tu asistente IA del Sistema GDE. ¿En qué puedo ayudarte?"
    
    if 'cómo estás' in pregunta.lower():
        return "¡Perfecto! 😊 Listo para analizar el manual y ayudarte."
    
    if 'gracias' in pregunta.lower():
        return "¡De nada! 😊 ¿Necesitas más información?"
    
    # Si no hay manual cargado
    if not MANUAL_COMPLETO:
        return "❌ No se pudo cargar el manual. Verifica que el PDF esté en la carpeta 'documents/'."
    
    # Extraer contexto relevante del manual
    contexto = extraer_texto_relevante(pregunta, MANUAL_COMPLETO)
    
    if not contexto:
        return "🔍 No encontré información relevante en el manual para tu pregunta. ¿Podrías reformularla?"
    
    # Consultar a la IA
    print(f"🔍 Buscando en el manual: {pregunta}")
    respuesta_ia = consultar_ia(pregunta, contexto)
    
    return respuesta_ia

# ================================
# RUTAS PRINCIPALES
# ================================
@app.route('/')
def home():
    return render_template('chat.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        pregunta = data.get('prompt', '').strip()
        
        if not pregunta:
            return jsonify({'success': False, 'error': 'Por favor escribe una pregunta'})
        
        respuesta = procesar_con_ia(pregunta)
        return jsonify({'success': True, 'response': respuesta})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error: {str(e)}'})

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'manual_cargado': MANUAL_COMPLETO is not None})

# ================================
# INICIALIZACIÓN
# ================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    if MANUAL_COMPLETO:
        print("✅ Manual cargado correctamente")
        print(f"📖 Tamaño del manual: {len(MANUAL_COMPLETO)} caracteres")
    else:
        print("❌ No se pudo cargar el manual")
    
    print(f"🚀 ChatBot IA iniciado en puerto {port}")
    app.run(host='0.0.0.0', port=port, debug=False)