import os
import json
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
import tempfile
from system_prompt import SYSTEM_PROMPT

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    system_instruction=SYSTEM_PROMPT
)

app = FastAPI(title="Assistente RESPAD/CBMAL")
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

@app.get("/", response_class=HTMLResponse)
async def root():
    return FileResponse("static/index.html")

@app.post("/chat")
async def chat(request: Request):
    body = await request.json()
    messages = body.get("messages", [])

    # Convert history to Gemini format
    history = []
    for msg in messages[:-1]:
        history.append({
            "role": "user" if msg["role"] == "user" else "model",
            "parts": [msg["content"]]
        })

    user_message = messages[-1]["content"] if messages else ""

    chat_session = model.start_chat(history=history)

    async def generate():
        response = chat_session.send_message(user_message, stream=True)
        for chunk in response:
            if chunk.text:
                yield {"data": json.dumps({"text": chunk.text})}
        yield {"data": json.dumps({"done": True})}

    return EventSourceResponse(generate())

@app.post("/export")
async def export_doc(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    title = body.get("title", "Documento RESPAD")

    doc = Document()

    # Page setup
    section = doc.sections[0]
    section.page_width = Inches(8.27)
    section.page_height = Inches(11.69)
    section.left_margin = Inches(1.18)
    section.right_margin = Inches(1.18)
    section.top_margin = Inches(0.98)
    section.bottom_margin = Inches(0.98)

    # Header with brasao
    header = doc.sections[0].header
    header_para = header.paragraphs[0]
    header_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = header_para.add_run()
    brasao_path = Path("assets/brasao.png")
    if brasao_path.exists():
        run.add_picture(str(brasao_path), width=Inches(0.6))

    # Red separator line
    header_para2 = header.add_paragraph()
    header_para2.paragraph_format.space_before = Pt(4)
    border_run = header_para2.add_run("─" * 80)
    border_run.font.color.rgb = RGBColor(0xC1, 0x0A, 0x0A)
    border_run.font.size = Pt(8)

    # Document title
    title_para = doc.add_heading(title, level=1)
    title_para.runs[0].font.color.rgb = RGBColor(0xC1, 0x0A, 0x0A)
    title_para.runs[0].font.name = "Calibri"

    doc.add_paragraph()

    # Add assistant responses only
    for msg in messages:
        if msg["role"] == "assistant":
            para = doc.add_paragraph(msg["content"])
            para.runs[0].font.size = Pt(11)
            para.runs[0].font.name = "Calibri"
            doc.add_paragraph()

    # Footer
    footer = doc.sections[0].footer
    footer_para = footer.paragraphs[0]
    footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer_run = footer_para.add_run(
        "Gerado pelo Assistente RESPAD/CBMAL · Corpo de Bombeiros Militar de Alagoas"
    )
    footer_run.font.size = Pt(8)
    footer_run.font.color.rgb = RGBColor(0x66, 0x66, 0x66)

    # Save to temp file and return
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp:
        doc.save(tmp.name)
        tmp_path = tmp.name

    safe_title = "".join(c for c in title if c.isalnum() or c in " -_").strip()
    filename = f"{safe_title}.docx" if safe_title else "documento-respad.docx"

    return FileResponse(
        tmp_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=filename
    )
