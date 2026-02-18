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
from text_processor.sd_labeler import SDLabeler
from vector_db import VectorDBManager, EmbeddingService, VectorIndexer
from utils.video_registry import VideoRegistry, VideoMetadata, ProcessingRecord
from utils.youtube_metadata_fetcher import YouTubeAPIMetadataFetcher
from utils.file_utils import create_filename, get_date_paths
from utils.channel_list_parser import ChannelListParser
from utils.markdown_updater import MarkdownUpdater
from datetime import datetime

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
        
        # 3.5) Video Registry и Metadata Fetcher
        registry_path = self.config.get('pipeline', {}).get('registry_path', 'data/video_registry.json')
        self.registry = VideoRegistry(registry_path)
        self.metadata_fetcher = YouTubeAPIMetadataFetcher()
        
        # 3.6) Markdown Updater для обновления списка видео
        channel_list_config = self.config.get('channel_list', {})
        markdown_path = Path(__file__).resolve().parent / "data" / "channel_video_list" / "channel_videos_list.md"
        if markdown_path.exists():
            try:
                self.markdown_updater = MarkdownUpdater(str(markdown_path), registry_path)
            except:
                self.markdown_updater = None
        else:
            self.markdown_updater = None
        
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
                self.logger.info("✅ Vector DB индексация активирована")
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

    def _apply_sd_labeling(self, sag_json_path: Path) -> None:
        """Дополнить SAG JSON SD-метаданными блоков (best effort, без падения pipeline)."""
        sd_cfg = self.config.get("sd_labeling", {})
        if not sd_cfg.get("enabled", True):
            self.logger.info("[PIPELINE] SD labeling disabled by config")
            return

        try:
            with open(sag_json_path, "r", encoding="utf-8") as f:
                sag_data = json.load(f)

            blocks = sag_data.get("blocks", [])
            if not blocks:
                self.logger.warning("[PIPELINE] SD labeling skipped: no blocks in SAG JSON")
                return

            labeler = SDLabeler(
                model=sd_cfg.get("model", "gpt-4o-mini"),
                temperature=float(sd_cfg.get("temperature", 0.1)),
                max_tokens=int(sd_cfg.get("max_tokens", 200)),
                max_chars=int(sd_cfg.get("max_chars", 1500)),
            )
            author_id = (
                sd_cfg.get("author_id")
                or self.config.get("author", {}).get("author_id")
                or "unknown"
            )
            sag_data["blocks"] = labeler.label_blocks_batch(blocks, author_id=author_id)

            with open(sag_json_path, "w", encoding="utf-8") as f:
                json.dump(sag_data, f, ensure_ascii=False, indent=2)

            self.logger.info(
                f"[PIPELINE] SD labeling complete: {len(sag_data['blocks'])} blocks labeled"
            )
        except Exception as exc:
            self.logger.warning(
                f"[PIPELINE] SD labeling failed: {exc}. Continue without SD metadata."
            )
    
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
        
        video_id = None
        video_metadata = None
        
        try:
            # Pre-stage: Extract video ID and check for duplicates
            self.logger.info("🔍 Pre-stage: Extracting video ID and checking registry")
            video_id = self.subtitle_extractor.extract_video_id(youtube_url)
            if not video_id:
                raise ValueError(f"Could not extract video_id from URL: {youtube_url}")
            
            # Проверка дубликатов
            if self.registry.is_processed(video_id):
                self.logger.info(f"⏭️  Пропуск {video_id}: уже обработано")
                return {
                    "status": "skipped",
                    "reason": "already_processed",
                    "video_id": video_id,
                    "youtube_url": youtube_url
                }
            
            # Получение метаданных через YouTube API
            self.logger.info(f"📥 Получение метаданных для {video_id}...")
            try:
                metadata_dict = self.metadata_fetcher.fetch_metadata(youtube_url)
                video_metadata = VideoMetadata(**metadata_dict)
                
                # Добавляем в реестр, если еще нет
                if not self.registry.video_exists(video_id):
                    self.registry.add_video(video_metadata)
                else:
                    # Обновляем метаданные если они изменились
                    video_metadata = VideoMetadata(**metadata_dict)
                    self.registry.update_status(video_id, "pending")
                
                self.logger.info(f"✅ Метаданные получены: {video_metadata.title}")
            except Exception as e:
                self.logger.warning(f"⚠️ Ошибка получения метаданных: {e}. Используем базовые значения.")
                # Создаем базовые метаданные
                video_metadata = VideoMetadata(
                    video_id=video_id,
                    title=f"Video {video_id}",
                    channel="Unknown",
                    published_date=datetime.now().isoformat(),
                    duration_seconds=0,
                    url=youtube_url
                )
                if not self.registry.video_exists(video_id):
                    self.registry.add_video(video_metadata)
            
            # Обновляем статус на "processing"
            self.registry.update_status(video_id, "processing")
            
            # Stage 1: Get Subtitles
            self.logger.info("📥 Stage 1: Downloading subtitles from YouTube")
            stage1_start = time.time()
            
            subtitles = self.subtitle_extractor.get_subtitles(video_id)
            if not subtitles:
                raise RuntimeError(f"Failed to retrieve subtitles for video_id: {video_id}")

            # Сохраняем субтитры с новыми именами (если есть метаданные)
            if video_metadata:
                saved_files = self.subtitle_extractor.save_subtitles(
                    video_id, 
                    subtitles,
                    title=video_metadata.title,
                    published_date=video_metadata.published_date
                )
            else:
                saved_files = self.subtitle_extractor.save_subtitles(video_id, subtitles)

            results["stages"]["subtitles"] = {
                "status": "success",
                "duration": time.time() - stage1_start,
                "json_path": saved_files["json"],
                "srt_path": saved_files["srt"],
                "txt_path": saved_files["txt"]
            }
            self.logger.info(f"Stage 1 complete: {saved_files['json']}")
            
            # Сохраняем путь к файлу субтитров в реестре
            if video_metadata:
                self.registry.set_file_path(video_id, "raw_subtitles", saved_files["json"])
            
            # Stage 2: Text Processing (SAG v2.0)
            self.logger.info("📝 Stage 2: Processing text for SAG v2.0")
            stage2_start = time.time()
            
            transcript_path = Path(saved_files["json"])
            
            # Определяем output_dir с учетом дат (если есть метаданные)
            if video_metadata:
                base_output_dir = Path(self.config['pipeline']['text_processing']['output_dir'])
                output_dir, year, month = get_date_paths(base_output_dir, video_metadata.published_date)
                output_dir.mkdir(parents=True, exist_ok=True)
            else:
                output_dir = Path(self.config['pipeline']['text_processing']['output_dir'])
            
            # Прямая обработка в SAG v2.0
            text_result = self.text_processor.process_subtitles_file(
                transcript_path, output_dir
            )
            
            # Если есть метаданные, переименовываем файлы с датами и названиями
            if video_metadata:
                try:
                    # Переименовываем SAG JSON файл
                    old_json_path = Path(text_result["json_output"])
                    new_json_filename = create_filename(
                        video_id, 
                        video_metadata.title, 
                        video_metadata.published_date, 
                        ext="for_vector.json"
                    )
                    new_json_path = output_dir / new_json_filename
                    if old_json_path.exists() and old_json_path != new_json_path:
                        old_json_path.rename(new_json_path)
                        text_result["json_output"] = str(new_json_path)
                    
                    # Переименовываем MD файл
                    old_md_path = Path(text_result["md_output"])
                    new_md_filename = create_filename(
                        video_id,
                        video_metadata.title,
                        video_metadata.published_date,
                        ext="for_review.md"
                    )
                    new_md_path = output_dir / new_md_filename
                    if old_md_path.exists() and old_md_path != new_md_path:
                        old_md_path.rename(new_md_path)
                        text_result["md_output"] = str(new_md_path)
                except Exception as e:
                    self.logger.warning(f"⚠️ Не удалось переименовать файлы: {e}")

            # SD-разметка блоков после формирования SAG JSON
            self._apply_sd_labeling(Path(text_result["json_output"]))
            
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
            
            # Подсчитываем количество сущностей из SAG результата
            entities_count = 0
            blocks_count = text_result.get("blocks_created", 0)
            try:
                with open(text_result["json_output"], 'r', encoding='utf-8') as f:
                    sag_data = json.load(f)
                    for block in sag_data.get("blocks", []):
                        entities_count += len(block.get("graph_entities", []))
            except:
                pass
            
            # Оценка стоимости API (упрощенная)
            api_cost_estimate = blocks_count * 0.01  # Примерная оценка
            
            # Сохраняем пути к файлам в реестре
            if video_metadata:
                self.registry.set_file_path(video_id, "sag_json", text_result["json_output"])
                self.registry.set_file_path(video_id, "sag_md", text_result["md_output"])
            
            # Создаем запись об обработке
            processing_record = ProcessingRecord(
                processed_at=datetime.now().isoformat(),
                pipeline_version="v2.1",
                stage_completed="all",
                blocks_created=blocks_count,
                entities_extracted=entities_count,
                processing_time_seconds=total_duration,
                api_cost_estimate=api_cost_estimate
            )
            self.registry.add_processing_record(video_id, processing_record)
            
            results.update({
                "status": "success",
                "video_id": video_id,
                "total_duration": total_duration,
                "pipeline_end": time.strftime("%Y-%m-%d %H:%M:%S"),
                "final_outputs": {
                    "sag_v2_json": text_result["json_output"],
                    "review_markdown": text_result["md_output"]
                },
                "blocks_created": blocks_count,
                "entities_extracted": entities_count
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
            
            # Записываем ошибку в реестр
            if video_id:
                try:
                    error_record = ProcessingRecord(
                        processed_at=datetime.now().isoformat(),
                        pipeline_version="v2.1",
                        stage_completed="failed",
                        blocks_created=0,
                        entities_extracted=0,
                        processing_time_seconds=time.time() - pipeline_start,
                        api_cost_estimate=0.0,
                        error_message=str(e)
                    )
                    self.registry.add_processing_record(video_id, error_record)
                except:
                    pass
            
            results.update({
                "status": "failed",
                "error": str(e),
                "video_id": video_id,
                "total_duration": time.time() - pipeline_start
            })
            return results
    
    def run_batch_pipeline(self, urls_file: str) -> List[Dict[str, Any]]:
        """Run pipeline for multiple URLs from file with support for video numbers from channel list"""
        # Проверяем настройки использования списка канала
        channel_list_config = self.config.get('channel_list', {})
        use_channel_list = channel_list_config.get('use_channel_list', True)
        json_path = channel_list_config.get('json_path', 'data/channel_videos_list.json')
        
        urls = []
        warnings = []
        
        # Если включено использование списка канала
        if use_channel_list:
            json_path_full = Path(__file__).resolve().parent / json_path
            if json_path_full.exists():
                try:
                    parser = ChannelListParser(str(json_path_full))
                    urls, warnings = parser.parse_urls_file(urls_file)
                    
                    # Выводим предупреждения если есть
                    for warning in warnings:
                        self.logger.warning(f"[WARNING] {warning}")
                    
                    self.logger.info(f"[INFO] Использован список канала: найдено {len(urls)} URL из файла {urls_file}")
                except Exception as e:
                    self.logger.warning(f"[WARNING] Ошибка при использовании списка канала: {e}. Используется обычный режим.")
                    # Fallback на обычный режим
                    with open(urls_file, 'r', encoding='utf-8') as f:
                        urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            else:
                self.logger.warning(f"[WARNING] Файл списка канала не найден: {json_path_full}. Используется обычный режим.")
                # Fallback на обычный режим
                with open(urls_file, 'r', encoding='utf-8') as f:
                    urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        else:
            # Обычный режим без использования списка
            with open(urls_file, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        self.logger.info(f"🚀 Starting SAG v2.0 batch pipeline for {len(urls)} URLs")
        
        # Шаг 1: Сбор метаданных и проверка дубликатов
        videos_to_process = []
        skipped_count = 0
        
        for url in urls:
            try:
                video_id = self.subtitle_extractor.extract_video_id(url)
                if not video_id:
                    self.logger.warning(f"⚠️ Не удалось извлечь video_id из: {url}")
                    continue
                
                # Проверка: уже обработано?
                if self.registry.is_processed(video_id):
                    self.logger.info(f"⏭️  Пропуск {video_id}: уже обработано")
                    skipped_count += 1
                    continue
                
                videos_to_process.append((video_id, url))
                
            except Exception as e:
                self.logger.error(f"❌ Ошибка обработки URL {url}: {e}")
                continue
        
        self.logger.info(f"✅ К обработке: {len(videos_to_process)} видео (пропущено: {skipped_count})")
        
        # Шаг 2: Обработка видео
        results = []
        for i, (video_id, url) in enumerate(videos_to_process, 1):
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"📹 Обработка видео {i}/{len(videos_to_process)}: {video_id}")
            self.logger.info(f"{'='*60}\n")
            
            result = self.run_full_pipeline(url)
            results.append(result)
            
            # Обновляем Markdown файл после обработки
            if self.markdown_updater and result.get("status") == "success":
                try:
                    self.markdown_updater.update_after_processing(video_id)
                    self.logger.info(f"[INFO] Markdown файл обновлен для видео {video_id}")
                except Exception as e:
                    self.logger.warning(f"[WARNING] Не удалось обновить Markdown для {video_id}: {e}")
        
        # Финальная статистика
        stats = self.registry.get_statistics()
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"📊 ИТОГОВАЯ СТАТИСТИКА")
        self.logger.info(f"{'='*60}")
        self.logger.info(f"Всего видео: {stats['total_videos']}")
        self.logger.info(f"Обработано: {stats['processed']}")
        self.logger.info(f"Ошибок: {stats['failed']}")
        self.logger.info(f"В очереди: {stats['pending']}")
        self.logger.info(f"Всего блоков: {stats['total_blocks']}")
        self.logger.info(f"Всего сущностей: {stats['total_entities']}")
        self.logger.info(f"Затраты API: ${stats['total_api_cost']}")
        self.logger.info(f"{'='*60}\n")
        
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
        with open(results_file, "w", encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Очищаем старые batch результаты (оставляем только последние 2)
        batch_results = list(results_dir.glob("batch_pipeline_results_*.json"))
        if len(batch_results) > 2:
            batch_results.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            for old_batch in batch_results[2:]:
                old_batch.unlink()
                orchestrator.logger.info(f"🗑️ Old batch result removed: {old_batch.name}")
        
        successful = sum(1 for r in results if r["status"] == "success")
        print(f"\n[BATCH COMPLETE] SAG v2.0: {successful}/{len(results)} URLs processed successfully")
        print(f"[RESULTS] Saved to: {results_file}")
        
        return 0 if successful == len(results) else 1

if __name__ == "__main__":
    sys.exit(main())
