from dotenv import load_dotenv
load_dotenv()
import os
import logging
import yagmail
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InputFile
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
EMAIL_SENDER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

client_data = {}
languages = ["Suomi", "Русский", "English"]

def send_email(name, phone, message, language, photo_paths=None):
    subject = "Uusi asiakaspyyntö - Driveline"
    body = f"""Uusi pyyntö on vastaanotettu:

Nimi: {name}
Puhelin: {phone}
Kuvaus: {message}
Kieli: {language}
"""
    try:
        yag = yagmail.SMTP(EMAIL_SENDER, EMAIL_PASSWORD)
        if photo_paths:
            yag.send(EMAIL_RECEIVER, subject, contents=[body] + photo_paths)
        else:
            yag.send(EMAIL_RECEIVER, subject, body)
        print("Email lähetetty!")
    except Exception as e:
        print(f"Virhe emailin lähetyksessä: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    client_data[user_id] = {}

    keyboard = ReplyKeyboardMarkup(
        [[lang] for lang in languages], resize_keyboard=True, one_time_keyboard=True
    )
    await update.message.reply_text("Valitse kieli / Выберите язык / Choose language:", reply_markup=keyboard)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if user_id not in client_data:
        client_data[user_id] = {}

    user = client_data[user_id]

    if text == "/skip" and "message" in user:
        await finish_request(update, context)
        return

    if user.get("finished"):
        lang = user.get("language", "English")
        await update.message.reply_text({
            "Suomi": "✉️ Kiitos! Viestisi on vastaanotettu.",
            "Русский": "✉️ Спасибо! Ваше сообщение получено.",
            "English": "✉️ Thank you! Your message has been received."
        }[lang])
        send_email(user["name"], user["phone"], f"Lisäviesti / Доп. сообщение:\n{text}", lang)
        return

    if text in languages:
        user["language"] = text
        lang = user["language"]
        prompts = {
            "Suomi": "Kirjoita nimesi:",
            "Русский": "Введите ваше имя:",
            "English": "Please enter your name:",
        }
        await update.message.reply_text(prompts[lang])
        return

    lang = user.get("language", "English")

    if "name" not in user:
        user["name"] = text
        prompts = {
            "Suomi": "Anna puhelinnumerosi:",
            "Русский": "Введите номер телефона:",
            "English": "Enter your phone number:",
        }
        await update.message.reply_text(prompts[lang])
        return

    if "phone" not in user:
        user["phone"] = text
        prompts = {
            "Suomi": "Kerro, mikä on ongelma tai toiveesi.",
            "Русский": "Опишите, пожалуйста, суть вашего вопроса или проблемы.",
            "English": "Please describe your question or issue.",
        }
        await update.message.reply_text(prompts[lang])
        return

    if "message" not in user:
        user["message"] = text
        user["photos"] = []
        prompts = {
            "Suomi": "📷 Voit lähettää kuvia tai kirjoita /skip jatkaaksesi ilman niitä.",
            "Русский": "📷 Вы можете отправить фото или напишите /skip чтобы продолжить без фото.",
            "English": "📷 You can send photos or type /skip to continue without them.",
        }
        await update.message.reply_text(prompts[lang])
        return

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in client_data or "message" not in client_data[user_id]:
        return

    photo_file = await update.message.photo[-1].get_file()
    photo_path = f"photo_{user_id}_{len(client_data[user_id]['photos'])}.jpg"
    await photo_file.download_to_drive(photo_path)
    client_data[user_id]["photos"].append(photo_path)

    await update.message.reply_text("📸 Kuva vastaanotettu / Фото получено / Photo received")

async def finish_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = client_data.get(user_id, {})
    lang = user.get("language", "English")

    confirmation = {
        "Suomi": "✅ Kiitos! Pyyntö on vastaanotettu. Otamme sinuun yhteyttä mahdollisimman pian!",
        "Русский": "✅ Спасибо! Ваша заявка отправлена. Мы свяжемся с вами в кратчайшие сроки!",
        "English": "✅ Thank you! Your request has been sent. We will contact you shortly!",
    }

    extra = {
        "Suomi": "💬 Jos sinulla on lisäkysymyksiä, voit kirjoittaa ne suoraan tähän chattiin.",
        "Русский": "💬 Если у вас есть дополнительные вопросы — просто напишите их сюда.",
        "English": "💬 If you have any additional questions, feel free to type them here.",
    }

    await update.message.reply_text(confirmation[lang])
    await update.message.reply_text(extra[lang])

    send_email(
        user.get("name", ""),
        user.get("phone", ""),
        user.get("message", ""),
        lang,
        photo_paths=user.get("photos", []),
    )

    for photo in user.get("photos", []):
        try:
            os.remove(photo)
        except:
            pass

    user["finished"] = True

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CommandHandler("skip", finish_request))

    print("Bot is running...")
    app.run_polling()