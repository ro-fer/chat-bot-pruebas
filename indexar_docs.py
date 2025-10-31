import chromadb
from chromadb.utils import embedding_functions
import os

# Carpeta con tus documentos
DATA_PATH = "data/"

# Crea la base local
chroma_client = chromadb.Client()
collection = chroma_client.get_or_create_collection("documentacion")

# Función para leer los archivos de texto
def leer_documentos():
    docs = []
    for file in os.listdir(DATA_PATH):
        if file.endswith(".pdf"):
            with open(os.path.join(DATA_PATH, file), "r", encoding="utf-8") as f:
                docs.append(f.read())
    return docs

# Insertar textos en la base
documentos = leer_documentos()
for i, texto in enumerate(documentos):
    collection.add(
        documents=[texto],
        ids=[f"doc_{i}"]
    )

print(f"Se indexaron {len(documentos)} documentos.")
