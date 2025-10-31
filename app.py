from flask import Flask, request, jsonify, render_template
import os
import pdfplumber
import re

app = Flask(__name__)

# ================================
# CONFIGURACIÓN
# ================================
DOCUMENTS_DIR = "documents"
PROCESSED_DIR = "processed_data"
os.makedirs(DOCUMENTS_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

def buscar_respuesta_simple(pregunta):
    """Busca respuestas solo para preguntas completas"""
    pregunta_limpia = pregunta.lower().strip()
    
    # 🚨 DETECTAR PALABRAS SUELTAS
    palabras = pregunta_limpia.split()
    if len(palabras) <= 1:
        return "❌ No entiendo la pregunta. Por favor, haz una pregunta completa como: '¿Cómo ingreso al sistema?'"
    
    # Respuestas rápidas para conversación
    if re.search(r'hola|buen(os|as)', pregunta_limpia):
        return "¡Hola! 👋 Soy tu asistente del Manual de Escritorio Único. ¿En qué puedo ayudarte?"
    
    if re.search(r'como estas|qué tal', pregunta_limpia):
        return "¡Perfecto! 😊 Listo para ayudarte con el Sistema GDE."
    
    if re.search(r'gracias', pregunta_limpia):
        return "¡De nada! 😊 ¿Necesitas ayuda con algo más?"
    
    # Si es una pregunta completa, buscar en el manual
    try:
        for archivo_pdf in os.listdir(DOCUMENTS_DIR):
            if archivo_pdf.lower().endswith('.pdf'):
                ruta_pdf = os.path.join(DOCUMENTS_DIR, archivo_pdf)
                texto = extraer_texto_pdf(ruta_pdf)
                
                if texto:
                    # Buscar párrafos relevantes
                    parrafos = [p.strip() for p in texto.split('\n\n') if len(p.strip()) > 50]
                    
                    for parrafo in parrafos:
                        # Verificar si el párrafo contiene palabras de la pregunta
                        palabras_pregunta = set(palabras)
                        palabras_parrafo = set(re.findall(r'\b[a-záéíóúñ]+\b', parrafo.lower()))
                        
                        coincidencias = palabras_pregunta.intersection(palabras_parrafo)
                        if len(coincidencias) >= 2:  # Mínimo 2 palabras coincidentes
                            # Acortar si es muy largo
                            if len(parrafo) > 300:
                                parrafo = parrafo[:300] + "..."
                            return f"📄 **Manual GDE**:\n{parrafo}"
        
        # Si no encontró nada
        return f"🔍 No encontré información específica sobre '{pregunta}'.\n\n💡 **Ejemplos de preguntas:**\n• ¿Cómo ingreso al sistema?\n• ¿Qué son los datos personales?\n• ¿Cómo gestiono una licencia?"
        
    except Exception as e:
        return f"❌ Error buscando en el manual: {str(e)}"

def extraer_texto_pdf(ruta_pdf):
    """Extrae texto básico del PDF"""
    try:
        texto = ""
        with pdfplumber.open(ruta_pdf) as pdf:
            for pagina in pdf.pages:
                texto_pagina = pagina.extract_text()
                if texto_pagina:
                    texto += texto_pagina + "\n\n"
        return texto.strip() if texto else ""
    except Exception as e:
        print(f"Error procesando PDF: {e}")
        return ""

# ================================
# RUTAS PRINCIPALES
# ================================
@app.route('/')
def index():
    return render_template('chat.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    pregunta = data.get("prompt", "")
    
    if not pregunta.strip():
        return jsonify({"success": False, "error": "Por favor escribe una pregunta"})

    try:
        respuesta = buscar_respuesta_simple(pregunta)
        return jsonify({"success": True, "response": respuesta})
        
    except Exception as e:
        return jsonify({"success": False, "error": f"Error: {str(e)}"})

# ================================
# INICIALIZACIÓN
# ================================
print("🚀 Iniciando ChatBot GDE - Modo Simple...")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)