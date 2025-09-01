#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Transcript to Structured JSON/MD Processor
Converts transcripts into semantic blocks for vector database ingestion
"""

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import timedelta

import orjson
import tiktoken
from openai import OpenAI

from env_utils import load_env

def _hms(sec: Optional[float]) -> Optional[str]:
    if sec is None: return None
    sec = int(sec)
    return f"{sec//3600:02d}:{(sec%3600)//60:02d}:{sec%60:02d}"

class TranscriptProcessor:
    def __init__(self, primary_model: str = "gpt-4o-mini", refine_model: str = ""):
        load_env()  # сначала .env
        self.primary_model = primary_model
        self.refine_model  = refine_model
        self.client = OpenAI()  # потом клиент
        self.encoding = tiktoken.get_encoding("cl100k_base")

    def _tok(self, text: str) -> int:
        return len(self.encoding.encode(text))

    def _ask(self, model: str, prompt: str, max_tokens: int = 2000) -> str:
        r = self.client.chat.completions.create(
            model=model,
            messages=[{"role":"user","content":prompt}],
            temperature=0.2,
            max_tokens=max_tokens
        )
        return r.choices[0].message.content

    def load_transcript(self, file_path: Path) -> Dict[str, Any]:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        segments = data.get("transcript", {}).get("segments", [])
        file_info = data.get("file_info", {})
        segs = []
        for i, s in enumerate(segments):
            st = s.get("start", 0.0); dur = s.get("duration", 0.0)
            segs.append({"id": i, "start": st, "end": st+dur, "text": s.get("text",""), "duration": dur})
        return {"segments": segs, "file_info": file_info, "full_text": " ".join(s.get("text","") for s in segments)}

    def chunk_segments(self, segments: List[Dict], max_tokens: int = 3800, overlap_tokens: int = 200) -> List[Dict]:
        chunks, cur, cur_tok = [], [], 0
        for sg in segments:
            t = sg.get("text","")
            n = self._tok(t)
            if cur and cur_tok + n > max_tokens:
                chunk_text = " ".join(x.get("text","") for x in cur)
                chunks.append({
                    "text": chunk_text,
                    "start_time": cur[0]["start"],
                    "end_time":   cur[-1]["end"],
                    "segments":   cur.copy()
                })
                if overlap_tokens > 0:
                    tail = cur[-3:]
                    tail_tok = sum(self._tok(x.get("text","")) for x in tail)
                    cur, cur_tok = (tail, tail_tok) if tail_tok <= overlap_tokens else ([], 0)
                else:
                    cur, cur_tok = [], 0
            cur.append(sg); cur_tok += n
        if cur:
            chunk_text = " ".join(x.get("text","") for x in cur)
            chunks.append({
                "text": chunk_text,
                "start_time": cur[0]["start"],
                "end_time":   cur[-1]["end"],
                "segments":   cur
            })
        return chunks

    def process_chunk_to_blocks(self, chunk: Dict[str, Any]) -> List[Dict[str, Any]]:
        prompt = f"""Ты - редактор русскоязычных транскриптов.
Задача - разрезать входной текст на тематические блоки длительностью 2-5 минут каждый.

СТРОГИЕ ПРАВИЛА:
1) Меняй блок при смене подтемы, аргумента или вопроса
2) Заголовок - информативный, 5-10 слов, без клише
3) Summary - 2-3 фактических предложения о содержании блока
4) Keywords - 3-7 ключевых слов/фраз из блока
5) Content - полный текст блока без изменений
6) Таймкоды в формате HH:MM:SS или null если неизвестны
7) Выводи ТОЛЬКО валидный JSON массив

Формат вывода:
[
  {{
    "start": "HH:MM:SS",
    "end": "HH:MM:SS",
    "title": "краткий информативный заголовок",
    "summary": "2-3 предложения о содержании блока",
    "keywords": ["слово1", "слово2", "фраза3"],
    "content": "полный текст блока"
  }}
]

