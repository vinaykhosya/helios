"""
ai/engines/resume/latex_renderer.py

LaTeXRenderer — Substitutes placeholders in LaTeX template files and sanitizes special characters.
"""
from __future__ import annotations

import os


class LaTeXRenderer:
    """
    Renders LaTeX documents safely by substituting template variables.
    """

    LATEX_SPECIAL_CHARS = {
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }

    def escape_latex(self, text: str) -> str:
        """
        Escapes LaTeX special characters in raw strings.
        """
        if not text:
            return ""

        res = []
        for char in text:
            res.append(self.LATEX_SPECIAL_CHARS.get(char, char))
        return "".join(res)

    def render(self, template_path: str, variables: dict[str, str], sanitize: bool = True) -> str:
        """
        Reads template_path and substitutes all {{VARIABLE_NAME}} tokens.

        Args:
            template_path: Absolute or relative path to .tex template file.
            variables: Key-value dictionary of template variables.
            sanitize: If True, escapes LaTeX special characters in string values.

        Returns:
            Rendered LaTeX content string.
        """
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"LaTeX template file not found: {template_path}")

        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()

        for key, val in variables.items():
            token = f"{{{{{key}}}}}"
            val_str = str(val) if val is not None else ""

            # Don't sanitize raw LaTeX commands like \item or formatting tags
            if sanitize and not key.endswith("_LATEX") and not key.startswith("RAW_"):
                val_str = self.escape_latex(val_str)

            content = content.replace(token, val_str)

        return content
