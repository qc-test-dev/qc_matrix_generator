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
Eres un asistente experto en soporte técnico y QA/BDD.

IMPORTANTE: Detecta primero qué quiere el usuario:

🔹 CASO 1: Si el usuario pide EXPLÍCITAMENTE generar Gherkin/BDD/escenarios:
   - Palabras clave: "genera gherkin", "convierte a BDD", "escenarios Given/When/Then"
   - Solo entonces generas formato Gherkin completo
   - Feature → Scenario → Given/When/Then en español con keywords en inglés

🔹 CASO 2: Para CUALQUIER otra pregunta (DEFAULT):
   - Responde como soporte técnico normal
   - Usa el formato del documento original (listas numeradas, pasos, etc.)
   - Si el PDF tiene 10 pasos, incluye los 10 pasos
   - Mantén la estructura clara y organizada
   - NO uses formato Gherkin a menos que lo pidan explícitamente

REGLAS GENERALES:
✅ NUNCA omitas información del PDF
✅ Si hay pasos numerados, respétalos todos en orden
✅ Sé exhaustivo: incluye URLs, credenciales, configuraciones
✅ Si no estás seguro de la intención, responde en formato normal de soporte técnico
✅ Responde solo con información del contexto proporcionado

Idioma: Español
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
        chunk_size=1200,
        chunk_overlap=300,
        separators=["\n\n", "\n", ".", "?", "!", " ", "-"]
    )
    return text_splitter.split_documents(docs)

# ============================
# Vector DB (Chroma + Ollama)
# ============================
def get_vector_collection():
    ollama_ef=OllamaEmbeddingFunction(
        url="http://localhost:11434",
        #url="http://host.docker.internal:11434",
        #url="http://172.17.0.1:11434", #gateway de docker
        model_name="nomic-embed-text:latest",
        timeout=120
    )
    chroma_client = chromadb.PersistentClient(path="./demo-rag-chroma")
    #chroma_client = chromadb.PersistentClient(path="/app/demo-rag-chroma")
    return chroma_client.get_or_create_collection(
        "chatbot-soporte-tecnico_v2", 
        embedding_function=ollama_ef, 
        metadata={"hnsw:space": "cosine"}
    )

def add_to_vector_collection(all_splits: list[Document], file_name: str, original_name: str, batch_size: int = 100):
    collection = get_vector_collection()
    documents, metadatas, ids = [], [], []

    for idx, split in enumerate(all_splits):
        documents.append(split.page_content)
        # 🔥 FIX: Sobrescribir el source con el nombre original
        metadata = split.metadata.copy()
        metadata["source"] = original_name  # Usar el nombre real del PDF
        metadatas.append(metadata)
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

def query_collection(prompt:str, n_results=22):
    collection = get_vector_collection()
    results = collection.query(query_texts=[prompt], n_results=n_results)
    return results

# ============================
# LLM call (soporte + Gherkin)
# ============================

