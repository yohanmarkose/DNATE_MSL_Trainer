import json
import time
import streamlit as st
import requests, os, base64
from dotenv import load_dotenv
from litellm import completion
from io import StringIO
from dotenv import load_dotenv

load_dotenv()


# API_URL = os.getenv("API_DNS")
API_URL = "http://localhost:8000"

if "page" not in st.session_state:
    st.session_state.page = "Document Parser"
if "text_url" not in st.session_state:
    st.session_state.text_url = ""
if "file_upload" not in st.session_state:
    st.session_state.file_upload = None
if 'mode' not in st.session_state:
    st.session_state.mode = 'preview'
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'pdf_content' not in st.session_state:
    st.session_state.pdf_content = ""
if 'selected_file' not in st.session_state:
    st.session_state.selected_file = None
if 'preview_content' not in st.session_state:
    st.session_state.preview_content = ""
if 'file_selected' not in st.session_state:
    st.session_state.file_selected = False
 
def main():
    # Set up navigation
    st.sidebar.header("Main Menu")

    page = st.sidebar.radio("Choose a page:", ["Document Parser", "Chat with Documents","Logging Metrics"])
    
    st.session_state.page = page    
    if page == "Document Parser":
        document_parser_page()
    elif page == "Chat with Documents":
        chat_page()
    elif page == "Logging Metrics":
        athina_logging()

def athina_logging():
    import streamlit as st

    st.title("Athina Logging 📊")

    st.info("⚠️ If you have trouble observe the logs open [Athina AI](https://app.athina.ai/) or try logging in via Email OTP option")
    ATHINA_DATASET_URL = os.getenv("ATHINA_DATASET_URL")

    st.markdown(
        f"""
        <iframe src="{ATHINA_DATASET_URL}" width="100%" height="700px" style="border:none;"></iframe>
        """,
        unsafe_allow_html=True,
    )

 
    
def document_parser_page():
    # Set the title of the app
    st.title("Select PDF for Parsing... 📃")
            
    if "file_upload" not in st.session_state:
        st.session_state.file_upload = None
      
    st.session_state.file_upload = st.file_uploader("Choose a PDF File", type="pdf", accept_multiple_files=False)    
    convert = st.button("Process", use_container_width=True)
        
    # Define what happens on each page
    if convert:
        if st.session_state.file_upload:
            st.success(f"File '{st.session_state.file_upload.name}' uploaded successfully!")
            convert_PDF_to_markdown(st.session_state.file_upload)
        else:
            st.info("Please upload a PDF file.")
            
