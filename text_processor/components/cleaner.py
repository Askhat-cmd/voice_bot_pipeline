from __future__ import annotations

import re


class Cleaner:
    """Utility class for text cleaning operations."""

    def light_clean(self, text: str) -> str:
        """Performs a light cleanup of the provided text."""
        replacements = [
            ("[музыка]", ""), ("[Music]", ""), (">>", ""), ("&gt;&gt;", ""),
        ]
        speech_fixes = [
            (" ээ ", " "), (" э-э ", " "), (" эээ ", " "), (" ээээ ", " "),
            (" ах ", " "), (" ох ", " "), (" ух ", " "), (" эх ", " "),
            (" мм ", " "), (" хм ", " "), (" ну ", " "),
            ("Ээ, ", ""), ("Эх, ", ""), ("Ох, ", ""), ("Ах, ", ""),
            (" ээ,", ","), (" ох,", ","), (" ах,", ","),
            ("пото что", "потому что"),
            ("новосте", "новости"),
            ("боговесть", "божественность"),
            ("потму что", "потому что"),
            ("тоесть", "то есть"),
            ("вобще", "вообще"),
            (" вот вот ", " вот "), (" это это ", " это "),
            (" да да ", " да "), (" ну ну ", " ну "),
            ("мало ли что", ""), ("я не знаю, ", ""),
            ("как бы ", " "), ("типа ", " "),
            ("короче говоря", "короче"),
        ]
        cleaned = text
        for old, new in replacements + speech_fixes:
            cleaned = cleaned.replace(old, new)
        cleaned = re.sub(r"\s+", " ", cleaned)
        cleaned = re.sub(r"\s*,\s*,", ",", cleaned)
        cleaned = re.sub(r"\s*\.\s*\.", ".", cleaned)
        return cleaned.strip()

    def final_polish(self, text: str) -> str:
        """Applies final polish to the text removing filler words."""
        paragraphs = text.split("\n")
        polished_paragraphs = []
        for para in paragraphs:
            if not para.strip():
                polished_paragraphs.append(para)
                continue
            words = para.split()
            vot_count = words.count("вот")
            if vot_count > 3:
                vot_removed = 0
                for i, word in enumerate(words):
                    if word == "вот" and vot_removed < vot_count // 2:
                        words[i] = ""
                        vot_removed += 1
            eto_count = words.count("это")
            if eto_count > 5:
                eto_removed = 0
                for i, word in enumerate(words):
                    if word == "это" and eto_removed < eto_count // 3:
                        words[i] = ""
                        eto_removed += 1
            nu_pattern = []
            for i, word in enumerate(words):
                if word == "ну" and (i == 0 or words[i-1].endswith(".") or words[i-1].endswith("!")):
                    if len(nu_pattern) % 2 == 1:
                        words[i] = ""
                    nu_pattern.append(i)
            polished_paragraphs.append(" ".join(w for w in words if w))
        return "\n".join(polished_paragraphs)

    def clean(self, text: str) -> str:
        """Convenience wrapper performing light clean followed by final polish."""
        return self.final_polish(self.light_clean(text))
