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


import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app import storage

class StorageSafetyTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.patch = patch.object(storage, 'DATA_DIR', Path(self.directory.name))
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def test_snapshot_can_be_read_by_another_process(self):
        import subprocess, sys, os, json
        storage.write_json('snapshots/example.json', {'brief': 'complete'})
        env = {**os.environ, 'DATA_DIR': self.directory.name}
        output = subprocess.check_output([sys.executable, '-c',
            "from app.storage import read_json; import json; print(json.dumps(read_json('snapshots/example.json')))"], env=env)
        self.assertEqual(json.loads(output), {'brief': 'complete'})

    def test_paths_cannot_escape_data_directory(self):
        for path in ('../secret.json', '/tmp/secret.json', 'snapshots/../../secret.json'):
            with self.assertRaises(ValueError):
                storage.read_json(path)
            with self.assertRaises(ValueError):
                storage.write_json(path, {})

    def test_list_ignores_broken_files_and_replaces_snapshots(self):
        storage.write_json('metrics/one.json', {'version': 1})
        storage.write_json('metrics/one.json', {'version': 2})
        (storage.DATA_DIR / 'metrics/bad.json').write_text('{')
        self.assertEqual(storage.list_json('metrics'), [{'version': 2}])
        self.assertEqual(list((storage.DATA_DIR / 'metrics').glob('tmp*')), [])

if __name__ == '__main__':
    unittest.main()
