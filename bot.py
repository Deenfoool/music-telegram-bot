import logging
import os
import re
import requests
from bs4 import BeautifulSoup
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# === Настройки логирования ===
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# === Переменные окружения ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("Не установлен TELEGRAM_BOT_TOKEN")

# === Парсер mp3uks.ru ===
def search_mp3uks(query):
    url = "https://mp3uks.ru/index.php "
    params = {
        "do": "search",
        "subaction": "search",
        "story": query
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    }

    try:
        response = requests.get(url, params=params, headers=headers)
        if response.status_code != 200:
            logging.error(f"Ошибка при поиске на mp3uks.ru: {response.status_code}")
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        results = []

        for item in soup.select(".track"):
            try:
                title = item.select_one(".track-name").text.strip()
                artist = item.select_one(".artist-name").text.strip()
                download_link = item.select_one("a.download")['href']
                results.append({"title": title, "artist": artist, "link": download_link})
            except Exception as e:
                logging.warning(f"Ошибка парсинга трека: {e}")
                continue

        return results

    except Exception as e:
        logging.error(f"Ошибка подключения к mp3uks.ru: {e}")
        return []

# === Загрузка и отправка файла ===
async def send_audio_file(update: Update, context: ContextTypes.DEFAULT_TYPE, audio_url: str, title: str, artist: str):
    try:
        # Скачиваем файл
        response = requests.get(audio_url)
        filename = f"{title}.mp3"
        with open(filename, 'wb') as f:
            f.write(response.content)

        # Отправляем в Telegram
        with open(filename, 'rb') as f:
            await context.bot.send_audio(
                chat_id=update.effective_chat.id,
                audio=InputFile(f),
                title=title,
                performer=artist,
                caption=f"🎧 {artist} — {title}"
            )

        # Удаляем временный файл
        os.remove(filename)

    except Exception as e:
        await update.message.reply_text("❌ Ошибка при загрузке или отправке файла.")
        logging.error(f"Ошибка при отправке аудио: {e}")

# === Обработка сообщений ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Проверяем, что это текстовое сообщение
    if not update.message or not update.message.text:
        return

    text = update.message.text

    # Ищем команду: @F3o1Bot vkmus Название песни
    if re.search(r'@F3o1Bot\s+vkmus', text, re.IGNORECASE):
        match = re.search(r'vkmus\s+(.+)', text, re.IGNORECASE)
        if match:
            query = match.group(1).strip()
            await update.message.reply_text(f"🔍 Ищу на mp3uks.ru: {query}...")

            tracks = search_mp3uks(query)
            if tracks:
                first_track = tracks[0]
                await update.message.reply_text("⬇️ Скачиваю и отправляю трек...")
                await send_audio_file(update, context, first_track["link"], first_track["title"], first_track["artist"])
            else:
                await update.message.reply_text("❌ Ничего не найдено.")

# === Обработчик ошибок ===
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.error(f"Ошибка при обработке обновления: {update}", exc_info=context.error)

# === Точка входа ===
if __name__ == '__main__':
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)

    application.add_handler(message_handler)
    application.add_error_handler(error_handler)

    logging.info("🎵 Бот запущен и ожидает команды...")
    application.run_polling()
