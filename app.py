from flask import Flask, request, jsonify, render_template
import os
import pdfplumber
import re
from collections import Counter

app = Flask(__name__)

# ================================
# CONFIGURACIÓN
# ================================
DOCUMENTS_DIR = "documents"
PROCESSED_DIR = "processed_data"
os.makedirs(DOCUMENTS_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

# ================================
# SISTEMA DE BÚSQUEDA MEJORADO
# ================================
def extraer_texto_pdf(ruta_pdf):
    """Extrae texto de PDF manteniendo estructura"""
    try:
        texto = ""
        with pdfplumber.open(ruta_pdf) as pdf:
            for pagina in pdf.pages:
                texto_pagina = pagina.extract_text()
                if texto_pagina:
                    # Limpiar y estructurar el texto
                    texto_pagina = re.sub(r'\n+', '\n', texto_pagina)  # Eliminar saltos múltiples
                    texto += texto_pagina + "\n\n"
        return texto.strip() if texto else ""
    except Exception as e:
        print(f"❌ Error procesando {ruta_pdf}: {e}")
        return ""

def procesar_y_indexar_pdfs():
    """Procesa PDFs y crea un índice de búsqueda"""
    documentos_indexados = {}
    
    for archivo_pdf in os.listdir(DOCUMENTS_DIR):
        if archivo_pdf.lower().endswith('.pdf'):
            nombre_base = os.path.splitext(archivo_pdf)[0]
            ruta_pdf = os.path.join(DOCUMENTS_DIR, archivo_pdf)
            ruta_txt = os.path.join(PROCESSED_DIR, f"{nombre_base}.txt")
            
            if os.path.exists(ruta_pdf):
                print(f"📖 Procesando: {archivo_pdf}")
                texto = extraer_texto_pdf(ruta_pdf)
                
                if texto:
                    # Guardar texto procesado
                    with open(ruta_txt, 'w', encoding='utf-8') as f:
                        f.write(texto)
                    
                    # Indexar por secciones/párrafos
                    secciones = []
                    # Dividir en párrafos significativos
                    parrafos = [p.strip() for p in texto.split('\n\n') if len(p.strip()) > 30]
                    
                    for i, parrafo in enumerate(parrafos):
                        # Extraer palabras clave del párrafo
                        palabras = re.findall(r'\b[a-záéíóúñ]{4,}\b', parrafo.lower())
                        palabras_clave = [p for p in palabras if p not in ['para', 'como', 'este', 'esta', 'esto']]
                        
                        secciones.append({
                            'id': f"{nombre_base}_p{i}",
                            'texto': parrafo,
                            'palabras_clave': palabras_clave,
                            'longitud': len(parrafo)
                        })
                    
                    documentos_indexados[nombre_base] = secciones
                    print(f"✅ {archivo_pdf}: {len(secciones)} secciones indexadas")
    
    return documentos_indexados

# Variable global para el índice
indice_documentos = {}

def buscar_respuesta_inteligente(pregunta):
    """Busca la respuesta más relevante usando matching inteligente"""
    global indice_documentos
    
    pregunta_limpia = pregunta.lower().strip()
    
    # Respuestas rápidas para conversación
    respuestas_rapidas = {
        r'hola|buen(os|as)': "¡Hola! 👋 Soy tu asistente del GDE. ¿En qué puedo ayudarte?",
        r'como estas|qué tal': "¡Perfecto! 😊 Listo para ayudarte con el Sistema GDE.",
        r'quien eres|qué eres': "Soy tu asistente especializado en el Sistema de Gestión Documental Electrónica.",
        r'gracias|thanks': "¡De nada! 😊 ¿Necesitas ayuda con algo más del GDE?",
        r'adiós|chao|hasta luego': "¡Hasta luego! 👋 Recuerda que estoy aquí para ayudarte.",
    }
    
    # Verificar respuestas rápidas
    for patron, respuesta in respuestas_rapidas.items():
        if re.search(patron, pregunta_limpia):
            return respuesta
    
    # Si es muy corta
    if len(pregunta_limpia) < 3:
        return "🤖 ¿Podrías contarme más específicamente en qué necesitas ayuda?"
    
    # Extraer palabras clave de la pregunta
    palabras_pregunta = set(re.findall(r'\b[a-záéíóúñ]{4,}\b', pregunta_limpia))
    palabras_pregunta = {p for p in palabras_pregunta if p not in [
        'puede', 'puedo', 'donde', 'como', 'que', 'cual', 'para', 'porque'
    ]}
    
    if not palabras_pregunta:
        return "🔍 ¿Podrías reformular tu pregunta? Por ejemplo: '¿Cómo ingreso al sistema GDE?' o '¿Qué trámites están disponibles?'"
    
    # Buscar en todos los documentos indexados
    mejores_resultados = []
    
    for doc_nombre, secciones in indice_documentos.items():
        for seccion in secciones:
            # Calcular puntaje de relevancia
            palabras_comunes = palabras_pregunta.intersection(seccion['palabras_clave'])
            puntaje = len(palabras_comunes)
            
            # Bonus por coincidencia exacta de frases
            for palabra in palabras_pregunta:
                if palabra in seccion['texto'].lower():
                    puntaje += 1
            
            if puntaje > 0:
                # Penalizar secciones muy largas o muy cortas
                factor_longitud = 1.0
                if seccion['longitud'] < 50 or seccion['longitud'] > 1000:
                    factor_longitud = 0.7
                
                puntaje_ajustado = puntaje * factor_longitud
                mejores_resultados.append((puntaje_ajustado, seccion['texto'], doc_nombre))
    
    # Ordenar por relevancia y tomar los mejores
    mejores_resultados.sort(reverse=True, key=lambda x: x[0])
    
    if mejores_resultados:
        # Tomar los 2 mejores resultados
        resultados_finales = []
        for puntaje, texto, doc_nombre in mejores_resultados[:2]:
            # Acortar si es muy largo
            if len(texto) > 400:
                oraciones = texto.split('.')
                texto_acortado = '.'.join(oraciones[:3]) + '.' if len(oraciones) > 3 else texto[:400] + "..."
                texto = texto_acortado
            
            resultados_finales.append(f"📄 **{doc_nombre}**:\n{texto}")
        
        respuesta = "\n\n---\n\n".join(resultados_finales)
        
        # Agregar sugerencias si el puntaje no es muy alto
        if mejores_resultados[0][0] < 2:
            respuesta += "\n\n💡 **Sugerencia:** Si no es lo que buscabas, intenta ser más específico con términos como 'ingreso', 'trámites', 'firma digital', etc."
        
        return respuesta
    else:
        # No se encontraron resultados
        sugerencias = [
            "• '¿Cómo ingresar al sistema GDE?'",
            "• '¿Qué documentos necesito para un trámite?'", 
            "• '¿Cómo funciona la firma digital?'",
            "• '¿Dónde encuentro el manual de usuario?'",
            "• '¿Qué hacer si olvidé mi contraseña?'"
        ]
        return f"🔍 No encontré información específica sobre: '{pregunta}'\n\n💡 **Puedes preguntar:**\n" + "\n".join(sugerencias)

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
        respuesta = buscar_respuesta_inteligente(pregunta)
        return jsonify({"success": True, "response": respuesta})
        
    except Exception as e:
        return jsonify({"success": False, "error": f"Error: {str(e)}"})

@app.route('/api/status')
def status():
    """Endpoint para ver el estado del sistema"""
    pdfs = [f for f in os.listdir(DOCUMENTS_DIR) if f.endswith('.pdf')]
    total_secciones = sum(len(secciones) for secciones in indice_documentos.values())
    
    return jsonify({
        "estado": "activo",
        "pdfs_cargados": pdfs,
        "documentos_indexados": list(indice_documentos.keys()),
        "total_secciones": total_secciones,
        "mensaje": f"✅ Sistema listo con {len(pdfs)} PDF(s) y {total_secciones} secciones indexadas"
    })

# ================================
# INICIALIZACIÓN
# ================================
print("🚀 Iniciando ChatBot GDE Mejorado...")
print("📂 Cargando y indexando PDFs...")

# Cargar e indexar todos los PDFs
indice_documentos = procesar_y_indexar_pdfs()

if indice_documentos:
    total_secciones = sum(len(secciones) for secciones in indice_documentos.values())
    print(f"✅ Sistema listo: {len(indice_documentos)} documento(s) con {total_secciones} secciones indexadas")
else:
    print("⚠️ No se pudieron cargar PDFs. El chatbot funcionará en modo básico.")

print("🔧 Servicio listo en http://0.0.0.0:5000")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