Текст транскрипта:
{chunk['text']}"""
        try:
            resp = self._ask(self.primary_model, prompt, max_tokens=3000).strip()
            if resp.startswith("```json"):
                resp = resp[7:]
            if resp.endswith("```"):
                resp = resp[:-3]
            blocks = orjson.loads(resp.strip())

            # добавим тайминги из чанка, если модель не указала
            start_t, end_t = _hms(chunk.get('start_time')), _hms(chunk.get('end_time'))
            for b in blocks:
                if not b.get('start') and start_t: b['start'] = start_t
                if not b.get('end')   and end_t:   b['end']   = end_t

            # защита от пустого/невалидного ответа
            if not isinstance(blocks, list) or not blocks:
                raise ValueError("LLM вернула пустой или невалидный массив блоков")
            return blocks
        except Exception as e:
            print(f"[WARNING] Failed to process chunk: {e}")
            return [{
                "start": _hms(chunk.get('start_time')),
                "end":   _hms(chunk.get('end_time')),
                "title": "Автоматически созданный блок",
                "summary": "Блок создан автоматически из-за ошибки обработки.",
                "keywords": ["транскрипт", "аудио"],
                "content": (chunk['text'][:1000] + ("..." if len(chunk['text']) > 1000 else ""))
            }]

    def refine_blocks(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not self.refine_model:
            return blocks
        prompt = (
            "Ты - редактор текстов. Получишь массив блоков с title и summary.\n"
            "- title: сделать более информативным и ёмким (до 12 слов)\n"
            "- summary: переписать ясно и фактически (2-3 предложения), убрать воду\n"
            "- keywords и content не трогай\n\n"
            "Верни JSON-массив в том же формате.\n\n"
            f"{orjson.dumps(blocks, option=orjson.OPT_INDENT_2).decode()}"
        )
        try:
            resp = self._ask(self.refine_model, prompt, max_tokens=4000).strip()
            if resp.startswith("```json"): resp = resp[7:]
            if resp.endswith("```"):       resp = resp[:-3]
            refined = orjson.loads(resp.strip())
            print(f"[INFO] Refined {len(refined)} blocks")
            return refined
        except Exception as e:
            print(f"[WARNING] Refinement failed: {e}")
            return blocks

    def create_document_summary(self, blocks: List[Dict[str, Any]]) -> Optional[Dict[str, str]]:
        print("[INFO] Creating document-level title and summary...")
        summary_model = self.refine_model or self.primary_model
        if not summary_model:
            return None
        toc = "\n".join(f"- {b.get('start','')}: {b.get('title','')}" for b in blocks)
        prompt = (
            "Тебе предоставлено полное оглавление видео. Проанализируй его и выполни две задачи:\n"
            "1. Придумай общий заголовок для всего видео.\n"
            "2. Напиши краткое саммари (2-4 предложения).\n\n"
            'Верни результат в формате JSON: {"document_title": "...", "document_summary": "..."}\n\n'
            f"Оглавление:\n{toc}"
        )
        try:
            resp = self._ask(summary_model, prompt, max_tokens=1000).strip()
            if resp.startswith("```json"): resp = resp[7:]
            if resp.endswith("```"):       resp = resp[:-3]
            s, e = resp.find('{'), resp.rfind('}')
            if s != -1 and e != -1:
                return orjson.loads(resp[s:e+1])
            raise ValueError("JSON объект не найден в ответе модели")
        except Exception as e:
            print(f"[WARNING] Could not create document summary: {e}")
            return None

    def process_transcript_file(self, input_path: Path, output_dir: Path) -> Dict[str, Any]:
        print(f"Processing: {input_path.name}")
        subdata = self.load_transcript(input_path)
        if not subdata["segments"]:
            raise RuntimeError("No segments found in transcript")

        chunks = self.chunk_segments(subdata["segments"])
        print(f"[INFO] Split into {len(chunks)} chunks")

        all_blocks: List[Dict[str,Any]] = []
        for i, ch in enumerate(chunks, 1):
            print(f"[INFO] Processing chunk {i}/{len(chunks)}")
            try:
                all_blocks.extend(self.process_chunk_to_blocks(ch))
                time.sleep(0.5)
            except Exception as e:
                print(f"[ERROR] Failed to process chunk {i}: {e}")

        if not all_blocks:
            raise RuntimeError("No blocks were created")

        if self.refine_model:
            all_blocks = self.refine_blocks(all_blocks)

        doc = self.create_document_summary(all_blocks)

        meta = subdata.get("file_info", {})
        for b in all_blocks:
            b["metadata"] = {
                "source_file": input_path.name,
                "processing_date": time.strftime("%Y-%m-%d %H:%M:%S")
            }

        base = input_path.stem
        final_json = {
            "document_title":   (doc.get("document_title")   if doc else base),
            "document_summary": (doc.get("document_summary") if doc else "Описание недоступно"),
            "blocks": all_blocks
        }

        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / f"{base}.for_vector.json"
        md_path   = output_dir / f"{base}.for_review.md"

        with open(json_path, "wb") as f:
            f.write(orjson.dumps(final_json, option=orjson.OPT_INDENT_2))

        md_lines = ["# Оглавление\n"]
        if doc:
            md_lines += [f"**{doc.get('document_title', base)}**\n",
                         f"{doc.get('document_summary', 'Нет данных')}\n", "---\n"]
        else:
            md_lines += [f"**Транскрипт: {base}**\n"]
        for b in all_blocks:
            md_lines += [
                f"### [{b.get('start','N/A')} - {b.get('end','N/A')}] {b.get('title','Без названия')}",
                f"**Summary:** {b.get('summary','')}",
                f"**Keywords:** {', '.join(b.get('keywords', []))}\n",
                (b.get('content','') + "\n"),
                "---\n"
            ]
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))

        print(f"[OK] {base}: {len(all_blocks)} blocks created")
        print(f"[OK] Vector JSON: {json_path}")
        print(f"[OK] Review MD: {md_path}")

        return {
            "input_file": str(input_path),
            "json_output": str(json_path),
            "md_output": str(md_path),
            "blocks_created": len(all_blocks),
            "total_chunks": len(chunks)
        }

def main() -> int:
    ap = argparse.ArgumentParser(description="Transcript -> Structured JSON/MD")
    ap.add_argument("--input",  required=True, help="File or directory with transcript JSONs")
    ap.add_argument("--output", default="data/vector_ready", help="Output directory")
    ap.add_argument("--primary-model", default="gpt-4o-mini")
    ap.add_argument("--refine-model",  default="")
    args = ap.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        print("[ERROR] OPENAI_API_KEY environment variable not set"); return 1

    tp = TranscriptProcessor(args.primary_model, args.refine_model)
    inp = Path(args.input); out = Path(args.output); out.mkdir(parents=True, exist_ok=True)

    files: List[Path] = []
    if inp.is_file(): files = [inp]
    else: files = list(inp.glob("*.json"))
    
    results = []
    for jf in files:
        try:
            results.append(tp.process_transcript_file(jf, out))
        except Exception as e:
            print(f"[ERROR] Failed to process {jf.name}: {e}")
    
    print(f"\n[PIPELINE] Transcript processing complete: {len(results)} files processed")
    print(f"[PIPELINE] Output directory: {out.resolve()}")
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
