# 🤖 ChatBot Punto Digital - Asistente Inteligente 

**Python 3.8+** | **Flask 2.0+** | **Deploy on Railway** | **License MIT**

Un asistente inteligente que puede leer y buscar información en documentos DOCX, desplegado en Railway y proporciona respuestas contextuales precisas. En este caso, se carga documentación de procedimientos sobre Punto Digital.

## ✨ Características Principales

### 🌐 **Desplegado en Railway**
- Despliegue automático desde GitHub
- SSL integrado

### 🤖 Sistema Dual de Chat
- **Chat Normal**: Interfaz completa de conversación.
- **Widget Flotante**: Componente integrable en página web, para este caso se armó una página de ejemplo.

### 📄 Procesamiento Inteligente de Documentos
- Extracción contenido DOCX
- Procesamiento de párrafos y tablas
- Detección automática de secciones importantes

### 🧠 **Inteligencia Artificial**
- **Groq API**: Para respuestas contextuales avanzadas
- **Búsqueda local**: Fallback inteligente sin conexión
- Procesamiento de lenguaje natural

## 🛠️ Tecnologías

- **Backend**: Python + Flask
- **Frontend**: HTML + CSS + JavaScript
- **IA**: Groq API (LLaMA 3.1 8B Instant)
- **Procesamiento**: python-docx
- **Deploy**: Railway
- **Archivos**: .docx


## 🎯 Uso

### Chat Normal
- **URL**: `https://chat-bot-pruebas-production.up.railway.app`
- Interfaz completa de conversación

### Widget Flotante  
- **URL**: `https://chat-bot-pruebas-production.up.railway.app/probando-widget`
- Página de ejemplo con chat integrado

### Preguntas Ejemplo (en este caso)
- "¿Qué equipamiento hay en stock?"
- "Información sobre instalación"
- "Procedimientos de soporte técnico"

## 📝 Licencia

MIT License - ver [LICENSE](LICENSE) para detalles.
