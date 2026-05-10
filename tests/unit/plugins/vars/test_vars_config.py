import os
import unittest
import tempfile
import shutil
from unittest.mock import MagicMock, patch

from ansible.inventory.group import InventoryObjectType
from ansible.errors import AnsibleParserError
from plugins.vars.vars_config import VarsModule

class MockEntity:
    def __init__(self, name, base_type):
        self.name = name
        self.base_type = base_type

class TestVarsConfig(unittest.TestCase):
    def setUp(self):
        self.vars_plugin = VarsModule()
        # Mock set_options/get_option behavior
        self.vars_plugin._options = {}
        self.vars_plugin.get_option = MagicMock(side_effect=lambda x: self.vars_plugin._options.get(x))
        self.vars_plugin.set_options = MagicMock()
        # Mock display
        self.vars_plugin._display = MagicMock()

        self.loader = MagicMock()
        self.loader.load_from_file.return_value = {}
        self.loader.find_vars_files.return_value = []

        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_get_vars_no_paths(self):
        # Test with no paths configured
        self.vars_plugin._options = {
            'group_vars_path': None,
            'host_vars_path': None
        }
        host = MockEntity('test_host', InventoryObjectType.HOST)
        results = self.vars_plugin.get_vars(self.loader, '/some/path', host)
        self.assertEqual(results, {})

    def test_get_vars_group_vars(self):
        group_vars_dir = os.path.join(self.test_dir, "my_group_vars")
        os.mkdir(group_vars_dir)
        var_file = os.path.join(group_vars_dir, "all.yml")
        with open(var_file, 'w') as f:
            f.write("foo: bar")

        self.vars_plugin._options = {
            'group_vars_path': group_vars_dir,
            'host_vars_path': None
        }
        
        group = MockEntity('all', InventoryObjectType.GROUP)
        
        self.loader.find_vars_files.return_value = [var_file]
        self.loader.load_from_file.return_value = {'foo': 'bar'}
        
        results = self.vars_plugin.get_vars(self.loader, '/some/path', group)
        
        self.assertEqual(results, {'foo': 'bar'})
        self.loader.find_vars_files.assert_called_once_with(os.path.realpath(group_vars_dir), 'all')
        self.loader.load_from_file.assert_called_once_with(
            var_file,
            cache="all",
            unsafe=True,
            trusted_as_template=True,
        )

    def test_get_vars_host_vars(self):
        host_vars_dir = os.path.join(self.test_dir, "my_host_vars")
        os.mkdir(host_vars_dir)
        var_file = os.path.join(host_vars_dir, "web.yml")
        with open(var_file, 'w') as f:
            f.write("ansible_port: 2222")

        self.vars_plugin._options = {
            'group_vars_path': None,
            'host_vars_path': host_vars_dir
        }
        
        host = MockEntity('web', InventoryObjectType.HOST)
        
        self.loader.find_vars_files.return_value = [var_file]
        self.loader.load_from_file.return_value = {'ansible_port': 2222}
        
        results = self.vars_plugin.get_vars(self.loader, '/some/path', host)
        
        self.assertEqual(results, {'ansible_port': 2222})
        self.loader.find_vars_files.assert_called_once_with(os.path.realpath(host_vars_dir), 'web')

    def test_get_vars_invalid_entity(self):
        self.vars_plugin._options = {
            'group_vars_path': '/tmp',
            'host_vars_path': '/tmp'
        }
        
        invalid_entity = object()
        with self.assertRaisesRegex(AnsibleParserError, "Supplied entity must be Host or Group"):
            self.vars_plugin.get_vars(self.loader, '/some/path', invalid_entity)

    def test_get_vars_path_not_dir(self):
        not_a_dir = os.path.join(self.test_dir, "not_a_dir")
        with open(not_a_dir, 'w') as f:
            f.write("I am a file")
        
        self.vars_plugin._options = {
            'group_vars_path': not_a_dir,
            'host_vars_path': None
        }
        
        group = MockEntity('all', InventoryObjectType.GROUP)
        
        # We need to clear FOUND and NAK because they are global and might be populated by other tests
        from plugins.vars import vars_config
        vars_config.FOUND = {}
        vars_config.NAK = set()

        results = self.vars_plugin.get_vars(self.loader, '/some/path', group)
        
        self.assertEqual(results, {})
        self.vars_plugin._display.warning.assert_called_once()
        self.assertIn(os.path.realpath(not_a_dir), vars_config.NAK)

    def test_get_vars_caching(self):
        group_vars_dir = os.path.join(self.test_dir, "cached_vars")
        os.mkdir(group_vars_dir)
        
        self.vars_plugin._options = {
            'group_vars_path': group_vars_dir,
            'host_vars_path': None
        }
        
        group = MockEntity('all', InventoryObjectType.GROUP)
        
        from plugins.vars import vars_config
        vars_config.FOUND = {}
        vars_config.NAK = set()

        self.loader.find_vars_files.return_value = ['/path/to/var_file.yml']
        self.loader.load_from_file.return_value = {'cached': True}
        
        # First call
        self.vars_plugin.get_vars(self.loader, '/some/path', group)
        self.assertEqual(self.loader.find_vars_files.call_count, 1)
        
        # Second call - should use FOUND cache
        self.loader.find_vars_files.reset_mock()
        self.vars_plugin.get_vars(self.loader, '/some/path', group)
        self.assertEqual(self.loader.find_vars_files.call_count, 0)
