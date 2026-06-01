from __future__ import annotations
from io import BytesIO
import pandas as pd
from docx import Document
from pypdf import PdfReader

def read_uploaded_file(uploaded_file) -> str:
    if uploaded_file is None:
        return ""
    name = uploaded_file.name.lower()
    data = uploaded_file.read()
    if name.endswith(".txt"):
        return data.decode("utf-8", errors="ignore")
    if name.endswith(".csv"):
        df = pd.read_csv(BytesIO(data))
        return dataframe_to_text(df)
    if name.endswith(".xlsx") or name.endswith(".xls"):
        xl = pd.ExcelFile(BytesIO(data))
        chunks = []
        for sheet in xl.sheet_names:
            df = xl.parse(sheet)
            chunks.append(f"Sheet: {sheet}\n{dataframe_to_text(df)}")
        return "\n\n".join(chunks)
    if name.endswith(".docx"):
        doc = Document(BytesIO(data))
        return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    if name.endswith(".pdf"):
        reader = PdfReader(BytesIO(data))
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        return "\n".join(pages)
    return data.decode("utf-8", errors="ignore")

def dataframe_to_text(df: pd.DataFrame, max_rows: int = 200) -> str:
    if df.empty:
        return ""
    return df.head(max_rows).to_csv(index=False)
