
---

## ⚙️ Tech Stack

| Component | Technology |
|------------|-------------|
| **Frontend (Future)** | React.js |
| **Backend** | Node.js + Express |
| **Parser Service** | Python + SpaCy + Scikit-learn |
| **Database** | MongoDB |
| **Version Control** | Git & GitHub |
| **Environment** | Virtualenv (Python), npm (Node.js) |

---

## 🧩 Core Logic Overview

1. **Upload Resume / JD** → via API endpoint.  
2. **Extract Text** → PDF/DOCX parsed using PyPDF2 / docx.  
3. **Process with SpaCy** → Extract entities like skills, names, and experience.  
4. **Vectorize (TF-IDF)** → Compare similarity between resume and job description.  
5. **Return Matching Score** → Backend sends JSON response with ranked candidates.

---

## 🌱 Future Enhancements

- 🧠 Integrate **LLM-based Resume Scoring (Gemini / GPT)**  
- ☁️ **Deploy** backend and parser on **AWS Lambda / EC2**  
- 📊 Add **Admin Dashboard** for viewing shortlisted candidates  
- 🔒 Include **Authentication & Role-based Access**

---

## 👥 Team

- **Hardik Raheja** — Core Developer (Backend & NLP Integration) , Frontend / API testing  

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
📧 [hardik.21raheja@gmail.com](mailto:hardik.21raheja@gmail.com)  
🌐 [LinkedIn](https://linkedin.com/in/hardikraheja21)  
📍 *Mathura, India*
