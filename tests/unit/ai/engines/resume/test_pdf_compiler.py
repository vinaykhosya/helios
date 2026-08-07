"""
tests/unit/ai/engines/resume/test_pdf_compiler.py

Unit tests for PDFCompiler subprocess execution and error handling.
"""
import os
import pytest
from ai.engines.resume.pdf_compiler import PDFCompiler, PDFCompilationError


@pytest.mark.asyncio
async def test_pdf_compiler_simulated_or_real(tmp_path):
    compiler = PDFCompiler(output_dir=str(tmp_path), engine="lualatex")
    latex_sample = r"\documentclass{article}\begin{document}Hello Helios\end{document}"

    pdf_path = await compiler.compile(latex_sample, output_name="test_resume")
    assert os.path.exists(pdf_path)
    assert pdf_path.endswith(".pdf")


@pytest.mark.asyncio
async def test_pdf_compiler_custom_output_dir(tmp_path):
    out_dir = tmp_path / "custom_out"
    compiler = PDFCompiler(output_dir=str(out_dir))
    latex_sample = r"\documentclass{article}\begin{document}Hello World\end{document}"

    pdf_path = await compiler.compile(latex_sample, output_name="custom_test")
    assert os.path.exists(pdf_path)
    assert str(out_dir) in pdf_path
