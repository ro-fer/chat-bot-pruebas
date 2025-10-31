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
# BÚSQUEDA INTELIGENTE EN DOCX
# ================================
def buscar_en_documentos(pregunta, documentos):
    """Busca en todos los documentos DOCX cargados"""
    pregunta_limpia = pregunta.lower().strip()
    
    # 🚨 Una sola palabra = No entiendo
    if len(pregunta_limpia.split()) <= 1:
        return None
    
    palabras_clave = set(re.findall(r'\b[a-záéíóúñ]{4,}\b', pregunta_limpia))
    
    # Filtrar palabras muy comunes
    palabras_filtro = {'sobre', 'sobre el', 'sobre la', 'sobre los', 'sobre las', 'como', 'que', 'donde'}
    palabras_clave = {p for p in palabras_clave if p not in palabras_filtro}
    
    if not palabras_clave:
        return None
    
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
    return resultados

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
        
        # Buscar en documentos
        resultados = buscar_en_documentos(pregunta, documentos)
        
        if resultados:
            respuesta = f"🔍 **Encontré esto sobre '{pregunta}':**\n\n"
            
            for i, resultado in enumerate(resultados[:2]):  # Máximo 2 resultados
                respuesta += f"📄 **{resultado['documento']}:**\n{resultado['contenido']}\n\n"
                
                if i < len(resultados) - 1:
                    respuesta += "---\n\n"
            
            return jsonify({'success': True, 'response': respuesta})
        else:
            return jsonify({
                'success': True,
                'response': f"🤔 No encontré información específica sobre '{pregunta}' en los documentos.\n\n📂 **Documentos disponibles:** {list(documentos.keys())}"
            })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error: {str(e)}'})

@app.route('/api/documents')
def list_documents():
    """Endpoint para ver los documentos cargados"""
    documentos = cargar_documentos_docx()
    return jsonify({
        'documentos_cargados': list(documentos.keys()),
        'total': len(documentos),
        'tipo': 'DOCX'
    })

@app.route('/health')
def health():
    documentos = cargar_documentos_docx()
    return jsonify({
        'status': 'healthy',
        'documentos_cargados': len(documentos),
        'documentos': list(documentos.keys())
    })

# ================================
# INICIALIZACIÓN
# ================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    print("🚀 ChatBot DOCX iniciado")
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