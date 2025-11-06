import express from "express";
import axios from "axios";
import Candidate from "../models/Candidate.js";

const router = express.Router();

router.post("/upload", async (req, res) => {
  try {
    const { resumeText, jobDescription } = req.body;
    const response = await axios.post("http://127.0.0.1:8000/parse_resume", { resumeText, jobDescription });
    const { name, skills, experience, score } = response.data;

    const candidate = new Candidate({ name, skills, experience, score });
    await candidate.save();

    res.status(201).json({ message: "Resume processed successfully", candidate });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

router.get("/leaderboard", async (req, res) => {
  try {
    const leaderboard = await Candidate.find().sort({ score: -1 });
    res.json(leaderboard);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

export default router;
