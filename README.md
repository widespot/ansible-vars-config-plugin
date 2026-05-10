# Ansible Vars Config Plugin

This Ansible collection provides a vars plugin called `vars_config` that allows you to load `group_vars` and `host_vars` from custom absolute or relative paths defined in your `ansible.cfg`.

## Description

By default, Ansible looks for `group_vars` and `host_vars` in the same directory as the inventory file or the playbook. 
This plugin extends that behavior by allowing you to specify absolute or relative paths for these variables. 
This is particularly useful in complex environments where variable management is centralized or decoupled from the inventory structure.

## Installation

### From Source

1. Clone this repository:
   ```bash
   git clone https://github.com/widespot/ansible-vars-config-plugin.git
   ```

2. Build and install the collection:
   ```bash
   ansible-galaxy collection build
   ansible-galaxy collection install widespot-vars_config-0.1.0.tar.gz
   ```

## Configuration

To use the plugin, you need to enable it and configure the paths in your `ansible.cfg` file.

```ini
[defaults]
vars_plugins_enabled = host_group_vars, widespot.vars_config.vars_config

[vars_config]
group_vars_path = /path/to/your/custom/group_vars
host_vars_path = /path/to/your/custom/host_vars
```

### Options

| Option            | Description                                                            | INI Section   | INI Key           | Type |
|-------------------|------------------------------------------------------------------------|---------------|-------------------|------|
| `group_vars_path` | Absolute or relative path to the directory containing group variables. | `vars_config` | `group_vars_path` | path |
| `host_vars_path`  | Absolute or relative path to the directory containing host variables.  | `vars_config` | `host_vars_path`  | path |

## Usage

Once configured, Ansible will automatically use the `vars_config` plugin to load variables from the specified paths whenever it processes hosts or groups.

The plugin follows standard Ansible variable loading rules:
- It searches for files matching the entity name (e.g., `all.yml`, `webservers.yml`) within the configured directories.
- It supports both files and directories (where all files inside the directory are loaded).

## Development and Testing

### Requirements

- [Poetry](https://python-poetry.org/)
- `ansible-core`

### Running Tests

#### Unit Tests

You can install dependencies and run the unit tests using `poetry`:

```bash
poetry install
poetry run python3 tests/unit/plugins/vars/test_vars_config.py
```

#### Integration Tests

The integration tests run a sample Ansible playbook that uses the `vars_config` plugin.

```bash
# Run the integration test
ANSIBLE_CONFIG=tests/integration/ansible.cfg ansible-playbook tests/integration/playbooks/verify.yml
cd tests/integration
ANSIBLE_CONFIG=ansible.cfg ansible-playbook playbooks/verify.yml
```
