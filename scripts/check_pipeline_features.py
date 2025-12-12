#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для проверки реализованных компонентов в pipeline.
Анализирует выходной JSON файл и показывает статус всех фич.
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, Any, List

# Установка UTF-8 для Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


class FeatureChecker:
    """Проверяет наличие и качество реализованных фич."""

    def __init__(self, json_path: Path):
        self.json_path = json_path
        self.data = None
        self.results = {}
    
    def load_data(self) -> bool:
        """Загружает JSON файл."""
        try:
            with open(self.json_path, encoding='utf-8') as f:
                self.data = json.load(f)
            return True
        except Exception as e:
            print(f"❌ Ошибка загрузки файла: {e}")
            return False
    
    def check_practices(self) -> Dict[str, Any]:
        """Проверяет экстрактор практик."""
        result = {
            'implemented': False,
            'count': 0,
            'details': {},
            'issues': []
        }
        
        # Проверяем наличие practices в блоках или на верхнем уровне
        blocks = self.data.get('blocks', [])
        practices_found = []
        
        for block in blocks:
            if 'practices' in block and block['practices']:
                practices_found.extend(block['practices'] if isinstance(block['practices'], list) else [block['practices']])
        
        # Также проверяем верхний уровень
        if 'practices' in self.data:
            top_level_practices = self.data['practices']
            if isinstance(top_level_practices, list):
                practices_found.extend(top_level_practices)
            else:
                practices_found.append(top_level_practices)
        
        if not practices_found:
            result['issues'].append('Ключ "practices" отсутствует или пуст')
            return result
        
        result['implemented'] = True
        result['count'] = len(practices_found)
        
        # Проверка первой практики
        first = practices_found[0] if practices_found else {}
        result['details'] = {
            'title': str(first.get('title', first.get('name', 'Отсутствует')))[:60],
            'steps_count': len(first.get('steps', [])),
            'has_goal': bool(first.get('goal')),
            'difficulty': first.get('difficulty', 'Не указано'),
            'has_contraindications': len(first.get('contraindications', [])) > 0
        }
        
        # Проверка структуры
        required_fields = ['title', 'steps']
        missing = [f for f in required_fields if f not in first and f not in first.get('name', '')]
        if missing:
            result['issues'].append(f'Отсутствуют поля: {missing}')
        
        if len(first.get('steps', [])) < 2:
            result['issues'].append('Недостаточно шагов в практике (< 2)')
        
        return result
    
    def check_global_safety(self) -> Dict[str, Any]:
        """Проверяет модуль безопасности."""
        result = {
            'implemented': False,
            'details': {},
            'issues': []
        }
        
        # Проверяем наличие safety в блоках
        blocks = self.data.get('blocks', [])
        all_safety_data = []
        
        # Собираем все данные safety из всех блоков
        for block in blocks:
            if 'safety' in block:
                all_safety_data.append(block['safety'])
        
        # Также проверяем верхний уровень
        if 'global_safety' in self.data:
            all_safety_data.append(self.data['global_safety'])
        elif 'safety' in self.data:
            all_safety_data.append(self.data['safety'])
        
        if not all_safety_data:
            result['issues'].append('Ключ "safety" или "global_safety" отсутствует')
            return result
        
        result['implemented'] = True
        
        # Агрегируем данные из всех блоков
        total_contraindications = 0
        total_limitations = 0
        total_when_to_stop = 0
        total_when_to_seek_help = 0
        total_red_flags = 0
        total_notes = 0
        blocks_with_data = 0
        
        for safety_data in all_safety_data:
            if isinstance(safety_data, dict):
                total_contraindications += len(safety_data.get('contraindications', []))
                total_limitations += len(safety_data.get('limitations', []))
                total_when_to_stop += len(safety_data.get('when_to_stop', []))
                total_when_to_seek_help += len(safety_data.get('when_to_seek_professional_help', []))
                total_red_flags += len(safety_data.get('red_flags', []))
                total_notes += len(safety_data.get('notes', []))
                
                # Проверяем, есть ли хотя бы какие-то данные
                if any([
                    len(safety_data.get('contraindications', [])),
                    len(safety_data.get('limitations', [])),
                    len(safety_data.get('when_to_stop', [])),
                    len(safety_data.get('when_to_seek_professional_help', [])),
                    len(safety_data.get('red_flags', [])),
                    len(safety_data.get('notes', []))
                ]):
                    blocks_with_data += 1
        
        # Подсчет элементов
        result['details'] = {
            'contraindications': total_contraindications,
            'limitations': total_limitations,
            'when_to_stop': total_when_to_stop,
            'when_to_seek_help': total_when_to_seek_help,
            'red_flags': total_red_flags,
            'notes': total_notes,
            'blocks_with_safety': len(all_safety_data),
            'blocks_with_data': blocks_with_data
        }
        
        # Критические проверки
        if blocks_with_data == 0:
            result['issues'].append('Структура safety есть, но все поля пустые во всех блоках')
            result['issues'].append('Возможно, экстрактор Safety не вызывается или не находит данных')
        
        if total_when_to_seek_help < 3 and blocks_with_data > 0:
            result['issues'].append(
                f'Недостаточно рекомендаций обращения за помощью: '
                f'{total_when_to_seek_help} (нужно минимум 3)'
            )
        
        if total_notes == 0 and blocks_with_data > 0:
            result['issues'].append('Отсутствуют общие заметки о безопасности')
        
        return result
    
    def check_concept_hierarchy(self) -> Dict[str, Any]:
        """Проверяет иерархию концептов."""
        result = {
            'implemented': False,
            'details': {},
            'issues': []
        }
        
        # Проверяем наличие concept_hierarchy в блоках
        blocks = self.data.get('blocks', [])
        all_hierarchies = []
        
        # Собираем все concept_hierarchy из всех блоков
        for block in blocks:
            if 'concept_hierarchy' in block:
                hierarchy_data = block['concept_hierarchy']
                if isinstance(hierarchy_data, list) and hierarchy_data:
                    all_hierarchies.extend(hierarchy_data)
                elif isinstance(hierarchy_data, dict):
                    all_hierarchies.append(hierarchy_data)
        
        # Также проверяем верхний уровень
        if 'concept_hierarchy' in self.data:
            top_level = self.data['concept_hierarchy']
            if isinstance(top_level, list):
                all_hierarchies.extend(top_level)
            elif isinstance(top_level, dict):
                all_hierarchies.append(top_level)
        
        if not all_hierarchies:
            result['issues'].append('Ключ "concept_hierarchy" отсутствует или все массивы пустые')
            result['issues'].append('Возможно, экстрактор ConceptHierarchy не вызывается или не находит данных')
            return result
        
        result['implemented'] = True
        
        # Подсчет элементов
        total_concepts = len(all_hierarchies)
        fundamental_count = 0
        advanced_count = 0
        fundamental_concepts = []
        
        for hierarchy in all_hierarchies:
            if isinstance(hierarchy, dict):
                level = hierarchy.get('level', '').lower()
                if 'fundamental' in level or level == 'root' or level == 'domain':
                    fundamental_count += 1
                    if hierarchy.get('name'):
                        fundamental_concepts.append(hierarchy.get('name'))
                elif 'advanced' in level or level == 'practice' or level == 'technique':
                    advanced_count += 1
        
        result['details'] = {
            'total_concepts': total_concepts,
            'fundamental_count': fundamental_count,
            'advanced_count': advanced_count,
            'fundamental_concepts': fundamental_concepts[:5],
            'blocks_with_hierarchy': len([b for b in blocks if 'concept_hierarchy' in b and b['concept_hierarchy']])
        }
        
        # Проверки
        if total_concepts == 0:
            result['issues'].append('Структура concept_hierarchy есть, но все массивы пустые')
            result['issues'].append('Возможно, экстрактор ConceptHierarchy не находит данных для извлечения')
        
        if fundamental_count == 0 and total_concepts > 0:
            result['issues'].append('Нет базовых концептов (fundamental/root/domain)')
        
        return result
    
    def check_knowledge_graph(self) -> Dict[str, Any]:
        """Проверяет граф знаний и веса связей."""
        result = {
            'implemented': False,
            'details': {},
            'issues': []
        }
        
        if 'knowledge_graph' not in self.data:
            result['issues'].append('Ключ "knowledge_graph" отсутствует')
            return result
        
        kg = self.data['knowledge_graph']
        result['implemented'] = True
        
        nodes = kg.get('nodes', [])
        edges = kg.get('edges', [])
        
        result['details']['nodes_count'] = len(nodes)
        result['details']['edges_count'] = len(edges)
        
        # Проверка весов
        if edges:
            weights = [e.get('confidence', 0) for e in edges if 'confidence' in e]
            
            if not weights:
                result['issues'].append('Рёбра не содержат поле "confidence"')
            else:
                result['details']['weights'] = {
                    'min': round(min(weights), 3),
                    'max': round(max(weights), 3),
                    'avg': round(sum(weights) / len(weights), 3),
                    'unique_count': len(set(weights))
                }
                
                # Проверка на разнообразие весов
                if len(set(weights)) == 1:
                    result['issues'].append(
                        f'Все веса одинаковые: {weights[0]} (нужно разнообразие!)'
                    )
                elif result['details']['weights']['unique_count'] < 3:
                    result['issues'].append(
                        f'Мало уникальных весов: {result["details"]["weights"]["unique_count"]}'
                    )
        
        # Проверка метаданных
        if 'metadata' in kg:
            if 'weight_statistics' in kg['metadata']:
                result['details']['has_weight_stats'] = True
                stats = kg['metadata']['weight_statistics']
                result['details']['weight_stats'] = {
                    'min': stats.get('min_weight'),
                    'max': stats.get('max_weight'),
                    'avg': stats.get('avg_weight')
                }
            else:
                result['issues'].append('Отсутствует weight_statistics в метаданных')
        
        return result
    
    def print_results(self):
        """Выводит результаты проверки."""
        print('=' * 80)
        print('📦 ПРОВЕРКА РЕАЛИЗОВАННЫХ КОМПОНЕНТОВ')
        print('=' * 80)
        print(f'Файл: {self.json_path.name}')
        print(f'Полный путь: {self.json_path}')
        print()
        
        # 1. Practices
        print('1️⃣  PRACTICES (Экстрактор практик)')
        print('-' * 80)
        practices = self.results['practices']
        
        if practices['implemented']:
            print(f'✅ РЕАЛИЗОВАНО')
            print(f'   Извлечено практик: {practices["count"]}')
            if practices['details']:
                print(f'   Первая практика:')
                print(f'     - Название: {practices["details"]["title"]}...')
                print(f'     - Шагов: {practices["details"]["steps_count"]}')
                print(f'     - Сложность: {practices["details"]["difficulty"]}')
                print(f'     - Есть цель: {"✅" if practices["details"]["has_goal"] else "❌"}')
                print(f'     - Есть противопоказания: {"✅" if practices["details"]["has_contraindications"] else "❌"}')
        else:
            print(f'❌ НЕ РЕАЛИЗОВАНО')
        
        if practices['issues']:
            print(f'   ⚠️  Проблемы:')
            for issue in practices['issues']:
                print(f'     - {issue}')
        print()
        
        # 2. Global Safety
        print('2️⃣  GLOBAL SAFETY (Модуль безопасности)')
        print('-' * 80)
        safety = self.results['global_safety']
        
        if safety['implemented']:
            print(f'✅ РЕАЛИЗОВАНО')
            print(f'   Противопоказания: {safety["details"]["contraindications"]}')
            print(f'   Ограничения: {safety["details"]["limitations"]}')
            print(f'   Когда остановиться: {safety["details"]["when_to_stop"]}')
            print(f'   Когда за помощью: {safety["details"]["when_to_seek_help"]}')
            print(f'   Красные флаги: {safety["details"]["red_flags"]}')
            print(f'   Общие заметки: {safety["details"]["notes"]}')
        else:
            print(f'❌ НЕ РЕАЛИЗОВАНО')
        
        if safety['issues']:
            print(f'   ⚠️  Проблемы:')
            for issue in safety['issues']:
                print(f'     - {issue}')
        print()
        
        # 3. Concept Hierarchy
        print('3️⃣  CONCEPT HIERARCHY (Иерархия концептов)')
        print('-' * 80)
        hierarchy = self.results['concept_hierarchy']
        
        if hierarchy['implemented']:
            print(f'✅ РЕАЛИЗОВАНО')
            print(f'   Fundamental концептов: {hierarchy["details"]["fundamental_count"]}')
            print(f'   Advanced концептов: {hierarchy["details"]["advanced_count"]}')
            print(f'   Уровней обучения: {hierarchy["details"]["learning_levels"]}')
            print(f'   Prerequisites карта: {"✅" if hierarchy["details"]["has_prerequisites"] else "❌"}')
            if hierarchy["details"]["fundamental_concepts"]:
                print(f'   Базовые концепты: {hierarchy["details"]["fundamental_concepts"]}')
        else:
            print(f'❌ НЕ РЕАЛИЗОВАНО')
        
        if hierarchy['issues']:
            print(f'   ⚠️  Проблемы:')
            for issue in hierarchy['issues']:
                print(f'     - {issue}')
        print()
        
        # 4. Knowledge Graph
        print('4️⃣  KNOWLEDGE GRAPH (Граф знаний с весами)')
        print('-' * 80)
        kg = self.results['knowledge_graph']
        
        if kg['implemented']:
            print(f'✅ РЕАЛИЗОВАНО')
            print(f'   Узлов (концептов): {kg["details"]["nodes_count"]}')
            print(f'   Рёбер (связей): {kg["details"]["edges_count"]}')
            
            if 'weights' in kg['details']:
                print(f'   Веса связей:')
                print(f'     - Минимум: {kg["details"]["weights"]["min"]}')
                print(f'     - Максимум: {kg["details"]["weights"]["max"]}')
                print(f'     - Средний: {kg["details"]["weights"]["avg"]}')
                print(f'     - Уникальных: {kg["details"]["weights"]["unique_count"]}')
                
                if kg["details"]["weights"]["unique_count"] > 3:
                    print(f'     ✅ Веса хорошо варьируются!')
            
            if 'has_weight_stats' in kg['details']:
                print(f'   Weight Statistics: ✅ Присутствует в метаданных')
                if 'weight_stats' in kg['details']:
                    stats = kg['details']['weight_stats']
                    print(f'     - Min: {stats.get("min")}')
                    print(f'     - Max: {stats.get("max")}')
                    print(f'     - Avg: {stats.get("avg")}')
        else:
            print(f'❌ НЕ РЕАЛИЗОВАНО')
        
        if kg['issues']:
            print(f'   ⚠️  Проблемы:')
            for issue in kg['issues']:
                print(f'     - {issue}')
        print()
        
        # Итоговая рекомендация
        print('=' * 80)
        print('🎯 ИТОГОВАЯ ОЦЕНКА')
        print('=' * 80)
        
        implemented_count = sum([
            self.results['practices']['implemented'],
            self.results['global_safety']['implemented'],
            self.results['concept_hierarchy']['implemented'],
            self.results['knowledge_graph']['implemented']
        ])
        
        total_issues = sum([
            len(self.results['practices']['issues']),
            len(self.results['global_safety']['issues']),
            len(self.results['concept_hierarchy']['issues']),
            len(self.results['knowledge_graph']['issues'])
        ])
        
        print(f'Реализовано компонентов: {implemented_count}/4')
        print(f'Всего проблем: {total_issues}')
        print()
        
        if implemented_count == 4 and total_issues == 0:
            print('✅ ВСЕ КОМПОНЕНТЫ РЕАЛИЗОВАНЫ КОРРЕКТНО!')
            print('   Можно переходить к тестированию и масштабированию на 500 видео.')
        elif implemented_count == 4:
            print('⚠️  Все компоненты реализованы, но есть проблемы с качеством.')
            print('   Рекомендуется исправить выявленные проблемы.')
        else:
            print(f'❌ Не хватает {4 - implemented_count} компонента(ов)')
            print('   Необходимо реализовать недостающие фичи:')
            
            if not self.results['practices']['implemented']:
                print('   - Фаза 2: Экстрактор практик')
            if not self.results['global_safety']['implemented']:
                print('   - Фаза 3: Модуль Safety')
            if not self.results['concept_hierarchy']['implemented']:
                print('   - Фаза 4: Иерархия концептов')
            if not self.results['knowledge_graph']['implemented']:
                print('   - Фаза 1: Улучшение графа знаний')
        
        print('=' * 80)
    
    def run(self):
        """Запускает полную проверку."""
        if not self.load_data():
            return False
        
        self.results['practices'] = self.check_practices()
        self.results['global_safety'] = self.check_global_safety()
        self.results['concept_hierarchy'] = self.check_concept_hierarchy()
        self.results['knowledge_graph'] = self.check_knowledge_graph()
        
        self.print_results()
        
        return True


def find_latest_json() -> Path:
    """Находит последний обработанный JSON файл."""
    base_dir = Path('data/sag_final')
    
    if not base_dir.exists():
        raise FileNotFoundError(f"Директория {base_dir} не найдена")
    
    # Найти все .for_vector.json файлы
    json_files = list(base_dir.rglob('*.for_vector.json'))
    
    if not json_files:
        raise FileNotFoundError("Не найдено ни одного .for_vector.json файла")
    
    # Отсортировать по времени модификации
    json_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    
    return json_files[0]


def main():
    """Главная функция."""
    try:
        # Если передан путь к файлу, использовать его
        if len(sys.argv) > 1:
            json_path = Path(sys.argv[1])
            if not json_path.exists():
                print(f"❌ Файл не найден: {json_path}")
                return 1
        else:
            # Иначе найти последний файл
            json_path = find_latest_json()
            print(f"📁 Найден последний файл: {json_path}")
            print()
        
        # Запустить проверку
        checker = FeatureChecker(json_path)
        checker.run()
        
        return 0
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

