import io

from dotenv import load_dotenv
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from pdf2image import convert_from_path

from google_ocr import (
    google_ocr_bytes,
)

load_dotenv()

png_path = "test_docs/cnh.png"
pdf_path = "est_docs/cnh.pdf"


def detect_format(path):
    with open(path, "rb") as f:
        header = f.read(8)

    if header.startswith(b"%PDF"):
        return "pdf"
    if header.startswith(b"\x89PNG"):
        return "png"
    if header.startswith(b"\xff\xd8\xff"):
        return "jpg"

    return "unknown"


def convert_file(file):
    file_format = detect_format(file)

    if file_format == "pdf":
        parsed_file = convert_from_path(file, dpi=300)

        buf = io.BytesIO()
        parsed_file[0].save(buf, format="PNG")
        text = google_ocr_bytes(buf.getvalue())

    else:
        with open(file, "rb") as f:
            text = google_ocr_bytes(f.read())

    return text


text = convert_file(png_path)

llm = ChatOpenAI(model_name="gpt-4o-mini", temperature=0)


template = """
Extraia e retorna as informações mais relevantes do texto fornecido:

- Nome
- CPF
- Data de Nascimento
- Filiação

Forneça as informações no seguinte formato JSON com as chaves correspondentes em snake_case:
{text}
"""


prompt = PromptTemplate(
    input_variables=["text"],
    template=template,
)

chain = prompt | llm | JsonOutputParser()

response = chain.invoke({"text": text})

print(response)
