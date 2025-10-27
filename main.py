import os
import fitz
import json
import re
import zipfile
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "7674350644:AAE85BFXjF8P8n2n8Ab3dG8xcP3euNHfBCs"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📄 Send me a JEE/NEET PDF, and I’ll convert it into JSON with diagrams!")

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    os.makedirs("downloads", exist_ok=True)
    os.makedirs("output", exist_ok=True)
    pdf_path = f"downloads/{update.message.document.file_name}"
    await file.download_to_drive(pdf_path)

    await update.message.reply_text("🔍 Processing your file... please wait a moment.")

    # === Extract questions + diagrams ===
    doc = fitz.open(pdf_path)
    questions = []
    image_count = 1
    q_id = 1

    for page in doc:
        text = page.get_text("text")
        matches = re.findall(r"Q\d+\..*?(?=Q\d+\.|ANSWER KEYS|$)", text, flags=re.S)
        for m in matches:
            q_text = re.sub(r"\s+", " ", m).strip()
            opts = re.findall(r"\(\d+\)\s*([A-Za-z0-9π√\+\-\*/\^ ]+)", q_text)
            question_data = {
                "id": f"q{q_id}",
                "question": q_text,
                "questionImage": "",
                "options": [{"id": i, "text": o.strip(), "image": ""} for i, o in enumerate(opts[:4])],
                "correctOption": None,
                "marks": 4,
                "negativeMarks": 1
            }
            questions.append(question_data)
            q_id += 1

        for img in page.get_images(full=True):
            xref = img[0]
            pix = fitz.Pixmap(doc, xref)
            img_path = f"output/q{image_count}.png"
            if pix.n < 5:
                pix.save(img_path)
            else:
                pix = fitz.Pixmap(fitz.csRGB, pix)
                pix.save(img_path)
            image_count += 1

    json_file = "output/questions.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)

    # === Create zip file ===
    zip_path = "output/jee_json_output.zip"
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        zipf.write(json_file, os.path.basename(json_file))
        for img_file in os.listdir("output"):
            if img_file.endswith(".png"):
                zipf.write(os.path.join("output", img_file), img_file)

    await update.message.reply_document(open(zip_path, "rb"), caption="✅ Here's your JSON + images!")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))

print("🤖 Bot is running...")
app.run_polling()
