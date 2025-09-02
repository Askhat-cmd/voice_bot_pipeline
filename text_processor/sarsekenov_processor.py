#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sarsekenov-Specific Subtitle Processor
Адаптация под лекции Саламата Сарсекенова (нейросталкинг / неосталкинг)
Сохраняет стиль, терминологию и ключевые концепции направления.
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import orjson
import tiktoken
from openai import OpenAI

"""
Позволяет работать как напрямую по .json субтитрам, так и автоматически
извлекать субтитры по URL из файла urls.txt в корне проекта.
"""

# Добавляем корень проекта (.. от text_processor) в sys.path для импорта утилит
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from env_utils import load_env
from subtitle_extractor.get_subtitles import YouTubeSubtitlesExtractor


def _hms(seconds: Optional[float]) -> Optional[str]:
    if seconds is None:
        return None
    seconds = int(seconds)
    return f"{seconds//3600:02d}:{(seconds%3600)//60:02d}:{seconds%60:02d}"


class SarsekenovProcessor:
    """Специализированный процессор под лекции С. Сарсекенова.

    Фокус на терминах и концепциях: нейросталкинг, неосталкинг,
    наблюдение за умом, внимание, метанаблюдение, паттерны, триггеры,
    поле внимания, осознавание, исследование переживаний, практики и упражнения.
    """

    def __init__(self, primary_model: str = "gpt-4o-mini", refine_model: str = "gpt-5-mini"):
        load_env()
        self.primary_model = primary_model
        self.refine_model = refine_model
        self.client = OpenAI()
        self.encoding = tiktoken.get_encoding("cl100k_base")

        # Доменные указания для более точной обработки речи Сарсекенова
        self.domain_context = (
            "Это лекция Саламата Сарсекенова по нейросталкингу/неосталкингу. "
            "СТРОГО сохраняй терминологию и авторские формулировки: нейросталкинг, неосталкинг, "
            "поле внимания, наблюдение за умом, метанаблюдение, осознавание, паттерны, триггеры, "
            "автоматизмы, исследование переживаний. "
            "ДОПОЛНИТЕЛЬНО: исправь очевидные речевые сбои и грамматические ошибки "
            "БЕЗ изменения смысла. Убери избыточные междометия, но сохрани естественность речи.")

    # ---------------------- Internal helpers ---------------------- #
    def _tok(self, text: str) -> int:
        return len(self.encoding.encode(text))

    def _ask(self, model: str, prompt: str, max_tokens: int = 2200, temperature: float = 0.3) -> str:
        r = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Ты редактор лекций Саламата Сарсекенова. Сохраняй терминологию нейросталкинга/неосталкинга и авторский стиль."},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return r.choices[0].message.content

    # Улучшенная очистка с сохранением авторского стиля
    def _light_clean(self, text: str) -> str:
        """
        Улучшенная очистка с сохранением авторского стиля
        Убираем: технический шум, междометия, грамматические ошибки, речевые сбои
        """
        # Технический шум (базовый)
        replacements = [
            ("[музыка]", ""), ("[Music]", ""), (">>", ""), ("&gt;&gt;", ""),
        ]
        
        # НОВОЕ: Междометия и речевые сбои
        speech_fixes = [
            # Междометия (с пробелами для точности)
            (" ээ ", " "), (" э-э ", " "), (" эээ ", " "), (" ээээ ", " "),
            (" ах ", " "), (" ох ", " "), (" ух ", " "), (" эх ", " "),
            (" мм ", " "), (" хм ", " "), (" ну ", " "),
            
            # Начало и конец предложений
            ("Ээ, ", ""), ("Эх, ", ""), ("Ох, ", ""), ("Ах, ", ""),
            (" ээ,", ","), (" ох,", ","), (" ах,", ","),
            
            # Явные грамматические ошибки
            ("пото что", "потому что"),
            ("новосте", "новости"), 
            ("боговесть", "божественность"),
            ("потму что", "потому что"),
            ("тоесть", "то есть"),
            ("вобще", "вообще"),
            
            # Избыточные повторы слов
            (" вот вот ", " вот "), (" это это ", " это "),
            (" да да ", " да "), (" ну ну ", " ну "),
            
            # Речевые сбои (осторожно, только явные)
            ("мало ли что", ""), ("я не знаю, ", ""),
            ("как бы ", " "), ("типа ", " "),
            ("короче говоря", "короче"),
        ]
        
        cleaned = text
        for old, new in replacements + speech_fixes:
            cleaned = cleaned.replace(old, new)
        
        # Убираем множественные пробелы и лишние знаки
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = re.sub(r'\s*,\s*,', ',', cleaned)  # двойные запятые
        cleaned = re.sub(r'\s*\.\s*\.', '.', cleaned)  # двойные точки
        
        return cleaned.strip()

    def _final_polish(self, text: str) -> str:
        """
        Финальная полировка текста - умное удаление избыточных слов-паразитов
        Убираем каждое второе "вот", "это" если их слишком много в абзаце
        """
        paragraphs = text.split('\n')
        polished_paragraphs = []
        
        for para in paragraphs:
            if not para.strip():
                polished_paragraphs.append(para)
                continue
                
            words = para.split()
            
            # Убираем каждое второе "вот" если их больше 3 в абзаце
            vot_count = words.count('вот')
            if vot_count > 3:
                vot_removed = 0
                for i, word in enumerate(words):
                    if word == 'вот' and vot_removed < vot_count // 2:
                        words[i] = ''
                        vot_removed += 1
            
            # Убираем каждое третье "это" если их больше 5 в абзаце
            eto_count = words.count('это')
            if eto_count > 5:
                eto_removed = 0
                for i, word in enumerate(words):
                    if word == 'это' and eto_removed < eto_count // 3:
                        words[i] = ''
                        eto_removed += 1
            
            # Убираем лишние "ну" в начале предложений
            nu_pattern = []
            for i, word in enumerate(words):
                if word == 'ну' and (i == 0 or words[i-1].endswith('.') or words[i-1].endswith('!')):
                    # Оставляем только каждое второе "ну" в начале предложений
                    if len(nu_pattern) % 2 == 1:
                        words[i] = ''
                    nu_pattern.append(i)
            
            polished_paragraphs.append(' '.join(w for w in words if w))
        
        return '\n'.join(polished_paragraphs)

    # ---------------------- IO ---------------------- #
    def load_input(self, file_path: Path) -> Dict[str, Any]:
        """Поддержка входа из get_subtitles.json формата и универсальных транскриптов."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if "subtitles" in data:
            raw_segments = data["subtitles"]
        elif "transcript" in data and isinstance(data["transcript"], dict):
            raw_segments = data["transcript"].get("segments", [])
        else:
            raw_segments = data.get("segments", [])

        segments: List[Dict[str, Any]] = []
        for i, s in enumerate(raw_segments):
            start = s.get("start", 0.0)
            dur = s.get("duration", max(0.0, s.get("end", 0.0) - s.get("start", 0.0)))
            end = start + dur
            segments.append({
                "id": i,
                "start": start,
                "end": end,
                "duration": dur,
                "text": s.get("text", ""),
            })

        return {
            "segments": segments,
            "metadata": data.get("metadata", data.get("file_info", {})),
            "full_text": " ".join(s.get("text", "") for s in segments),
        }

    # ---------------------- Chunking ---------------------- #
    def chunk_segments(self, segments: List[Dict[str, Any]], *, max_tokens: int = 4800, overlap_tokens: int = 200) -> List[Dict[str, Any]]:
        """Умное разбиение: учитываем маркеры смены темы и длинные примеры."""
        chunks: List[Dict[str, Any]] = []
        current: List[Dict[str, Any]] = []
        cur_tokens = 0

        def flush_chunk():
            nonlocal current, cur_tokens
            if not current:
                return
            chunks.append({
                "text": " ".join(s.get("text", "") for s in current),
                "start_time": current[0]["start"],
                "end_time": current[-1]["end"],
                "segments": list(current),
            })
            # overlap по последним 5 сегментам, если не превышает overlap_tokens
            tail = current[-5:]
            tail_tok = sum(self._tok(s.get("text", "")) for s in tail)
            if tail_tok <= overlap_tokens:
                current, cur_tokens = tail, tail_tok
            else:
                current, cur_tokens = [], 0

        for s in segments:
            t = s.get("text", "")
            n = self._tok(t)

            is_boundary = any(marker in t for marker in [
                "Итак", "Подведём итог", "Подводя итог", "Таким образом",
                "Давайте", "Теперь", "Следующий", "Вопрос из зала", "Практика", "Упражнение",
            ])

            # Делаем блоки крупнее: минимум 2000 токенов, максимум 4800
            if current and (cur_tokens + n > max_tokens or (is_boundary and cur_tokens > 2000)):
                flush_chunk()

            current.append(s)
            cur_tokens += n

        flush_chunk()
        return chunks

    # ---------------------- LLM prompts ---------------------- #
    def process_chunk(self, chunk: Dict[str, Any]) -> List[Dict[str, Any]]:
        source_text = self._light_clean(chunk['text'])
        prompt = f"""{self.domain_context}

