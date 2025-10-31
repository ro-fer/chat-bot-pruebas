from flask import Flask, request, jsonify, render_template
import os
import re
from docx import Document

app = Flask(__name__)

# ================================
# CONFIGURACIÓN
# ================================
DOCUMENTS_DIR = "documents"

# ================================
# PROCESADOR DE DOCX
# ================================
def procesar_docx(ruta_archivo):
    """Extrae texto de archivos DOCX"""
    try:
        doc = Document(ruta_archivo)
        texto_completo = ""
        
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                texto_completo += paragraph.text + "\n\n"
        
        return texto_completo.strip()
    except Exception as e:
        return f"❌ Error procesando DOCX: {str(e)}"

def cargar_documentos_docx():
    """Carga todos los archivos DOCX de la carpeta"""
    documentos = {}
    
    if not os.path.exists(DOCUMENTS_DIR):
        os.makedirs(DOCUMENTS_DIR)
        return documentos
    
    for archivo in os.listdir(DOCUMENTS_DIR):
        if archivo.lower().endswith('.docx'):
            ruta_archivo = os.path.join(DOCUMENTS_DIR, archivo)
            texto = procesar_docx(ruta_archivo)
            
            if texto and not texto.startswith("❌ Error"):
                documentos[archivo] = texto
    
    return documentos

# ================================
# PROCESADOR DE PREGUNTAS MEJORADO
# ================================
def es_pregunta_meta(pregunta):
    """Detecta si es una pregunta sobre el chatbot"""
    pregunta_limpia = pregunta.lower().strip()
    
    preguntas_meta = [
        'quién eres', 'qué eres', 'quien eres', 'que eres',
        'qué puedes', 'qué sabes', 'qué haces', 'para qué sirves',
        'qué preguntar', 'qué puedo preguntar', 'preguntas posibles',
        'cuántos documentos', 'qué documentos', 'documentos cargados',
        'cómo funcionas', 'qué puedes hacer'
    ]
    
    return any(meta in pregunta_limpia for meta in preguntas_meta)

def responder_pregunta_meta(pregunta, documentos):
    """Responde preguntas sobre el chatbot"""
    pregunta_limpia = pregunta.lower().strip()
    documentos_lista = list(documentos.keys())
    
    if 'quién eres' in pregunta_limpia or 'qué eres' in pregunta_limpia:
        return "🤖 **¡Hola! Soy tu asistente inteligente**\n\nPuedo leer y buscar información en tus documentos DOCX. Estoy aquí para ayudarte a encontrar rápidamente la información que necesitas."
    
    elif 'qué puedes' in pregunta_limpia or 'qué haces' in pregunta_limpia:
        return f"🔍 **Puedo ayudarte a:**\n\n• Buscar información en tus documentos\n• Encontrar procedimientos específicos\n• Localizar datos técnicos\n• Explicar conceptos del manual\n\n📂 **Documentos cargados:** {len(documentos_lista)}\n💡 **Solo necesito preguntas completas**"
    
    elif 'qué preguntar' in pregunta_limpia or 'preguntas posibles' in pregunta_limpia:
        ejemplos = [
            "¿Cómo ingreso al sistema?",
            "¿Qué es la firma digital?",
            "¿Cómo gestiono una licencia?",
            "¿Dónde encuentro soporte técnico?",
            "¿Qué son los datos personales?"
        ]
        ejemplos_texto = "\n".join([f"• {ej}" for ej in ejemplos])
        return f"❓ **Ejemplos de preguntas:**\n\n{ejemplos_texto}\n\n💡 **Consejo:** Haz preguntas completas en lugar de palabras sueltas."
    
    elif 'documentos' in pregunta_limpia:
        return f"📂 **Documentos cargados ({len(documentos_lista)}):**\n\n" + "\n".join([f"• {doc}" for doc in documentos_lista])
    
    else:
        return "🤖 Soy tu asistente para buscar información en documentos DOCX. ¿En qué puedo ayudarte?"

def buscar_en_documentos(pregunta, documentos):
    """Busca en documentos solo si NO es pregunta meta"""
    # Si es pregunta meta, no buscar en documentos
    if es_pregunta_meta(pregunta):
        return None
    
    pregunta_limpia = pregunta.lower().strip()
    
    # 🚨 Una sola palabra = No entiendo
    if len(pregunta_limpia.split()) <= 1:
        return "❌ No entiendo. Por favor haz una pregunta completa como: '¿Cómo ingreso al sistema?'"
    
    palabras_clave = set(re.findall(r'\b[a-záéíóúñ]{4,}\b', pregunta_limpia))
    palabras_filtro = {'sobre', 'como', 'que', 'donde', 'puedo', 'preguntar'}
    palabras_clave = {p for p in palabras_clave if p not in palabras_filtro}
    
    if not palabras_clave:
        return "🤔 ¿Podrías ser más específico? Por ejemplo: '¿Cómo ingreso al sistema?'"
    
    resultados = []
    
    for doc_nombre, contenido in documentos.items():
        parrafos = contenido.split('\n\n')
        
        for parrafo in parrafos:
            if len(parrafo.strip()) < 30:
                continue
                
            parrafo_lower = parrafo.lower()
            coincidencias = sum(1 for palabra in palabras_clave if palabra in parrafo_lower)
            
            if coincidencias > 0:
                if len(parrafo) > 400:
                    parrafo = parrafo[:400] + "..."
                
                resultados.append({
                    'documento': doc_nombre,
                    'contenido': parrafo.strip(),
                    'relevancia': coincidencias
                })
                break
    
    resultados.sort(key=lambda x: x['relevancia'], reverse=True)
    
    if resultados:
        respuesta = f"🔍 **Encontré esto sobre '{pregunta}':**\n\n"
        for i, resultado in enumerate(resultados[:2]):
            respuesta += f"📄 **{resultado['documento']}:**\n{resultado['contenido']}\n\n"
            if i < len(resultados) - 1:
                respuesta += "---\n\n"
        return respuesta
    else:
        return f"🤔 No encontré información específica sobre '{pregunta}'."

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
        
        # Cargar documentos
        documentos = cargar_documentos_docx()
        
        if not documentos:
            return jsonify({
                'success': True,
                'response': "📂 No hay archivos DOCX en la carpeta 'documents/'."
            })
        
        # Respuestas rápidas
        pregunta_lower = pregunta.lower()
        
        if any(saludo in pregunta_lower for saludo in ['hola', 'buenos días', 'buenas tardes']):
            return jsonify({
                'success': True,
                'response': f"¡Hola! 👋 Soy tu asistente. Tengo {len(documentos)} documento(s) cargados. ¿En qué puedo ayudarte?"
            })
        
        if 'cómo estás' in pregunta_lower:
            return jsonify({
                'success': True, 
                'response': "¡Perfecto! 😊 Listo para ayudarte."
            })
        
        if 'gracias' in pregunta_lower:
            return jsonify({
                'success': True,
                'response': "¡De nada! 😊"
            })
        
        # 🎯 PRIMERO verificar si es pregunta meta
        if es_pregunta_meta(pregunta):
            respuesta = responder_pregunta_meta(pregunta, documentos)
            return jsonify({'success': True, 'response': respuesta})
        
        # Si NO es pregunta meta, buscar en documentos
        respuesta = buscar_en_documentos(pregunta, documentos)
        return jsonify({'success': True, 'response': respuesta})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error: {str(e)}'})

# ================================
# INICIALIZACIÓN
# ================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 ChatBot iniciado en puerto {port}")
    app.run(host='0.0.0.0', port=port, debug=False)