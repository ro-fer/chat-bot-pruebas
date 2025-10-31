from flask import Flask, request, jsonify, render_template
import os
import pdfplumber
from pathlib import Path

app = Flask(__name__)

# ================================
# CONFIGURACIÓN ESCALABLE
# ================================
DOCUMENTS_DIR = "documents"
PROCESSED_DIR = "processed_data"
os.makedirs(DOCUMENTS_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

# ================================
# PROCESADOR DE PDFs CON PDFPLUMBER
# ================================
def extraer_texto_pdf(ruta_pdf):
    """Extrae texto de PDF usando pdfplumber"""
    try:
        texto = ""
        with pdfplumber.open(ruta_pdf) as pdf:
            for pagina in pdf.pages:
                texto_pagina = pagina.extract_text()
                if texto_pagina:
                    texto += texto_pagina + "\n"
        return texto if texto else "❌ No se pudo extraer texto del PDF"
    except Exception as e:
        return f"❌ Error procesando PDF: {str(e)}"

def procesar_todos_los_pdfs():
    """Procesa todos los PDFs en la carpeta documents/"""
    base_conocimiento = {}
    
    for archivo_pdf in os.listdir(DOCUMENTS_DIR):
        if archivo_pdf.lower().endswith('.pdf'):
            nombre_base = os.path.splitext(archivo_pdf)[0]
            ruta_pdf = os.path.join(DOCUMENTS_DIR, archivo_pdf)
            ruta_txt = os.path.join(PROCESSED_DIR, f"{nombre_base}.txt")
            
            if os.path.exists(ruta_pdf):
                print(f"📖 Procesando: {archivo_pdf}")
                texto = extraer_texto_pdf(ruta_pdf)
                
                # Guardar versión procesada
                with open(ruta_txt, 'w', encoding='utf-8') as f:
                    f.write(texto)
                
                base_conocimiento[nombre_base] = texto[:500] + "..."
                print(f"✅ PDF procesado: {archivo_pdf}")
    
    return base_conocimiento

def buscar_en_pdfs(pregunta):
    """Busca en todos los PDFs procesados"""
    resultados = []
    
    for archivo_txt in os.listdir(PROCESSED_DIR):
        if archivo_txt.endswith('.txt'):
            ruta_txt = os.path.join(PROCESSED_DIR, archivo_txt)
            
            try:
                with open(ruta_txt, 'r', encoding='utf-8') as f:
                    contenido = f.read()
                
                # Búsqueda simple por palabras clave
                palabras = pregunta.lower().split()
                coincidencias = [palabra for palabra in palabras if palabra in contenido.lower()]
                
                if coincidencias:
                    # Encontrar párrafo con coincidencias
                    lineas = contenido.split('\n')
                    for i, linea in enumerate(lineas):
                        if any(palabra in linea.lower() for palabra in coincidencias):
                            contexto = "\n".join(lineas[max(0, i-1):min(len(lineas), i+3)])
                            nombre_doc = archivo_txt.replace('.txt', '')
                            resultados.append(f"📄 **{nombre_doc}**:\n{contexto}\n")
                            break
                            
            except Exception as e:
                print(f"Error leyendo {archivo_txt}: {e}")
    
    return resultados if resultados else ["🔍 No encontré información específica sobre eso en la documentación."]

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
        resultados = buscar_en_pdfs(pregunta)
        respuesta = "🤖 **Resultados de la búsqueda:**\n\n" + "\n---\n".join(resultados)
        
        return jsonify({"success": True, "response": respuesta})
        
    except Exception as e:
        return jsonify({"success": False, "error": f"Error: {str(e)}"})

@app.route('/api/status')
def status():
    """Endpoint para ver el estado de los PDFs"""
    pdfs = [f for f in os.listdir(DOCUMENTS_DIR) if f.endswith('.pdf')]
    procesados = [f for f in os.listdir(PROCESSED_DIR) if f.endswith('.txt')]
    
    return jsonify({
        "pdfs_en_carpeta": pdfs,
        "pdfs_procesados": procesados,
        "mensaje": f"✅ {len(procesados)} de {len(pdfs)} PDFs procesados"
    })

# ================================
# INICIALIZACIÓN
# ================================
print("🚀 Iniciando chatbot multi-PDF...")
if os.path.exists(DOCUMENTS_DIR) and os.listdir(DOCUMENTS_DIR):
    base_conocimiento = procesar_todos_los_pdfs()
    print(f"✅ {len(base_conocimiento)} PDF(s) procesado(s)")
else:
    print("⚠️ No hay PDFs en la carpeta 'documents/'")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)