ЗАДАЧА: Разбей фрагмент лекции на КРУПНЫЕ информативные блоки (4–8 минут каждый, минимум 300-500 слов). СТРОГО сохраняй авторские термины и стиль речи.

ТРЕБОВАНИЯ:
1) КРУПНЫЕ БЛОКИ: Каждый блок должен содержать 300-500+ слов. НЕ дели на мелкие части.
2) Термины не трогать: нейросталкинг, неосталкинг, поле внимания, наблюдение за умом, метанаблюдение, автоматизмы, паттерны, триггеры, исследование переживаний, практика, упражнение, разбор и др.
3) ВЕСЬ ТЕКСТ включать: НЕ перефразируй и НЕ пересказывай. Включи ВСЁ содержимое фрагмента в блоки. Удаляй только технический мусор.
4) Уникальные заголовки: каждый title должен быть уникальным и отражать конкретную тему блока.
5) Формат ответа — JSON-массив:
[
  {{
    "start": "HH:MM:SS",
    "end": "HH:MM:SS",
    "title": "Уникальный конкретный заголовок (5–12 слов)",
    "summary": "Краткое содержание (2–3 предложения) с терминами из лекции",
    "keywords": ["термин1", "термин2", "концепт3"],
    "content": "ПОЛНЫЙ очищенный текст блока (300-500+ слов, весь контент фрагмента)"
  }}
]

