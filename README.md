# 🚀 AI-Based Resume Screening & Job Matching System

An AI-powered resume shortlisting system that automatically parses, analyzes, and matches resumes with job descriptions using Natural Language Processing (NLP) and Machine Learning techniques.

---

## ⚙️ Tech Stack

| Component | Technology |
|------------|-------------|
| **Frontend (Future)** | React.js |
| **Backend** | Node.js + Express *(Developed by Ashish Agrawal)* |
| **Parser Service** | Python + SpaCy + Scikit-learn *(Developed by Hardik Raheja)* |
| **Database** | MongoDB |
| **Version Control** | Git & GitHub |
| **Environment** | Virtualenv (Python), npm (Node.js) |

---

## 🧩 Core Logic Overview

1. **Upload Resume / JD** → via API endpoint  
2. **Extract Text** → PDF/DOCX parsed using PyPDF2 / docx  
3. **Process with SpaCy** → Extract entities like skills, names, and experience  
4. **Vectorize (TF-IDF)** → Compare similarity between resume and job description  
5. **Return Matching Score** → Backend sends JSON response with ranked candidates  

---

## 🌱 Future Enhancements

- 🧠 Integrate *LLM-based Resume Scoring (Gemini / GPT)*  
- ☁️ *Deploy* backend and parser on *AWS Lambda / EC2*  
- 📊 Add *Admin Dashboard* for viewing shortlisted candidates  
- 🔒 Include *Authentication & Role-based Access*

---

## 👥 Team

| Member | Role |
|---------|------|
| **Ashish Agrawal** | Core Developer – *Backend Development (Node.js + Express)*, *Frontend & API Testing*  |
| **Hardik Raheja** | Core Developer – *NLP Integration (Python + SpaCy)*, *Frontend & API Testing* |

---
## 🛠️ Setup Instructions

### Backend (Node.js)
```bash
cd backend
npm install
node server.js



## 🧠 Parser Service (Python)

### Setup Instructions
```bash
cd parser_service
pip install -r requirements.txt
uvicorn main:app --reload








Then open your browser and visit:  
👉 [http://localhost:8000/docs](http://localhost:8000/docs) *(for API testing)*

---

## 🏗️ Deployment Plan

- Deploy backend on **AWS EC2**
- Use **NGINX** as a reverse proxy
- Host parser microservice using **FastAPI + Docker**
- Connect both services via **REST endpoints**

---

## 🏁 Status

✅ **Core logic completed**  
🧩 **Integration & deployment — Next phase**

---

## 📫 Contact

**Hardik Raheja**  
📧 [hardik.21raheja@gmail.com]
🌐 [LinkedIn](https://linkedin.com/in/hardikraheja21)  
📍 *Mathura, India*
