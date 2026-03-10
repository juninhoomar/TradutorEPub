
import os
import uuid
import threading
import traceback
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from src.docx_processor import DocxProcessor
from src.pdf_processor import PdfProcessor
from src.task_manager import TaskManager
from src.underline_remover import UnderlineRemover

app = Flask(__name__)

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
TRANSLATED_FOLDER = os.path.join(BASE_DIR, 'translated')
ALLOWED_EXTENSIONS = {'docx', 'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['TRANSLATED_FOLDER'] = TRANSLATED_FOLDER

# Ensure directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TRANSLATED_FOLDER, exist_ok=True)

# Task Manager for persistence
task_manager = TaskManager(os.path.join(BASE_DIR, 'tasks.json'))

def check_stale_tasks():
    """Verifica tarefas interrompidas e atualiza status baseando-se no arquivo de saída."""
    print("Verificando tarefas pendentes...")
    tasks = task_manager.get_all_tasks()
    for task_id, task in tasks.items():
        if not task.get('completed') and not task.get('error'):
            # Reconstruct path
            # filename stored in task is the original filename, but we need the output filename
            # The logic in upload_file:
            # unique_output_filename = f"{file_id}_{output_filename_user}"
            # output_filename_user = f"{base_name}_pt.docx"
            
            # This is tricky because we didn't store the exact output path in the task data explicitly in a way we can easily reconstruct without logic duplication.
            # But we can reconstruct it.
            
            original_filename = task.get('original_filename')
            if original_filename:
                base_name = os.path.splitext(original_filename)[0]
                output_filename_user = f"{base_name}_pt.docx"
                internal_filename = f"{task_id}_{output_filename_user}"
                output_path = os.path.join(app.config['TRANSLATED_FOLDER'], internal_filename)
                
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    print(f"[{task_id}] Tarefa recuperada: arquivo encontrado.")
                    task_manager.update_task(task_id, {
                        'status': 'Concluído (Recuperado)',
                        'percentage': 100,
                        'completed': True
                    })
                else:
                    print(f"[{task_id}] Tarefa marcada como erro: arquivo não encontrado após reinício.")
                    task_manager.update_task(task_id, {
                        'status': 'Erro: Processamento interrompido pelo servidor',
                        'error': True
                    })

# Run check on startup
check_stale_tasks()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_file_background(task_id, input_path, output_path):
    def progress_callback(current, total, status_text):
        task = task_manager.get_task(task_id)
        if task:
            updates = {
                'current': current,
                'total': total,
                'status': status_text
            }
            if total > 0:
                updates['percentage'] = int((current / total) * 100)
            task_manager.update_task(task_id, updates)

    try:
        task_manager.update_task(task_id, {'status': 'Iniciando processamento...'})
        print(f"[{task_id}] Iniciando processamento de {input_path}")
        
        # Check if input is PDF
        _, ext = os.path.splitext(input_path)
        if ext.lower() == '.pdf':
             # Ensure output path is .docx
             if not output_path.endswith('.docx'):
                 output_path = os.path.splitext(output_path)[0] + '.docx'
             processor = PdfProcessor(input_path, output_path, progress_callback=progress_callback)
        else:
             processor = DocxProcessor(input_path, output_path, progress_callback=progress_callback)
        
        processor.process()
        
        print(f"[{task_id}] Processamento concluído. Salvando em {output_path}")
        
        # Verify file exists
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"[{task_id}] Arquivo salvo com sucesso. Tamanho: {file_size} bytes")
            task_manager.update_task(task_id, {
                'status': 'Concluído',
                'percentage': 100,
                'completed': True
            })
        else:
            raise FileNotFoundError(f"Arquivo de saída não encontrado em {output_path}")

    except Exception as e:
        error_msg = str(e)
        print(f"Error processing task {task_id}: {error_msg}")
        traceback.print_exc()
        task_manager.update_task(task_id, {
            'status': f'Erro: {error_msg}',
            'error': True
        })

