"""
automation/fillers/semantic_filler.py

Helios Semantic Form Engine & Question Answering Decision Hierarchy.
- Inspects DOM element attributes (ARIA labels, placeholders, labels, autocomplete).
- Maps fields to CandidateProfile attributes.
- Implements strict Question Answering Decision Hierarchy:
  Memory -> CandidateProfile -> Deterministic Rules -> Groq 70B -> RECOVERY_REQUIRED.
"""
from typing import Dict, Any, Tuple, Optional

DEFAULT_CANDIDATE_PROFILE = {
    "name": "Vinay Khosya",
    "first_name": "Vinay",
    "last_name": "Khosya",
    "email": "vinay.khosya.ug23@nsut.ac.in",
    "phone": "+919996303072",
    "org": "Netaji Subhas University of Technology (NSUT)",
    "degree": "B.Tech in Artificial Intelligence & Machine Learning",
    "graduation_year": 2027,
    "experience_years": 2,
    "work_authorization_india": True,
    "sponsorship_required": False,
    "linkedin": "https://linkedin.com/in/vinaykhosya",
    "github": "https://github.com/vinaykhosya",
    "website": "https://vinaykhosya.com"
}

VERIFIED_MEMORY_QA = {
    "are you legally authorized to work in india": "Yes",
    "do you now or in the future require sponsorship for employment visa status": "No",
    "highest degree completed": "B.Tech",
    "university name": "Netaji Subhas University of Technology (NSUT), Delhi"
}


class SemanticFormEngine:
    def __init__(self, profile: Dict[str, Any] = None):
        self.profile = profile or DEFAULT_CANDIDATE_PROFILE

    def resolve_question(self, question_text: str) -> Tuple[Optional[str], str, float]:
        """
        Executes strict Q&A Decision Hierarchy:
        1. Exact Memory Match
        2. Candidate Profile Attribute Derivation
        3. Deterministic Rules
        4. Low Confidence -> RECOVERY_REQUIRED
        Returns: (answer_string, source_type, confidence_score)
        """
        q_clean = question_text.lower().strip().rstrip("?").rstrip(":")

        # 1. Exact Memory Match
        for mem_q, mem_ans in VERIFIED_MEMORY_QA.items():
            if mem_q in q_clean:
                return (mem_ans, "MEMORY", 1.0)

        # 2. Candidate Profile Attribute Derivation
        if "sponsorship" in q_clean:
            ans = "No" if not self.profile.get("sponsorship_required") else "Yes"
            return (ans, "CANDIDATE_PROFILE", 0.99)
        
        if "authorized to work" in q_clean or "work authorization" in q_clean:
            ans = "Yes" if self.profile.get("work_authorization_india") else "No"
            return (ans, "CANDIDATE_PROFILE", 0.99)

        if "graduation" in q_clean or "graduating" in q_clean:
            return (str(self.profile.get("graduation_year", 2027)), "CANDIDATE_PROFILE", 0.95)

        if "experience" in q_clean and "years" in q_clean:
            return (str(self.profile.get("experience_years", 2)), "CANDIDATE_PROFILE", 0.95)

        # 3. Low Confidence -> RECOVERY_REQUIRED (Never hallucinate factual personal data)
        return (None, "RECOVERY_REQUIRED", 0.0)
