from flask import Flask, request, jsonify, render_template
import os
import re
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
# PROCESADOR DE PDFs (Versión LIVIANA)
# ================================
def extraer_texto_pdf_simple(ruta_pdf):
    """Extrae texto básico de PDF sin dependencias pesadas"""
    try:
        # Intentar con PyMuPDF si está disponible
        try:
            import fitz
            doc = fitz.open(ruta_pdf)
            texto = ""
            for pagina in doc:
                texto += pagina.get_text() + "\n"
            doc.close()
            return texto
        except ImportError:
            # Fallback: usar pdfminer (más liviano)
            from pdfminer.high_level import extract_text
            return extract_text(ruta_pdf)
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
            
            # Procesar PDF y guardar texto
            if os.path.exists(ruta_pdf):
                texto = extraer_texto_pdf_simple(ruta_pdf)
                
                # Guardar versión procesada
                with open(ruta_txt, 'w', encoding='utf-8') as f:
                    f.write(texto)
                
                # Agregar a base de conocimiento
                base_conocimiento[nombre_base] = texto[:1000] + "..."  # Solo preview
                
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
                coincidencias = sum(1 for palabra in palabras if palabra in contenido.lower())
                
                if coincidencias > 0:
                    # Extraer contexto alrededor de las coincidencias
                    lineas = contenido.split('\n')
                    for i, linea in enumerate(lineas):
                        if any(palabra in linea.lower() for palabra in palabras):
                            contexto = "\n".join(lineas[max(0, i-1):min(len(lineas), i+2)])
                            resultados.append(f"📄 {archivo_txt}:\n{contexto}\n")
                            break
                            
            except Exception as e:
                print(f"Error leyendo {archivo_txt}: {e}")
    
    return resultados if resultados else ["ℹ️ Información no encontrada en la documentación."]

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
        # Buscar en todos los PDFs procesados
        resultados = buscar_en_pdfs(pregunta)
        respuesta = "🔍 **Resultados de la búsqueda:**\n\n" + "\n---\n".join(resultados)
        
        return jsonify({"success": True, "response": respuesta})
        
    except Exception as e:
        return jsonify({"success": False, "error": f"Error: {str(e)}"})

@app.route('/api/status')
def status():
    """Endpoint para ver el estado de los PDFs procesados"""
    pdfs = os.listdir(DOCUMENTS_DIR)
    procesados = os.listdir(PROCESSED_DIR)
    
    return jsonify({
        "pdfs_en_carpeta": pdfs,
        "pdfs_procesados": procesados,
        "total_pdfs": len(pdfs),
        "total_procesados": len(procesados)
    })

# ================================
# INICIALIZACIÓN
# ================================
print("🚀 Iniciando chatbot multi-PDF...")
print("📂 Procesando PDFs...")

# Procesar PDFs al inicio (solo los nuevos)
base_conocimiento = procesar_todos_los_pdfs()

if base_conocimiento:
    print(f"✅ {len(base_conocimiento)} PDF(s) procesado(s)")
    for nombre, preview in base_conocimiento.items():
        print(f"   📄 {nombre}: {preview[:100]}...")
else:
    print("⚠️ No se encontraron PDFs en la carpeta 'documents/'")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)