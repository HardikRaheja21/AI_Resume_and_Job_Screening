<<<<<<< HEAD
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
=======
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
>>>>>>> e3761875c99d5c92134c9a9fa2255c256c20fb91
