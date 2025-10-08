import os
import tempfile
import pandas as pd
from io import BytesIO

import streamlit as st
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_core.documents import Document 
from langchain_text_splitters import RecursiveCharacterTextSplitter
from streamlit.runtime.uploaded_file_manager import UploadedFile
from sentence_transformers import CrossEncoder
import chromadb
import ollama
from chromadb.utils.embedding_functions.ollama_embedding_function import OllamaEmbeddingFunction

# ============================
# Configuración de página
# ============================
st.set_page_config(
    page_title="Chatbot Soporte Técnico", 
    page_icon="🤖",
    layout="wide"
)

# ============================
# Botón BACK en la parte superior
# ============================
col1, col2 = st.columns([1, 10])
with col1:
    if st.button("⬅️ Volver", use_container_width=True):
        st.markdown(
            '<meta http-equiv="refresh" content="0; url=/" />',
            unsafe_allow_html=True
        )

with col2:
    st.title("🤖 Chat Soporte Técnico QC")

st.markdown("---")

# ============================
# System prompt general
# ============================
system_prompt = """
Eres un asistente experto en QA y BDD. 
Tienes acceso al contenido de PDFs que contienen información de soporte técnico y BRFs de historias de usuario. 
Tu tarea es decidir automáticamente la intención del usuario y responder de manera adecuada:

1. Si el usuario dice algo como:
   - "Genera Gherkin"
   - "Convierte las historias de usuario a Gherkin"
   - "Escenarios Given/When/Then"
   
   Entonces debes:
   - Tomar las historias de usuario y criterios de aceptación del contenido del PDF.
   - Generar escenarios Gherkin válidos en español.
   - Mantener el formato correcto (Feature, Scenario, Given/When/Then).
   - Cada historia de usuario debe ser una Feature, y cada criterio un Scenario.

2. Para cualquier otra pregunta o duda relacionada con los PDFs, incluyendo consultas sobre funcionalidad, nodos, métricas o visualización:
   - Responde como soporte técnico basado solo en el contenido de los PDFs.
   - Sé claro y detallado.
   
3. Nunca inventes información, responde solo con lo que está en el contexto del PDF.

Formato de salida:
- Si es Gherkin: Feature → Scenario → Given/When/Then
- Si es soporte: respuesta en párrafos claros, bullet points si aplica.
- Responde siempre en español.
- Los pasos de las historias de usuario deben ser en español pero las palabras clave deben estar en inglés com
"""

# ============================
# Funciones de procesamiento de PDF
# ============================
def procesar_pdf(uploaded_file: UploadedFile) -> list[Document]:
    temp_file = tempfile.NamedTemporaryFile("wb",suffix=".pdf", delete=False)
    temp_file.write(uploaded_file.read())
    loader=PyMuPDFLoader(temp_file.name)
    docs= loader.load()
    os.unlink(temp_file.name)

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=100,
        separators=["\n\n", "\n", ".", "?", "!", " ", "-"]
    )
    return text_splitter.split_documents(docs)

# ============================
# Vector DB (Chroma + Ollama)
# ============================
def get_vector_collection():
    ollama_ef=OllamaEmbeddingFunction(
        #url="http://localhost:11434",
        #url="http://host.docker.internal:11434",
        url="http://172.17.0.1:11434", #gateway de docker
        model_name="nomic-embed-text:latest",
        timeout=120
    )
    #chroma_client = chromadb.PersistentClient(path="./demo-rag-chroma")
    chroma_client = chromadb.PersistentClient(path="/app/demo-rag-chroma")
    return chroma_client.get_or_create_collection(
        "chatbot-soporte-tecnico_v2", 
        embedding_function=ollama_ef, 
        metadata={"hnsw:space": "cosine"}
    )

def add_to_vector_collection(all_splits: list[Document], file_name: str, batch_size: int = 100):
    collection = get_vector_collection()
    documents, metadatas, ids = [], [], []

    for idx, split in enumerate(all_splits):
        documents.append(split.page_content)
        metadatas.append(split.metadata)
        ids.append(f"{file_name}_{idx}")

    for i in range(0, len(documents), batch_size):
        batch_docs = documents[i:i+batch_size]
        batch_metas = metadatas[i:i+batch_size]
        batch_ids = ids[i:i+batch_size]

        collection.upsert(
            documents=batch_docs,
            metadatas=batch_metas,
            ids=batch_ids
        )

    st.success(f"✅ Se han agregado {len(all_splits)} documentos a la colección en lotes de {batch_size}.")

