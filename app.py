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
                    texto_pagina = re.sub(r'\n+', '\n', texto_pagina)
                    texto += texto_pagina + "\n\n"
        return texto.strip() if texto else ""
    except Exception as e:
        print(f"❌ Error procesando {ruta_pdf}: {e}")
        return ""

def procesar_y_indexar_pdfs():
    """Procesa PDFs y crea un índice de búsqueda mejorado"""
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
                    with open(ruta_txt, 'w', encoding='utf-8') as f:
                        f.write(texto)
                    
                    # Mejor división en secciones
                    secciones = []
                    # Dividir por puntos y saltos de línea significativos
                    parrafos = [p.strip() for p in re.split(r'\.\s+|\n\n', texto) if len(p.strip()) > 20]
                    
                    for i, parrafo in enumerate(parrafos):
                        # Limitar longitud de párrafos
                        if len(parrafo) > 800:
                            parrafo = parrafo[:800] + "..."
                        
                        # Extraer palabras clave más específicas
                        palabras = re.findall(r'\b[a-záéíóúñ]{5,}\b', parrafo.lower())
                        # Filtrar palabras comunes del dominio GDE
                        stop_words = {'sistema', 'documental', 'digital', 'gestión', 'módulo', 'manual', 'escritorio', 'único'}
                        palabras_clave = [p for p in palabras if p not in stop_words and len(p) > 4]
                        
                        # Tomar las 10 palabras más frecuentes
                        if palabras_clave:
                            palabras_frecuentes = Counter(palabras_clave).most_common(10)
                            palabras_clave = [p[0] for p in palabras_frecuentes]
                        
                        secciones.append({
                            'id': f"{nombre_base}_p{i}",
                            'texto': parrafo,
                            'palabras_clave': palabras_clave,
                            'longitud': len(parrafo)
                        })
                    
                    documentos_indexados[nombre_base] = secciones
                    print(f"✅ {archivo_pdf}: {len(secciones)} secciones indexadas")
    
    return documentos_indexados

indice_documentos = {}

def buscar_respuesta_inteligente(pregunta):
    """Busca la respuesta más relevante con matching mejorado"""
    global indice_documentos
    
    pregunta_limpia = pregunta.lower().strip()
    
    # Mapeo de preguntas comunes a términos de búsqueda
    mapeo_preguntas = {
        'ingreso': ['ingreso', 'acceso', 'login', 'entrar', 'portal', 'url'],
        'firma digital': ['firma', 'digital', 'certificado', 'firmar', 'electrónica'],
        'trámites': ['trámite', 'procedimiento', 'proceso', 'paso'],
        'contraseña': ['contraseña', 'password', 'olvidé', 'recuperar'],
        'usuario': ['usuario', 'cuenta', 'registro', 'crear'],
        'licencia': ['licencia', 'vacaciones', 'permiso', 'ausencia'],
    }
    
    # Respuestas rápidas para conversación
    respuestas_rapidas = {
        r'hola|buen(os|as)': "¡Hola! 👋 Soy tu asistente del GDE. ¿En qué puedo ayudarte?",
        r'como estas|qué tal': "¡Perfecto! 😊 Listo para ayudarte con el Sistema GDE.",
        r'quien eres|qué eres': "Soy tu asistente especializado en el Sistema de Gestión Documental Electrónica.",
        r'gracias|thanks': "¡De nada! 😊 ¿Necesitas ayuda con algo más del GDE?",
        r'adiós|chao|hasta luego': "¡Hasta luego! 👋",
    }
    
    # Verificar respuestas rápidas
    for patron, respuesta in respuestas_rapidas.items():
        if re.search(patron, pregunta_limpia):
            return respuesta
    
    # Expandir términos de búsqueda basado en la pregunta
    terminos_busqueda = set()
    palabras_pregunta = re.findall(r'\b[a-záéíóúñ]+\b', pregunta_limpia)
    
    for palabra in palabras_pregunta:
        terminos_busqueda.add(palabra)
        # Expandir usando el mapeo
        for categoria, terminos in mapeo_preguntas.items():
            if palabra in terminos:
                terminos_busqueda.update(terminos)
    
    # Filtrar palabras muy comunes
    palabras_filtro = {'como', 'que', 'donde', 'cuando', 'para', 'por', 'con', 'los', 'las', 'del', 'al'}
    terminos_busqueda = {t for t in terminos_busqueda if t not in palabras_filtro and len(t) > 3}
    
    if not terminos_busqueda:
        return "🔍 ¿Podrías ser más específico? Por ejemplo: '¿Cómo ingreso al sistema?' o '¿Necesito firma digital?'"
    
    # Buscar en todos los documentos indexados
    mejores_resultados = []
    
    for doc_nombre, secciones in indice_documentos.items():
        for seccion in secciones:
            # Calcular puntaje de relevancia mejorado
            puntaje = 0
            
            for termino in terminos_busqueda:
                if termino in seccion['texto'].lower():
                    # Puntaje más alto si el término está en palabras clave
                    if termino in seccion['palabras_clave']:
                        puntaje += 3
                    else:
                        puntaje += 1
            
            # Bonus por múltiples coincidencias
            coincidencias_totales = sum(1 for termino in terminos_busqueda if termino in seccion['texto'].lower())
            if coincidencias_totales > 1:
                puntaje += coincidencias_totales * 2
            
            if puntaje > 0:
                # Ajustar por longitud (preferir párrafos de 100-500 caracteres)
                if 100 <= seccion['longitud'] <= 500:
                    puntaje *= 1.5
                elif seccion['longitud'] > 800:
                    puntaje *= 0.7
                
                mejores_resultados.append((puntaje, seccion['texto'], doc_nombre))
    
    # Ordenar por relevancia y tomar los mejores
    mejores_resultados.sort(reverse=True, key=lambda x: x[0])
    
    if mejores_resultados:
        # Tomar solo el MEJOR resultado para evitar repetición
        mejor_puntaje, mejor_texto, mejor_doc = mejores_resultados[0]
        
        # Resumir el texto si es muy largo
        if len(mejor_texto) > 300:
            oraciones = mejor_texto.split('.')
            texto_resumido = '.'.join(oraciones[:2]) + '.' if len(oraciones) > 2 else mejor_texto[:300] + "..."
            mejor_texto = texto_resumido
        
        respuesta = f"📄 **{mejor_doc}**:\n{mejor_texto}"
        
        # Agregar contexto si el puntaje es bajo
        if mejor_puntaje < 3:
            respuesta += "\n\n💡 **Sugerencia:** Si no es la información que buscas, intenta ser más específico."
        
        return respuesta
    else:
        # No se encontraron resultados - sugerencias específicas
        terminos_sugeridos = "', '".join(list(terminos_busqueda)[:3])
        return f"🔍 No encontré información específica sobre '{terminos_sugeridos}'.\n\n💡 **Puedes preguntar sobre:** ingreso al sistema, firma digital, trámites disponibles, recuperar contraseña, o licencias."

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

# ================================
# INICIALIZACIÓN
# ================================
print("🚀 Iniciando ChatBot GDE Mejorado...")
print("📂 Cargando y indexando PDFs...")

indice_documentos = procesar_y_indexar_pdfs()

if indice_documentos:
    total_secciones = sum(len(secciones) for secciones in indice_documentos.values())
    print(f"✅ Sistema listo: {len(indice_documentos)} documento(s) con {total_secciones} secciones indexadas")
else:
    print("⚠️ No se pudieron cargar PDFs.")

print("🔧 Servicio listo!")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
