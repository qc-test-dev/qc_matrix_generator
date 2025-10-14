import os
import tempfile
import pandas as pd
from io import BytesIO
import re

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
# System prompt mejorado
# ============================
system_prompt = """
Eres un asistente experto en soporte técnico y QA/BDD.

VALIDACIÓN DE CONSULTA:
🔹 Primero verifica si la pregunta tiene sentido y está relacionada con soporte técnico, documentación o BDD
🔹 Si la entrada es aleatoria, sin sentido o no relacionada, responde educadamente pidiendo aclaración
🔹 Ejemplo de entrada inválida: "32s4fd6n5", "asdfgh", texto aleatorio sin contexto

DETECCIÓN DE INTENCIÓN:

🔹 CASO 1: Generación de Gherkin/BDD (SOLO si el usuario lo pide EXPLÍCITAMENTE)
   Palabras clave: "genera gherkin", "convierte a BDD", "escenarios Given/When/Then", "casos de prueba BDD"
   Acción: Generar formato Gherkin completo
   Formato: Feature → Scenario → Given/When/Then en español con keywords en inglés

🔹 CASO 2: Consulta de soporte técnico (DEFAULT)
   Acción: Responder como asistente de soporte técnico
   - Usa el formato del documento original (listas numeradas, pasos, etc.)
   - Incluye TODOS los pasos sin omitir ninguno
   - Mantén URLs, credenciales, configuraciones exactas
   - Estructura clara y organizada
   - NO uses formato Gherkin

🔹 CASO 3: Consulta ambigua o sin contexto suficiente
   Acción: Pedir aclaración específica sobre qué necesita el usuario

REGLAS CRÍTICAS:
✅ Si el contexto proporcionado no contiene información relacionada con la pregunta, indícalo claramente
✅ NUNCA omitas información relevante del PDF
✅ Si hay pasos numerados (1, 2, 3...), respétalos TODOS en orden
✅ Sé exhaustivo: incluye URLs, credenciales, configuraciones completas
✅ Si la pregunta no tiene relación con el contexto, indícalo y ofrece ayuda
✅ NO inventes información que no esté en el contexto
✅ Si no puedes responder con certeza, admítelo y pide más detalles

FORMATO DE RESPUESTA CUANDO NO HAY INFORMACIÓN:
"No encuentro información relacionada con '[tema de la consulta]' en la documentación disponible. 
¿Podrías reformular tu pregunta o proporcionar más contexto sobre lo que necesitas?"

Idioma: Español (excepto keywords de Gherkin)
"""