def call_llm(context: str, prompt: str):
    ollama_client = ollama.Client(host='http://localhost:11434')
    #response = ollama.chat(
    # 🔥 NUEVO: Prompt más específico
    enhanced_prompt = f"""
Contexto del documento PDF:
{context}

Pregunta del usuario: {prompt}

INSTRUCCIONES CRÍTICAS:
- Lee CUIDADOSAMENTE todo el contexto proporcionado
- Si hay múltiples secciones o procedimientos, INCLÚYELOS TODOS
- Si ves números de pasos (1, 2, 3...), verifica que NO falte ninguno
- Si el contexto menciona diferentes formas de instalación, menciónalas todas
- Sé exhaustivo y no omitas detalles técnicos (URLs, comandos, configuraciones)

Responde ahora:
"""
    
    response = ollama_client.chat(
        model="qwen2.5:7b",
        stream=True,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": enhanced_prompt},  # 👈 Usar el prompt mejorado
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
    ranks = encoder_model.rank(prompt, documents, top_k=8)
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
            # 🔥 NUEVO: Crear carpeta media/pdfs si no existe
            pdf_folder = os.path.join(os.path.dirname(__file__), "media", "pdfs")
            os.makedirs(pdf_folder, exist_ok=True)
            
            # 🔥 NUEVO: Guardar el PDF original
            pdf_path = os.path.join(pdf_folder, uploaded_file.name)
            with open(pdf_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Procesar para ChromaDB (lo que ya tenías)
            normalized_upload_file_name = uploaded_file.name.translate(
                str.maketrans({"-":"_", ".":"_", " ":"_"})
            )
            all_splits = procesar_pdf(uploaded_file)
            # 🔥 FIX: Pasar el nombre original del PDF
            add_to_vector_collection(all_splits, normalized_upload_file_name, uploaded_file.name)
            
            st.success(f"✅ PDF guardado en: media/pdfs/{uploaded_file.name}")

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

    # 🔥 NUEVO: Extraer PDFs fuente de los metadatas
    metadatas = results.get("metadatas")[0]
    pdf_sources = set()

    # 🐛 DEBUG TEMPORAL
    st.write("🔍 **DEBUG - Información de fuentes:**")
    st.write(f"Total de metadatas: {len(metadatas)}")
    st.write(f"IDs relevantes: {relevant_text_ids}")

    for idx in relevant_text_ids:
        if idx < len(metadatas):
            st.write(f"Metadata[{idx}]: {metadatas[idx]}")

    pdf_folder = os.path.join(os.path.dirname(__file__), "media", "pdfs")
    if os.path.exists(pdf_folder):
        archivos = os.listdir(pdf_folder)
        st.write(f"📁 Archivos en media/pdfs: {archivos}")
    else:
        st.write("⚠️ La carpeta media/pdfs no existe")

    # Verificar que la carpeta existe
    if os.path.exists(pdf_folder):
        archivos_disponibles = {f.lower(): f for f in os.listdir(pdf_folder)}
        
        for idx in relevant_text_ids:
            if idx < len(metadatas):
                source = metadatas[idx].get("source", "")
                
                if source:
                    # Limpiar el source y buscar coincidencias
                    # El source puede venir como "ruta/completa/archivo.pdf" o "archivo_pdf"
                    source_base = os.path.basename(source)  # Solo el nombre del archivo
                    source_base = source_base.lower()
                    
                    # Intentar match directo
                    if source_base in archivos_disponibles:
                        pdf_sources.add(archivos_disponibles[source_base])
                    else:
                        # Intentar match aproximado (sin extensión o con _ en lugar de .)
                        for archivo_key, archivo_real in archivos_disponibles.items():
                            # Comparar sin extensión
                            if source_base.replace(".pdf", "") in archivo_key.replace(".pdf", ""):
                                pdf_sources.add(archivo_real)
                                break
                            # Comparar con normalización de _ y -
                            source_normalizado = source_base.replace("_", "").replace("-", "").replace(".pdf", "")
                            archivo_normalizado = archivo_key.replace("_", "").replace("-", "").replace(".pdf", "")
                            if source_normalizado in archivo_normalizado or archivo_normalizado in source_normalizado:
                                pdf_sources.add(archivo_real)
                                break

    # 🔥 NUEVO: Mostrar y ofrecer descarga de PDFs consultados
    if pdf_sources:
        st.info(f"📚 **Información encontrada en:** {', '.join(pdf_sources)}")
        
        # Crear columnas para los botones de descarga
        cols = st.columns(len(pdf_sources))
        for idx, pdf_name in enumerate(pdf_sources):
            pdf_path = os.path.join(pdf_folder, pdf_name)
            if os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    with cols[idx]:
                        st.download_button(
                            label=f"📥 {pdf_name}",
                            data=f.read(),
                            file_name=pdf_name,
                            mime="application/pdf",
                            key=f"pdf_{idx}",
                            use_container_width=True
                        )

    # Detectar si es Gherkin y ofrecer descarga en Excel
    if "Feature:" in response or "Scenario:" in response:
        excel_data = export_gherkin_to_excel(response)
        st.download_button(
            label="📥 Descargar Gherkin en Excel",
            data=excel_data,
            file_name="gherkin_brf.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    # 🔥 NUEVO: Botón para descargar la respuesta como texto
    st.download_button(
        label="📄 Descargar respuesta (.txt)",
        data=response,
        file_name="respuesta_soporte.txt",
        mime="text/plain",
        use_container_width=True
    )

    # Expanders para información adicional
    with st.expander("📚 Ver documentos recuperados"):
        st.json(results)

    with st.expander("🎯 Ver IDs de documentos más relevantes"):
        st.write("**IDs:**", relevant_text_ids)
        st.text_area("Texto relevante:", relevant_text, height=200)