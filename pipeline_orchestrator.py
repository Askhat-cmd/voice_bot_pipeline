#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Voice Bot Pipeline Orchestrator (SAG v2.0 Optimized)
Coordinates the pipeline: YouTube Subtitles -> SAG v2.0 Final Data
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Any

import yaml

from env_utils import load_env
from subtitle_extractor.get_subtitles import YouTubeSubtitlesExtractor
from text_processor.sarsekenov_processor import SarsekenovProcessor
from vector_db import VectorDBManager, EmbeddingService, VectorIndexer

class PipelineOrchestrator:
    def __init__(self, config_path: str, domain: str = "sarsekenov"):
        """Initialize the pipeline orchestrator for SAG v2.0"""
        # 1) env
        load_env()
        # 2) config
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        # 3) logging
        self._setup_logging()
        self.logger = logging.getLogger("pipeline")
        self._setup_dirs()
        # 4) stages - только SAG v2.0
        self.subtitle_extractor = YouTubeSubtitlesExtractor(
            output_dir=self.config['pipeline']['subtitles']['output_dir']
        )
        # Только SarsekenovProcessor для SAG v2.0
        self.text_processor = SarsekenovProcessor()
        
        # 5) Vector DB (опционально, если настроено)
        self.vector_indexer = None
        if self.config.get('vector_db', {}).get('auto_index', False):
            try:
                db_manager = VectorDBManager(
                    db_path=self.config['vector_db']['db_path'],
                    collection_prefix=self.config['vector_db']['collection_prefix']
                )
                
                # Модель: сначала из env, потом из config
                embedding_model = os.getenv("SENTENCE_TRANSFORMERS_MODEL") or self.config['vector_db']['embedding'].get('model')
                embedding_service = EmbeddingService(model=embedding_model)
                self.vector_indexer = VectorIndexer(
                    db_manager=db_manager,
                    embedding_service=embedding_service,
                    batch_size=self.config['vector_db'].get('batch_size', 100)
                )
                self.logger.info("✅ Vector DB индексация активирована с rate limiting")
            except Exception as e:
                self.logger.warning(f"⚠️ Не удалось инициализировать Vector DB: {e}")
                self.vector_indexer = None
    
    def _setup_logging(self) -> None:
        log_cfg = self.config['logging']
        Path(Path(log_cfg['log_file']).parent).mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            level=getattr(logging, log_cfg['level'], logging.INFO),
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            handlers=[
                logging.FileHandler(log_cfg['log_file'], encoding='utf-8'),
                logging.StreamHandler()
            ],
        )

    def _setup_dirs(self) -> None:
        for d in [
            self.config['pipeline']['subtitles']['output_dir'],
            self.config['pipeline']['text_processing']['output_dir'],
        ]:
            Path(d).mkdir(parents=True, exist_ok=True)
    
    def run_full_pipeline(self, youtube_url: str, custom_name: str = None) -> Dict[str, Any]:
        """Run the complete SAG v2.0 pipeline for a single YouTube URL"""
        pipeline_start = time.time()
        results = {
            "youtube_url": youtube_url,
            "custom_name": custom_name,
            "pipeline_start": time.strftime("%Y-%m-%d %H:%M:%S"),
            "schema_version": "2.0",
            "processing_version": "v2.1",
            "stages": {}
        }
        
        self.logger.info(f"🚀 Starting SAG v2.0 pipeline for: {youtube_url}")
        
        try:
            # Stage 1: Get Subtitles (временная папка)
            self.logger.info("📥 Stage 1: Downloading subtitles from YouTube")
            stage1_start = time.time()
            
            video_id = self.subtitle_extractor.extract_video_id(youtube_url)
            if not video_id:
                raise ValueError(f"Could not extract video_id from URL: {youtube_url}")

            subtitles = self.subtitle_extractor.get_subtitles(video_id)
            if not subtitles:
                raise RuntimeError(f"Failed to retrieve subtitles for video_id: {video_id}")

            filename_id = custom_name if custom_name else video_id
            saved_files = self.subtitle_extractor.save_subtitles(filename_id, subtitles)

            results["stages"]["subtitles"] = {
                "status": "success",
                "duration": time.time() - stage1_start,
                "json_path": saved_files["json"],
                "srt_path": saved_files["srt"],
                "txt_path": saved_files["txt"]
            }
            self.logger.info(f"Stage 1 complete: {saved_files['json']}")
            
            # Stage 2: Text Processing (SAG v2.0)
            self.logger.info("📝 Stage 2: Processing text for SAG v2.0")
            stage2_start = time.time()
            
            transcript_path = Path(saved_files["json"])
            output_dir = Path(self.config['pipeline']['text_processing']['output_dir'])
            
            # Прямая обработка в SAG v2.0
            text_result = self.text_processor.process_subtitles_file(
                transcript_path, output_dir
            )
            
            results["stages"]["text_processing"] = {
                "status": "success", 
                "duration": time.time() - stage2_start,
                "sag_v2_output": text_result["json_output"],
                "review_markdown": text_result["md_output"],
                "blocks_created": text_result["blocks_created"],
                "schema_version": "2.0"
            }
            self.logger.info(f"✅ Stage 2 complete: {text_result['blocks_created']} SAG v2.0 blocks created")
            
            # Stage 3: Pipeline завершен
            self.logger.info("✅ Stage 3: Pipeline complete")
            results["stages"]["pipeline_complete"] = {
                "status": "success",
                "duration": 0.0
            }
            
            # Pipeline Summary
            total_duration = time.time() - pipeline_start
            results.update({
                "status": "success",
                "total_duration": total_duration,
                "pipeline_end": time.strftime("%Y-%m-%d %H:%M:%S"),
                "final_outputs": {
                    "sag_v2_json": text_result["json_output"],
                    "review_markdown": text_result["md_output"]
                }
            })
            
            self.logger.info(f"🎯 SAG v2.0 Pipeline complete! Total time: {total_duration:.1f}s")
            self.logger.info(f"📁 SAG v2.0 JSON: {text_result['json_output']}")
            self.logger.info(f"📖 Review Markdown: {text_result['md_output']}")
            
            # Stage 4: Vector DB Indexing (опционально)
            if self.vector_indexer:
                self.logger.info("🔍 Stage 4: Indexing to Vector DB")
                stage4_start = time.time()
                try:
                    index_levels = self.config['vector_db'].get('index_levels', ['documents', 'blocks', 'graph_entities'])
                    index_result = self.vector_indexer.index_sag_file(
                        Path(text_result['json_output']),
                        index_levels=index_levels
                    )
                    results["stages"]["vector_indexing"] = {
                        "status": "success" if index_result["success"] else "failed",
                        "duration": time.time() - stage4_start,
                        "indexed": index_result["indexed"]
                    }
                    if index_result["success"]:
                        self.logger.info(f"✅ Vector DB индексация завершена: {index_result['indexed']}")
                    else:
                        self.logger.warning(f"⚠️ Vector DB индексация завершена с ошибками")
                except Exception as e:
                    self.logger.error(f"Ошибка при индексации в Vector DB: {e}", exc_info=True)
                    results["stages"]["vector_indexing"] = {
                        "status": "failed",
                        "duration": time.time() - stage4_start,
                        "error": str(e)
                    }
            
            return results
            
        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}", exc_info=True)
            results.update({
                "status": "failed",
                "error": str(e),
                "total_duration": time.time() - pipeline_start
            })
            return results
    
    def run_batch_pipeline(self, urls_file: str) -> List[Dict[str, Any]]:
        """Run pipeline for multiple URLs from file"""
        with open(urls_file, 'r') as f:
            urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        self.logger.info(f"🚀 Starting SAG v2.0 batch pipeline for {len(urls)} URLs")
        results = []
        
        for i, url in enumerate(urls, 1):
            self.logger.info(f"📝 Processing URL {i}/{len(urls)}: {url}")
            result = self.run_full_pipeline(url)
            results.append(result)
            
            # Save batch results in raw_subtitles folder (не в SAG!)
            batch_dir = Path(self.config['pipeline']['subtitles']['output_dir'])
            batch_file = batch_dir / "batch_results.json"
            with open(batch_file, "w") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            # Очищаем старые batch результаты (оставляем только последние 2)
            batch_results = list(batch_dir.glob("batch_pipeline_results_*.json"))
            if len(batch_results) > 2:
                batch_results.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                for old_batch in batch_results[2:]:
                    old_batch.unlink()
                    self.logger.info(f"🗑️ Old batch result removed: {old_batch.name}")
        
        return results

