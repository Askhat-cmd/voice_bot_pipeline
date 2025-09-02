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

    # ---------------------- SAG v2.0 CLASSIFICATION FUNCTIONS ---------------------- #
    
    def detect_speaker(self, content: str) -> str:
        """
        Определяет спикера блока на основе содержания
        """
        # Если в тексте есть >> - это диалог
        if ">>" in content:
            return "mixed"  # Смешанный контент
        
        # Маркеры речи Сарсекенова
        sarsekenov_markers = [
            "понимаете", "заметили", "чувствуете", "прямо сейчас", 
            "повторяюсь", "вот смотрите", "штрих-код бросаю",
            "к примеру", "мало того", "опять же", "видите ли"
        ]
        
        # Подсчитываем маркеры
        content_lower = content.lower()
        marker_count = sum(1 for marker in sarsekenov_markers if marker in content_lower)
        
        # Если много маркеров Сарсекенова или длинный текст - это он
        if marker_count >= 2 or len(content) > 500:
            return "sarsekenov"
        
        # Иначе - неизвестно или участник
        return "unknown"

    def detect_block_type(self, content: str) -> str:
        """
        Определяет тип блока (монолог/диалог/практика)
        """
        # Проверяем наличие диалоговых маркеров
        if ">>" in content:
            return "dialogue"
        
        # Маркеры практических упражнений
        practice_keywords = [
            "упражнение", "практика", "медитация", "прочувствуйте",
            "ощутите", "попробуйте", "сосредоточьтесь", "наблюдайте",
            "почувствуйте", "исследуйте"
        ]
        
        content_lower = content.lower()
        if any(keyword in content_lower for keyword in practice_keywords):
            return "practice"
        
        # Маркеры вопросов
        if content.strip().endswith("?") or "вопрос" in content_lower:
            return "question"
        
        # По умолчанию - монолог
        return "monologue"

    def detect_emotional_tone(self, content: str, title: str) -> str:
        """
        Определяет эмоциональный тон блока
        """
        # Ключевые слова для разных тонов
        tones = {
            "contemplative": ["размышления", "осознание", "понимание", "глубокое", "суть", "сущность"],
            "explanatory": ["объяснение", "к примеру", "смотрите", "понимаете", "заметили", "видите"],
            "intense": ["критически", "важно", "серьезно", "драматически", "сильно", "страдание"],
            "light": ["смех", "игра", "легко", "просто", "улыбка", "классно", "забавно"]
        }
        
        # Подсчитываем совпадения
        text_to_analyze = (content + " " + title).lower()
        scores = {}
        for tone, keywords in tones.items():
            score = sum(1 for kw in keywords if kw in text_to_analyze)
            scores[tone] = score
        
        # Возвращаем тон с наибольшим счетом или neutral
        if max(scores.values()) > 0:
            return max(scores.keys(), key=lambda k: scores[k])
        return "neutral"

    def detect_conceptual_depth(self, content: str, keywords: list) -> str:
        """
        Определяет концептуальную глубину блока
        """
        # Маркеры высокой глубины
        deep_concepts = [
            "сущность", "природа", "абсолют", "бытие", "сознание",
            "просветление", "пробуждение", "божественность", "истина",
            "трансформация", "исцеление"
        ]
        
        # Маркеры средней глубины  
        medium_concepts = [
            "понимание", "осознание", "исследование", "наблюдение",
            "внимание", "переживание", "опыт", "мудрость", "практика"
        ]
        
        # Подсчитываем
        content_lower = content.lower()
        keywords_str = " ".join(keywords).lower()
        
        deep_count = sum(1 for concept in deep_concepts 
                        if concept in content_lower or concept in keywords_str)
        medium_count = sum(1 for concept in medium_concepts 
                          if concept in content_lower or concept in keywords_str)
        
        if deep_count >= 2:
            return "high"
        elif medium_count >= 2 or deep_count >= 1:
            return "medium"
        else:
            return "low"

    def calculate_complexity_score(self, content: str, keywords: list, conceptual_depth: str) -> float:
        """
        Рассчитывает числовую оценку сложности (1-10)
        """
        base_score = 5.0
        
        # Корректировка по глубине
        depth_modifier = {"low": -1.5, "medium": 0, "high": 2.0}
        base_score += depth_modifier.get(conceptual_depth, 0)
        
        # Корректировка по количеству ключевых слов
        if len(keywords) > 5:
            base_score += 1.0
        elif len(keywords) < 3:
            base_score -= 0.5
            
        # Корректировка по длине текста (сложность растет с объемом)
        if len(content) > 1500:
            base_score += 1.0
        elif len(content) < 500:
            base_score -= 0.5
        
        # Ограничиваем диапазон 1-10
        return max(1.0, min(10.0, round(base_score, 1)))

    def extract_graph_entities(self, content: str, keywords: list) -> list:
        """
        Извлекает ключевые сущности для граф-системы знаний нейросталкинга
        Основано на коллекции из 442 узлов граф-системы
        """
        # КОНЦЕПТЫ НЕЙРОСТАЛКИНГА (74 узла) - приоритетные
        neurostalking_concepts = [
            # Ключевые термины Сарсекенова
            "нейросталкинг", "неосталкинг", "сталкинг ума",
            "метанаблюдение", "поле внимания", "поле восприятия",
            "свободное внимание", "чистое осознавание", "само-осознавание",
            "самоосознание", "присутствие", "здесь и сейчас",
            "живое переживание", "живое знание", "непосредственное восприятие",
            
            # Процессы познания
            "самоисследование", "самопознание", "сталкинг", "наблюдение за умом",
            "исследование ума", "разотождествление", "центрирование", "осознавание",
            "внимательность", "осознанность", "випашьяна", "шаматха",
            
            # Духовные концепты
            "пробуждение", "просветление", "освобождение", "единство", "недуальность",
            "божественность", "абсолют", "истина", "сущность", "сознание",
            "чистое сознание", "бытие", "присутствие бытия",
            
            # Психологические концепты
            "личность", "эго", "ложное я", "истинное я", "высшее я", "самость",
            "идентичность", "проекция", "интроекция", "защитные механизмы"
        ]
        
        # ПСИХОЛОГИЧЕСКИЕ СОСТОЯНИЯ (94 узла)
        psychological_states = [
            # Негативные состояния
            "страдание", "боль", "печаль", "горе", "депрессия", "тревога", "страх",
            "обида", "гнев", "ярость", "вина", "стыд", "одиночество", "отчуждение",
            
            # Позитивные состояния
            "радость", "счастье", "блаженство", "любовь", "сострадание", "эмпатия",
            "благодарность", "прощение", "принятие", "доверие", "вера", "покой",
            "умиротворение", "гармония", "баланс", "целостность", "свобода",
            
            # Трансформационные состояния
            "инсайт", "прозрение", "озарение", "откровение", "понимание", "ясность",
            "трансценденция", "экстаз", "поток", "центрированность", "заземленность",
            
            # Специфические состояния нейросталкинга
            "живость", "подлинность", "искренность", "честность", "открытость",
            "уязвимость", "смелость", "мужество", "позерство", "фальшь", "сопротивление"
        ]
        
        # ПРОЦЕССЫ ТРАНСФОРМАЦИИ (101 узел)
        transformation_processes = [
            # Процессы познания
            "познание", "изучение", "исследование", "анализ", "синтез", "интеграция",
            "понимание", "постижение", "осмысление", "прозрение", "инсайт", "интуиция",
            
            # Процессы трансформации
            "изменение", "трансформация", "эволюция", "развитие", "рост", "созревание",
            "возрождение", "метаморфоза", "алхимия", "трансмутация", "очищение", "исцеление",
            
            # Процессы интеграции
            "интеграция опыта", "объединение", "слияние", "единение", "гармонизация",
            "балансировка", "стабилизация", "центрирование", "заземление", "укоренение",
            "признание", "принятие", "одобрение", "поддержка",
            
            # Процессы освобождения
            "освобождение", "отпускание", "отдача", "сдача", "капитуляция", "смирение",
            "доверие", "преданность", "служение", "непривязанность", "отрешенность"
        ]
        
        # ПРАКТИКИ И ТЕХНИКИ (77 узлов)
        practices = [
            # Основные практики нейросталкинга
            "наблюдение за наблюдающим", "исследование поля внимания",
            "работа с присутствием", "дыхательные практики", "телесные практики",
            
            # Медитативные практики
            "медитация", "дзен", "дзадзен", "коан", "мантра", "пранаяма", "асана",
            "визуализация", "воображение",
            
            # Практики самоисследования
            "самонаблюдение", "самоанализ", "саморефлексия", "самопознание",
            "самопринятие", "самопрощение", "самолюбовь", "самореализация"
        ]
        
        # Собираем все концепты
        all_concepts = (neurostalking_concepts + psychological_states + 
                       transformation_processes + practices)
        
        entities = []
        content_lower = content.lower()
        
        # Добавляем ключевые слова (высокий приоритет)
        entities.extend(keywords)
        
        # Ищем концепты в тексте
        for concept in all_concepts:
            if concept in content_lower:
                entities.append(concept)
        
        # Убираем дубликаты и сортируем по приоритету
        unique_entities = list(set(entities))
        
        # Приоритизация: концепты нейросталкинга в начале
        prioritized_entities = []
        
        # Сначала добавляем концепты нейросталкинга
        for entity in unique_entities:
            if entity in neurostalking_concepts:
                prioritized_entities.append(entity)
        
        # Затем остальные
        for entity in unique_entities:
            if entity not in neurostalking_concepts and entity not in prioritized_entities:
                prioritized_entities.append(entity)
        
        # Ограничиваем количество (максимум 12 сущностей для SAG)
        raw_entities = prioritized_entities[:15]
        
        # Применяем нормализацию
        normalized_entities = self._normalize_graph_entities(raw_entities)
        
        return normalized_entities[:12]

    def _normalize_graph_entities(self, entities: list) -> list:
        """
        Нормализует граф-сущности: синонимы, фильтр общих слов, дедупликация
        """
        if not entities:
            return []
        
        # Словарь синонимов (приводим к канонической форме)
        synonym_map = {
            "осознанность": "осознание",
            "наблюдение за умом": "метанаблюдение", 
            "внимательность": "осознание",
            "центрирование внимания": "центрирование",
            "поле внимания": "внимание",
            "исследование переживаний": "переживания",
            "автоматические реакции": "автоматизмы",
            "паттерны поведения": "паттерны",
            "триггерные ситуации": "триггеры",
            "медитативные практики": "медитация",
            "дыхательные практики": "дыхание",
            "телесные ощущения": "тело",
            "эмоциональные состояния": "эмоции",
            "ментальные процессы": "ум",
            "духовные практики": "духовность",
            "трансформационные процессы": "трансформация"
        }
        
        # Стоп-слова (слишком общие для граф-системы)
        stop_words = {
            "рост", "боль", "ощущение", "мысль", "идея", "состояние",
            "процесс", "опыт", "чувство", "момент", "время", "жизнь",
            "человек", "люди", "мир", "путь", "способ", "метод"
        }
        
        # Фильтр коротких и общеязыковых слов
        min_length = 4
        
        normalized = []
        seen = set()
        
        for entity in entities:
            if not entity or not isinstance(entity, str):
                continue
                
            # Очистка и нормализация
            clean_entity = entity.strip().lower()
            
            # Пропускаем слишком короткие
            if len(clean_entity) < min_length:
                continue
            
            # Применяем синонимы
            canonical_form = synonym_map.get(clean_entity, clean_entity)
            
            # Пропускаем стоп-слова
            if canonical_form in stop_words:
                continue
            
            # Дедупликация
            if canonical_form in seen:
                continue
                
            seen.add(canonical_form)
            normalized.append(canonical_form)
        
        # Дополнительная фильтрация по частотности
        # Если слишком много сущностей, оставляем только наиболее специфичные
        if len(normalized) > 12:
            # Приоритизируем длинные составные термины
            specialized_terms = [e for e in normalized if len(e) > 8 or " " in e]
            basic_terms = [e for e in normalized if e not in specialized_terms]
            
            # Берем все специализированные + лучшие базовые
            normalized = specialized_terms + basic_terms[:12-len(specialized_terms)]
        
        return normalized[:12]

    def detect_has_dialogue(self, blocks: list, full_text: str = None) -> bool:
        """
        Определяет есть ли диалоги в документе (анализ блоков + full_text)
        """
        
        # 1. ПРИОРИТЕТ: Анализ full_text (более надежный)
        if full_text:
            # Диалоговые маркеры в полном тексте
            if ">>" in full_text:
                return True
            
            # Вопросительные конструкции в конце строк
            import re
            if re.search(r'\?\s*$', full_text, re.MULTILINE):
                return True
            
            # Частые диалоговые фразы
            dialogue_markers = [
                "можете спросить", "да, вопрос", "вопрос есть", 
                "спрашива", "отвеча", "а если", "можно ли",
                "как же", "что делать", "почему так"
            ]
            
            full_text_lower = full_text.lower()
            for marker in dialogue_markers:
                if marker in full_text_lower:
                    return True
        
        # 2. Анализ блоков (резервный)
        for block in blocks:
            content = block.get("content", "")
            block_type = block.get("block_type", "")
            
            # Диалоговые маркеры в блоках
            if ">>" in content:
                return True
            if block_type in ["dialogue", "question"]:
                return True
            
            # Вопросительные конструкции
            if content.strip().endswith("?"):
                return True
            if any(marker in content.lower() for marker in [
                "можете спросить", "вопрос", "спрашива", "отвеча"
            ]):
                return True
        
        return False

    def structure_dialogue_block(self, content: str) -> dict:
        """
        Структурирует диалоговый блок для SAG-системы v2.1 с улучшенной классификацией
        """
        if ">>" not in content:
            return {}
        
        # Разделяем на реплики по маркеру >>
        parts = content.split(">>")
        dialogue_structure = []
        dialogue_turn = 0
        
        for i, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue
            
            dialogue_turn += 1
            
            # Улучшенное определение спикера и типа реплики
            is_question = part.endswith("?") or any(marker in part.lower() for marker in [
                "можете спросить", "вопрос", "как", "что", "почему", "зачем", "где", "когда"
            ])
            
            # Эвристика определения спикера
            if i == 0:  # Первая часть обычно Сарсекенов
                speaker = "sarsekenov"
                question_type = None
                answer_completeness = None
            elif is_question and len(part) < 200:  # Короткие вопросы - участники
                speaker = "participant"
                # Улучшенная классификация типа вопроса
                part_lower = part.lower()
                if any(kw in part_lower for kw in ["как", "можно ли", "что делать", "как применить"]):
                    question_type = "practical"
                elif any(kw in part_lower for kw in ["что такое", "почему", "в чем", "зачем"]):
                    question_type = "theoretical"  
                elif any(kw in part_lower for kw in ["у меня", "со мной", "мне", "я"]):
                    question_type = "personal"
                else:
                    question_type = "clarification"
                answer_completeness = None
            else:  # Длинные ответы - Сарсекенов
                speaker = "sarsekenov"
                question_type = None
                # Оценка полноты ответа
                if len(part) > 500:
                    answer_completeness = "full"
                elif len(part) > 200:
                    answer_completeness = "partial"
                elif any(redirect in part.lower() for redirect in [
                    "это отдельная тема", "об этом позже", "не сейчас", "потом"
                ]):
                    answer_completeness = "redirected"
                else:
                    answer_completeness = "partial"
            
            dialogue_structure.append({
                "turn_id": dialogue_turn,
                "speaker": speaker,
                "content": part,
                "question_type": question_type,
                "answer_completeness": answer_completeness,
                "word_count": len(part.split()),
                "char_length": len(part)
            })
        
        # Анализируем участников
        participant_turns = [turn for turn in dialogue_structure if turn["speaker"] == "participant"]
        sarsekenov_turns = [turn for turn in dialogue_structure if turn["speaker"] == "sarsekenov"]
        
        # Улучшенная оценка качества взаимодействия
        quality_factors = []
        
        # Фактор 1: Количество обменов (больше = лучше, но не линейно)
        exchange_count = min(len(participant_turns), len(sarsekenov_turns))
        turn_score = min(4.0, exchange_count * 1.5)
        quality_factors.append(turn_score)
        
        # Фактор 2: Разнообразие типов вопросов
        question_types = set(turn["question_type"] for turn in participant_turns if turn["question_type"])
        diversity_score = len(question_types) * 1.2
        quality_factors.append(diversity_score)
        
        # Фактор 3: Полнота ответов
        full_answers = len([t for t in sarsekenov_turns if t["answer_completeness"] == "full"])
        completeness_score = full_answers * 1.8
        quality_factors.append(completeness_score)
        
        # Фактор 4: Развернутость ответов
        avg_answer_length = sum(t["word_count"] for t in sarsekenov_turns) / len(sarsekenov_turns) if sarsekenov_turns else 0
        if avg_answer_length > 100:
            length_score = 2.0
        elif avg_answer_length > 50:
            length_score = 1.0
        else:
            length_score = 0.5
        quality_factors.append(length_score)
        
        # Итоговая оценка (1-10)
        interaction_quality = min(10.0, max(3.0, sum(quality_factors)))
        
        return {
            "dialogue_structure": dialogue_structure,
            "interaction_quality": round(interaction_quality, 1),
            "total_turns": dialogue_turn,
            "participant_turns": len(participant_turns),
            "sarsekenov_turns": len(sarsekenov_turns),
            "total_exchanges": exchange_count,
            "question_types": list(question_types),
            "question_count": len([t for t in dialogue_structure if t["question_type"]]),
            "answer_count": len([t for t in dialogue_structure if t["answer_completeness"]]),
            "full_answers": full_answers,
            "avg_answer_length": round(avg_answer_length, 1)
        }

    def determine_collection_target(self, main_topics: list, keywords: list, has_dialogue: bool, 
                                   blocks: list) -> tuple:
        """
        Определяет целевую коллекцию для блока в граф-системе SAG
        Возвращает: (collection_target, routing_confidence)
        """
        # Объединяем все ключевые слова
        all_keywords = main_topics + keywords
        keywords_str = " ".join(all_keywords).lower()
        
        # Анализируем содержание блоков для более точного определения
        all_content = " ".join([block.get("content", "") for block in blocks]).lower()
        
        # Если есть диалог - приоритет dialogue_sessions
        if has_dialogue:
            return "dialogue_sessions"
        
        # Маркеры для разных коллекций (на основе граф-системы)
        collection_markers = {
            "neurostalking_basics": [
                "нейросталкинг", "неосталкинг", "основы", "концепция", 
                "определение", "терминология", "система", "метанаблюдение",
                "поле внимания", "свободное внимание", "сталкинг ума"
            ],
            "meditation_practices": [
                "медитация", "практика", "упражнение", "дыхание", "пранаяма",
                "центрирование", "заземление", "техника", "випашьяна", "шаматха",
                "наблюдение за наблюдающим", "исследование поля внимания"
            ],
            "healing_transformation": [
                "исцеление", "трансформация", "преодоление", "боль", "страдание",
                "обида", "прощение", "принятие", "интеграция", "освобождение",
                "отпускание", "сдача", "капитуляция", "смирение"
            ],
            "advanced_concepts": [
                "пробуждение", "просветление", "сознание", "абсолют", "бытие", 
                "сущность", "божественность", "мудрость", "единство", "недуальность",
                "чистое сознание", "присутствие бытия", "истина"
            ],
            "psychological_states": [
                "состояние", "эмоция", "чувство", "переживание", "настроение",
                "радость", "счастье", "печаль", "гнев", "страх", "тревога",
                "покой", "умиротворение", "блаженство", "экстаз"
            ],
            "spiritual_development": [
                "развитие", "эволюция", "рост", "созревание", "прогресс",
                "самопознание", "самоисследование", "самореализация",
                "духовность", "духовный путь", "путь", "практикующий"
            ]
        }
        
        # Подсчитываем совпадения для keywords
        keyword_scores = {}
        for collection, markers in collection_markers.items():
            score = sum(1 for marker in markers if marker in keywords_str)
            keyword_scores[collection] = score
        
        # Подсчитываем совпадения для контента (с меньшим весом)
        content_scores = {}
        for collection, markers in collection_markers.items():
            score = sum(1 for marker in markers if marker in all_content)
            content_scores[collection] = score * 0.5  # Меньший вес для контента
        
        # Объединяем оценки
        total_scores = {}
        for collection in collection_markers.keys():
            total_scores[collection] = keyword_scores[collection] + content_scores[collection]
        
        # Специальные правила для более точного определения
        
        # Если много практических терминов - медитативные практики
        practice_terms = ["упражнение", "техника", "метод", "способ", "практика"]
        practice_count = sum(1 for term in practice_terms if term in keywords_str)
        if practice_count >= 2:
            total_scores["meditation_practices"] += 2.0
        
        # Если есть эмоциональные термины - психологические состояния
        emotion_terms = ["чувство", "эмоция", "переживание", "состояние"]
        emotion_count = sum(1 for term in emotion_terms if term in keywords_str)
        if emotion_count >= 2:
            total_scores["psychological_states"] += 2.0
        
        # Если есть глубокие концепты - продвинутые концепты
        deep_terms = ["сущность", "абсолют", "бытие", "истина", "божественность"]
        deep_count = sum(1 for term in deep_terms if term in keywords_str)
        if deep_count >= 1:
            total_scores["advanced_concepts"] += 2.0
        
        # Возвращаем коллекцию с наибольшим счетом + confidence
        if max(total_scores.values()) > 0:
            best_collection = max(total_scores.keys(), key=lambda k: total_scores[k])
            best_score = total_scores[best_collection]
            total_possible_score = sum(total_scores.values())
            
            # Рассчитываем уверенность
            if has_dialogue:
                # Для диалогов высокая уверенность
                confidence = 0.95
            elif total_possible_score == 0:
                confidence = 0.3  # Низкая уверенность при отсутствии совпадений
            else:
                # Уверенность = доля лучшего результата от общего
                confidence = min(0.95, max(0.4, best_score / total_possible_score))
                
                # Бонус за высокие абсолютные значения
                if best_score >= 5:
                    confidence = min(0.95, confidence + 0.1)
                elif best_score >= 3:
                    confidence = min(0.9, confidence + 0.05)
            
            return best_collection, round(confidence, 2)
        
        # По умолчанию - основы нейросталкинга с низкой уверенностью
        return "neurostalking_basics", 0.3

    # ---------------------- HELPER FUNCTIONS FOR METADATA ---------------------- #
    
    def _calculate_document_metadata(self, blocks: list, full_text: str) -> dict:
        """Рассчитывает все метаданные документа одним вызовом для оптимизации"""
        has_dialogue = self.detect_has_dialogue(blocks, full_text)
        main_topics = self._extract_main_topics(blocks)
        all_keywords = self._get_all_keywords(blocks)
        # ВРЕМЕННО: без routing_confidence из-за ошибки распаковки
        collection_result = self.determine_collection_target(main_topics, all_keywords, has_dialogue, blocks)
        if isinstance(collection_result, tuple):
            collection_target, routing_confidence = collection_result
        else:
            collection_target = collection_result
            routing_confidence = 0.7  # По умолчанию
        
        return {
            "recording_date": None,
            "lecture_type": "seminar" if has_dialogue else "lecture",
            "has_dialogue": has_dialogue,
            "main_topics": main_topics,
            "difficulty_level": self._calculate_difficulty_level(blocks),
            "collection_target": collection_target,
            "routing_confidence": routing_confidence
        }
    
    def _extract_main_topics(self, blocks: list) -> list:
        """Извлекает главные темы из всех блоков"""
        all_keywords = []
        for block in blocks:
            all_keywords.extend(block.get("keywords", []))
        
        # Подсчитываем частоту
        keyword_counts = {}
        for keyword in all_keywords:
            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1
        
        # Сортируем по частоте и берем топ-5
        sorted_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)
        return [kw[0] for kw in sorted_keywords[:5]]
    
    def _get_all_keywords(self, blocks: list) -> list:
        """Получает все ключевые слова из блоков"""
        all_keywords = []
        for block in blocks:
            all_keywords.extend(block.get("keywords", []))
        return list(set(all_keywords))  # Уникальные
    
    def _calculate_difficulty_level(self, blocks: list) -> str:
        """Рассчитывает средний уровень сложности документа"""
        complexity_scores = [block.get("complexity_score", 5.0) for block in blocks]
        avg_complexity = sum(complexity_scores) / len(complexity_scores) if complexity_scores else 5.0
        
        if avg_complexity < 4.0:
            return "beginner"
        elif avg_complexity < 7.0:
            return "intermediate"
        else:
            return "advanced"
    
    def _estimate_participant_count(self, blocks: list) -> int:
        """Примерная оценка количества участников по диалогам"""
        dialogue_blocks = [b for b in blocks if b.get("block_type") == "dialogue"]
        if not dialogue_blocks:
            return None
        
        # Примерная оценка: 1-2 участника на каждые 2-3 диалоговых блока
        return max(1, len(dialogue_blocks) // 2)
    
    def _calculate_duration_minutes(self, blocks: list) -> int:
        """Рассчитывает длительность из временных меток"""
        if not blocks:
            return None
        
        try:
            last_block = blocks[-1]
            end_time = last_block.get("end", "00:00:00")
            # Парсим время в формате HH:MM:SS
            h, m, s = map(int, end_time.split(":"))
            return h * 60 + m + (1 if s > 0 else 0)
        except:
            return None

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

        base = Path(input_path).stem
        video_id = base
        
        # Добавляем стабильные ID и метаданные для RAG + новые поля SAG v2.0
        for i, block in enumerate(all_blocks):
            # Существующие поля
            block["block_id"] = f"{video_id}_{i:03d}"
            block["video_id"] = video_id
            block["source_url"] = f"https://youtube.com/watch?v={video_id}"
            # Временная ссылка на YouTube
            if block.get("start"):
                start_seconds = self._hms_to_seconds(block["start"])
                if start_seconds is not None:
                    block["youtube_link"] = f"https://youtube.com/watch?v={video_id}&t={start_seconds}s"
            
            # НОВЫЕ поля для SAG-системы v2.0 - АВТОМАТИЧЕСКАЯ КЛАССИФИКАЦИЯ
            content = block.get("content", "")
            title = block.get("title", "")
            keywords = block.get("keywords", [])
            
            # Применяем функции классификации
            speaker = self.detect_speaker(content)
            block_type = self.detect_block_type(content)
            emotional_tone = self.detect_emotional_tone(content, title)
            conceptual_depth = self.detect_conceptual_depth(content, keywords)
            complexity_score = self.calculate_complexity_score(content, keywords, conceptual_depth)
            graph_entities = self.extract_graph_entities(content, keywords)
            
            # Заполняем все поля
            block["speaker"] = speaker
            block["block_type"] = block_type
            block["emotional_tone"] = emotional_tone
            block["conceptual_depth"] = conceptual_depth
            block["complexity_score"] = complexity_score
            block["graph_entities"] = graph_entities
            block["contains_practice"] = block_type == "practice"
            block["dialogue_turn"] = None  # Будет обновлено для диалогов
            block["question_type"] = None  # Будет обновлено для диалогов
            block["answer_completeness"] = None
            block["interaction_quality"] = None
            block["key_insights"] = min(len(keywords), 8)  # Оценка на основе ключевых слов
            block["transformation_stage"] = "beginning"    # По умолчанию
            block["transcript_edited"] = True
            
            # Специальная обработка диалоговых блоков
            if block_type == "dialogue":
                dialogue_data = self.structure_dialogue_block(content)
                if dialogue_data:
                    block["interaction_quality"] = dialogue_data.get("interaction_quality")
                    block["dialogue_turn"] = 1  # Первый ход диалога
                    # Дополнительные диалоговые метаданные можно добавить при необходимости
        
        doc = {
            "document_title": f"Лекция Сарсекенова: {base}",
            "document_summary": "Конспект лекции, структурированный по темам нейросталкинга/неосталкинга.",
            "document_metadata": {
                # Существующие поля
                "total_blocks": len(all_blocks),
                "language": "ru",
                "domain": "sarsekenov_neurostalking",
                "video_id": video_id,
                "source_url": f"https://youtube.com/watch?v={video_id}",
                "schema_version": "2.0",  # ОБНОВЛЕНО до v2.0
                
                # НОВЫЕ поля для SAG-системы - АВТОМАТИЧЕСКОЕ ЗАПОЛНЕНИЕ
                # Предварительные расчеты для оптимизации
                **self._calculate_document_metadata(all_blocks, data.get("full_text", "")),
                "transcript_confidence": 0.85,       # По умолчанию 0.85
                "participant_count": self._estimate_participant_count(all_blocks),
                "duration_minutes": self._calculate_duration_minutes(all_blocks),
                "audio_quality": "good",             # По умолчанию good
                "processing_version": "v2.1"         # Версия процессора
            },
            "blocks": all_blocks,
            "full_text": data.get("full_text", ""),
        }

        # Сформировать «короткое оглавление» и «общее резюме» на основе всех блоков
        overview = self.generate_overview(doc)
        
        # Агрегируем граф-сущности на уровне документа для SAG-системы
        all_document_entities = []
        for block in all_blocks:
            all_document_entities.extend(block.get("graph_entities", []))
        
        # Считаем частоту и берем топ-сущности
        entity_counts = {}
        for entity in all_document_entities:
            entity_counts[entity] = entity_counts.get(entity, 0) + 1
        top_document_entities = sorted(entity_counts.items(), key=lambda x: x[1], reverse=True)[:12]
        
        doc.update({
            "overview_toc": overview.get("overview_toc", ""),
            "overview_summary": overview.get("overview_summary", ""),
            "graph_entities": top_document_entities,  # Добавляем граф-сущности на уровне документа
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

    # ---------------------- SAG v2.0 OVERVIEW GENERATION ---------------------- #
    def generate_overview(self, doc: Dict[str, Any]) -> Dict[str, str]:
        """
        Генерирует улучшенный обзор для SAG-системы v2.0
        """
        return self.generate_enhanced_overview(doc)
    
    def generate_enhanced_overview(self, doc: Dict[str, Any]) -> Dict[str, str]:
        """
        Генерирует улучшенный обзор для SAG-системы v2.0
        Использует метаданные и граф-сущности для более точного анализа
        """
        blocks = doc.get("blocks", [])
        metadata = doc.get("document_metadata", {})
        
        # Собираем аналитику для overview
        main_topics = metadata.get("main_topics", [])
        has_dialogue = metadata.get("has_dialogue", False)
        collection_target = metadata.get("collection_target", "neurostalking_basics")
        difficulty_level = metadata.get("difficulty_level", "intermediate")
        
        # Анализируем граф-сущности
        all_entities = []
        for block in blocks:
            all_entities.extend(block.get("graph_entities", []))
        
        # Топ-сущности по частоте
        entity_counts = {}
        for entity in all_entities:
            entity_counts[entity] = entity_counts.get(entity, 0) + 1
        top_entities = sorted(entity_counts.items(), key=lambda x: x[1], reverse=True)[:8]
        
        # Анализируем эмоциональные тона
        tones = [block.get("emotional_tone", "neutral") for block in blocks]
        dominant_tone = max(set(tones), key=tones.count) if tones else "neutral"
        
        # Базовое оглавление
        titles = [b.get("title", "") for b in blocks if b.get("title")]
        toc_sentence_default = " • ".join(titles[:15])
        
        # Генерируем улучшенный overview с помощью LLM
        try:
            # Подготавливаем контекст для LLM
            context_data = {
                "main_topics": main_topics[:5],
                "top_entities": [entity[0] for entity in top_entities[:6]] if top_entities else [],
                "collection_target": collection_target,
                "difficulty_level": difficulty_level,
                "has_dialogue": has_dialogue,
                "dominant_tone": dominant_tone,
                "block_count": len(blocks),
                "titles": titles[:10]
            }
            
            prompt = f"""
{self.domain_context}

ЗАДАЧА: Создай улучшенный обзор лекции для SAG-системы v2.0.

КОНТЕКСТ ЛЕКЦИИ:
- Главные темы: {', '.join(main_topics[:5])}
- Ключевые концепты: {', '.join([e[0] for e in top_entities[:6]]) if top_entities else 'отсутствуют'}
- Целевая коллекция: {collection_target}
- Уровень сложности: {difficulty_level}
- Формат: {"семинар с диалогами" if has_dialogue else "лекция-монолог"}
- Эмоциональный тон: {dominant_tone}
- Количество блоков: {len(blocks)}

СОЗДАЙ:
1) **Краткое оглавление** (одно предложение с основными темами по порядку)
2) **Обзор лекции** (3-4 развернутых предложения о содержании, подходе Сарсекенова, ключевых инсайтах)

ТРЕБОВАНИЯ:
- Сохраняй терминологию нейросталкинга
- Укажи специфику подхода автора
- Отрази уровень сложности и формат
- **МИНИМУМ 200 символов** в обзоре (это критично!)
- **ИСПОЛЬЗУЙ ПРАВИЛЬНЫЕ ГРАММАТИЧЕСКИЕ ФОРМЫ для русских терминов:**
  * "исследование осознания" (не "исследование осознание")
  * "практики медитации" (не "практики медитация") 
  * "природа восприятия" (не "природа восприятие")
  * "интеграция опыта" (не "интеграция опыт")
  * "трансформация сознания" (не "трансформация сознание")
  
**КОНКРЕТНЫЕ ПРИМЕРЫ для данной лекции:**
- Если тема "исцеление" → используй "исцеления" (родительный падеж)
- Если тема "осознавание" → используй "осознавания" (родительный падеж)
- Если тема "божественность" → используй "божественности" (родительный падеж)
- Если тема "автоматизмы" → используй "автоматизмов" (родительный падеж)
- Если тема "самопознание" → используй "самопознания" (родительный падеж)
- Добавь детали о практических аспектах и инсайтах

ФОРМАТ ОТВЕТА:
ОГЛАВЛЕНИЕ: [краткое оглавление одним предложением]

ОБЗОР: [развернутый обзор лекции 3-4 предложения, минимум 200 символов]
"""
            
            resp = self._ask(self.refine_model or self.primary_model, prompt, max_tokens=400, temperature=0.2)
            
            # Парсим ответ
            lines = [l.strip() for l in resp.splitlines() if l.strip()]
            toc_line = ""
            summary_lines = []
            
            for line in lines:
                if line.upper().startswith("ОГЛАВЛЕНИЕ:"):
                    toc_line = line.split(":", 1)[-1].strip()
                elif line.upper().startswith("ОБЗОР:"):
                    summary_lines.append(line.split(":", 1)[-1].strip())
                elif summary_lines and not line.upper().startswith(("ОГЛАВЛЕНИЕ", "ОБЗОР")):
                    summary_lines.append(line)
            
            overview_summary = " ".join(summary_lines).strip()
            
            # ВАЛИДАЦИЯ: Проверяем минимальную длину overview
            if len(overview_summary) < 200:
                print(f"[WARNING] LLM overview слишком короткий ({len(overview_summary)} символов), используем fallback с морфологией")
                overview_summary = self._generate_fallback_summary(metadata, top_entities)
            
            return {
                "overview_toc": toc_line or toc_sentence_default,
                "overview_summary": overview_summary[:800],
            }
            
        except Exception as e:
            # Fallback: создаем обзор на основе метаданных
            return {
                "overview_toc": toc_sentence_default,
                "overview_summary": self._generate_fallback_summary(metadata, top_entities)
            }
    
    def _generate_fallback_summary(self, metadata: dict, top_entities: list) -> str:
        """Резервная генерация обзора на основе метаданных с морфологией"""
        main_topics = metadata.get("main_topics", [])
        collection = metadata.get("collection_target", "neurostalking_basics")
        has_dialogue = metadata.get("has_dialogue", False)
        difficulty_level = metadata.get("difficulty_level", "intermediate")
        
        # Морфологические формы для частых терминов (родительный падеж)
        morph_dict = {
            "осознание": "осознания",
            "осознавание": "осознавания",
            "интеграция": "интеграции", 
            "восприятие": "восприятия",
            "исцеление": "исцеления",
            "взаимодействие": "взаимодействия",
            "практика": "практик",
            "медитация": "медитации",
            "наблюдение": "наблюдения",
            "метанаблюдение": "метанаблюдения",
            "понимание": "понимания",
            "переживание": "переживаний",
            "трансформация": "трансформации",
            "просветление": "просветления",
            "божественность": "божественности",
            "центрирование": "центрирования",
            "внимание": "внимания",
            "присутствие": "присутствия",
            "паттерн": "паттернов",
            "паттерны": "паттернов",
            "автоматизм": "автоматизмов",
            "автоматизмы": "автоматизмов",
            "самопознание": "самопознания",
            "сознание": "сознания",
            "абсолют": "абсолюта",
            "природа": "природы",
            "опыт": "опыта",
            "мудрость": "мудрости",
            "рост": "роста"
        }
        
        # Синонимы для разнообразия
        synonyms = {
            "осознание": "осознанного присутствия",
            "интеграция": "интеграции опыта", 
            "восприятие": "природы восприятия",
            "исцеление": "глубинного исцеления",
            "взаимодействие": "живого взаимодействия"
        }
        
        summary_parts = []
        
        # Основная тема с правильной грамматикой
        if main_topics:
            topics_genitive = []
            for topic in main_topics[:3]:
                # Применяем морфологию
                genitive_form = morph_dict.get(topic.lower(), topic)
                topics_genitive.append(genitive_form)
            
            if len(topics_genitive) == 1:
                summary_parts.append(f"Лекция посвящена исследованию {topics_genitive[0]}.")
            elif len(topics_genitive) == 2:
                summary_parts.append(f"Лекция посвящена исследованию {topics_genitive[0]} и {topics_genitive[1]}.")
            else:
                summary_parts.append(f"Лекция посвящена исследованию {', '.join(topics_genitive[:-1])} и {topics_genitive[-1]}.")
        else:
            summary_parts.append("Лекция посвящена исследованию практик нейросталкинга.")
        
        # Подход автора с синонимами
        if main_topics:
            author_concepts = []
            for topic in main_topics[:2]:
                synonym = synonyms.get(topic.lower(), morph_dict.get(topic.lower(), topic))
                author_concepts.append(synonym)
            
            if author_concepts:
                summary_parts.append(f"Саламат Сарсекенов подчёркивает важность {' и '.join(author_concepts)}.")
        
        # Формат
        if has_dialogue:
            summary_parts.append("Формат: лекция с диалогами и вопросами участников.")
        else:
            summary_parts.append("Формат: лекция-монолог с практическими рекомендациями.")
        
        # Соединяем и чистим
        text = " ".join(summary_parts)
        
        # Убираем двойные пробелы и лишние запятые
        import re
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r',\s*,', ',', text)
        
        # ВАЛИДАЦИЯ: Если текст слишком короткий, добавляем детали
        if len(text.strip()) < 200:
            # Добавляем дополнительные детали для достижения минимума
            additional_details = []
            
            if has_dialogue:
                additional_details.append("Особое внимание уделяется интерактивному формату с вопросами и ответами.")
            
            if difficulty_level == "advanced":
                additional_details.append("Материал рассчитан на продвинутый уровень практикующих.")
            elif difficulty_level == "beginner":
                additional_details.append("Лекция подходит для начинающих практиков нейросталкинга.")
            
            if main_topics and len(main_topics) > 2:
                additional_details.append(f"Дополнительно рассматриваются аспекты {' и '.join(main_topics[2:4])}.")
            
            # ОБЯЗАТЕЛЬНЫЕ дополнения для достижения минимума
            if collection != "neurostalking_basics":
                additional_details.append(f"Лекция относится к коллекции '{collection}' и содержит специализированные практики.")
            
            # Добавляем детали о ключевых концептах
            if top_entities and len(top_entities) > 0:
                top_concepts = [e[0] for e in top_entities[:3]]
                additional_details.append(f"Ключевые концепты включают: {', '.join(top_concepts)}.")
            
            # Добавляем информацию о формате
            if has_dialogue:
                additional_details.append("Интерактивный формат позволяет участникам задавать вопросы и получать практические ответы.")
            else:
                additional_details.append("Монологический формат обеспечивает глубокое погружение в тему.")
            
            if additional_details:
                text += " " + " ".join(additional_details)
        
        return text.strip()

    # ---------------------- SAG v2.0 VALIDATION ---------------------- #
    
    def validate_enhanced_json(self, result: dict) -> list:
        """
        Проверяет корректность сгенерированного JSON для SAG v2.0
        """
        errors = []
        
        # Проверяем обязательные поля документа
        required_doc_fields = [
            "document_title", "document_summary", "overview_summary",
            "document_metadata", "blocks"
        ]
        
        for field in required_doc_fields:
            if not result.get(field):
                errors.append(f"Отсутствует обязательное поле документа: {field}")
        
        # Проверяем метаданные документа SAG v2.0
        metadata = result.get("document_metadata", {})
        required_metadata = [
            "schema_version", "collection_target", "main_topics", "has_dialogue", 
            "difficulty_level", "processing_version"
        ]
        
        for field in required_metadata:
            if field not in metadata:
                errors.append(f"Отсутствует критическое метаданное SAG: {field}")
        
        # Проверяем версию схемы
        if metadata.get("schema_version") != "2.0":
            errors.append(f"Неверная версия схемы: {metadata.get('schema_version')}, ожидается 2.0")
        
        # Проверяем блоки
        blocks = result.get("blocks", [])
        if not blocks:
            errors.append("Отсутствуют блоки в документе")
        
        for i, block in enumerate(blocks):
            # Проверяем новые поля SAG v2.0
            required_block_fields = [
                "speaker", "block_type", "emotional_tone", "conceptual_depth", 
                "complexity_score", "graph_entities", "contains_practice"
            ]
            
            for field in required_block_fields:
                if field not in block:
                    errors.append(f"Блок {i}: отсутствует поле SAG v2.0: {field}")
            
            # Проверяем типы данных
            if "complexity_score" in block:
                try:
                    score = float(block["complexity_score"])
                    if not 1.0 <= score <= 10.0:
                        errors.append(f"Блок {i}: complexity_score вне диапазона 1-10: {score}")
                except (ValueError, TypeError):
                    errors.append(f"Блок {i}: complexity_score не является числом")
            
            # Проверяем граф-сущности
            if "graph_entities" in block:
                entities = block["graph_entities"]
                if not isinstance(entities, list):
                    errors.append(f"Блок {i}: graph_entities должен быть списком")
                elif len(entities) > 15:
                    errors.append(f"Блок {i}: слишком много граф-сущностей: {len(entities)}")
        
        return errors

    def generate_quality_report(self, result: dict) -> dict:
        """
        Генерирует отчет о качестве обработки SAG v2.0
        """
        blocks = result.get("blocks", [])
        metadata = result.get("document_metadata", {})
        
        # Базовая статистика
        report = {
            "schema_version": metadata.get("schema_version"),
            "processing_version": metadata.get("processing_version"),
            "total_blocks": len(blocks),
            "collection_target": metadata.get("collection_target"),
            "has_dialogue": metadata.get("has_dialogue", False),
            "difficulty_level": metadata.get("difficulty_level"),
        }
        
        if blocks:
            # Анализ блоков
            speakers = [b.get("speaker") for b in blocks]
            block_types = [b.get("block_type") for b in blocks]
            tones = [b.get("emotional_tone") for b in blocks]
            
            report.update({
                # Распределение спикеров
                "sarsekenov_blocks": speakers.count("sarsekenov"),
                "participant_blocks": speakers.count("participant"),
                "unknown_blocks": speakers.count("unknown"),
                "mixed_blocks": speakers.count("mixed"),
                
                # Распределение типов блоков
                "dialogue_blocks": block_types.count("dialogue"),
                "practice_blocks": block_types.count("practice"),
                "monologue_blocks": block_types.count("monologue"),
                "question_blocks": block_types.count("question"),
                
                # Эмоциональная аналитика
                "contemplative_blocks": tones.count("contemplative"),
                "explanatory_blocks": tones.count("explanatory"),
                "intense_blocks": tones.count("intense"),
                "neutral_blocks": tones.count("neutral"),
                
                # Сложность
                "average_complexity": round(sum(b.get("complexity_score", 0) for b in blocks) / len(blocks), 1),
                "high_complexity_blocks": len([b for b in blocks if b.get("conceptual_depth") == "high"]),
                
                # Граф-аналитика
                "total_unique_entities": len(set().union(*[b.get("graph_entities", []) for b in blocks])),
                "blocks_with_entities": len([b for b in blocks if b.get("graph_entities")]),
                
                # Качество overview
                "overview_summary_length": len(result.get("overview_summary", "")),
                "overview_toc_length": len(result.get("overview_toc", "")),
            })
        
        # Оценка готовности для SAG
        sag_readiness = self._calculate_sag_readiness(result, report)
        report["sag_readiness_score"] = sag_readiness
        
        return report

    def _calculate_sag_readiness(self, result: dict, report: dict) -> float:
        """Рассчитывает готовность для SAG-системы (0-100%)"""
        score = 0.0
        
        # Базовые требования (40 баллов)
        if result.get("document_metadata", {}).get("schema_version") == "2.0":
            score += 10
        if result.get("document_metadata", {}).get("collection_target"):
            score += 10
        if result.get("overview_summary"):
            score += 10
        if result.get("blocks"):
            score += 10
        
        # Качество блоков (30 баллов)
        blocks = result.get("blocks", [])
        if blocks:
            # Наличие граф-сущностей
            entities_coverage = report.get("blocks_with_entities", 0) / len(blocks)
            score += entities_coverage * 10
            
            # Разнообразие типов блоков
            types_count = len(set(b.get("block_type") for b in blocks))
            score += min(types_count * 5, 10)
            
            # Классификация спикеров
            classified_speakers = len([b for b in blocks if b.get("speaker") != "unknown"])
            speaker_coverage = classified_speakers / len(blocks)
            score += speaker_coverage * 10
        
        # Метаданные (20 баллов)
        metadata = result.get("document_metadata", {})
        if metadata.get("main_topics"):
            score += 10
        if metadata.get("difficulty_level") != "intermediate":  # Не по умолчанию
            score += 5
        if metadata.get("has_dialogue") and report.get("dialogue_blocks", 0) > 0:
            score += 5
        
        # Дополнительные баллы (10 баллов)
        if report.get("total_unique_entities", 0) > 20:
            score += 5
        if report.get("overview_summary_length", 0) > 100:
            score += 5
        
        return min(100.0, round(score, 1))


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