ФРАГМЕНТ ТЕКСТА (не пересказывать, использовать как есть; только минимальная чистка):
{source_text}
"""

        try:
            resp = self._ask(self.primary_model, prompt, max_tokens=4200, temperature=0.2)
            txt = resp.strip()
            if txt.startswith("```json"):
                txt = txt[7:]
            elif txt.startswith("```"):
                txt = txt[3:]
            if txt.endswith("```"):
                txt = txt[:-3]
            blocks = orjson.loads(txt)

            st, et = _hms(chunk.get("start_time")), _hms(chunk.get("end_time"))
            for b in blocks:
                b.setdefault("start", st)
                b.setdefault("end", et)
                # Применяем финальную полировку к содержимому блока
                if 'content' in b:
                    b['content'] = self._final_polish(b['content'])
            return blocks
        except Exception:
            # Безопасный резерв: вернуть исходный фрагмент без изменений смысла
            return [{
                "start": _hms(chunk.get("start_time")),
                "end": _hms(chunk.get("end_time")),
                "title": "Фрагмент лекции (без изменений)",
                "summary": "Блок сформирован из исходного текста (минимальная очистка).",
                "keywords": ["нейросталкинг"],
                "content": self._final_polish(source_text)
            }]

    def refine_blocks(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not self.refine_model:
            return blocks

        prompt = f"""{self.domain_context}

ПОЛИРОВКА БЛОКОВ: улучши читаемость, но строго сохрани термины и авторские формулировки. 
Можно: править пунктуацию, абзацы, делать заголовки информативнее, расширять keywords. Нельзя: переписывать content своими словами.

