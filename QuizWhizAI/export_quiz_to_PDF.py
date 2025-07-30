from fpdf import FPDF, HTMLMixin


class QuizPDF(FPDF, HTMLMixin):
    def __init__(self, quiz_title):
        super().__init__()
        self.quiz_title = quiz_title
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, self.quiz_title, ln=True, align="C")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


def generate_quiz_pdf(quiz_data, quiz_title="Quiz", output_path="quiz.pdf"):
    pdf = QuizPDF(quiz_title)
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)

    # Quiz Questions Section
    for idx, q in enumerate(quiz_data, start=1):
        pdf.set_font("Helvetica", "B", 12)
        pdf.multi_cell(0, 8, f"{idx}. {q['question']}")
        pdf.set_font("Helvetica", "", 11)
        if q.get("options"):
            for opt in q["options"]:
                pdf.multi_cell(0, 6, f"    - {opt}")
        pdf.ln(3)

    # Answers and Explanations Section
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Answers & Explanations", ln=True)
    pdf.ln(4)

    for idx, q in enumerate(quiz_data, start=1):
        pdf.set_font("Helvetica", "B", 12)
        pdf.multi_cell(0, 7, f"{idx}. Correct Answer: {q['answer']}")
        pdf.set_font("Helvetica", "", 11)
        explanation = q.get("explanation", "No explanation provided.")
        pdf.multi_cell(0, 6, f"Explanation: {explanation}")
        pdf.ln(3)

    pdf.output(output_path)
