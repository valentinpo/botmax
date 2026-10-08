# 🤖 BotMax — боты для платформы MAX

Telegram-боты для платформы **MAX** (platform-api.max.ru) на Python.

## 📁 Структура

```
botmax/
├── MAXbot/            # Короткий бот: get_me, отправка сообщений, long-polling
│   └── bot.py
└── olga_max_bot/      # Расширенный бот: SQLite-база, приветствия, статистика, контакты
    ├── bot.py
    └── requirements.txt
```

## 🚀 Установка

```bash
pip install requests
cp .env.example .env   # укажите свой MAX_BOT_TOKEN
```

## ⚙️ Настройка

Токен читается из переменной окружения `MAX_BOT_TOKEN` (файл `.env` или системная переменная).

## 📄 Лицензия

MIT (см. [LICENSE](LICENSE)).