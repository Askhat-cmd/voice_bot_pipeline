#!/usr/bin/env python3
# -*- coding: utf-8 -*- 
"""
Subtitles to Structured Blocks Processor
Converts YouTube subtitles into semantic blocks for vector database ingestion
"""

import argparse
import json
import os
import time
from datetime import timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import orjson
import tiktoken
from openai import OpenAI

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from env_utils import load_env


class SubtitlesProcessor:
    def __init__(self):
        # сначала .env, потом клиент
        load_env()
        self.primary_model = os.getenv("PRIMARY_MODEL", "gpt-4o-mini")
        self.refine_model = os.getenv("REFINE_MODEL", "")
        self.client = OpenAI()
        self.encoding = tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self.encoding.encode(text))

    def seconds_to_hms(self, seconds: Optional[float]) -> Optional[str]:
        """Convert seconds to HH:MM:SS format"""
        if seconds is None:
            return None
        td = timedelta(seconds=int(seconds))
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def load_subtitles(self, file_path: Path) -> Dict[str, Any]:
        """Load subtitles from JSON file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        subtitles = data.get("subtitles", [])
        metadata = data.get("metadata", {})

        segments = []
        for i, subtitle in enumerate(subtitles):
            start_time = subtitle.get('start', 0)
            duration = subtitle.get('duration', 0)
            end_time = start_time + duration

            segments.append({
                "id": i,
                "start": start_time,
                "end": end_time,
                "text": subtitle.get('text', ''),
                "duration": duration
            })

        return {
            "segments": segments,
            "metadata": metadata,
            "full_text": " ".join(sub.get('text', '') for sub in subtitles)
        }

    def chunk_segments(self, segments: List[Dict], max_tokens: int = 3800,
                       overlap_tokens: int = 200) -> List[Dict]:
        """Split segments into chunks for processing"""
        chunks = []
        current_chunk = []
        current_tokens = 0

        for segment in segments:
            text = segment.get("text", "")
            tokens = self.count_tokens(text)

            if current_tokens + tokens > max_tokens and current_chunk:
                chunk_text = " ".join(seg.get("text", "") for seg in current_chunk)
                chunks.append({
                    "text": chunk_text,
                    "start_time": current_chunk[0].get("start"),
                    "end_time": current_chunk[-1].get("end"),
                    "segments": current_chunk.copy()
                })

                if overlap_tokens > 0:
                    overlap_segments = current_chunk[-3:]
                    overlap_token_count = sum(self.count_tokens(seg.get("text", ""))
                                            for seg in overlap_segments)
                    if overlap_token_count <= overlap_tokens:
                        current_chunk = overlap_segments
                        current_tokens = overlap_token_count
                    else:
                        current_chunk = []
                        current_tokens = 0
                else:
                    current_chunk = []
                    current_tokens = 0

            current_chunk.append(segment)
            current_tokens += tokens

        if current_chunk:
            chunk_text = " ".join(seg.get("text", "") for seg in current_chunk)
            chunks.append({
                "text": chunk_text,
                "start_time": current_chunk[0].get("start"),
                "end_time": current_chunk[-1].get("end"),
                "segments": current_chunk
            })

        return chunks

    def call_llm(self, model: str, prompt: str, max_tokens: int = 2000) -> str:
        """Call OpenAI API"""
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"LLM API call failed: {e}")

    def _clean_llm_response(self, response: str) -> str:
        """Очищает ответ LLM от markdown разметки и лишних символов"""
        if not response:
            return ""
        
        # Убираем markdown блоки кода
        response = response.strip()
        
        # Убираем ```json в начале
        if response.startswith("```json"):
            response = response[7:]
        elif response.startswith("```"):
            response = response[3:]
            
        # Убираем ``` в конце
        if response.endswith("```"):
            response = response[:-3]
            
        return response.strip()

    def process_chunk_to_blocks(self, chunk: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert a chunk into semantic blocks"""
        prompt = f"""Ты - редактор русскоязычных транскриптов.
Задача - разрезать входной текст на 2-3 тематических блока.

ПРАВИЛА:
1) Создавай 2-3 блока максимум
2) Меняй блок при смене темы или аргумента
3) Заголовок - информативный, 5-8 слов
4) Summary - 2-3 предложения о содержании
5) Keywords - 3-5 ключевых слов
6) Content - полный текст блока
7) Таймкоды в формате HH:MM:SS

Формат вывода:
[
  {{
    "start": "HH:MM:SS",
    "end": "HH:MM:SS", 
    "title": "краткий заголовок",
    "summary": "описание блока",
    "keywords": ["слово1", "слово2", "слово3"],
    "content": "полный текст блока"
  }}
]

Текст транскрипта:
{chunk['text']} """
        
        try:
            response = self.call_llm(self.primary_model, prompt, max_tokens=3000)
            print(f"[DEBUG] Raw LLM Response: {response[:200]}...")  # Отладочная информация
            
            # Проверяем, что ответ не пустой
            if not response or response.strip() == "":
                raise ValueError("LLM вернула пустой ответ")
            
            # Очищаем ответ от markdown разметки
            cleaned_response = self._clean_llm_response(response)
            print(f"[DEBUG] Cleaned Response: {cleaned_response[:200]}...")  # Отладочная информация
                
            blocks = orjson.loads(cleaned_response)
            # Гарантируем, что получили непустой список блоков
            if not isinstance(blocks, list) or len(blocks) == 0:
                raise ValueError("LLM вернула пустой или невалидный массив блоков")
            
            # Add timing information from chunk
            start_time = self.seconds_to_hms(chunk.get('start_time'))
            end_time = self.seconds_to_hms(chunk.get('end_time'))
            
            for block in blocks:
                if not block.get('start') and start_time:
                    block['start'] = start_time
                if not block.get('end') and end_time:
                    block['end'] = end_time
            
            return blocks
        except Exception as e:
            print(f"[WARNING] Failed to process chunk: {e}")
            # Fallback: create single block from chunk
            return [{
                "start": self.seconds_to_hms(chunk.get('start_time')),
                "end": self.seconds_to_hms(chunk.get('end_time')),
                "title": "Автоматически созданный блок",
                "summary": "Блок создан автоматически из-за ошибки обработки.",
                "keywords": ["транскрипт", "аудио"],
                "content": chunk['text'][:1000] + ("..." if len(chunk['text']) > 1000 else "")
            }]
    
    def refine_blocks(self, blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Refine block titles and summaries using secondary model"""
        if not self.refine_model:
            return blocks
        
        prompt = f"""Обработай эти блоки:

1. Убери из content: [музыка], э-э, ну, короче, типа, как бы, в общем, то есть
2. Исправь грамматику
3. Сохрани стиль и детали
4. Улучши title (до 10 слов)
5. Перепиши summary (2-3 предложения)

JSON:
{orjson.dumps(blocks, option=orjson.OPT_INDENT_2).decode()}"""

        try:
            response = self.call_llm(self.refine_model, prompt, max_tokens=4000)
            # Очищаем ответ от markdown разметки
            cleaned_response = self._clean_llm_response(response)
            refined_blocks = orjson.loads(cleaned_response)
            print(f"[INFO] Refined {len(refined_blocks)} blocks")
            return refined_blocks
        except Exception as e:
            print(f"[WARNING] Refinement failed: {e}")
            return blocks
    
    def _create_document_summary(self, all_blocks: List[Dict]) -> Dict[str, str]:
        """Create a document-level title and summary from all blocks."""
        print("[INFO] Creating document-level title and summary...")

        summary_model = self.refine_model if self.refine_model else self.primary_model
        if not summary_model:
            return None

        toc = "\n".join([f"- {b.get('start', '')}: {b.get('title', '')}" for b in all_blocks])

        prompt = f"""Тебе предоставлено полное оглавление видео. Проанализируй его и выполни две задачи:
1.  **Придумай общий заголовок для всего видео.** Заголовок должен быть информативным, состоять из одного полного предложения и отражать главную суть всего материала.
2.  **Напиши краткое саммари (2-4 предложения),** обобщающее ключевые темы из оглавления.

Верни результат в формате JSON:
{{"document_title": "...", "document_summary": "..."}}


""" + f"\n\nОглавление:\n{toc}"

        try:
            response = self.call_llm(summary_model, prompt, max_tokens=1000)
            # More robust JSON extraction to handle markdown code blocks
            first_brace = response.find('{')
            last_brace = response.rfind('}')
            if first_brace != -1 and last_brace != -1:
                json_string = response[first_brace:last_brace+1]
                summary_data = orjson.loads(json_string)
                print("[INFO] Document summary created successfully.")
                return summary_data
            else:
                raise ValueError("Could not find JSON object in model response")
        except Exception as e:
            print(f"[WARNING] Could not create document summary: {e}")
            return None

    def process_subtitles_file(self, input_path: Path, output_dir: Path) -> Dict[str, Any]:
        """Process a single subtitles file"""
        print(f"Processing: {input_path.name}")

        try:
            subtitles_data = self.load_subtitles(input_path)
        except Exception as e:
            raise Exception(f"Failed to load subtitles: {e}")

        if not subtitles_data["segments"]:
            raise Exception("No segments found in subtitles")

        chunks = self.chunk_segments(subtitles_data["segments"])
        print(f"[INFO] Split into {len(chunks)} chunks")

        all_blocks = []
        for i, chunk in enumerate(chunks):
            print(f"[INFO] Processing chunk {i + 1}/{len(chunks)}")
            try:
                blocks = self.process_chunk_to_blocks(chunk)
                all_blocks.extend(blocks)
                time.sleep(0.5)
            except Exception as e:
                print(f"[ERROR] Failed to process chunk {i + 1}: {e}")

        if not all_blocks:
            raise Exception("No blocks were created")

        if self.refine_model:
            all_blocks = self.refine_blocks(all_blocks)

        doc_summary_data = self._create_document_summary(all_blocks)

        metadata = subtitles_data.get("metadata", {})
        for block in all_blocks:
            block["metadata"] = {
                "video_id": metadata.get("video_id", "unknown"),
                "subtitle_count": metadata.get("subtitle_count", 0),
                "total_duration": metadata.get("total_duration", 0),
                "source_file": input_path.name,
                "processing_date": time.strftime("%Y-%m-%d %H:%M:%S")
            }

        base_name = input_path.stem

        final_json_output = {
            "document_title": doc_summary_data.get('document_title', base_name) if doc_summary_data else base_name,
            "document_summary": doc_summary_data.get('document_summary', 'N/A') if doc_summary_data else 'N/A',
            "blocks": all_blocks
        }
        json_output_path = output_dir / f"{base_name}.for_vector.json"
        with open(json_output_path, "wb") as f:
            f.write(orjson.dumps(final_json_output, option=orjson.OPT_INDENT_2))

        # 2. Markdown for human review (New Layout)
        md_lines = ["# Оглавление\n"]
        if doc_summary_data:
            md_lines.append(f"**{doc_summary_data.get('document_title', base_name)}**\n")
            md_lines.append(f"{doc_summary_data.get('document_summary', 'Нет данных')}\n")
            md_lines.append("---\n")
        else:
            md_lines.append(f"**Видео: {base_name}**\n")

        for block in all_blocks:
            start = block.get('start', 'N/A')
            end = block.get('end', 'N/A')
            title = block.get('title', 'Без названия')
            summary = block.get('summary', '')
            keywords = ', '.join(block.get('keywords', []))
            content = block.get('content', '')

            md_lines.extend([
                f"### [{start} - {end}] {title}",
                f"**Summary:** {summary}",
                f"**Keywords:** {keywords}\n",
                content + "\n",
                "---\n"
            ])

        md_output_path = output_dir / f"{base_name}.for_review.md"
        with open(md_output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_lines))

        print(f"[OK] {base_name}: {len(all_blocks)} blocks created")
        print(f"[OK] Vector JSON: {json_output_path}")
        print(f"[OK] Review MD: {md_output_path}")

        return {
            "input_file": str(input_path),
            "json_output": str(json_output_path),
            "md_output": str(md_output_path),
            "blocks_created": len(all_blocks),
            "total_chunks": len(chunks)
        }

    def batch_process(self, input_dir: Path, output_dir: Path) -> List[Dict[str, Any]]:
        """Process all subtitle JSON files in directory"""
        input_dir = Path(input_dir)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        json_files = list(input_dir.glob("*.json"))

        if not json_files:
            print(f"No JSON subtitle files found in {input_dir}")
            return []

        print(f"Found {len(json_files)} subtitle files")
        results = []

        for json_file in json_files:
            try:
                result = self.process_subtitles_file(json_file, output_dir)
                results.append(result)
            except Exception as e:
                print(f"[ERROR] Failed to process {json_file.name}: {e}")

        print(f"\n[PIPELINE] Text processing complete: {len(results)} files processed")
        print(f"[PIPELINE] Output directory: {output_dir.resolve()}")

        return results


def main():
    # Загружаем .env в начале
    load_env()
    
    parser = argparse.ArgumentParser(description="Convert YouTube subtitles to structured JSON/MD for vector database")
    parser.add_argument("--input", default="data/subtitles", help="Input directory or file with subtitle JSON")
    parser.add_argument("--output", default="data/vector_ready", help="Output directory for structured files")

    args = parser.parse_args()

    if not os.getenv("OPENAI_API_KEY"):
        print("[ERROR] OPENAI_API_KEY environment variable not set")
        print("[INFO] Make sure your .env file contains: OPENAI_API_KEY=your-key-here")
        return 1

    processor = SubtitlesProcessor()
    input_path = Path(args.input)
    output_path = Path(args.output)
    
    if input_path.is_file():
        # Обрабатываем один файл
        try:
            result = processor.process_subtitles_file(input_path, output_path)
            print(f"[SUCCESS] Processed {input_path.name}")
        except Exception as e:
            print(f"[ERROR] Failed to process {input_path.name}: {e}")
            return 1
    else:
        # Обрабатываем директорию
        processor.batch_process(input_path, output_path)

    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())