def query_collection(prompt:str, n_results=10):
    collection = get_vector_collection()
    results = collection.query(query_texts=[prompt], n_results=n_results)
    return results

# ============================
# LLM call (soporte + Gherkin)
# ============================
def call_llm(context: str, prompt: str):
    ollama_client = ollama.Client(host='http://172.17.0.1:11434')
    #response = ollama.chat(
    response = ollama_client.chat(
        model="llama3.2:3b",
        stream=True,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Contexto PDF:\n{context}\n\nPregunta del usuario:\n{prompt}"},
        ],
    )
    for chunk in response:
        if chunk["done"] is False:
            yield chunk["message"]["content"]
        else:
            break

# ============================
# Re-rank con cross-encoder
# ============================
def re_rank_cross_encoders(prompt: str, documents: list[str]) -> tuple[str, list[int]]:
    relevant_text = ""
    relevant_text_ids = []

    encoder_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    ranks = encoder_model.rank(prompt, documents, top_k=3)
    for rank in ranks:
        relevant_text += documents[rank["corpus_id"]]
        relevant_text_ids.append(rank["corpus_id"])

    return relevant_text, relevant_text_ids

# ============================
# Exportar Gherkin a Excel
# ============================
def export_gherkin_to_excel(gherkin_text: str):
    rows = []
    current_feature = ""
    current_scenario = ""
    
    for line in gherkin_text.splitlines():
        line = line.strip()
        if line.startswith("Feature:"):
            current_feature = line.replace("Feature:", "").strip()
        elif line.startswith("Scenario:"):
            current_scenario = line.replace("Scenario:", "").strip()
        elif line.startswith(("Given", "When", "Then", "And", "But")):
            step_type = line.split()[0]
            step_text = line[len(step_type):].strip()
            rows.append([current_feature, current_scenario, step_type, step_text])
    
    df = pd.DataFrame(rows, columns=["Feature", "Scenario", "Step Type", "Step Text"])
    output = BytesIO()
    df.to_excel(output, index=False)
    return output.getvalue()

# ============================
# Streamlit UI
# ============================
# Sidebar para subir PDFs
with st.sidebar:
    st.header("📄 Gestión de Documentos")
    uploaded_file = st.file_uploader(
        "Sube PDF para agregar a la Base de conocimientos", 
        type=["pdf"], 
        accept_multiple_files=False
    )
    process = st.button("🔄 Procesar PDF", use_container_width=True)
    
    if uploaded_file and process:
        with st.spinner("Procesando PDF..."):
            normalized_upload_file_name = uploaded_file.name.translate(
                str.maketrans({"-":"_", ".":"_", " ":"_"})
            )
            all_splits = procesar_pdf(uploaded_file)
            add_to_vector_collection(all_splits, normalized_upload_file_name)

# Área principal del chat
st.header("💬 Realiza tu Consulta")
prompt = st.text_area(
    "Escribe tu pregunta o solicitud:", 
    placeholder="Ejemplo: Genera Gherkin para las historias de usuario del PDF",
    height=100
)

pregunta_click = st.button("🚀 Preguntar", use_container_width=True, type="primary")

if pregunta_click and prompt:
    with st.spinner("Buscando información relevante..."):
        results = query_collection(prompt)
        context = results.get("documents")[0]
        relevant_text, relevant_text_ids = re_rank_cross_encoders(prompt, context)
    
    with st.spinner("Generando respuesta..."):
        response = "".join(call_llm(context=relevant_text, prompt=prompt))

    st.success("✅ Respuesta generada:")
    st.text_area("Respuesta del Chat", value=response, height=400)

    # Detectar si es Gherkin y ofrecer descarga en Excel
    if "Feature:" in response:
        excel_data = export_gherkin_to_excel(response)
        st.download_button(
            label="📥 Descargar Gherkin en Excel",
            data=excel_data,
            file_name="gherkin_brf.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    # Expanders para información adicional
    with st.expander("📚 Ver documentos recuperados"):
        st.json(results)

    with st.expander("🎯 Ver IDs de documentos más relevantes"):
        st.write("**IDs:**", relevant_text_ids)
        st.text_area("Texto relevante:", relevant_text, height=200)