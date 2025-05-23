import os
import telebot
import speech_recognition as sr
from pydub import AudioSegment
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import smtplib
from email.message import EmailMessage

BOT_TOKEN = os.getenv("BOT_TOKEN")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

bot = telebot.TeleBot(BOT_TOKEN)

def summarize(text):
    sentences = text.split(".")
    return ". ".join(sentences[:2]) if len(sentences) > 1 else text

def send_email(subject, body):
    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_USER

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(EMAIL_USER, EMAIL_PASSWORD)
        smtp.send_message(msg)

def upload_to_gdrive(file_path, folder_id):
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    SERVICE_ACCOUNT_FILE = 'credentials.json'

    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('drive', 'v3', credentials=creds)

    file_metadata = {'name': os.path.basename(file_path), 'parents': [folder_id]}
    media = MediaFileUpload(file_path, mimetype='text/plain')

    service.files().create(body=file_metadata, media_body=media, fields='id').execute()

@bot.message_handler(commands=['start'])
def start_handler(message):
    bot.reply_to(message, "Привет! Отправь голосовое сообщение, и я пришлю выжимку на почту и сохраню в Google Drive.")

@bot.message_handler(content_types=['voice'])
def voice_handler(message):
    try:
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
            bot.reply_to(message, "Не удалось распознать речь.")
            return

        summary = summarize(text)
        bot.reply_to(message, f"Выжимка:
{summary}")

        send_email("Новая выжимка от бота", summary)

        with open("summary.txt", "w") as f:
            f.write(summary)

        upload_to_gdrive("summary.txt", GOOGLE_DRIVE_FOLDER_ID)

    except Exception as e:
        bot.reply_to(message, f"Произошла ошибка: {e}")

bot.polling()