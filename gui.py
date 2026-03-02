import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import os
import threading
import shutil
import queue
from src.docx_processor import DocxProcessor
from src.pdf_processor import PdfProcessor

class TranslatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Tradutor DOCX AI")
        self.root.geometry("600x400")
        
        # Configure grid weight
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Main Frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.columnconfigure(1, weight=1)

        # Title
        title_label = ttk.Label(main_frame, text="Tradutor de Documentos (DOCX)", font=("Helvetica", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))

        # File Selection
        ttk.Label(main_frame, text="Arquivo:").grid(row=1, column=0, sticky="w")
        
        self.file_path_var = tk.StringVar()
        self.entry_file = ttk.Entry(main_frame, textvariable=self.file_path_var, state="readonly")
        self.entry_file.grid(row=1, column=1, sticky="ew", padx=10)
        
        self.btn_select = ttk.Button(main_frame, text="Selecionar", command=self.select_file)
        self.btn_select.grid(row=1, column=2)

        # Action Button
        self.btn_translate = ttk.Button(main_frame, text="Iniciar Tradução", command=self.start_translation, state="disabled")
        self.btn_translate.grid(row=2, column=0, columnspan=3, pady=20)

        # Progress Area
        self.progress_frame = ttk.LabelFrame(main_frame, text="Progresso", padding="10")
        self.progress_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=10)
        self.progress_frame.columnconfigure(0, weight=1)
        
        self.progress_bar = ttk.Progressbar(self.progress_frame, orient="horizontal", mode="determinate")
        self.progress_bar.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        
        self.status_var = tk.StringVar(value="Aguardando início...")
        self.lbl_status = ttk.Label(self.progress_frame, textvariable=self.status_var)
        self.lbl_status.grid(row=1, column=0, sticky="w")

        # Result Area (Initially Hidden or Disabled)
        self.result_frame = ttk.Frame(main_frame, padding="10")
        self.result_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=10)
        
        self.btn_save_copy = ttk.Button(self.result_frame, text="Salvar Cópia em Outro Local", command=self.save_copy, state="disabled")
        self.btn_save_copy.pack()
        
        self.lbl_result_path = ttk.Label(self.result_frame, text="", font=("Helvetica", 9, "italic"), foreground="gray")
        self.lbl_result_path.pack(pady=5)

        # Internal State
        self.selected_file = None
        self.output_file = None
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.output_dir = os.path.join(self.base_dir, 'Traduzido')
        
        # Ensure output directory exists
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            
        # UI Queue for thread-safe updates
        self.gui_queue = queue.Queue()
        self.root.after(100, self.check_queue)

    def select_file(self):
        filetypes = (("Word Documents", "*.docx"), ("PDF Files", "*.pdf"), ("All files", "*.*"))
        filename = filedialog.askopenfilename(title="Selecione o arquivo DOCX ou PDF", filetypes=filetypes)
        if filename:
            self.selected_file = filename
            self.file_path_var.set(filename)
            self.btn_translate.config(state="normal")
            self.status_var.set("Arquivo selecionado. Pronto para traduzir.")
            self.progress_bar["value"] = 0
            self.btn_save_copy.config(state="disabled")
            self.lbl_result_path.config(text="")

    def start_translation(self):
        if not self.selected_file:
            return
        
        self.btn_translate.config(state="disabled")
        self.btn_select.config(state="disabled")
        self.status_var.set("Iniciando tradução...")
        self.progress_bar["value"] = 0
        
        # Prepare output path
        base_name = os.path.splitext(os.path.basename(self.selected_file))[0]
        output_filename = f"{base_name}_pt.docx"
        self.output_file = os.path.join(self.output_dir, output_filename)
        
        # Start thread
        thread = threading.Thread(target=self.run_translation)
        thread.start()

    def check_queue(self):
        try:
            while True:
                msg = self.gui_queue.get_nowait()
                if msg['type'] == 'progress':
                    self._update_progress_ui(msg['percentage'], msg['current'], msg['total'], msg.get('prefix', 'Traduzindo'))
                elif msg['type'] == 'complete':
                    self.translation_complete(msg['success'], msg.get('error_msg'), msg.get('output_file'))
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.check_queue)

    def run_translation(self):
        try:
            # Check file extension
            _, ext = os.path.splitext(self.selected_file)
            ext = ext.lower()
            
            if ext == '.pdf':
                # For PDF, output is still DOCX (translated)
                # Ensure output file has .docx extension
                if not self.output_file.endswith('.docx'):
                    self.output_file = os.path.splitext(self.output_file)[0] + '.docx'
                    
                processor = PdfProcessor(self.selected_file, self.output_file, progress_callback=self.update_progress)
            else:
                processor = DocxProcessor(self.selected_file, self.output_file, progress_callback=self.update_progress)
                
            processor.process()
            
            # Success
            self.gui_queue.put({'type': 'complete', 'success': True, 'output_file': self.output_file})
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            self.gui_queue.put({'type': 'complete', 'success': False, 'error_msg': str(e)})

    def update_progress(self, current, total, status_text="Traduzindo"):
        # Calculate percentage
        if total > 0:
            percentage = (current / total) * 100
        else:
            percentage = 0
            
        # Schedule UI update
        self.gui_queue.put({'type': 'progress', 'percentage': percentage, 'current': current, 'total': total, 'prefix': status_text})

    def _update_progress_ui(self, percentage, current, total, prefix="Traduzindo"):
        self.progress_bar["value"] = percentage
        self.status_var.set(f"{prefix}: {int(percentage)}% ({current}/{total})")

    def translation_complete(self, success, error_msg=None, output_file=None):
        self.btn_translate.config(state="normal")
        self.btn_select.config(state="normal")
        
        if success:
            self.status_var.set("Tradução Concluída com Sucesso!")
            self.progress_bar["value"] = 100
            self.btn_save_copy.config(state="normal")
            if output_file:
                self.output_file = output_file
            self.lbl_result_path.config(text=f"Salvo em: {self.output_file}")
            messagebox.showinfo("Sucesso", f"Arquivo traduzido com sucesso!\nSalvo em: {self.output_file}")
        else:
            self.status_var.set("Erro na tradução.")
            messagebox.showerror("Erro", f"Ocorreu um erro durante a tradução:\n{error_msg}")

    def save_copy(self):
        if not self.output_file or not os.path.exists(self.output_file):
            return
            
        initial_file = os.path.basename(self.output_file)
        dest_path = filedialog.asksaveasfilename(
            defaultextension=".docx",
            filetypes=(("Word Documents", "*.docx"),),
            initialfile=initial_file,
            title="Salvar Cópia Como"
        )
        
        if dest_path:
            try:
                shutil.copy2(self.output_file, dest_path)
                messagebox.showinfo("Salvo", f"Cópia salva em:\n{dest_path}")
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível salvar a cópia:\n{e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = TranslatorApp(root)
    root.mainloop()
