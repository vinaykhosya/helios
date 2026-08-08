"""
scripts/generate_valid_resume.py

Generates a valid binary PDF file for candidate Vinay Khosya using reportlab or clean PDF structure.
"""
import os
import sys

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def generate_pdf():
    pdf_path = os.path.join(base_dir, "Vinay_Khosya_Master_Resume.pdf")
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        c = canvas.Canvas(pdf_path, pagesize=letter)
        c.drawString(100, 750, "Vinay Khosya")
        c.drawString(100, 735, "Email: vinay.khosya.ug23@nsut.ac.in | Phone: +919996303072")
        c.drawString(100, 720, "LinkedIn: linkedin.com/in/vinaykhosya | GitHub: github.com/vinaykhosya")
        c.drawString(100, 690, "EDUCATION")
        c.drawString(100, 675, "Netaji Subhas University of Technology (NSUT Delhi) - B.Tech AI & ML (GPA 8.8)")
        c.drawString(100, 645, "EXPERIENCE & SKILLS")
        c.drawString(100, 630, "Machine Learning Engineer | Python, PyTorch, C++, Deep Learning, LLMs")
        c.drawString(100, 615, "Full Stack Web Automation & Autonomous Intelligence Engines")
        c.save()
        print(f"[SUCCESS] Generated valid PDF at {pdf_path}")
    except Exception as e:
        print(f"[PDF GENERATION ERROR] {e}")

if __name__ == "__main__":
    generate_pdf()
