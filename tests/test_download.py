
import unittest
import os
import json
import shutil
import tempfile
from src.task_manager import TaskManager
from web_app import app, task_manager

class TestDownload(unittest.TestCase):
    def setUp(self):
        # Configurar ambiente de teste
        self.test_dir = tempfile.mkdtemp()
        app.config['TRANSLATED_FOLDER'] = self.test_dir
        app.config['TESTING'] = True
        self.client = app.test_client()
        
        # Reset task manager with a test file
        self.task_file = os.path.join(self.test_dir, 'test_tasks.json')
        task_manager.data_file = self.task_file
        task_manager.tasks = {}
        task_manager.save()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_download_existing_file_with_task(self):
        # 1. Create task
        task_id = 'task-123'
        filename = 'test_pt.docx'
        internal_filename = f"{task_id}_{filename}"
        
        task_manager.add_task(task_id, {
            'id': task_id,
            'completed': True,
            'status': 'Concluído'
        })
        
        # 2. Create physical file
        file_path = os.path.join(self.test_dir, internal_filename)
        with open(file_path, 'w') as f:
            f.write("Test content")
            
        # 3. Request download
        response = self.client.get(f'/download/{task_id}/{filename}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Content-Disposition'], f'attachment; filename={filename}')

    def test_download_existing_file_without_task(self):
        # 1. Simulate server restart (empty task manager)
        task_manager.tasks = {}
        task_manager.save()
        
        # 2. Create physical file anyway
        task_id = 'task-456'
        filename = 'orphan_pt.docx'
        internal_filename = f"{task_id}_{filename}"
        
        file_path = os.path.join(self.test_dir, internal_filename)
        with open(file_path, 'w') as f:
            f.write("Orphan content")
            
        # 3. Request download - Should work because file exists!
        response = self.client.get(f'/download/{task_id}/{filename}')
        self.assertEqual(response.status_code, 200)

    def test_download_missing_file(self):
        response = self.client.get('/download/invalid-id/missing.docx')
        self.assertEqual(response.status_code, 404)

if __name__ == '__main__':
    unittest.main()
