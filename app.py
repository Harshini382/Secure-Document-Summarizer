import streamlit as st
import boto3
import json
import fitz  # PyMuPDF
import docx  # python-docx
import io

bedrock_client = boto3.client("bedrock-runtime", region_name="us-east-1")

def summarize_text(text):
    model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"
    prompt = f"Please summarize the following document:\n\n{text}"
    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 500,
        "temperature": 0.3
    }
    body = json.dumps(payload)
    response = bedrock_client.invoke_model(
        modelId=model_id,
        contentType="application/json",
        accept="application/json",
        body=body.encode("utf-8")
    )
    response_body = response['body'].read().decode('utf-8')
    response_json = json.loads(response_body)
    summary = response_json.get("content", "No summary generated.")
    if isinstance(summary, list) and len(summary) > 0:
        summary = summary[0]
    if isinstance(summary, str):
        summary = summary.strip()
    else:
        summary = str(summary)
    return summary

def extract_text_from_pdf(file_bytes):
    pdf_stream = io.BytesIO(file_bytes)
    text = ""
    with fitz.open(stream=pdf_stream, filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()
    return text

def extract_text_from_docx(file_bytes):
    file_stream = io.BytesIO(file_bytes)
    doc = docx.Document(file_stream)
    return "\n".join([para.text for para in doc.paragraphs])

st.set_page_config(page_title="📄 Multi-format Document Summarizer", layout="centered")

st.title("📄 Multi-format Document Summarizer")
st.markdown("Upload a `.txt`, `.pdf`, or `.docx` file, and get a concise summary powered by **Claude 3.5 Sonnet on AWS Bedrock**.")

# Add a unique key to the uploader so it resets when you upload new files
uploaded_file = st.file_uploader("Upload your file", type=["txt", "pdf", "docx"], key="file_uploader")

if uploaded_file is not None:
    try:
        # Read bytes once per file upload
        file_bytes = uploaded_file.read()
        mime_type = uploaded_file.type
        filename = uploaded_file.name
        filesize = uploaded_file.size

        st.write(f"Uploaded file MIME type: {mime_type}")

        if mime_type == "text/plain":
            file_content = file_bytes.decode("utf-8")
        elif mime_type == "application/pdf":
            file_content = extract_text_from_pdf(file_bytes)
        elif mime_type == "application/octet-stream" and filename.lower().endswith(".pdf"):
            file_content = extract_text_from_pdf(file_bytes)
        elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            file_content = extract_text_from_docx(file_bytes)
        else:
            st.error("Unsupported file type.")
            st.stop()

        st.markdown(f"**Filename:** {filename}  \n**File size:** {filesize} bytes")

        with st.spinner("Summarizing your document..."):
            summary = summarize_text(file_content)
            st.success("✅ Summary generated successfully!")

        with st.expander("Show Uploaded Text"):
            st.text_area("Uploaded Text", file_content, height=250)

        if summary:
            with st.expander("Show Summary"):
                st.text_area("Summary", summary, height=250)

    except Exception as e:
        st.error(f"⚠️ Error during processing or summarization: {e}")

else:
    st.info("Please upload a `.txt`, `.pdf`, or `.docx` file to summarize.")
