"""
resume_reader.py

Job of this file: open a PDF or DOCX resume file and pull out the plain text.
Nothing smart happens here - no AI, just "open file -> get text".
"""

from pypdf import PdfReader
import docx


def read_pdf(file_path):
    """Read a PDF file and return all its text as one string."""
    reader = PdfReader(file_path)
    all_text = ""
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            all_text += page_text + "\n"
    return all_text


def read_docx(file_path):
    """Read a DOCX (Word) file and return all its text as one string."""
    document = docx.Document(file_path)
    all_text = ""
    for paragraph in document.paragraphs:
        all_text += paragraph.text + "\n"
    return all_text


def read_resume(file_path):
    """
    Main function to use. Looks at the file extension (.pdf or .docx)
    and calls the right reader function.
    """
    if file_path.lower().endswith(".pdf"):
        text = read_pdf(file_path)
    elif file_path.lower().endswith(".docx"):
        text = read_docx(file_path)
    else:
        raise ValueError("File must be a .pdf or .docx file")

    if text.strip() == "":
        raise ValueError("Could not find any text in this file")

    return text


# quick test - only runs if you run THIS file directly
if __name__ == "__main__":
    # change this path to a real resume file on your computer to test
    sample_path = r"C:\Users\prasa\Downloads\resume_archive\data\data\INFORMATION-TECHNOLOGY\36856210.pdf"
    text = read_resume(sample_path)
    print(text)
