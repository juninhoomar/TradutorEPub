import os
from pdf2docx import Converter
from src.docx_processor import DocxProcessor

class PdfProcessor:
    def __init__(self, input_file, output_file, progress_callback=None):
        self.input_file = input_file
        self.output_file = output_file
        self.progress_callback = progress_callback
        
        # Determine intermediate DOCX path
        base, _ = os.path.splitext(output_file)
        self.temp_docx = f"{base}_temp.docx"

    def process(self):
        """
        Converts PDF to DOCX, then translates the DOCX.
        """
        try:
            print(f"Converting PDF to DOCX: {self.input_file}")
            if self.progress_callback:
                self.progress_callback(0, 100, "Convertendo PDF para DOCX...")

            # Convert PDF to DOCX
            cv = Converter(self.input_file)
            # We can't easily hook into pdf2docx progress, but it's usually fast for small files.
            # For large files, it might hang a bit.
            cv.convert(self.temp_docx, start=0, end=None)
            cv.close()
            
            if self.progress_callback:
                self.progress_callback(10, 100, "PDF convertido. Iniciando tradução...")

            # Now translate the DOCX
            # We use the existing DocxProcessor, but we need to wrap its progress callback
            # to map it to our remaining percentage (10% to 100%)
            
            def wrapped_progress(current, total, status):
                # Map 0-100% of translation to 10-100% of total process
                if total > 0:
                    percentage = 10 + (current / total) * 90
                    if self.progress_callback:
                        self.progress_callback(int(percentage), 100, f"Traduzindo: {status}")

            processor = DocxProcessor(self.temp_docx, self.output_file, progress_callback=wrapped_progress)
            processor.process()

            print(f"Translation completed: {self.output_file}")
            
        finally:
            # Clean up temporary file
            if os.path.exists(self.temp_docx):
                try:
                    os.remove(self.temp_docx)
                except Exception as e:
                    print(f"Warning: Could not remove temp file {self.temp_docx}: {e}")
