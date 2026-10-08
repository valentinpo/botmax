import os
import requests
import time
import logging
import sqlite3
import json
from datetime import datetime

# === НАСТРОЙКИ ===
TOKEN = os.environ.get("MAX_BOT_TOKEN", "")
API_URL = "https://platform-api.max.ru"
HEADERS = {"Authorization": TOKEN, "Content-Type": "application/json"}
ADMIN_ID = 5194550  # ID Ольги в MAX (замени на актуальный)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

marker = None
user_states = {}  # Состояния пользователей для формы заявки

# === БАЗА ДАННЫХ ===
def init_db():
    conn = sqlite3.connect('olga_max_leads.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            user_id TEXT,
            username TEXT,
            name TEXT,
            service TEXT,
            budget TEXT,
            deadline TEXT,
            contacts TEXT,
            task_description TEXT,
            status TEXT DEFAULT 'new'
        )
    ''')
    conn.commit()
    conn.close()

def add_lead(data):
    conn = sqlite3.connect('olga_max_leads.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO leads (date, user_id, username, name, service, budget, deadline, contacts, task_description, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        data.get('user_id'),
        data.get('username'),
        data.get('name'),
        data.get('service'),
        data.get('budget'),
        data.get('deadline'),
        data.get('contacts'),
        data.get('task_description'),
        'new'
    ))
    conn.commit()
    conn.close()

# === ОТПРАВКА СООБЩЕНИЙ (ПРАВИЛЬНЫЙ ФОРМАТ) ===
def send_message(user_id, text):
    """✅ Отправка сообщения: user_id в URL, текст в JSON body"""
    url = f"{API_URL}/messages?user_id={user_id}"
    
    payload = {
        "text": text,
        "format": "markdown"
    }
    
    try:
        resp = requests.post(url, headers=HEADERS, json=payload, timeout=5)
        
        if resp.status_code == 200:
            logger.info(f"✅ Сообщение отправлено пользователю {user_id}")
            return True
        else:
            logger.error(f"❌ Ошибка {resp.status_code}: {resp.text}")
            return False
    except Exception as e:
        logger.error(f"❌ Исключение при отправке: {e}")
        return False

# === ПОЛУЧЕНИЕ ОБНОВЛЕНИЙ ===
def get_updates():
    global marker
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

# === ОБРАБОТКА СООБЩЕНИЙ (ЛОГИКА ОЛЬГИ) ===
def handle_message(update):
    try:
        update_type = update.get("update_type", "")
        
        # Обработка запуска бота
        if update_type == "bot_started":
            logger.info("🤖 Пользователь запустил бота")
            sender = update.get("user", {})
            user_id = sender.get("user_id")
            user_name = sender.get("name", sender.get("first_name", "Пользователь"))
            if user_id:
                send_message(user_id, 
                    f"👋 Привет, {user_name}!\n\n"
                    f"Я помощник **Ольги Егоровой** — Data Analyst.\n\n"
                    f"*Доступные команды:*\n"
                    f"• `услуги` — цены и направления\n"
                    f"• `портфолио` — примеры работ\n"
                    f"• `заявка` — оставить заявку на проект\n"
                    f"• `контакты` — как связаться\n"
                    f"• `помощь` — эта справка")
            return
        
        # Пропускаем другие типы обновлений
        if update_type != "message_created":
            logger.debug(f"⏭️ Пропускаем тип: {update_type}")
            return
        
        message = update.get("message", {})
        if not message:
            logger.warning("⚠️ Пустое сообщение")
            return
        
        # 🔍 Берём user_id из SENDER (отправитель)
        sender = message.get("sender", {})
        user_id = sender.get("user_id")
        user_name = sender.get("name", sender.get("first_name", "Пользователь"))
        username = sender.get("username", "N/A")
        
        body = message.get("body", {})
        text = body.get("text", "").strip()
        
        logger.info(f"📨 От {user_name} (user_id: {user_id}): '{text}'")
        
        if not user_id:
            logger.warning("⚠️ Не найден user_id отправителя!")
            return
        
        text_lower = text.lower()
        
        # === ПРОВЕРКА СОСТОЯНИЯ (форма заявки) ===
        if user_id in user_states:
            handle_lead_form(user_id, text_lower, user_name, username)
            return
        
        # === ОБРАБОТКА КОМАНД ===
        if text_lower in ["/start", "привет", "хай", "здравствуй", "старт"]:
            send_message(user_id,
                f"👋 Привет, {user_name}!\n\n"
                f"Я помощник **Ольги Егоровой** — Data Analyst.\n\n"
                f"*Доступные команды:*\n"
                f"• `услуги` — цены и направления\n"
                f"• `портфолио` — примеры работ\n"
                f"• `заявка` — оставить заявку на проект\n"
                f"• `контакты` — как связаться\n"
                f"• `помощь` — эта справка")
        
        elif text_lower in ["услуги", "цены", "прайс", "стоимость"]:
            send_message(user_id,
                "📊 *УСЛУГИ И ЦЕНЫ*\n\n"
                "🔍 **Исследовательский анализ** — от 15 000 ₽\n"
                "  • EDA и статистика\n"
                "  • Когортный анализ\n"
                "  • Отчёты в Jupyter\n\n"
                "📈 **Дашборды и визуализация** — от 25 000 ₽\n"
                "  • DataLens / Tableau\n"
                "  • Автообновление\n"
                "  • Алерты по аномалиям\n\n"
                "⚙️ **Автоматизация отчётности** — от 30 000 ₽\n"
                "  • ETL-пайплайны\n"
                "  • AirFlow / cron\n"
                "  • API интеграции\n\n"
                "🎯 **Консалтинг по данным** — от 20 000 ₽\n"
                "  • Метрики продукта\n"
                "  • A/B-тесты\n"
                "  • Стратегия данных\n\n"
                "Хотите оставить заявку? Напишите `заявка`")
        
        elif text_lower in ["портфолио", "кейсы", "работы", "проекты"]:
            send_message(user_id,
                "📁 *ИЗБРАННЫЕ ПРОЕКТЫ*\n\n"
                "🎬 **Стриминг**\n"
                "Анализ пользовательского поведения\n"
                "• Точность: 94%\n"
                "• Пользователи: 50K+\n\n"
                "🛒 **E-commerce**\n"
                "Оптимизация воронки продаж\n"
                "• Конверсия: +23%\n"
                "• Выручка: +18%\n\n"
                "📱 **Мобильные приложения**\n"
                "Мониторинг метрик продукта\n"
                "• DAU tracked\n"
                "• Real-time\n\n"
                "❤️ **Соцпроекты**\n"
                "Анализ эффективности НКО\n"
                "• Impact measured\n"
                "• Transparency\n\n"
                "🌐 Полное портфолио: https://skylume.ru/olga/")
        
        elif text_lower in ["заявка", "заказать", "сотрудничество", "начать проект"]:
            user_states[user_id] = {
                'step': 'name',
                'user_id': user_id,
                'username': username,
                'name': user_name
            }
            send_message(user_id,
                "📝 *ОФОРМЛЕНИЕ ЗАЯВКИ*\n\n"
                "Для начала, представьтесь пожалуйста:\n"
                "(ваше имя или название компании)")
        
        elif text_lower in ["контакты", "связь", "как связаться", "контакт"]:
            send_message(user_id,
                "📞 *КОНТАКТЫ*\n\n"
                "👤 **Ольга Егорова** — Data Analyst\n\n"
                "💬 MAX: https://max.ru/u/ВАШ_НИК_В_MAX\n"
                "✈️ Telegram: @eoe66eoe\n"
                "📧 Email: eoe66eoe@gmail.com\n"
                "🐙 GitHub: github.com/eoe66\n"
                "🌐 Сайт: https://skylume.ru/olga/\n"
                "📍 Екатеринбург, Россия")
        
        elif text_lower in ["помощь", "help", "команды", "меню"]:
            send_message(user_id,
                "📋 *ДОСТУПНЫЕ КОМАНДЫ*\n\n"
                "`/start` — начать диалог\n"
                "`услуги` — цены и направления\n"
                "`портфолио` — примеры работ\n"
                "`заявка` — оставить заявку\n"
                "`контакты` — как связаться\n"
                "`помощь` — эта справка\n\n"
                "🌐 Сайт: https://skylume.ru/olga/")
        
        elif text_lower in ["faq", "вопросы", "часто задаваемые"]:
            send_message(user_id,
                "❓ *ЧАСТЫЕ ВОПРОСЫ*\n\n"
                "📌 **Какие данные вы анализируете?**\n"
                "Любые структурированные данные: веб-аналитика, CRM, базы данных, логи, соцсети.\n\n"
                "📌 **В каких инструментах работаете?**\n"
                "Python, PostgreSQL, ClickHouse, pandas, DataLens, Tableau, AirFlow.\n\n"
                "📌 **Какой формат работы?**\n"
                "Удалённо / Гибрид. Часовой пояс: UTC+5 (Екатеринбург).\n\n"
                "📌 **Как происходит оплата?**\n"
                "50% предоплата, 50% после принятия работы. Работа по договору.\n\n"
                "📌 **Сколько длится проект?**\n"
                "От 1 недели до 2 месяцев в зависимости от задачи.\n\n"
                "📌 **Предоставляете ли поддержку?**\n"
                "Да, 30 дней бесплатной поддержки после сдачи проекта.")
        
        else:
            send_message(user_id,
                f"🔁 _Получено:_ `{text}`\n\n"
                "Напишите `помощь` для списка команд.\n"
                "Или `заявка` чтобы оставить заявку на проект.")
                
    except Exception as e:
        logger.error(f"❌ Ошибка в handle_message: {e}")
        import traceback
        logger.error(traceback.format_exc())

# === ОБРАБОТКА ФОРМЫ ЗАЯВКИ ===
def handle_lead_form(user_id, text, user_name, username):
    """Обработка пошаговой формы заявки"""
    state = user_states[user_id]
    step = state.get('step')
    
    if step == 'name':
        state['name'] = text
        state['step'] = 'service'
        send_message(user_id,
            "✅ Принято.\n\n"
            "*Какая услуга вас интересует?*\n"
            "• Исследовательский анализ\n"
            "• Дашборды и визуализация\n"
            "• Автоматизация отчётности\n"
            "• Консалтинг по данным")
    
    elif step == 'service':
        state['service'] = text
        state['step'] = 'task'
        send_message(user_id,
            "📋 *Опишите задачу кратко:*\n"
            "Что нужно сделать? Какие данные есть? Какой результат ожидаете?")
    
    elif step == 'task':
        state['task_description'] = text
        state['step'] = 'budget'
        send_message(user_id,
            "💰 *Какой у вас бюджет на проект?*\n"
            "(например: 15-30к, 30-50к, 50к+)")
    
    elif step == 'budget':
        state['budget'] = text
        state['step'] = 'deadline'
        send_message(user_id,
            "📅 *Какие сроки вас интересуют?*\n"
            "(например: 2 недели, месяц, срочно)")
    
    elif step == 'deadline':
        state['deadline'] = text
        state['step'] = 'contacts'
        send_message(user_id,
            "📬 *Оставьте контакты для связи:*\n"
            "(телефон, email, или ник в MAX)")
    
    elif step == 'contacts':
        state['contacts'] = text
        
        # Сохраняем в БД
        add_lead(state)
        
        # Формируем заявку для Ольги
        application = f"""
🔥 *НОВАЯ ЗАЯВКА С MAX БОТА*

👤 *Клиент:* {state['name']} (@{state['username']})
🆔 *ID:* `{state['user_id']}`
📊 *Услуга:* {state.get('service', 'N/A')}
📝 *Задача:* {state.get('task_description', 'N/A')}
💰 *Бюджет:* {state.get('budget', 'N/A')}
⏰ *Сроки:* {state.get('deadline', 'N/A')}
📞 *Контакты:* {state['contacts']}
📅 *Дата:* {datetime.now().strftime('%d.%m.%Y %H:%M')}
        """
        
        # Отправляем Ольге
        if ADMIN_ID:
            send_message(ADMIN_ID, application)
        
        # Подтверждение клиенту
        send_message(user_id,
            "✅ *Спасибо! Ваша заявка принята.*\n\n"
            "Ольга изучит информацию и свяжется с вами в ближайшее время.\n\n"
            "📄 Портфолио: https://skylume.ru/olga/\n"
            "📞 Контакты: max.ru/u/ВАШ_НИК_В_MAX")
        
        # Очищаем состояние
        del user_states[user_id]
        logger.info(f"✅ Заявка сохранена от пользователя {user_id}")

# === ЗАПУСК ===
def main():
    print("🤖 Запуск бота Ольги для MAX... (нажми Ctrl+C для остановки)")
    
    # Инициализация БД
    init_db()
    print("✅ База данных готова")
    
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