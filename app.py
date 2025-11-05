from flask import Flask, request, jsonify, render_template, send_from_directory, Response
import os
from docx import Document
import requests
import re

app = Flask(__name__)
DOCUMENTS_DIR = "documents"

# ================================
# CONFIGURACIÓN BÁSICA
# ================================
def check_auth(username, password):
    return username == os.environ.get('DOC_USER', 'admin') and password == os.environ.get('DOC_PASS', 'password123')

def authenticate():
    return Response('Acceso requerido', 401, {'WWW-Authenticate': 'Basic realm="Documentación Privada"'})

@app.route('/documentos/<path:filename>')
def download_document(filename):
    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password):
        return authenticate()
    return send_from_directory(DOCUMENTS_DIR, filename)

@app.route('/documentos/')
def list_documents():
    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password):
        return authenticate()
    
    documentos = [archivo for archivo in os.listdir(DOCUMENTS_DIR) if archivo.lower().endswith('.docx')]
    html = "<h1>📁 Documentos Disponibles</h1><ul>"
    for doc in documentos:
        html += f'<li><a href="/documentos/{doc}" download>{doc}</a></li>'
    html += "</ul><p><em>Usa Ctrl+Click para descargar</em></p>"
    return html

# ================================
# PROCESADOR DE DOCX COMPLETO
# ================================
def procesar_docx_completo(ruta_archivo):
    """Procesa TODO el contenido del DOCX incluyendo tablas"""
    try:
        doc = Document(ruta_archivo)
        texto_completo = ""
        
        print(f"🔍 Procesando: {ruta_archivo}")
        
        # Procesar párrafos
        for i, paragraph in enumerate(doc.paragraphs):
            if paragraph.text.strip():
                texto_completo += f"P[{i}]: {paragraph.text}\n"
        
        # Procesar tablas
        for t, table in enumerate(doc.tables):
            texto_completo += f"\n=== TABLA {t+1} ===\n"
            for r, row in enumerate(table.rows):
                fila_texto = f"Fila {r+1}: "
                celdas = []
                for c, cell in enumerate(row.cells):
                    if cell.text.strip():
                        celdas.append(f"[C{c+1}: {cell.text.strip()}]")
                if celdas:
                    texto_completo += fila_texto + " | ".join(celdas) + "\n"
            texto_completo += "=== FIN TABLA ===\n\n"
        
        return texto_completo.strip()
    except Exception as e:
        print(f"❌ Error procesando DOCX: {e}")
        return f"ERROR: {str(e)}"

def cargar_documentos_docx():
    documentos = {}
    if not os.path.exists(DOCUMENTS_DIR):
        return documentos
    
    for archivo in os.listdir(DOCUMENTS_DIR):
        if archivo.lower().endswith('.docx'):
            ruta_archivo = os.path.join(DOCUMENTS_DIR, archivo)
            texto = procesar_docx_completo(ruta_archivo)
            if texto:
                documentos[archivo] = texto
                print(f"✅ Documento cargado: {archivo} - {len(texto)} caracteres")
    
    return documentos

# ================================
# BÚSQUEDA MEJORADA - VISTA COMPLETA
# ================================
def mostrar_contenido_completo(contenido, limite=50):
    """Muestra el contenido completo del documento procesado"""
    lineas = contenido.split('\n')
    resultado = []
    
    resultado.append("<strong>📄 CONTENIDO COMPLETO DEL DOCUMENTO:</strong><br><br>")
    
    for i, linea in enumerate(lineas[:limite]):
        if linea.strip():
            # Resaltar tablas y secciones importantes
            if '=== TABLA' in linea:
                resultado.append(f"<br>🎯 <strong>{linea}</strong><br>")
            elif 'P[' in linea and any(palabra in linea.lower() for palabra in ['puesta', 'marcha', 'servicio', 'procedimiento']):
                resultado.append(f"<br>🔍 {linea}<br>")
            else:
                resultado.append(f"{linea}<br>")
    
    if len(lineas) > limite:
        resultado.append(f"<br>... y {len(lineas) - limite} líneas más ...")
    
    return "".join(resultado)