Верни JSON-массив в том же формате:
{orjson.dumps(blocks, option=orjson.OPT_INDENT_2).decode()}
"""

        try:
            resp = self._ask(self.refine_model, prompt, max_tokens=5200, temperature=0.2)
            if resp.startswith("```json"):
                resp = resp[7:]
            elif resp.startswith("```"):
                resp = resp[3:]
            if resp.endswith("```"):
                resp = resp[:-3]
            refined_blocks = orjson.loads(resp)
            # Применяем финальную полировку к отрефайненным блокам
            for b in refined_blocks:
                if 'content' in b:
                    b['content'] = self._final_polish(b['content'])
            return refined_blocks
        except Exception:
            return blocks

    # ---------------------- Save ---------------------- #
    def save_markdown(self, md_path: Path, data: Dict[str, Any], base_name: str) -> None:
        lines: List[str] = [
            "# 🧭 Лекции С. Сарсекенова — конспект",
            f"## {data.get('document_title', base_name)}",
            f"*{data.get('document_summary', 'Описание недоступно')}*",
            "",
            # Короткое оглавление и обобщённое резюме сверху
            ("**Короткое оглавление:** " + data.get('overview_toc', '')).strip(),
            ("**Общее резюме:** " + data.get('overview_summary', '')).strip(),
            "",
            "---",
            "## 📑 Оглавление",
        ]

        for i, b in enumerate(data.get("blocks", [])):
            lines.append(f"{i+1}. [{b.get('title','Без названия')}](#{i+1}-block)")

        lines.append("\n---\n")

        for i, b in enumerate(data.get("blocks", [])):
            lines.extend([
                f"## <a id='{i+1}-block'></a> {i+1}. {b.get('title','Без названия')}",
                f"**⏱ Время:** [{b.get('start','N/A')} - {b.get('end','N/A')}]",
                f"**📝 Краткое содержание:** {b.get('summary','')}",
                f"**🏷 Ключевые слова:** {', '.join(b.get('keywords', []))}",
                "",
                "### Содержание:",
                b.get("content", ""),
                "",
                "---\n",
            ])

        md_path.write_text("\n".join(lines), encoding="utf-8")

    # ---------------------- Main processing ---------------------- #
    def process_file(self, input_path: Path, output_dir: Path) -> Dict[str, Any]:
        data = self.load_input(input_path)
        segments = data.get("segments", [])
        if not segments:
            raise RuntimeError("No segments found in input")

        chunks = self.chunk_segments(segments)
        all_blocks: List[Dict[str, Any]] = []
        for i, ch in enumerate(chunks, 1):
            print(f"[INFO] Processing chunk {i}/{len(chunks)}")
            blocks = self.process_chunk(ch)
            all_blocks.extend(blocks)
            time.sleep(0.4)

        if self.refine_model:
            all_blocks = self.refine_blocks(all_blocks)

        base = input_path.stem
        video_id = base
        
        # Добавляем стабильные ID и метаданные для RAG
        for i, block in enumerate(all_blocks):
            block["block_id"] = f"{video_id}_{i:03d}"
            block["video_id"] = video_id
            block["source_url"] = f"https://youtube.com/watch?v={video_id}"
            # Временная ссылка на YouTube
            if block.get("start"):
                start_seconds = self._hms_to_seconds(block["start"])
                if start_seconds is not None:
                    block["youtube_link"] = f"https://youtube.com/watch?v={video_id}&t={start_seconds}s"
        
        doc = {
            "document_title": f"Лекция Сарсекенова: {base}",
            "document_summary": "Конспект лекции, структурированный по темам нейросталкинга/неосталкинга.",
            "document_metadata": {
                "total_blocks": len(all_blocks),
                "language": "ru",
                "domain": "sarsekenov_neurostalking",
                "video_id": video_id,
                "source_url": f"https://youtube.com/watch?v={video_id}",
                "schema_version": "1.0",
            },
            "blocks": all_blocks,
            "full_text": data.get("full_text", ""),
        }

        # Сформировать «короткое оглавление» и «общее резюме» на основе всех блоков
        overview = self.generate_overview(doc)
        doc.update({
            "overview_toc": overview.get("overview_toc", ""),
            "overview_summary": overview.get("overview_summary", ""),
        })

        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / f"{base}.for_vector.json"
        md_path = output_dir / f"{base}.for_review.md"
        with open(json_path, "wb") as f:
            f.write(orjson.dumps(doc, option=orjson.OPT_INDENT_2))
        self.save_markdown(md_path, doc, base)

        print(f"[SUCCESS] JSON: {json_path}")
        print(f"[SUCCESS] MD  : {md_path}")
        return {"json_output": str(json_path), "md_output": str(md_path), "blocks": len(all_blocks)}

    # Совместимость с оркестратором (та же сигнатура, что у SubtitlesProcessor)
    def process_subtitles_file(self, transcript_path: Path, output_dir: Path) -> Dict[str, Any]:
        result = self.process_file(transcript_path, output_dir)
        return {
            "json_output": result["json_output"],
            "md_output": result["md_output"],
            "blocks_created": result.get("blocks", 0),
        }

    def _hms_to_seconds(self, hms_str: str) -> Optional[int]:
        """Конвертирует HH:MM:SS в секунды"""
        try:
            parts = hms_str.split(':')
            if len(parts) == 3:
                h, m, s = map(int, parts)
                return h * 3600 + m * 60 + s
        except:
            pass
        return None

    # ---------------------- Overview generation ---------------------- #
    def generate_overview(self, doc: Dict[str, Any]) -> Dict[str, str]:
        # Базовый вариант «оглавления одним предложением» из заголовков блоков
        titles = [b.get("title", "") for b in doc.get("blocks", []) if b.get("title")]
        toc_sentence_default = " • ".join(titles[:20])  # ограничим до 20 заголовков

        # Для обобщённого саммари воспользуемся refine-моделью, если доступна
        try:
            blocks_for_prompt = [
                {
                    "title": b.get("title", ""),
                    "summary": b.get("summary", ""),
                    "start": b.get("start", ""),
                    "end": b.get("end", ""),
                }
                for b in doc.get("blocks", [])
            ]
            prompt = (
                "Сформируй:\n"
                "1) Короткое оглавление одним предложением (главные темы по порядку).\n"
                "2) Обобщённое резюме на 2–4 предложения (сохраняй стиль автора, без потери смысла).\n\n"
                "Данные по блокам:\n" + orjson.dumps(blocks_for_prompt, option=orjson.OPT_INDENT_2).decode()
            )
            resp = self._ask(self.refine_model or self.primary_model, prompt, max_tokens=600, temperature=0.2)
            # Простой хэндлинг: искать разделители
            lines = [l.strip() for l in resp.splitlines() if l.strip()]
            toc_line = ""
            summary_lines: List[str] = []
            for line in lines:
                low = line.lower()
                if not toc_line and ("оглавлен" in low or "тем" in low):
                    toc_line = line.split(":", 1)[-1].strip() if ":" in line else line
                elif any(k in low for k in ["резюме", "итог", "summary", "обобщ"]):
                    # последующие строки считаем саммари
                    continue
                elif toc_line and not summary_lines:
                    # возможно следующий блок — это резюме, если строка длиннее
                    summary_lines.append(line)
                elif summary_lines:
                    summary_lines.append(line)
            overview_summary = " ".join(summary_lines).strip()
            return {
                "overview_toc": toc_line or toc_sentence_default,
                "overview_summary": overview_summary[:1200],
            }
        except Exception:
            return {"overview_toc": toc_sentence_default, "overview_summary": ""}


def main() -> int:
    ap = argparse.ArgumentParser(description="Процессор лекций С. Сарсекенова")
    ap.add_argument("--input", help="Файл или директория с субтитрами (.json). Если не указано, будет использован urls.txt")
    ap.add_argument("--output", default="data/vector_ready", help="Директория для результатов")
    ap.add_argument("--primary-model", default="gpt-4o-mini", help="Основная модель для нарезки")
    ap.add_argument("--refine-model", default="gpt-5-mini", help="Модель для полировки")
    ap.add_argument("--urls-file", default=str(PROJECT_ROOT / "urls.txt"), help="Файл со списком URL (по одному на строку)")
    ap.add_argument("--language", default="ru", help="Предпочитаемый язык субтитров для загрузки")
    args = ap.parse_args()

    # Загружаем .env до проверки ключа
    try:
        load_env()
    except Exception:
        pass

    if not os.getenv("OPENAI_API_KEY"):
        print("[ERROR] OPENAI_API_KEY не установлен")
        return 1

    proc = SarsekenovProcessor(args.primary_model, args.refine_model)

    # Если --input не задан, или в папке нет json, пытаемся загрузить субтитры из urls.txt
    input_candidate: Optional[Path] = Path(args.input) if args.input else None
    urls_file = Path(args.urls_file)
    subtitles_dir = PROJECT_ROOT / "data" / "subtitles"

    if input_candidate is None:
        # Автозагрузка по urls.txt
        if urls_file.exists():
            print(f"[INFO] --input не указан. Использую URLs из: {urls_file}")
            extractor = YouTubeSubtitlesExtractor(str(subtitles_dir))
            with open(urls_file, "r", encoding="utf-8") as f:
                urls = [ln.strip() for ln in f if ln.strip()]
            for u in urls:
                try:
                    extractor.process_url(u, args.language)
                except Exception as e:
                    print(f"[ERROR] Не удалось обработать URL {u}: {e}")
            input_candidate = subtitles_dir
        else:
            print("[ERROR] Не указан --input и отсутствует urls.txt. Укажите путь к .json или создайте urls.txt")
            return 1

    in_path = input_candidate
    out_dir = Path(args.output)
    files: List[Path] = []
    if in_path.is_file():
        files = [in_path]
    else:
        files = list(in_path.glob("*.json"))
    if not files:
        print(f"[ERROR] Не найдено JSON файлов в {in_path}")
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    for jf in files:
        try:
            proc.process_file(jf, out_dir)
        except Exception as e:
            print(f"[ERROR] {jf.name}: {e}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())


