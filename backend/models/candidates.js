import mongoose from "mongoose";

const candidateSchema = new mongoose.Schema({
  name: String,
  email: String,
  skills: [String],
  experience: String,
  score: Number
});

const Candidate = mongoose.model("Candidate", candidateSchema);
export default Candidate;