def buscar_puesta_marcha_inteligente(contenido):
    """Búsqueda inteligente de toda la información de puesta en marcha"""
    lineas = contenido.split('\n')
    resultados = []
    
    # Buscar en TODO el contenido, no solo en párrafos específicos
    for i, linea in enumerate(lineas):
        linea_limpia = linea.strip()
        
        # Buscar cualquier mención de puesta en marcha
        if any(termino in linea_limpia.lower() for termino in [
            'puesta en marcha', 'servicio de puesta', 'implementación', 
            'procedimiento', 'proceso general', 'detalle de los procedimientos'
        ]):
            resultados.append(f"🎯 <strong>Encontrado en línea {i}:</strong> {linea_limpia}<br>")
            
            # Mostrar contexto alrededor
            inicio = max(0, i-2)
            fin = min(len(lineas), i+8)
            resultados.append("<em>Contexto:</em><br>")
            for j in range(inicio, fin):
                if lineas[j].strip():
                    resultados.append(f"  {j}: {lineas[j].strip()}<br>")
            resultados.append("<br>")
    
    return resultados

def buscar_tablas_especificas(contenido):
    """Busca específicamente información de tablas"""
    lineas = contenido.split('\n')
    tablas = []
    en_tabla = False
    tabla_actual = []
    
    for i, linea in enumerate(lineas):
        if '=== TABLA' in linea:
            if tabla_actual:  # Guardar tabla anterior
                tablas.append((i, tabla_actual))
            en_tabla = True
            tabla_actual = [linea]
        elif '=== FIN TABLA ===' in linea:
            en_tabla = False
            tabla_actual.append(linea)
            tablas.append((i, tabla_actual))
            tabla_actual = []
        elif en_tabla:
            tabla_actual.append(linea)
    
    return tablas

def buscar_localmente_mejorada(pregunta, documentos):
    """Búsqueda local mejorada - VERSIÓN DIAGNÓSTICO"""
    pregunta_limpia = pregunta.lower()
    
    # 1. Pregunta sobre documentos disponibles
    if any(p in pregunta_limpia for p in ['documento', 'cargado', 'archivo', 'disponible']):
        docs = list(documentos.keys())
        doc_list = "<br>".join([f"• {d}" for d in docs])
        return f"<strong>📂 Documentos cargados ({len(docs)}):</strong><br><br>{doc_list}"
    
    resultados = []
    
    for doc_nombre, contenido in documentos.items():
        # 2. MODO DIAGNÓSTICO COMPLETO
        if any(p in pregunta_limpia for p in ['debug', 'diagnostico', 'completo', 'contenido']):
            contenido_completo = mostrar_contenido_completo(contenido, 80)
            return f"<strong>📄 {doc_nombre} - DIAGNÓSTICO COMPLETO</strong><br><br>{contenido_completo}"
        
        # 3. BUSCAR TABLAS
        if any(p in pregunta_limpia for p in ['tabla', 'puesta en marcha', 'procedimiento']):
            tablas = buscar_tablas_especificas(contenido)
            if tablas:
                resultados.append(f"<strong>📄 {doc_nombre} - TABLAS ENCONTRADAS ({len(tablas)})</strong><br><br>")
                for num_tabla, (linea, tabla) in enumerate(tablas, 1):
                    resultados.append(f"<strong>📊 TABLA {num_tabla} (línea {linea}):</strong><br>")
                    for linea_tabla in tabla[:15]:  # Mostrar primeras 15 líneas de cada tabla
                        resultados.append(f"{linea_tabla}<br>")
                    resultados.append("<br>")
        
        # 4. BÚSQUEDA INTELIGENTE DE PUESTA EN MARCHA
        if any(p in pregunta_limpia for p in ['puesta en marcha', 'marcha']):
            busqueda_inteligente = buscar_puesta_marcha_inteligente(contenido)
            if busqueda_inteligente:
                resultados.append(f"<strong>📄 {doc_nombre} - BÚSQUEDA INTELIGENTE</strong><br><br>" + "".join(busqueda_inteligente))
    
    if resultados:
        return "<br><br>".join(resultados)
    
    # 5. Si no encuentra nada específico, mostrar ayuda
    return """
    🤔 <strong>No encontré información específica.</strong><br><br>
    💡 <strong>Prueba estos comandos:</strong><br>
    • <strong>"DEBUG"</strong> - Ver contenido completo del documento<br>
    • <strong>"TABLAS"</strong> - Ver todas las tablas encontradas<br>
    • <strong>"PUESTA EN MARCHA"</strong> - Búsqueda inteligente<br>
    • <strong>"DOCUMENTOS"</strong> - Lista de documentos cargados<br><br>
    🎯 <strong>El problema puede ser:</strong><br>
    - El documento no se está procesando completamente<br>
    - Las tablas no se están extrayendo correctamente<br>
    - La información está en formato que no detectamos<br>
    """