def chat_page():
    st.title("Chat with your parsed documents... 🤖")

    # Get available files from API
    try:
        response = requests.get(f"{API_URL}/list_pdfcontent")
        if response.status_code == 200:
            available_files = response.json()["files"]
        else:
            st.error("Error fetching available files")
            available_files = []
    except Exception as e:
        st.error(f"Error connecting to API: {e}")
        available_files = []
    
    model_options = {
        "OpenAI": "gpt-4o-mini",
        "GROK xAI": "xai/grok-2-latest",
        "Gemini": "r",
        "HuggingFace": "huggingface/Qwen/Qwen2.5-Coder-32B-Instruct"
    }

    # Model selection dropdown
    selected_model = st.sidebar.selectbox("Choose LLM", options=list(model_options.keys()))
    model_name = model_options[selected_model]
    
    # File selection
    selected_file = st.sidebar.selectbox(
        "Select PDF for Context",
        options=available_files,
    )
    
    # Update the session state only when the selection changes
    if selected_file != st.session_state.selected_file:
        st.session_state.selected_file = selected_file
    
    # Select PDF
    if st.sidebar.button("Select"):
        try:
            response = requests.post(
                f"{API_URL}/select_pdfcontent",
                json={
                    "selected_file": st.session_state.selected_file
                }
            )
            if response.status_code == 200:
                reset_state()
                st.session_state.pdf_content = response.json()["content"]
            else:
                st.error(f"Error in Upload: {response.text}")
        except Exception as e:
            st.sidebar.error(f"Error: {e}")
    if st.session_state.pdf_content:
        st.session_state.file_selected = True
        st.sidebar.markdown("Selected ✅")
    else:
        st.sidebar.markdown("Not Selected ❌")

    # Define a callback function for the toggle
    if st.session_state.file_selected:
        mode_options = ["preview", "chat"]
        current_index = 1 if st.session_state.mode == 'chat' else 0
        
        # callback function to ensure state updates correctly
        def on_mode_change():
            st.session_state.mode = st.session_state.mode_radio
        selected_mode = st.radio(
            "Mode",
            options=mode_options,
            index=current_index,
            format_func=lambda x: "Preview" if x == "preview" else "Chat",
            key="mode_radio",
            on_change=on_mode_change,
            horizontal=True
        )
        current_mode = st.session_state.mode
        
        if current_mode == 'preview':
            st.session_state.preview_content = f"### {st.session_state.selected_file} - Preview \n\n {st.session_state.pdf_content}"
            st.markdown(st.session_state.preview_content)

        # Chat Functionality
        if current_mode == 'chat':
            # Display chat messages
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
            
            # Chat input
            if prompt := st.chat_input("Ask a question about the documents..."):
                # Add user message
                st.session_state.messages.append({"role": "user", "content": prompt})
                
                with st.chat_message("user"):
                    st.markdown(prompt)
                
                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        try:
                            response = requests.post(
                                f"{API_URL}/ask_question",
                                json={
                                    "question": prompt,
                                    "selected_file": st.session_state.pdf_content,
                                    "model": model_name
                                }
                            )
                            
                            if response.status_code == 200:
                                answer = response.json()["answer"]
                                st.markdown(answer)
                                st.session_state.messages.append({"role": "assistant", "content": answer})
                            else:
                                error_message = f"Error: {response.text}"
                                st.error(error_message)
                                st.session_state.messages.append({"role": "assistant", "content": error_message})
                        except Exception as e:
                            error_message = f"Error: {str(e)}"
                            st.error(error_message)
                            st.session_state.messages.append({"role": "assistant", "content": error_message})
            # Summarize button
            if st.button("Summarize"):
                with st.chat_message("assistant"):
                    with st.spinner("Generating Summary..."):
                        try:
                            response = requests.post(
                                f"{API_URL}/summarize",
                                json={
                                    "selected_file": st.session_state.pdf_content,
                                    "model": model_name
                                }
                            )
                            if response.status_code == 200:
                                summary = response.json()["summary"]
                                st.markdown(summary)
                                st.session_state.messages.append({"role": "assistant", "content": summary})
                            else:
                                error_message = f"Error: {response.text}"
                                st.error(error_message)
                                st.session_state.messages.append({"role": "assistant", "content": error_message})
                        except Exception as e:
                            error_message = f"Error: {str(e)}"
                            st.error(error_message)
                            st.session_state.messages.append({"role": "assistant", "content": error_message})

        # Reset chat button
        if st.sidebar.button("Reset Chat"):
            reset_state()
            st.session_state.file_selected = False

def reset_state():
    st.session_state.messages = []
    st.session_state.pdf_content = ""
    st.session_state.preview_content = ""
    st.session_state.mode = 'preview'
        
def convert_PDF_to_markdown(file_upload):    
    progress_bar = st.progress(0)
    progress_text = st.empty()
    
    progress_text.text("Uploading file...")
    progress_bar.progress(20)

    if file_upload is not None:
        bytes_data = file_upload.read()
        base64_pdf = base64.b64encode(bytes_data).decode('utf-8')
        
        progress_text.text("Sending file for processing...")
        progress_bar.progress(50)

        response = requests.post(f"{API_URL}/upload_pdf", json={"file": base64_pdf, "file_name": file_upload.name, "model": ""})
        
        progress_text.text("Processing document...")
        progress_bar.progress(75)
        
        try:
            if response.status_code == 200:
                data = response.json()
                progress_text.text("Finalizing output...")
                st.subheader(data["message"])
                st.markdown(data["scraped_content"], unsafe_allow_html=True)
            else:
                st.error("Server not responding.")
        except:
            st.error("An error occurred while processing the PDF.")
    
    progress_bar.progress(100)
    progress_text.empty()
    progress_bar.empty()        
    
if __name__ == "__main__":
# Set page configuration
    st.set_page_config(
        page_title="Document Parser",
        layout="wide",
        initial_sidebar_state="expanded"
    )    
    main()