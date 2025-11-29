from typing import List
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
import spacy
from sentence_transformers import SentenceTransformer, util
import PyPDF2
import docx

app = FastAPI(title="Resume Parser API")

# Load SpaCy English model
nlp = spacy.load("en_core_web_sm")

# Load the semantic model
model = SentenceTransformer('all-MiniLM-L6-v2')


def extract_text_from_pdf(file):
    """Extract text from PDF using PyPDF2"""
    reader = PyPDF2.PdfReader(file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text


def extract_text_from_docx(file):
    """Extract text from DOCX"""
    doc = docx.Document(file)
    return "\n".join([para.text for para in doc.paragraphs])


@app.get("/")
def home():
    return {"message": "Resume Parser API is running"}


@app.post("/parse_resume")
async def parse_resume(
    resumes: List[UploadFile] = File(...),
    job_description: str = Form(...)
):
    """Parse multiple resumes and compare with job description"""
    results = []

    for resume in resumes:
        # Extract text based on format
        if resume.filename.endswith(".pdf"):
            text = extract_text_from_pdf(resume.file)
        elif resume.filename.endswith(".docx"):
            text = extract_text_from_docx(resume.file)
        elif resume.filename.endswith(".txt"):
            text = resume.file.read().decode("utf-8", errors="ignore")
        else:
            return JSONResponse(status_code=400, content={"error": f"Unsupported file: {resume.filename}"})

        # NLP processing
        doc = nlp(text)

        # Extract top-level keywords (nouns and proper nouns)
        skills = [token.text.lower() for token in doc if token.pos_ in ["NOUN", "PROPN"]]

        # Extract name (PERSON entity)
        name = "Unknown"
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                name = ent.text
                break

        # Experience extraction (simple keyword check)
        experience = "2+ years" if "experience" in text.lower() else "Unknown"

        # Compute semantic similarity between JD and resume
        embeddings = model.encode([job_description, text], convert_to_tensor=True)
        score = util.cos_sim(embeddings[0], embeddings[1]).item() * 100

        # Append result
        results.append({
            "filename": resume.filename,
            "name": name,
            "skills": list(set(skills))[:10],
            "experience": experience,
            "score": round(score, 2)
        })

    # Sort leaderboard by score (highest first)
    results.sort(key=lambda x: x["score"], reverse=True)

    return {"leaderboard": results}
