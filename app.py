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
            if paragraph.text.strip():  # Ignorar párrafos vacíos
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
            
            print(f"📖 Procesando: {archivo}")
            texto = procesar_docx(ruta_archivo)
            
            if texto and not texto.startswith("❌ Error"):
                documentos[archivo] = texto
                print(f"✅ {archivo} cargado correctamente")
            else:
                print(f"❌ Error con {archivo}: {texto}")
    
    return documentos

# ================================
# BÚSQUEDA INTELIGENTE MEJORADA
# ================================
def procesar_pregunta_meta(pregunta, documentos):
    """Procesa preguntas sobre el chatbot mismo"""
    pregunta_limpia = pregunta.lower().strip()
    documentos_lista = list(documentos.keys())
    
    # Preguntas sobre el chatbot
    if any(palabra in pregunta_limpia for palabra in ['qué puedes', 'qué sabes', 'qué haces', 'para qué sirves']):
        return f"🤖 **Soy tu asistente de documentos**\n\nPuedo ayudarte a buscar información en tus archivos DOCX.\n\n📂 **Documentos cargados:** {documentos_lista}\n\n💡 **Puedes preguntarme sobre:**\n• Contenido de los documentos\n• Temas específicos\n• Información técnica\n• Procedimientos\n\nSolo haz una pregunta completa y buscaré en los documentos."
    
    if any(palabra in pregunta_limpia for palabra in ['qué preguntar', 'qué puedo preguntar', 'preguntas posibles']):
        doc_ejemplo = documentos_lista[0] if documentos_lista else "tus documentos"
        return f"❓ **Puedes preguntarme sobre:**\n\n• '¿Qué información hay sobre [tema]?'\n• '¿Cómo funciona el sistema?'\n• '¿Qué son los datos personales?'\n• 'Explicame sobre licencias'\n• '¿Dónde encuentro soporte técnico?'\n• 'Información sobre firma digital'\n\n📄 **Documento disponible:** {doc_ejemplo}\n\nSolo necesito preguntas completas, no palabras sueltas."
    
    if any(palabra in pregunta_limpia for palabra in ['cuántos documentos', 'qué documentos', 'documentos cargados']):
        return f"📂 **Documentos cargados ({len(documentos_lista)}):**\n\n" + "\n".join([f"• {doc}" for doc in documentos_lista])
    
    if 'quién eres' in pregunta_limpia or 'qué eres' in pregunta_limpia:
        return "🤖 **Soy tu asistente inteligente**\n\nPuedo leer y buscar información en tus documentos DOCX. Solo necesito que me hagas preguntas completas para encontrar la información que buscas."
    
    # Si no es pregunta meta, devolver None para buscar en documentos
    return None