# ============================
# Validación de consultas
# ============================
def validar_consulta(prompt: str) -> tuple[bool, str]:
    """
    Valida si la consulta tiene sentido antes de procesarla
    Retorna (es_valida, mensaje_error)
    """
    # Verificar longitud mínima
    if len(prompt.strip()) < 3:
        return False, "La consulta es demasiado corta. Por favor, escribe una pregunta más detallada."
    
    # Verificar si es solo caracteres aleatorios
    if re.match(r'^[^a-záéíóúñA-ZÁÉÍÓÚÑ\s]{5,}$', prompt):
        return False, "La consulta no parece ser una pregunta válida. ¿Podrías reformularla?"
    
    # Verificar que tenga al menos algunas palabras reconocibles
    palabras = prompt.split()
    if len(palabras) < 2:
        return False, "Por favor, proporciona más contexto en tu consulta."
    
    return True, ""

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
        model_name="nomic-embed-text:latest",
        timeout=120
    )
    chroma_client = chromadb.PersistentClient(path="./demo-rag-chroma")
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
        metadata = split.metadata.copy()
        metadata["source"] = original_name
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
# LLM call mejorado
# ============================
def call_llm(context: str, prompt: str):
    ollama_client = ollama.Client(host='http://localhost:11434')
    
    enhanced_prompt = f"""
Contexto del documento PDF:
---
{context}
---

Pregunta del usuario: {prompt}

INSTRUCCIONES CRÍTICAS:
1. PRIMERO: Verifica si el contexto contiene información relacionada con la pregunta
   - Si NO hay relación, responde: "No encuentro información sobre [tema] en la documentación disponible"
   
2. Si hay información relevante:
   - Lee CUIDADOSAMENTE todo el contexto proporcionado
   - Si hay múltiples secciones o procedimientos, INCLÚYELOS TODOS
   - Si ves pasos numerados (1, 2, 3...), verifica que estén COMPLETOS
   - Incluye URLs exactas, comandos completos, credenciales mencionadas
   - Mantén el formato original del documento (listas, numeración, etc.)

3. NUNCA inventes información que no esté en el contexto

4. Si la pregunta es ambigua, pide aclaración antes de responder

Responde ahora de forma completa y precisa:
"""
    
    response = ollama_client.chat(
        model="qwen2.5:7b",
        stream=True,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": enhanced_prompt},
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
            # Crear carpeta media/pdfs si no existe
            pdf_folder = os.path.join(os.path.dirname(__file__), "media", "pdfs")
            os.makedirs(pdf_folder, exist_ok=True)
            
            # Guardar el PDF original
            pdf_path = os.path.join(pdf_folder, uploaded_file.name)
            with open(pdf_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Procesar para ChromaDB
            normalized_upload_file_name = uploaded_file.name.translate(
                str.maketrans({"-":"_", ".":"_", " ":"_"})
            )
            all_splits = procesar_pdf(uploaded_file)
            add_to_vector_collection(all_splits, normalized_upload_file_name, uploaded_file.name)
            
            st.success(f"✅ PDF procesado exitosamente")

# Área principal del chat
st.header("💬 Realiza tu Consulta")
prompt = st.text_area(
    "Escribe tu pregunta o solicitud:", 
    placeholder="Ejemplo: ¿Cómo configurar un canal privado en Roku?",
    height=120
)

pregunta_click = st.button("🚀 Preguntar", use_container_width=True, type="primary")

if pregunta_click and prompt:
    # Validar la consulta primero
    es_valida, mensaje_error = validar_consulta(prompt)
    
    if not es_valida:
        st.error(f"⚠️ {mensaje_error}")
        st.info("💡 Ejemplo de consulta válida: '¿Cómo instalar un canal privado en Roku?'")
    else:
        with st.spinner("🔍 Buscando información relevante..."):
            results = query_collection(prompt)
            context = results.get("documents")[0]
            relevant_text, relevant_text_ids = re_rank_cross_encoders(prompt, context)
        
        with st.spinner("✨ Generando respuesta..."):
            response = "".join(call_llm(context=relevant_text, prompt=prompt))

        # Mostrar respuesta con estilo mejorado
        st.success("✅ Respuesta generada:")
        
        # Contenedor con estilo personalizado para la respuesta
        st.markdown(
            f"""
            <div style="
                background-color: #f0f2f6;
                border-left: 5px solid #4CAF50;
                padding: 20px;
                border-radius: 10px;
                font-size: 16px;
                line-height: 1.6;
                margin: 20px 0;
            ">
                {response.replace(chr(10), '<br>')}
            </div>
            """,
            unsafe_allow_html=True
        )

        # Extraer PDFs fuente de los metadatas
        metadatas = results.get("metadatas")[0]
        pdf_sources = set()

        pdf_folder = os.path.join(os.path.dirname(__file__), "media", "pdfs")
        
        if os.path.exists(pdf_folder):
            archivos_disponibles = {f.lower(): f for f in os.listdir(pdf_folder)}
            
            for idx in relevant_text_ids:
                if idx < len(metadatas):
                    source = metadatas[idx].get("source", "")
                    
                    if source:
                        source_base = os.path.basename(source)
                        source_base = source_base.lower()
                        
                        # Intentar match directo
                        if source_base in archivos_disponibles:
                            pdf_sources.add(archivos_disponibles[source_base])
                        else:
                            # Intentar match aproximado
                            for archivo_key, archivo_real in archivos_disponibles.items():
                                if source_base.replace(".pdf", "") in archivo_key.replace(".pdf", ""):
                                    pdf_sources.add(archivo_real)
                                    break
                                source_normalizado = source_base.replace("_", "").replace("-", "").replace(".pdf", "")
                                archivo_normalizado = archivo_key.replace("_", "").replace("-", "").replace(".pdf", "")
                                if source_normalizado in archivo_normalizado or archivo_normalizado in source_normalizado:
                                    pdf_sources.add(archivo_real)
                                    break

        # Mostrar y ofrecer descarga de PDFs consultados
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