def main():
    parser = argparse.ArgumentParser(description="Voice Bot Pipeline Orchestrator (SAG v2.0)")
    parser.add_argument("--url", help="Single YouTube URL to process")
    parser.add_argument("--urls-file", help="File containing multiple URLs (one per line)")
    parser.add_argument("--name", help="Custom name for the output files (defaults to video_id)")
    parser.add_argument("--config", required=True, help="Configuration file")
    parser.add_argument("--domain", default="sarsekenov", help="Domain processor (always sarsekenov for SAG v2.0)")
    parser.add_argument("--index-to-vector-db", action="store_true", help="Index to vector database after processing")
    
    args = parser.parse_args()
    
    # Если ничего не указано - пытаемся взять urls.txt рядом со скриптом
    default_urls = Path(__file__).resolve().parent / "urls.txt"
    if not args.url and not args.urls_file and default_urls.exists():
        args.urls_file = str(default_urls)
    if not args.url and not args.urls_file:
        parser.error("Specify --url or --urls-file (or create urls.txt in project root)")
    
    orchestrator = PipelineOrchestrator(args.config, domain=args.domain)
    
    # Включаем индексацию если указан флаг
    if args.index_to_vector_db:
        if orchestrator.config.get('vector_db'):
            orchestrator.config['vector_db']['auto_index'] = True
            # Переинициализируем векторный индексатор
            try:
                from vector_db import VectorDBManager, EmbeddingService, VectorIndexer
                db_manager = VectorDBManager(
                    db_path=orchestrator.config['vector_db']['db_path'],
                    collection_prefix=orchestrator.config['vector_db']['collection_prefix']
                )
                
                # Модель: сначала из env, потом из config
                embedding_model = os.getenv("SENTENCE_TRANSFORMERS_MODEL") or orchestrator.config['vector_db']['embedding'].get('model')
                embedding_service = EmbeddingService(model=embedding_model)
                orchestrator.vector_indexer = VectorIndexer(
                    db_manager=db_manager,
                    embedding_service=embedding_service,
                    batch_size=orchestrator.config['vector_db'].get('batch_size', 100)
                )
                orchestrator.logger.info("✅ Vector DB индексация активирована через CLI флаг")
            except Exception as e:
                orchestrator.logger.error(f"Ошибка при инициализации Vector DB: {e}")
                return 1
        else:
            orchestrator.logger.error("Vector DB не настроен в config.yaml")
            return 1
    
    # Check OpenAI API key (still needed for text processing)
    if not os.getenv("OPENAI_API_KEY"):
        orchestrator.logger.error("OPENAI_API_KEY environment variable not set")
        orchestrator.logger.info("Make sure your .env file contains: OPENAI_API_KEY=your-key-here")
        return 1
    
    if args.url:
        result = orchestrator.run_full_pipeline(args.url, args.name)
        
        # Сохраняем результаты в raw_subtitles папку (не в SAG!)
        results_dir = Path(orchestrator.config['pipeline']['subtitles']['output_dir'])
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        results_file = results_dir / f"pipeline_result_{timestamp}.json"
        with open(results_file, "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"\n[SUCCESS] Pipeline results saved: {results_file}")
        
        if result["status"] == "success":
            print(f"[OUTPUT] SAG v2.0 JSON: {result['final_outputs']['sag_v2_json']}")
            print(f"[OUTPUT] Review MD: {result['final_outputs']['review_markdown']}")
            return 0
        else:
            print(f"[ERROR] Pipeline failed: {result.get('error', 'Unknown error')}")
            return 1
    
    elif args.urls_file:
        results = orchestrator.run_batch_pipeline(args.urls_file)
        
        # Сохраняем batch результаты в raw_subtitles папку (не в SAG!)
        results_dir = Path(orchestrator.config['pipeline']['subtitles']['output_dir'])
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        results_file = results_dir / f"batch_pipeline_results_{timestamp}.json"
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        successful = sum(1 for r in results if r["status"] == "success")
        print(f"\n[BATCH COMPLETE] SAG v2.0: {successful}/{len(results)} URLs processed successfully")
        print(f"[RESULTS] Saved to: {results_file}")
        
        return 0 if successful == len(results) else 1

if __name__ == "__main__":
    sys.exit(main())