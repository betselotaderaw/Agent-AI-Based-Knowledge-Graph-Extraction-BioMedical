import os
import re
import pdfplumber

# Paths
PDF_FOLDER = "./dataset/research_papers/"
CLEANED_FOLDER = "./dataset/cleaned_papers/"

def clean_text(text):
    """Cleans extracted text by removing references, links, and unnecessary sections"""
    text = re.sub(r"http[s]?://\S+", "", text)  # Remove URLs
    text = re.sub(r"\[[0-9]+\]", "", text)  # Remove reference numbers like [1], [23]
    
    # Remove common reference section patterns
    text = re.sub(r"\n\s*References\s*\n.*", "", text, flags=re.S | re.I)
    text = re.sub(r"\n\s*Bibliography\s*\n.*", "", text, flags=re.S | re.I)
    
    # Remove excessive newlines and spaces
    text = re.sub(r"\n{2,}", "\n", text).strip()
    
    return text

def extract_and_clean_pdf(pdf_path, output_path):
    """Extracts and cleans text from a PDF"""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    # Remove tables (attempt by ignoring sections with many numbers and aligned text)
                    if len(page.extract_tables()) > 0:
                        page_text = re.sub(r"(\d{2,}(\s+\d{2,}){2,})", "", page_text)  
                    
                    text += page_text + "\n"
        
        cleaned_text = clean_text(text)

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(cleaned_text)

        print(f"✅ Cleaned text saved to {output_path}")
    
    except Exception as e:
        print(f"⚠️ Error processing {pdf_path}: {e}")

def process_all_pdfs(pdf_folder, cleaned_folder):
    """Processes all PDFs in the research papers folder"""
    if not os.path.exists(cleaned_folder):
        os.makedirs(cleaned_folder)
    
    pdf_files = [f for f in os.listdir(pdf_folder) if f.endswith(".pdf")]
    if not pdf_files:
        print("❌ No PDFs found in the folder.")
        return
    
    for pdf_file in pdf_files:
        pdf_path = os.path.join(pdf_folder, pdf_file)
        cleaned_text_path = os.path.join(cleaned_folder, f"{os.path.splitext(pdf_file)[0]}.txt")
        
        extract_and_clean_pdf(pdf_path, cleaned_text_path)

if __name__ == "__main__":
    process_all_pdfs(PDF_FOLDER, CLEANED_FOLDER)
