from __future__ import annotations

import os

from ansible.errors import AnsibleError, AnsibleParserError
from ansible.inventory.group import InventoryObjectType
from ansible.module_utils.common.text.converters import to_native
from ansible.plugins.vars import BaseVarsPlugin
from ansible.utils.vars import combine_vars


DOCUMENTATION = r"""
name: custom_host_group_vars
version_added: "1.0"
short_description: Load group_vars and host_vars from configured absolute paths
description:
  - Loads group and host vars from paths configured in ansible.cfg.
options:
  group_vars_path:
    description:
      - Absolute path to group vars directory.
    ini:
      - section: vars_custom_host_group_vars
        key: group_vars_path
    type: path
  host_vars_path:
    description:
      - Absolute path to host vars directory.
    ini:
      - section: vars_custom_host_group_vars
        key: host_vars_path
    type: path
  stage:
    ini:
      - section: vars_custom_host_group_vars
        key: stage
    env:
      - name: ANSIBLE_CUSTOM_HOST_GROUP_VARS_STAGE
extends_documentation_fragment:
  - vars_plugin_staging
"""


FOUND = {}
NAK = set()


class VarsModule(BaseVarsPlugin):
    REQUIRES_ENABLED = True
    is_stateless = True

    def load_found_files(self, loader, data, found_files):
        for found in found_files:
            new_data = loader.load_from_file(
                found,
                cache="all",
                unsafe=True,
                trusted_as_template=True,
            )
            if new_data:
                try:
                    data = combine_vars(data, new_data)
                except AnsibleError as e:
                    raise AnsibleParserError(f"Could not process {found!r}.") from e
        return data

    def get_vars(self, loader, path, entities, cache=True):
        super().get_vars(loader, path, entities)

        if not isinstance(entities, list):
            entities = [entities]

        group_vars_path = self.get_option("group_vars_path")
        host_vars_path = self.get_option("host_vars_path")

        data = {}

        for entity in entities:
            try:
                entity_name = entity.name
                entity_type = entity.base_type
            except AttributeError:
                raise AnsibleParserError(
                    f"Supplied entity must be Host or Group, got {type(entity)} instead"
                )

            try:
                first_char = entity_name[0]
            except (TypeError, IndexError, KeyError):
                raise AnsibleParserError(
                    f"Supplied entity must be Host or Group, got {type(entity)} instead"
                )

            # Match upstream behavior: skip hostnames that look like absolute paths.
            if first_char == os.path.sep:
                continue

            if entity_type is InventoryObjectType.HOST:
                opath = host_vars_path
                subdir = "host_vars"
            elif entity_type is InventoryObjectType.GROUP:
                opath = group_vars_path
                subdir = "group_vars"
            else:
                raise AnsibleParserError(
                    f"Supplied entity must be Host or Group, got {type(entity)} instead"
                )

            if not opath:
                continue

            opath = os.path.realpath(os.path.expanduser(opath))
            key = f"{entity_name}.{opath}"

            try:
                found_files = []

                if cache:
                    if opath in NAK:
                        continue

                    if key in FOUND:
                        data = self.load_found_files(loader, data, FOUND[key])
                        continue

                if os.path.isdir(opath):
                    FOUND[key] = found_files = loader.find_vars_files(opath, entity_name)
                elif not os.path.exists(opath):
                    NAK.add(opath)
                else:
                    self._display.warning(
                        f"Found {subdir} path that is not a directory, skipping: {opath}"
                    )
                    NAK.add(opath)

                data = self.load_found_files(loader, data, found_files)

            except Exception as e:
                raise AnsibleParserError(to_native(e))

        return data