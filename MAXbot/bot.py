import os
import requests
import time
import logging
import json

# === НАСТРОЙКИ ===
TOKEN = os.environ.get("MAX_BOT_TOKEN", "")
API_URL = "https://platform-api.max.ru"
HEADERS = {"Authorization": TOKEN, "Content-Type": "application/json"}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

last_update_id = 0
marker = None

def get_me():
    try:
        resp = requests.get(f"{API_URL}/me", headers=HEADERS, timeout=5)
        if resp.status_code == 200:
            info = resp.json()
            logger.info(f"✅ Успех! Бот: {info.get('name')}")
            return True
        else:
            logger.error(f"❌ Ошибка: {resp.status_code} - {resp.text}")
            return False
    except Exception as e:
        logger.error(f"⚠️ Ошибка подключения: {e}")
        return False

def send_message(user_id, text):
    """✅ Отправка сообщения: user_id в URL, текст в JSON body"""
    
    # 🔧 Правильный формат: user_id как query-параметр в URL
    url = f"{API_URL}/messages?user_id={user_id}"
    
    # Тело запроса: ТОЛЬКО текст и форматирование (без user_id/chat_id!)
    payload = {
        "text": text,
        "format": "markdown"
    }
    
    try:
        logger.debug(f"🔄 Отправка: URL={url}, Body={json.dumps(payload)}")
        resp = requests.post(url, headers=HEADERS, json=payload, timeout=5)
        
        logger.info(f"📡 Ответ: Status={resp.status_code}, Body={resp.text[:200]}")
        
        if resp.status_code == 200:
            logger.info(f"✅ УСПЕХ! Сообщение отправлено пользователю {user_id}")
            return True
        else:
            logger.error(f"❌ Ошибка {resp.status_code}: {resp.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Исключение при отправке: {e}")
        return False

def get_updates():
    global last_update_id, marker
    
    params = {"timeout": 30}
    if marker:
        params["marker"] = marker
    
    try:
        resp = requests.get(f"{API_URL}/updates", headers=HEADERS, params=params, timeout=35)
        if resp.status_code == 200:
            data = resp.json()
            updates = data.get("updates", [])
            marker = data.get("marker")
            if updates:
                logger.info(f"📨 Получено обновлений: {len(updates)}")
                for update in updates:
                    last_update_id = max(last_update_id, update.get("update_id", update.get("timestamp", 0)))
                    yield update
            else:
                logger.debug("⏳ Нет новых сообщений")
        elif resp.status_code == 204:
            logger.debug("⏳ Нет контента (204)")
    except requests.exceptions.ReadTimeout:
        logger.debug("⏳ Таймаут (нормально)")
    except Exception as e:
        logger.warning(f"⚠️ Ошибка получения: {e}")
        time.sleep(5)

def handle_message(update):
    try:
        update_type = update.get("update_type", "")
        
        if update_type == "bot_started":
            logger.info("🤖 Пользователь запустил бота")
            sender = update.get("user", {})
            user_id = sender.get("user_id")
            user_name = sender.get("name", sender.get("first_name", "Пользователь"))
            if user_id:
                send_message(user_id, f"👋 Привет, {user_name}! Я бот **NeuroLink** 🤖")
            return
            
        elif update_type != "message_created":
            logger.debug(f"⏭️ Пропускаем тип: {update_type}")
            return
        
        message = update.get("message", {})
        if not message:
            logger.warning("⚠️ Пустое сообщение")
            return
        
        # 🔍 Берём user_id из SENDER (отправитель)
        sender = message.get("sender", {})
        user_id = sender.get("user_id")  # ← ID пользователя (5194550)
        user_name = sender.get("name", sender.get("first_name", "Пользователь"))
        
        body = message.get("body", {})
        text = body.get("text", "")
        
        logger.info(f"📨 От {user_name} (user_id: {user_id}): '{text}'")
        
        if not user_id:
            logger.warning("⚠️ Не найден user_id отправителя!")
            return
        
        text_lower = text.lower().strip()
        
        if text_lower in ["/start", "привет", "хай", "здравствуй"]:
            send_message(user_id, f"👋 Привет, {user_name}!\n\nЯ бот **NeuroLink** 🤖\n\n*Что я умею:*\n• Отвечать на вопросы\n• Эхо-режим\n• Интеграция с ИИ (скоро!)\n\nНапиши `помощь` для списка команд.")
        
        elif text_lower in ["помощь", "/help", "help"]:
            send_message(user_id, "📋 *Команды:*\n`/start` — начать\n`помощь` — справка\n`ai [текст]` — запрос к ИИ")
        
        elif text_lower.startswith("ai "):
            prompt = text[3:].strip()
            send_message(user_id, f"🧠 *Запрос к ИИ:*\n`{prompt}`\n\n_Модуль в разработке..._")
        
        elif text_lower in ["тест", "проверка", "ты тут?"]:
            send_message(user_id, "✅ Да, я на связи! Всё работает 🎉")
        
        else:
            time.sleep(0.3)
            send_message(user_id, f"🔁 _Вы написали:_\n`{text}`")
            
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_message: {e}")
        import traceback
        logger.error(traceback.format_exc())

def main():
    print("🤖 Запуск бота NeuroLink... (нажми Ctrl+C для остановки)")
    if not get_me():
        print("❌ Не удалось подключиться. Проверь токен!")
        input("Нажми Enter для выхода...")
        return
    print("✅ Бот готов к работе! Жду сообщения...")
    
    while True:
        try:
            for update in get_updates():
                handle_message(update)
            time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Бот остановлен пользователем.")
            break
        except Exception as e:
            logger.error(f"🔥 Критическая ошибка: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()