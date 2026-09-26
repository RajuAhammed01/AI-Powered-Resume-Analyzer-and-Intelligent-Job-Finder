import pdfplumber
from docx import Document


def extract_text(filepath):
	if filepath.lower().endswith(".pdf"):
		return extract_pdf(filepath)
	if filepath.lower().endswith(".docx"):
		return extract_docx(filepath)
	return ""


def extract_pdf(filepath):
	pages = []
	with pdfplumber.open(filepath) as pdf:
		for page in pdf.pages:
			pages.append(page.extract_text() or "")
	return "\n".join(pages)


def extract_docx(filepath):
	document = Document(filepath)
	return "\n".join(paragraph.text for paragraph in document.paragraphs)
