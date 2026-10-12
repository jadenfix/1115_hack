import importlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

class StorageTests(unittest.TestCase):
    def test_worker_output_visible_to_api_process(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'DATA_DIR': directory}):
            from app import storage
            importlib.reload(storage)
            storage.write_json('snapshots/one.json', {'snapshot_id': 'one'})
            self.assertTrue((Path(directory) / 'snapshots/one.json').exists())
            output = subprocess.check_output([sys.executable, '-c', "from app import storage; print(storage.read_json('snapshots/one.json')['snapshot_id'])"], text=True)
            self.assertEqual(output.strip(), 'one')
            from app import agent_wall
            importlib.reload(agent_wall)
            self.assertEqual(agent_wall.DATA_ROOT, storage.DATA_DIR)
