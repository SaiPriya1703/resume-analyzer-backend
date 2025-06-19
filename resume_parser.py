import fitz  # PyMuPDF

def extract_text_from_pdf(file_path):
    text = ""
    try:
        doc = fitz.open(file_path)
        for page in doc:
            text += page.get_text()
    except Exception as e:
        text = f"Error extracting text: {e}"
    return text
