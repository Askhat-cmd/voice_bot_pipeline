# 🛡️ РУКОВОДСТВО ПО БЕЗОПАСНОЙ РАЗРАБОТКЕ SAG v2.0

## ⚠️ КРИТИЧНЫЕ ПРИНЦИПЫ

### 1. **Защищенная распаковка кортежей**
```python
# ❌ ОПАСНО - может вызвать "too many values to unpack"
result1, result2 = some_function()

# ✅ БЕЗОПАСНО - с проверкой типа
result = some_function()
if isinstance(result, tuple) and len(result) == 2:
    result1, result2 = result
else:
    result1, result2 = result, None  # или другие значения по умолчанию
```

### 2. **Защита от пустых списков**
```python
# ❌ ОПАСНО - может вызвать IndexError
top_item = my_list[0]
items_text = ', '.join([item[0] for item in my_list])

# ✅ БЕЗОПАСНО - с проверкой
top_item = my_list[0] if my_list else None
items_text = ', '.join([item[0] for item in my_list]) if my_list else 'отсутствуют'
```

### 3. **Обработка исключений с детализацией**
```python
# ❌ ПЛОХО - скрывает реальную ошибку
try:
    result = complex_function()
except Exception as e:
    return None  # Потеряли информацию об ошибке

# ✅ ХОРОШО - сохраняет контекст
try:
    result = complex_function()
except IndexError as e:
    print(f"[ERROR] IndexError in complex_function: {e}")
    return None
except ValueError as e:
    print(f"[ERROR] ValueError in complex_function: {e}")
    return None
```

### 4. **Валидация входных данных**
```python
def process_data(data: dict) -> dict:
    # ✅ Всегда проверяем обязательные поля
    if not data.get("blocks"):
        raise ValueError("Блоки не найдены в данных")
    
    if not isinstance(data["blocks"], list):
        raise ValueError("Блоки должны быть списком")
    
    return {"status": "processed"}
```

## 🔧 ИНСТРУМЕНТЫ ДЛЯ ОТЛАДКИ

### 1. **Логирование вместо print**
```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Используйте logger.debug() для отладочной информации
logger.debug(f"Processing {len(blocks)} blocks")
logger.error(f"Failed to process: {error}")
```

### 2. **Пошаговая отладка**
```python
def debug_function(data):
    print(f"[DEBUG] Input type: {type(data)}")
    print(f"[DEBUG] Input content: {data}")
    
    result = process(data)
    
    print(f"[DEBUG] Result type: {type(result)}")
    print(f"[DEBUG] Result: {result}")
    return result
```

### 3. **Тестирование граничных случаев**
- Пустые списки: `[]`
- Пустые строки: `""`
- None значения: `None`
- Неожиданные типы данных

## 📋 ЧЕКЛИСТ ПЕРЕД ВНЕСЕНИЕМ ИЗМЕНЕНИЙ

- [ ] Проверил все места распаковки кортежей
- [ ] Добавил защиту от пустых списков/словарей
- [ ] Протестировал на граничных случаях
- [ ] Добавил информативные сообщения об ошибках
- [ ] Проверил совместимость с существующим кодом
- [ ] Запустил тест на реальных данных

## 🚨 КРАСНЫЕ ФЛАГИ

Если видите эти паттерны - будьте осторожны:

1. `result1, result2 = function()` без проверки
2. `list[0]` без проверки на пустоту
3. `dict["key"]` вместо `dict.get("key")`
4. Общий `except Exception:` без детализации
5. Изменение функций, которые возвращают кортежи
