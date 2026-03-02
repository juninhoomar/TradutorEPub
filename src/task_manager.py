
import json
import os
import threading

class TaskManager:
    def __init__(self, data_file='tasks.json'):
        self.data_file = data_file
        self.tasks = {}
        self.lock = threading.RLock()
        self.load()

    def load(self):
        """Carrega as tarefas do arquivo JSON."""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    self.tasks = json.load(f)
            except (json.JSONDecodeError, IOError):
                self.tasks = {}
        else:
            self.tasks = {}

    def save(self):
        """Salva as tarefas no arquivo JSON."""
        with self.lock:
            try:
                with open(self.data_file, 'w', encoding='utf-8') as f:
                    json.dump(self.tasks, f, indent=4, ensure_ascii=False)
            except IOError as e:
                print(f"Erro ao salvar tarefas: {e}")

    def add_task(self, task_id, data):
        """Adiciona ou atualiza uma tarefa."""
        with self.lock:
            self.tasks[task_id] = data
        self.save()

    def update_task(self, task_id, updates):
        """Atualiza campos específicos de uma tarefa."""
        with self.lock:
            if task_id in self.tasks:
                self.tasks[task_id].update(updates)
                self.save()
                return True
            return False

    def get_task(self, task_id):
        """Retorna os dados de uma tarefa."""
        with self.lock:
            return self.tasks.get(task_id)

    def get_all_tasks(self):
        """Retorna todas as tarefas."""
        with self.lock:
            return self.tasks.copy()
