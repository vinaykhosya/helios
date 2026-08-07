"""
tests/unit/ai/engines/resume/test_latex_renderer.py

Unit tests for LaTeXRenderer template substitution and escaping.
"""
import os
import tempfile
from ai.engines.resume.latex_renderer import LaTeXRenderer


def test_latex_renderer_escaping():
    renderer = LaTeXRenderer()
    raw = "C++ & Python_Dev (100% $bonus)"
    escaped = renderer.escape_latex(raw)
    assert r"\&" in escaped
    assert r"\_" in escaped
    assert r"\%" in escaped
    assert r"\$" in escaped


def test_latex_renderer_render():
    renderer = LaTeXRenderer()
    template_content = r"\name{{{CANDIDATE_NAME}}}\company{{{COMPANY_NAME}}}"

    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".tex") as tmp:
        tmp.write(template_content)
        tmp_path = tmp.name

    try:
        res = renderer.render(tmp_path, {
            "CANDIDATE_NAME": "Vinay Khosya",
            "COMPANY_NAME": "Acme & Co",
        })
        assert r"\name{Vinay Khosya}" in res
        assert r"\company{Acme \& Co}" in res
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
