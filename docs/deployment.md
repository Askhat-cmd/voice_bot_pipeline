# 🚀 Развертывание на GitHub

## Навигация

- [Назад к README](../README.md)
- [Быстрый старт](./getting-started.md)
- [Мониторинг и отладка](./monitoring-debugging.md)

---

## Подготовка к первому пушу

### 1. Создание репозитория

```bash
# Создайте новый репозиторий на GitHub
# НЕ инициализируйте с README, .gitignore или лицензией
```

### 2. Инициализация Git в проекте

```powershell
# В корне проекта voice_bot_pipeline
git init
git add .
git commit -m "Initial commit: Voice Bot Pipeline for YouTube to Vector DB"
```

### 3. Настройка удаленного репозитория

```powershell
# Замените YOUR_USERNAME и YOUR_REPO на ваши данные
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git branch -M main
```

---

## ⚠️ КРИТИЧЕСКИ ВАЖНО: Защита секретов

### Проблема: GitHub Push Protection блокирует пуши с секретами

```bash
# ❌ ОШИБКА: Push cannot contain secrets
# GitHub автоматически обнаруживает API ключи и блокирует пуш
```

### Решение: Правильная настройка .gitignore и .env

```powershell
# 1. Убедитесь, что .env НЕ отслеживается Git
git status  # .env должен быть в "Untracked files"

# 2. Если .env уже в Git - удалите его из истории
git rm --cached .env
git commit -m "Remove .env from tracking"

# 3. Проверьте .gitignore содержит:
# .env
# .venv/
# __pycache__/
# *.log
# data/
```

### Создание .env.example (без секретов)

```bash
# Создайте .env.example с примером структуры
OPENAI_API_KEY=your_openai_api_key_here
REFINE_MODEL=gpt-5-mini
PRIMARY_MODEL=gpt-4o-mini
```

---

## 🔐 Аутентификация GitHub

### Вариант A: Personal Access Token (рекомендуется)

```powershell
# 1. Создайте PAT на GitHub: Settings → Developer settings → Personal access tokens
# 2. Выберите scopes: repo, workflow
# 3. Скопируйте токен

# 4. Настройте Git для использования токена
git config --global credential.helper store
# При следующем push введите username и токен как пароль
```

### Вариант B: SSH ключи

```powershell
# 1. Генерация SSH ключа
ssh-keygen -t ed25519 -C "your_email@example.com"

# 2. Добавление в GitHub: Settings → SSH and GPG keys
# 3. Изменение remote URL
git remote set-url origin git@github.com:YOUR_USERNAME/YOUR_REPO.git
```

---

## 📤 Первый пуш проекта

### Безопасный пуш

```powershell
# 1. Проверка статуса
git status

# 2. Добавление файлов (исключая секреты)
git add .

# 3. Проверка что .env НЕ добавлен
git status  # .env должен отсутствовать

# 4. Коммит
git commit -m "Initial commit: Complete Voice Bot Pipeline with SAG v2.0

- YouTube subtitle extraction
- Text processing with LLM
- 🆕 SAG v2.0: Structured Augmented Generation
- 🆕 Automatic block classification and graph entities
- 🆕 Morphological processing for Russian language
- 🆕 Smart routing with confidence metrics
- 🆕 ETAP 5: Fine-tuning completed (90% readiness)
- Vector-ready JSON output
- Domain-specific processors
- Pipeline orchestration"

# 5. Пуш (GitHub запросит аутентификацию)
git push -u origin main
```

---

## 🔄 Последующие обновления

### Ежедневная работа

```powershell
# 1. Проверка изменений
git status
git diff

# 2. Добавление и коммит
git add .
git commit -m "Update: [краткое описание изменений]"

# 3. Пуш
git push origin main
```

### Работа с ветками

```powershell
# Создание feature ветки
git checkout -b feature/improve-text-processing

# Работа над изменениями...
git add .
git commit -m "Feature: Enhanced text cleaning and polishing"

# Слияние с main
git checkout main
git merge feature/improve-text-processing
git push origin main

# Удаление feature ветки
git branch -d feature/improve-text-processing
```

---

## 🚨 Решение проблем с пушем

### Ошибка: "Push cannot contain secrets"

```powershell
# 1. Немедленно отмените последний коммит
git reset --soft HEAD~1

# 2. Удалите .env из Git
git rm --cached .env
git commit -m "Remove .env file"

# 3. Проверьте .gitignore
# 4. Повторите коммит и пуш
```

### Ошибка: "Authentication failed"

```powershell
# 1. Проверьте токен/SSH ключ
# 2. Обновите credentials
git config --global credential.helper store

# 3. Или используйте SSH
git remote set-url origin git@github.com:YOUR_USERNAME/YOUR_REPO.git
```

### Ошибка: "Large file detected"

```powershell
# 1. Проверьте размеры файлов
git status

# 2. Добавьте большие файлы в .gitignore
# 3. Удалите из Git если уже добавлены
git rm --cached large_file.mp4
```

---

## 📋 Чек-лист перед пушем

- [ ] `.env` файл НЕ отслеживается Git
- [ ] `.gitignore` настроен правильно
- [ ] Нет API ключей в коде
- [ ] Нет больших медиафайлов
- [ ] Все зависимости в `requirements.txt`
- [ ] README.md актуален
- [ ] Логи очищены от секретов

---

## 🌟 Лучшие практики

1. **Никогда не коммитьте `.env` файлы**
2. **Используйте `.env.example` для документации**
3. **Регулярно делайте коммиты с понятными сообщениями**
4. **Проверяйте статус перед каждым коммитом**
5. **Используйте feature ветки для крупных изменений**
6. **Держите main ветку стабильной**

### 🆕 SAG v2.0 Лучшие практики

7. **Используйте современные модели**: `gpt-4o-mini` + `gpt-5-mini`
8. **Проверяйте SAG Readiness Score**: Должен быть 80%+
9. **Валидируйте overview_length**: Минимум 200 символов
10. **Мониторьте граф-сущности**: 10+ сущностей для качества
11. **Проверяйте морфологию**: 2+ улучшений для русского языка
12. **Используйте правильные коллекции**: Автоматическая маршрутизация

---

## Навигация

- [Назад к README](../README.md)
- [Быстрый старт](./getting-started.md)
- [Мониторинг и отладка](./monitoring-debugging.md)
- [Поддержка и развитие](./support-development.md)