def buscar_en_documentos(pregunta, documentos):
    """Busca en todos los documentos DOCX cargados"""
    pregunta_limpia = pregunta.lower().strip()
    
    # 🚨 Una sola palabra = No entiendo
    if len(pregunta_limpia.split()) <= 1:
        return "❌ No entiendo la pregunta. Por favor haz una pregunta completa."
    
    palabras_clave = set(re.findall(r'\b[a-záéíóúñ]{4,}\b', pregunta_limpia))
    
    # Filtrar palabras muy comunes
    palabras_filtro = {'sobre', 'sobre el', 'sobre la', 'sobre los', 'sobre las', 'como', 'que', 'donde', 'puedo', 'preguntar'}
    palabras_clave = {p for p in palabras_clave if p not in palabras_filtro}
    
    if not palabras_clave:
        return "🤔 ¿Podrías ser más específico? Por ejemplo: '¿Cómo ingreso al sistema?' o '¿Qué son los datos personales?'"
    
    resultados = []
    
    for doc_nombre, contenido in documentos.items():
        contenido_lower = contenido.lower()
        
        # Buscar párrafos relevantes
        parrafos = contenido.split('\n\n')
        
        for parrafo in parrafos:
            if len(parrafo.strip()) < 30:  # Ignorar párrafos muy cortos
                continue
                
            parrafo_lower = parrafo.lower()
            coincidencias = sum(1 for palabra in palabras_clave if palabra in parrafo_lower)
            
            if coincidencias > 0:
                # Acortar si es muy largo
                if len(parrafo) > 400:
                    # Intentar cortar en oración completa
                    oraciones = parrafo.split('.')
                    parrafo_corto = ""
                    for oracion in oraciones:
                        if len(parrafo_corto + oracion) < 350:
                            parrafo_corto += oracion + '.'
                        else:
                            break
                    parrafo = parrafo_corto + ".." if parrafo_corto else parrafo[:400] + "..."
                
                resultados.append({
                    'documento': doc_nombre,
                    'contenido': parrafo.strip(),
                    'relevancia': coincidencias
                })
                break  # Solo un párrafo por documento
    
    # Ordenar por relevancia
    resultados.sort(key=lambda x: x['relevancia'], reverse=True)
    
    if resultados:
        respuesta = f"🔍 **Encontré esto sobre '{pregunta}':**\n\n"
        
        for i, resultado in enumerate(resultados[:2]):  # Máximo 2 resultados
            respuesta += f"📄 **{resultado['documento']}:**\n{resultado['contenido']}\n\n"
            
            if i < len(resultados) - 1:
                respuesta += "---\n\n"
        
        return respuesta
    else:
        return f"🤔 No encontré información específica sobre '{pregunta}'.\n\n💡 **Sugerencias:**\n• '¿Cómo funciona el sistema?'\n• 'Información sobre licencias'\n• '¿Qué son los datos personales?'"

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
        
        # Cargar documentos DOCX
        documentos = cargar_documentos_docx()
        
        if not documentos:
            return jsonify({
                'success': True,
                'response': "📂 No hay archivos DOCX en la carpeta 'documents/'.\n\n💡 Sube tus archivos .docx a la carpeta 'documents/' para que pueda leerlos."
            })
        
        # Respuestas rápidas para conversación
        pregunta_lower = pregunta.lower()
        
        if any(saludo in pregunta_lower for saludo in ['hola', 'buenos días', 'buenas tardes']):
            return jsonify({
                'success': True,
                'response': f"¡Hola! 👋 Soy tu asistente. Tengo {len(documentos)} documento(s) DOCX cargados. ¿En qué puedo ayudarte?"
            })
        
        if 'cómo estás' in pregunta_lower:
            return jsonify({
                'success': True, 
                'response': "¡Perfecto! 😊 Listo para buscar en tus documentos DOCX."
            })
        
        if 'gracias' in pregunta_lower:
            return jsonify({
                'success': True,
                'response': "¡De nada! 😊 ¿Necesitas buscar algo más en los documentos?"
            })
        
        # Primero verificar si es pregunta sobre el chatbot
        respuesta_meta = procesar_pregunta_meta(pregunta, documentos)
        if respuesta_meta:
            return jsonify({'success': True, 'response': respuesta_meta})
        
        # Si no es pregunta meta, buscar en documentos
        respuesta_docs = buscar_en_documentos(pregunta, documentos)
        return jsonify({'success': True, 'response': respuesta_docs})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error: {str(e)}'})

# ================================
# INICIALIZACIÓN
# ================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    print("🚀 ChatBot DOCX Mejorado iniciado")
    print("📂 Buscando archivos DOCX...")
    
    documentos = cargar_documentos_docx()
    
    if documentos:
        print(f"✅ Documentos cargados: {len(documentos)}")
        for doc in documentos.keys():
            print(f"   📄 {doc}")
    else:
        print("💡 Sube archivos .docx a la carpeta 'documents/'")
    
    print(f"🌐 Servidor iniciado en puerto {port}")
    app.run(host='0.0.0.0', port=port, debug=False)