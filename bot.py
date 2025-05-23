
import telebot
import os
import speech_recognition as sr
from pydub import AudioSegment
from summarizer import summarize
from utils import send_email, upload_to_gdrive

bot = telebot.TeleBot(os.getenv("BOT_TOKEN"))

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    file_info = bot.get_file(message.voice.file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    ogg_path = "voice.ogg"
    with open(ogg_path, 'wb') as f:
        f.write(downloaded_file)

    wav_path = ogg_path.replace(".ogg", ".wav")
    AudioSegment.from_file(ogg_path).export(wav_path, format="wav")

    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_path) as source:
        audio = recognizer.record(source)

    try:
        text = recognizer.recognize_google(audio, language="ru-RU")
    except:
        bot.reply_to(message, "Не удалось распознать голосовое сообщение.")
        return

    summary = summarize(text)
    bot.reply_to(message, f"Выжимка: {summary}")

    send_email("Новая выжимка от бота", summary)
    upload_to_gdrive("summary.txt", wav_path)

bot.polling()
