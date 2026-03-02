import argparse
import os
import sys
from src.docx_processor import DocxProcessor
from src.pdf_processor import PdfProcessor

# Configuração de diretórios
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, 'Original')
OUTPUT_DIR = os.path.join(BASE_DIR, 'Traduzido')

def ensure_directories():
    if not os.path.exists(INPUT_DIR):
        os.makedirs(INPUT_DIR)
        print(f"Diretório criado: {INPUT_DIR}")
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Diretório criado: {OUTPUT_DIR}")

def process_file(filename):
    input_path = os.path.join(INPUT_DIR, filename)
    
    if not os.path.exists(input_path):
        print(f"Erro: Arquivo não encontrado em {INPUT_DIR}: {filename}")
        return False
        
    # Define o caminho de saída
    base_name = os.path.splitext(filename)[0]
    output_filename = f"{base_name}_pt.docx"
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    
    print(f"\n--- Processando: {filename} ---")
    print(f"Entrada: {input_path}")
    print(f"Saída: {output_path}")
    
    try:
        _, ext = os.path.splitext(input_path)
        if ext.lower() == '.pdf':
            processor = PdfProcessor(input_path, output_path)
        else:
            processor = DocxProcessor(input_path, output_path)
            
        processor.process()
        print(f"Sucesso! Arquivo salvo em: {output_path}")
        return True
    except Exception as e:
        print(f"Erro ao processar {filename}: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    ensure_directories()
    
    parser = argparse.ArgumentParser(description="Tradutor de DOCX usando IA.")
    parser.add_argument("filename", nargs="?", help="Nome do arquivo na pasta 'Original' (opcional)")
    parser.add_argument("--all", "-a", action="store_true", help="Processar todos os arquivos da pasta 'Original'")
    
    args = parser.parse_args()
    
    if args.all:
        files = [f for f in os.listdir(INPUT_DIR) if (f.lower().endswith('.docx') or f.lower().endswith('.pdf')) and not f.startswith('~$')]
        if not files:
            print(f"Nenhum arquivo .docx ou .pdf encontrado em {INPUT_DIR}")
            return
            
        print(f"Encontrados {len(files)} arquivos para processar.")
        success_count = 0
        for f in files:
            if process_file(f):
                success_count += 1
        
        print(f"\nConcluído! {success_count}/{len(files)} arquivos processados com sucesso.")
        
    elif args.filename:
        process_file(args.filename)
    else:
        # Se nenhum argumento for passado, lista os arquivos disponíveis ou sugere o uso
        files = [f for f in os.listdir(INPUT_DIR) if (f.lower().endswith('.docx') or f.lower().endswith('.pdf')) and not f.startswith('~$')]
        if not files:
            print(f"A pasta '{INPUT_DIR}' está vazia ou não contém arquivos .docx/.pdf.")
            print("Coloque seus arquivos lá e execute novamente.")
        else:
            print(f"Arquivos disponíveis em '{INPUT_DIR}':")
            for f in files:
                print(f" - {f}")
            print("\nUso:")
            print("  python translate_docx.py <nome_do_arquivo.docx>")
            print("  python translate_docx.py --all")

if __name__ == "__main__":
    main()