def process_underline_removal_background(task_id, input_path, output_path):
    try:
        task_manager.update_task(task_id, {'status': 'Iniciando remoção de sublinhados...'})
        print(f"[{task_id}] Iniciando remoção de sublinhados em {input_path}")
        
        processor = UnderlineRemover(input_path, output_path)
        processor.process()
        
        print(f"[{task_id}] Processamento concluído. Salvando em {output_path}")
        
        # Verify file exists
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"[{task_id}] Arquivo salvo com sucesso. Tamanho: {file_size} bytes")
            task_manager.update_task(task_id, {
                'status': 'Concluído',
                'percentage': 100,
                'completed': True
            })
        else:
            raise FileNotFoundError(f"Arquivo de saída não encontrado em {output_path}")

    except Exception as e:
        error_msg = str(e)
        print(f"Error processing task {task_id}: {error_msg}")
        traceback.print_exc()
        task_manager.update_task(task_id, {
            'status': f'Erro: {error_msg}',
            'error': True
        })

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'Nenhum arquivo selecionado'}), 400
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_id = str(uuid.uuid4())
        
        # Save input file
        unique_input_filename = f"{file_id}_{filename}"
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_input_filename)
        file.save(input_path)
        
        # Prepare output file
        base_name = os.path.splitext(filename)[0]
        output_filename_user = f"{base_name}_pt.docx"
        unique_output_filename = f"{file_id}_{output_filename_user}"
        output_path = os.path.join(app.config['TRANSLATED_FOLDER'], unique_output_filename)
        
        # Initialize task
        task_id = file_id
        task_data = {
            'id': task_id,
            'original_filename': filename,
            'status': 'Aguardando',
            'percentage': 0,
            'current': 0,
            'total': 0,
            'completed': False,
            'error': False,
            'download_url': f"/download/{task_id}/{output_filename_user}",
            'created_at': str(uuid.uuid1()) # Timestamp info
        }
        task_manager.add_task(task_id, task_data)
        
        # Start background thread
        thread = threading.Thread(target=process_file_background, args=(task_id, input_path, output_path))
        thread.start()
        
        return jsonify({'task_id': task_id})
    
    return jsonify({'error': 'Tipo de arquivo não permitido'}), 400

@app.route('/upload_remove_underline', methods=['POST'])
def upload_remove_underline():
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'Nenhum arquivo selecionado'}), 400
        
    if file and allowed_file(file.filename):
        # We only support docx for this action
        if not file.filename.lower().endswith('.docx'):
             return jsonify({'error': 'Apenas arquivos .docx são suportados para esta ação'}), 400
             
        filename = secure_filename(file.filename)
        file_id = str(uuid.uuid4())
        
        # Save input file
        unique_input_filename = f"{file_id}_{filename}"
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_input_filename)
        file.save(input_path)
        
        # Prepare output file
        base_name = os.path.splitext(filename)[0]
        output_filename_user = f"{base_name}_sem_sublinhado.docx"
        unique_output_filename = f"{file_id}_{output_filename_user}"
        output_path = os.path.join(app.config['TRANSLATED_FOLDER'], unique_output_filename)
        
        # Initialize task
        task_id = file_id
        task_data = {
            'id': task_id,
            'original_filename': filename,
            'status': 'Aguardando',
            'percentage': 0,
            'current': 0,
            'total': 0,
            'completed': False,
            'error': False,
            'download_url': f"/download/{task_id}/{output_filename_user}",
            'created_at': str(uuid.uuid1())
        }
        task_manager.add_task(task_id, task_data)
        
        # Start background thread
        thread = threading.Thread(target=process_underline_removal_background, args=(task_id, input_path, output_path))
        thread.start()
        
        return jsonify({'task_id': task_id})
    
    return jsonify({'error': 'Tipo de arquivo não permitido'}), 400

@app.route('/status/<task_id>')
def get_status(task_id):
    task = task_manager.get_task(task_id)
    if task:
        return jsonify(task)
    return jsonify({'error': 'Tarefa não encontrada'}), 404

@app.route('/download/<task_id>/<filename>')
def download_file(task_id, filename):
    # Check if task exists in manager
    task = task_manager.get_task(task_id)
    
    # Reconstruct internal filename based on ID and requested filename
    # This is important: filename in URL is the "pretty" name, but on disk it has the UUID prefix
    internal_filename = f"{task_id}_{filename}"
    file_path = os.path.join(app.config['TRANSLATED_FOLDER'], internal_filename)
    
    # Check if file exists physically
    if os.path.exists(file_path):
        return send_from_directory(
            app.config['TRANSLATED_FOLDER'], 
            internal_filename, 
            as_attachment=True, 
            download_name=filename
        )
    
    # If file not found, check task status for error details
    if task:
        if task.get('error'):
            return jsonify({'error': f"A tradução falhou: {task.get('status')}"}), 404
        if not task.get('completed'):
            return jsonify({'error': 'Arquivo ainda está sendo processado'}), 404
            
    return jsonify({'error': 'Arquivo não encontrado'}), 404

if __name__ == '__main__':
    # Use 0.0.0.0 and PORT env variable to make it accessible in Docker/Coolify natively
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
