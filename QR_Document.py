import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import google.generativeai as genai
from langchain.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Fonction pour extraire le texte des fichiers PDF
def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

# Découpage du texte en morceaux
def get_text_chunks(text):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1000)
    return text_splitter.split_text(text)

# Création d'un index vectoriel
def get_vector_store(text_chunks):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
    vector_store.save_local("faiss_index")

# Création de la chaîne de conversation
def get_conversational_chain():
    prompt_template = """
    Réponse:Répondez à la question de la manière la plus détaillée possible à partir du contexte fourni, assurez-vous de fournir tous les détails possible, si la réponse n'est pas dans le contexte fourni, dites simplement « la réponse n'est pas dans le contexte fourni», ne donnez pas la mauvaise réponse\n\n.
    
    ### Contexte :
    {context}
    
    ### Question :
    {question}
    
    ### Réponse :
    """
    
    model = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.3)
    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
    return load_qa_chain(model, chain_type="stuff", prompt=prompt)

# Gestion des questions utilisateur avec historique
def user_input(user_question):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    new_db = FAISS.load_local("faiss_index", embeddings)
    docs = new_db.similarity_search(user_question)
    
    chain = get_conversational_chain()
    response = chain({"input_documents": docs, "question": user_question}, return_only_outputs=True)
    
    # Sauvegarde de l'historique
    if "history" not in st.session_state:
        st.session_state.history = []
    st.session_state.history.append((user_question, response["output_text"]))
    
    return response["output_text"]

# Interface principale
def main():
    st.set_page_config(page_title="Chat PDF", layout="wide")
    st.title("📄💬 Système de Questions-Réponses basé sur des Documents")
    
    st.markdown("**Interrogez vos fichiers PDF et obtenez des réponses instantanées dans le contexte de vos documents.**")
    
    with st.sidebar:
        st.header("📂 Télécharger des fichiers PDF")
        pdf_docs = st.file_uploader("**Importez un ou plusieurs PDF**", accept_multiple_files=True)
        
        if st.button("📥 Soumettre et Lancer"):
            if pdf_docs:
                with st.spinner("📄 Extraction du texte et génération des embeddings..."):
                    raw_text = get_pdf_text(pdf_docs)
                    text_chunks = get_text_chunks(raw_text)
                    get_vector_store(text_chunks)
                    st.success("✅ Analyse terminée. Vous pouvez poser vos questions !")
            else:
                st.warning("⚠️ Veuillez importer au moins un fichier PDF.")
    
    user_question = st.text_input("🔎 Posez votre question :")
    if user_question:
        response = user_input(user_question)
        st.markdown("### Réponse :")
        st.success(response)
    
    # Affichage de l'historique
    if "history" in st.session_state and st.session_state.history:
        st.markdown("## 📜 Historique des Questions")
        for q, r in reversed(st.session_state.history):
            with st.expander(f"❓ {q}"):
                st.write(r)

if __name__ == "__main__":
    main()
