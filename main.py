import os
import fitz
import json
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# --- Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📄 Send me a JEE/NEET PDF and I’ll convert it to JSON with diagrams!")

async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await update.message.document.get_file()
    os.makedirs("downloads", exist_ok=True)
    os.makedirs("output", exist_ok=True)

    pdf_path = f"downloads/{update.message.document.file_name}"
    await file.download_to_drive(pdf_path)
    await update.message.reply_text("🔍 Processing your PDF… please wait.")

    # === Extract questions ===
    doc = fitz.open(pdf_path)
    questions = []
    q_id = 1
    img_id = 1

    for page in doc:
        text = page.get_text("text")
        matches = re.findall(r"Q\d+\..*?(?=Q\d+\.|ANSWER KEYS|$)", text, flags=re.S)
        for m in matches:
            q_text = re.sub(r"\s+", " ", m).strip()
            opts = re.findall(r"\(\d+\)\s*([A-Za-z0-9π√\+\-\*/\^ ]+)", q_text)
            q_clean = re.sub(r"\(\d+\).*", "", q_text).strip()
            question = {
                "id": f"q{q_id}",
                "question": q_clean,
                "questionImage": f"https://example.com/q{img_id}.png",
                "options": [{"id": i, "text": o.strip(), "image": ""} for i, o in enumerate(opts[:4])],
                "correctOption": None,
                "marks": 4,
                "negativeMarks": 1
            }
            questions.append(question)
            q_id += 1
        for img in page.get_images(full=True):
            xref = img[0]
            pix = fitz.Pixmap(doc, xref)
            img_path = f"output/q{img_id}.png"
            if pix.n < 5:
                pix.save(img_path)
            else:
                pix = fitz.Pixmap(fitz.csRGB, pix)
                pix.save(img_path)
            img_id += 1

    out_path = "output/questions.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)

    await update.message.reply_text("✅ Extraction done! Sending your JSON…")
    await update.message.reply_document(open(out_path, "rb"))

# --- Main ---
if __name__ == "__main__":
    TOKEN = os.getenv("TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))
    print("🤖 Bot is running...")
    app.run_polling()

