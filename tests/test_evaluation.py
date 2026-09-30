import unittest
from app.services.matcher import basic_match_score, tfidf_cosine_score
from app.services.skill_extractor import extract_skills

class TestEvaluation(unittest.TestCase):
    def setUp(self):
        self.resumes = [
            {"id": 1, "text": "Experienced Python developer with Django and SQL.", "label_role": "Backend Developer"},
            {"id": 2, "text": "Data scientist skilled in Python, Pandas, and Machine Learning.", "label_role": "Data Scientist"},
            {"id": 3, "text": "Frontend engineer with React, JavaScript, and CSS.", "label_role": "Frontend Developer"},
            {"id": 4, "text": "DevOps engineer with Docker, Kubernetes, and AWS.", "label_role": "DevOps Engineer"},
            {"id": 5, "text": "Full stack developer using Node.js, Express, and MongoDB.", "label_role": "Full Stack Developer"},
            {"id": 6, "text": "Java backend developer with Spring Boot and Hibernate.", "label_role": "Backend Developer"},
            {"id": 7, "text": "Machine Learning Engineer with PyTorch, TensorFlow, and Python.", "label_role": "Machine Learning Engineer"},
            {"id": 8, "text": "UI/UX designer proficient in Figma, Adobe XD, and Sketch.", "label_role": "UI/UX Designer"},
            {"id": 9, "text": "Cybersecurity analyst with experience in Pen Testing and Wireshark.", "label_role": "Security Analyst"},
            {"id": 10, "text": "Cloud Architect with GCP, Azure, and AWS experience.", "label_role": "Cloud Architect"},
        ]
        
        self.jobs = [
            {"id": 101, "desc": "Looking for a Backend Developer with Python and SQL experience.", "target": "Backend Developer"},
            {"id": 102, "desc": "Data Scientist needed. Must know Python, Pandas, and Machine Learning.", "target": "Data Scientist"},
        ]

    def test_evaluation_metrics(self):
        # Dummy test to evaluate matching on the set
        correct_matches = 0
        total = len(self.jobs)
        
        for job in self.jobs:
            job_skills = extract_skills(job["desc"])
            best_match_id = None
            highest_score = -1
            
            for resume in self.resumes:
                resume_skills = extract_skills(resume["text"])
                b_score = basic_match_score(resume_skills, job_skills)
                c_score = tfidf_cosine_score(resume["text"], job["desc"])
                combined = (b_score + c_score) / 2
                
                if combined > highest_score:
                    highest_score = combined
                    best_match_id = resume["id"]
                    
            # Check if the best match label matches the job target
            best_resume = next(r for r in self.resumes if r["id"] == best_match_id)
            if best_resume["label_role"] == job["target"]:
                correct_matches += 1
                
        accuracy = correct_matches / total
        self.assertGreaterEqual(accuracy, 0.5)  # We expect at least 50% accuracy

if __name__ == '__main__':
    unittest.main()
