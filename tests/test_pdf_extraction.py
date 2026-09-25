from modules.extraction.pdf_extractor import extract_text_from_pdf


pdf_path = "data/uploads/Id_card.pdf"

pages = extract_text_from_pdf(pdf_path)

print(f"Total pages: {len(pages)}")

for page in pages[:3]:
    print("\n--- PAGE", page["page_number"], "---")
    print(page["text"][:1000])