# ================================
# GROQ 
# ================================
def preguntar_groq(pregunta, documentos):
    api_key = os.environ.get('GROQ_API_KEY')
    if not api_key:
        respuesta = buscar_localmente_mejorada(pregunta, documentos)
        return respuesta
    
    try:
        contexto = "INFORMACIÓN DISPONIBLE:\n\n"
        
        for doc_nombre, contenido in documentos.items():
            # Para diagnóstico, enviar información completa
            if any(p in pregunta.lower() for p in ['debug', 'diagnostico']):
                contexto += f"DOCUMENTO: {doc_nombre}\n{contenido[:2000]}\n\n"
            else:
                # Buscar información relevante
                lineas_relevantes = []
                lineas = contenido.split('\n')
                for linea in lineas:
                    if any(termino in linea.lower() for termino in ['puesta en marcha', 'procedimiento', 'servicio']):
                        lineas_relevantes.append(linea)
                        if len(lineas_relevantes) >= 10:
                            break
                
                if lineas_relevantes:
                    contexto += f"DOCUMENTO: {doc_nombre}\n" + "\n".join(lineas_relevantes) + "\n\n"
        
        if len(contexto) > 3000:
            contexto = contexto[:3000] + "..."
        
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama3-8b-8192",
                "messages": [
                    {
                        "role": "system", 
                        "content": "Eres un asistente especializado en diagnóstico. Analiza qué información está disponible y qué podría faltar. Responde de forma CLARA. Usa HTML básico: <br> para saltos de línea y <strong> para negritas."
                    },
                    {
                        "role": "user", 
                        "content": f"{contexto}\n\nPREGUNTA: {pregunta}\n\nANÁLISIS:"
                    }
                ],
                "temperature": 0.1,
                "max_tokens": 800
            },
            timeout=15
        )
        
        if response.status_code == 200:
            respuesta = response.json()["choices"][0]["message"]["content"]
            if '<br>' not in respuesta and '</strong>' not in respuesta:
                respuesta = respuesta.replace('\n', '<br>')
            return respuesta
        else:
            return buscar_localmente_mejorada(pregunta, documentos)
            
    except Exception as e:
        return buscar_localmente_mejorada(pregunta, documentos)

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
        
        documentos = cargar_documentos_docx()
        
        if not documentos:
            return jsonify({'success': True, 'response': "📂 No hay documentos cargados en la carpeta 'documents'."})
        
        # Respuestas rápidas
        if any(s in pregunta.lower() for s in ['hola', 'buenos días', 'buenas', 'hello', 'hi']):
            return jsonify({
                'success': True, 
                'response': f"¡Hola! 👋 Soy tu asistente de diagnóstico.<br><br>Tengo {len(documentos)} documento(s) cargados.<br><br>¿En qué puedo ayudarte?"
            })
        
        # Usar Groq con fallback transparente
        respuesta = preguntar_groq(pregunta, documentos)
        return jsonify({'success': True, 'response': respuesta})
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error: {str(e)}'})

# ================================
# INICIO DE LA APLICACIÓN
# ================================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 ChatBot Diagnóstico iniciado en puerto {port}")
    
    documentos = cargar_documentos_docx()
    print(f"📄 Documentos cargados: {len(documentos)}")
    
    # Mostrar diagnóstico inicial
    for doc_nombre, contenido in documentos.items():
        print(f"\n🔍 {doc_nombre}:")
        print(f"   Longitud: {len(contenido)} caracteres")
        print(f"   Líneas: {len(contenido.splitlines())}")
        print(f"   Tablas encontradas: {contenido.count('=== TABLA')}")
    
    app.run(host='0.0.0.0', port=port, debug=False)