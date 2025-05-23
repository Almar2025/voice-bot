import os
import telebot
import speech_recognition as sr
import tempfile
import smtplib
from email.mime.text import MIMEText
from pydub import AudioSegment
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.service_account import Credentials

# Настройки
TOKEN = os.getenv("BOT_TOKEN")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
GDRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

bot = telebot.TeleBot(TOKEN)

def summarize(text):
    # Упрощённая выжимка
    return text if len(text) < 400 else text[:400] + "..."

def send_email(subject, content):
    msg = MIMEText(content)
    msg["Subject"] = subject
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_USER
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.send_message(msg)

def upload_to_gdrive(filename, filepath):
    creds = Credentials.from_service_account_file("gdrive_creds.json")
    service = build("drive", "v3", credentials=creds)
    file_metadata = {"name": filename, "parents": [GDRIVE_FOLDER_ID]}
    media = MediaFileUpload(filepath, resumable=True)
    service.files().create(body=file_metadata, media_body=media, fields="id").execute()

@bot.message_handler(commands=["start"])
def send_welcome(message):
    bot.reply_to(message, "Привет! Отправь мне голосовое сообщение, и я сделаю выжимку.")

@bot.message_handler(content_types=["voice"])
def handle_voice(message):
    file_info = bot.get_file(message.voice.file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as f:
        f.write(downloaded_file)
        ogg_path = f.name

    wav_path = ogg_path.replace(".ogg", ".wav")
    AudioSegment.from_file(ogg_path).export(wav_path, format="wav")

    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_path) as source:
        audio = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio, language="ru-RU")
        except:
            bot.reply_to(message, "Не удалось распознать речь.")
            return

    summary = summarize(text)
    bot.reply_to(message, f"Выжимка:
{summary}")

    send_email("Новая выжимка от бота", summary)
    upload_to_gdrive("summary.txt", wav_path)

bot.polling()