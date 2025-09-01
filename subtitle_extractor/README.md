# YouTube Subtitles Extractor

Модуль для получения субтитров напрямую с YouTube используя `youtube-transcript-api`.

## Особенности

- ✅ Получает субтитры напрямую с YouTube (без загрузки аудио)
- ✅ Поддержка множества языков
- ✅ Автоматический перевод субтитров
- ✅ Сохранение в форматах JSON, TXT, SRT
- ✅ Пакетная обработка URL
- ✅ Высокое качество текста (лучше чем транскрибация)

## Установка

```bash
pip install -r requirements.txt
```

## Использование

### Один URL

```bash
python get_subtitles.py --url "https://www.youtube.com/watch?v=VIDEO_ID"
```

### Пакетная обработка

```bash
python get_subtitles.py --file "urls.txt"
```

### Показать доступные языки

```bash
python get_subtitles.py --url "https://www.youtube.com/watch?v=VIDEO_ID" --list-languages
```

### Настройка языка

```bash
# Основной язык русский, резервный английский
python get_subtitles.py --url "URL" --language ru --fallback en

# Только английский
python get_subtitles.py --url "URL" --language en
```

## Параметры

- `--url` - URL видео YouTube
- `--file` - Файл со списком URL (по одному на строку)
- `--output` - Папка для сохранения (по умолчанию: `data/subtitles`)
- `--language` - Предпочитаемый язык (по умолчанию: `ru`)
- `--fallback` - Резервный язык (по умолчанию: `en`)
- `--list-languages` - Показать доступные языки

## Форматы выходных файлов

### JSON
```json
{
  "metadata": {
    "video_id": "VIDEO_ID",
    "extraction_date": "2025-08-28",
    "subtitle_count": 150,
    "video_info": {}
  },
  "subtitles": [
    {
      "text": "Текст субтитров",
      "start": 0.0,
      "duration": 2.5
    }
  ]
}
```

### TXT
```
Текст субтитров без временных меток
```

### SRT
```
1
00:00:00,000 --> 00:00:02,500
Текст субтитров
```

## Примеры

### Файл со списком URL (urls.txt)
```
https://www.youtube.com/watch?v=VIDEO_ID_1
https://www.youtube.com/watch?v=VIDEO_ID_2
https://youtu.be/VIDEO_ID_3
```

### Получение субтитров на разных языках
```bash
# Русские субтитры
python get_subtitles.py --url "URL" --language ru

# Английские субтитры с переводом на русский
python get_subtitles.py --url "URL" --language ru --fallback en

# Только английские субтитры
python get_subtitles.py --url "URL" --language en
```

## Преимущества перед транскрибацией

1. **Качество**: Субтитры создаются людьми или профессиональными системами
2. **Скорость**: Мгновенное получение без обработки аудио
3. **Точность**: Временные метки точно соответствуют видео
4. **Многоязычность**: Поддержка переводов
5. **Размер**: Файлы намного меньше чем аудио

## Ограничения

- Работает только с видео, у которых есть субтитры
- Зависит от доступности YouTube API
- Некоторые видео могут не иметь субтитров на нужном языке
