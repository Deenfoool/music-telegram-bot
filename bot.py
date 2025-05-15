import logging
import re
import requests
from bs4 import BeautifulSoup
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

# === Настройки ===
TELEGRAM_BOT_TOKEN = '7508488892:AAFJnPNzDtsuowzBTmhkra3E6HzgCyRAwow'

# === Логирование ===
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

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

    response = requests.get(url, params=params, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    results = []

    for item in soup.select(".track"):
        try:
            title = item.select_one(".track-name").text.strip()
            artist = item.select_one(".artist-name").text.strip()
            download_link = item.select_one("a.download")['href']
            results.append({"title": title, "artist": artist, "link": download_link})
        except Exception as e:
            continue

    return results

# === Загрузка и отправка файла ===
async def send_audio_file(update: Update, context: ContextTypes.DEFAULT_TYPE, audio_url: str, title: str, artist: str):
    try:
        # Скачиваем файл
        response = requests.get(audio_url)
        filename = title + ".mp3"
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

        # Удаляем файл после отправки
        import os
        os.remove(filename)

    except Exception as e:
        await update.message.reply_text("Ошибка при загрузке или отправке файла.")
        print(e)

# === Обработка сообщений ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    chat_id = update.effective_chat.id

    if re.search(r'@F3olBot\s+vkmus', text, re.IGNORECASE):
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

# === Запуск бота ===
if __name__ == '__main__':
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)

    application.add_handler(message_handler)

    print("🎵 Бот запущен и ожидает команды...")
    application.run_polling()
