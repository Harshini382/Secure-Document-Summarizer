import json
import boto3
import os
import tempfile
from botocore.exceptions import ClientError
from PyPDF2 import PdfReader
from docx import Document

s3 = boto3.client('s3')
bedrock = boto3.client('bedrock-runtime')

def extract_text_from_pdf(file_path):
    text = []
    with open(file_path, 'rb') as f:
        reader = PdfReader(f)
        for page in reader.pages:
            text.append(page.extract_text() or "")
    return "\n".join(text)

def extract_text_from_docx(file_path):
    doc = Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs])

def extract_text_from_txt(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def lambda_handler(event, context):
    bucket = event.get('bucket')
    key = event.get('key')

    if not bucket or not key:
        return {
            'statusCode': 400,
            'body': 'Missing bucket or key in event'
        }

    # Download file from S3
    try:
        tmp_file = os.path.join(tempfile.gettempdir(), os.path.basename(key))
        s3.download_file(bucket, key, tmp_file)
    except ClientError as e:
        return {
            'statusCode': 500,
            'body': f'Error downloading file from S3: {e}'
        }

    ext = key.lower().split('.')[-1]
    if ext == 'pdf':
        text = extract_text_from_pdf(tmp_file)
    elif ext == 'docx':
        text = extract_text_from_docx(tmp_file)
    elif ext == 'txt':
        text = extract_text_from_txt(tmp_file)
    else:
        return {
            'statusCode': 400,
            'body': f'Unsupported file extension: {ext}'
        }

    if not text.strip():
        return {
            'statusCode': 400,
            'body': 'No text extracted from the document'
        }

    # Call Bedrock Cohere model
    try:
        response = bedrock.invoke_model(
            modelId="cohere.command-text-v14",
            contentType="application/json",
            accept="application/json",
            body=json.dumps({
                "prompt": f"summarize this:\n\n{text}\n\nSummary:",
                "max_tokens_to_sample": 200
            })
        )
        result = json.loads(response['body'].read())
        summary = result.get('completion', 'No summary returned')
    except Exception as e:
        return {
            'statusCode': 500,
            'body': f'Error calling Bedrock model: {e}'
        }

    return {
        'statusCode': 200,
        'body': summary
    }
