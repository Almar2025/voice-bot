import telebot
import speech_recognition as sr
from pydub import AudioSegment
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
import os
import smtplib
from email.message import EmailMessage
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

from dotenv import load_dotenv
load_dotenv(".env")

bot = telebot.TeleBot(os.getenv("BOT_TOKEN"))

@bot.message_handler(commands=["start"])
def start(message):
    bot.reply_to(message, "Привет! Отправь голосовое сообщение, и я пришлю выжимку на почту и Google Диск.")

@bot.message_handler(content_types=["voice"])
def handle_voice(message):
    try:
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        ogg_path = "voice.ogg"
        wav_path = "voice.wav"
        with open(ogg_path, "wb") as f:
            f.write(downloaded_file)

        AudioSegment.from_file(ogg_path).export(wav_path, format="wav")

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio = recognizer.record(source)

        text = recognizer.recognize_google(audio, language="ru-RU")
        summary = summarize(text)

        bot.reply_to(message, f"Выжимка: {summary}")

        send_email("Новая выжимка от бота", summary)
        upload_to_gdrive("summary.txt", summary)

    except Exception as e:
        bot.reply_to(message, f"Ошибка: {str(e)}")

def summarize(text):
    parser = PlaintextParser.from_string(text, Tokenizer("russian"))
    summarizer = LsaSummarizer()
    summary = summarizer(parser.document, 2)
    return " ".join(str(sentence) for sentence in summary)

def send_email(subject, body):
    msg = EmailMessage()
    msg.set_content(body)
    msg["Subject"] = subject
    msg["From"] = os.getenv("EMAIL_USER")
    msg["To"] = os.getenv("EMAIL_USER")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASSWORD"))
        smtp.send_message(msg)

def upload_to_gdrive(filename, content):
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()
    drive = GoogleDrive(gauth)

    file = drive.CreateFile({"title": filename, "parents": [{"id": os.getenv("GOOGLE_DRIVE_FOLDER_ID")}]})
    file.SetContentString(content)
    file.Upload()

bot.polling()
