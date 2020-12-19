from core.simple_logging import vprint, eprint, exprint
from core.eval_sandbox import evaluate

import yaml
import os
import copy
import re
import pprint


class Scheme:
    """
    Class for object to load and hold scheme description from YAML file or YAML string
    Besides loading provides string values extrapolation with generics and python expressions
    TODO: support loading fragments from other files (include and import)
    """

    def __init__(self, description, root_section=None, generics=None, verbose=False, extrapolate=True, specials=None):
        self.name = "__root__"
        self._data = {}
        self._extrapolation_counter = 0
        self._extrapolation_chain = []
        self._extrapolated_values = {}
        self._sch_data = None
        self._root_section = root_section
        if specials is None:
            specials = []
        self._specials = tuple(["generics", "alias"] + specials)
        self._sch_structure = None
        self._sch_structure_extrapolated = None
        self.load_description(description, generics, verbose, extrapolate=extrapolate)

    @property
    def data(self):
        result = copy.deepcopy(self._data)

        def wipe_metadata(node):
            if '__metadata__' in node:
                del node['__metadata__']
            for n in node:
                if isinstance(n, (list, tuple)):
                    subnodes = n
                else:
                    subnodes = [n]
                for s in subnodes:
                    if isinstance(s, dict):
                        wipe_metadata(s)
        wipe_metadata(result)

        return result

    def load_description(self, description, generics, verbose, extrapolate=True):
        # TODO: include could be at any level
        # TODO: include in specials should contain name
        self._sch_data = None
        if os.path.isfile(description):
            if verbose:
                vprint("openning {}".format(description))
            with open(description, 'r') as stream:
                try:
                    desc = yaml.safe_load(stream)
                    if verbose:
                        vprint("loaded data: {}".format(desc))
                except yaml.YAMLError as exc:
                    eprint(exc)
                    desc = {}
        elif isinstance(description, str):
            description = re.sub(r"\\n", "\n", description)  # TODO: unescape slashes
            desc = yaml.safe_load(description)
        else:
            desc = copy.deepcopy(description)

        assert isinstance(desc, dict), "Expecting a dict as scheme description! Got {}".format(type(desc))

        if self._root_section is not None:
            assert self._root_section in desc, "Root section '{}' wasn't found in description".format(
                self._root_section)
            assert isinstance(desc[self._root_section],
                              (dict, list, tuple)), "Root section should be a dict, list or tuple! " \
                                                    "Got {}".format(type(desc[self._root_section]))
            desc = desc[self._root_section]

        if isinstance(desc, (list, tuple)):
            assert len(desc) == 1, "descriptions with more than 1 root section isn't supported yet!"
            desc = desc[0]
            # if "__metadata__" in desc:
            #     raise ValueError("'__metadata__' section shouldn't be in testenv description")
            # if "__nodes__" in desc:
            #     raise ValueError("'__nodes__' section shouldn't be in testenv description")
            # desc["__metadata__"] = {'name': None, 'description': None}
            # desc["__nodes__"] = []

        if "name" not in desc:
            raise ValueError("No scheme name found in description!")
        self._name = desc["name"]


        for s in self.specials:  # S is for SECTION
            if s in desc:
                assert isinstance(desc[s], dict), "Specials like {} should be a dict only! Got: {} for {}".format(
                    " ".join(self.specials), type(desc[s]), s)
                self._data[s] = copy.deepcopy(desc[s])
            else:
                self._data[s] = {}

        if generics is not None:
            for g in generics:
                if g not in self._data["generics"]:
                    raise ValueError("Generic {} is not in environment".format(g))
                else:
                    if generics[g] in ("True", "False"):
                        self._data["generics"][g] = generics[g] == "True"
                    else:
                        try:
                            self._data["generics"][g] = int(generics[g])
                        except Exception as e:
                            try:
                                self._data["generics"][g] = float(generics[g])
                            except Exception as e:
                                self._data["generics"][g] = generics[g]

        self._sch_data = desc
        errors = []

        _sch_structure = self._sch_to_structured(errors, "", self._sch_data, 'root', None, None)
        if len(errors) > 0:
            message = "Errors occurred during description parsing:\n"+"\n".join(errors)
            raise ValueError(message)
        assert len(_sch_structure) == 1, "Unexpectedly found multiple roots for scheme"
        self._sch_structure = _sch_structure[0]

        if extrapolate:
            self.extrapolate_description()

    def _sch_to_structured_include(self, errors, path, include_node, node, parent, group,
                                   named_only=False, name_allowed=True):
        include_list = self._sch_to_structured(errors, path, include_node, kind='include', parent=parent, group=group)
        for include in include_list:
            if 'name' in include:
                if not name_allowed:
                    errors.append("'name' field is not allowed for include {}".format(include['path']))
                    continue

                if len(include['name']) == 0:
                    errors.append("Include's {} 'name' field can't be empty!".format(include['path']))
                    continue

                if include['name'][0] == '_' and include['name'][-1] == '_':
                    errors.append("Include's {} 'name' field shouldn't start from '_' and end with '_':\n"
                                  "  Include's 'name' value: {}".format(include['path'], include['name']))
                    continue

                if include['name'] in node:
                    errors.append("Can't apply include '{}' to '{}' "
                                  "since field named '{}' is already there!\n"
                                  "  Include content: {}".format(include['path'], node['path'],
                                                                 include['name'], include))
                    continue

                node[include['name']] = include
                node['__metadata__']['values'][include['name']] = "$include({})".format(include['path'])
                if 'condition' in include:
                    node['__metadata__']['values'][include['name']] += "\n  if {}".format(include['condition'])
            else:
                if named_only:
                    errors.append("Include {} for {} should contain 'name' field!\n"
                                  "  Include content: {}".format(include['path'], node['path'], include))
                    continue
                node['__nodes__'].apppend(include)

    def _sch_to_structured(self, errors, path, sch_data, kind, parent, group, name=None):
        # TODO: check all necessary fields are set
        # TODO: check there is not unsupported fields in objects like testenv, generate, group, import and so on
        # TODO: convert fields to common type (for example those that can be scalar or list -> convert to list,
        #       those that should be numbers -> convert to numbers etc.)
        initial_path = path
        try:
            results = []
            if isinstance(sch_data, (list, tuple)):
                nodes = sch_data
            else:
                nodes = [sch_data]
            idx = -1
            initial_parent = parent
            initial_group = group
            platform_kind = None
            if kind == 'root':
                initial_path = ''
            elif kind == 'special':
                initial_path = path + '/' + kind + '/' + name
            elif kind[:9] == 'platform:':
                initial_path = path + '/' + kind[9:]
                platform_kind = kind[9:]
                kind = kind[:8]
            else:
                initial_path = path + '/' + kind
            for n in nodes:

                # Copy description since data would be removed as it's being processed
                node_data = copy.copy(n)

                ### Initiate context
                idx += 1
                parent = initial_parent
                group = initial_group
                if isinstance(sch_data, (list, tuple)):
                    path = initial_path + "_{}".format(idx)
                else:
                    path = initial_path

                # Initiate node
                result = {
                    '__nodes__': [],
                    '__metadata__': {'name': name, 'path': path, 'kind': kind, 'parent': parent, 'group': group,
                                     'values': {}, 'description': ""},
                }
                meta = result['__metadata__']
                nodes = result['__nodes__']

                if platform_kind is not None:
                    meta['platform_kind'] = platform_kind

                ### Get base kind depended properties:
                # Name
                if kind == 'root' or kind == 'platform':
                    meta['name'] = result['name'] = node_data.pop('name')
                elif name is not None:  # For specials' names
                    meta['name'] = name

                # Platform
                if kind in ('platform', 'group', 'import'):
                    if 'platform' in node_data:
                        if parent is not None:
                            errors.append("'platform' field shouldn't be specified for node {} since that node is"
                                          " already binded to parent platform by hierarchy".format(result['path']))
                            continue
                        meta['parent'] = result['platform'] = node_data.pop('platform')
                    else:
                        result['platform'] = parent

                # Parent and Platform kind
                if kind == 'platform':
                    parent = result['name']  # Also set parent if node is platform

                # Description
                if kind != 'special' and kind != 'platforms':
                    if 'description' in node_data:
                        meta['description'] = node_data.pop('description')

                # Group name for nested items
                if kind in ('generate', 'group'):
                    group = path

                ### Process specials in root
                if kind == 'root':
                    for s in self.specials:
                        if s in node_data:
                            nodes += \
                                self._sch_to_structured(errors, path, node_data[s],
                                                        kind='special', name=s, parent=None, group=None)
                            del node_data[s]

                ### Iterate through content
                for k in list(node_data.keys()):
                    v = node_data[k]
                    # Platforms section is iterated in the end as it contains only nested items
                    if kind == 'platforms':
                        break

                    # Drop confidential data
                    if kind in ('import', 'include') and k == 'options' \
                    or k[:6] == "secret":
                        node_data.pop(k)
                        continue

                    # Skip nested structures (would be processed later)
                    if kind in ('platform', 'root', 'generate', 'group') and k == 'platforms':
                        continue

                    # Skip include (would be processed later)
                    if k == 'include':
                        continue

                    # Store node's data
                    result[k] = v
                    meta['values'][k] = str(v)
                    del node_data[k]

                ### Process include
                if 'include' in node_data:
                    self._sch_to_structured_include(errors, path, node_data['include'], result,
                                                    parent=parent, group=group,
                                                    named_only=kind == 'specials',
                                                    name_allowed=kind != 'platforms')
                    del node_data['include']

                ### Process nested structures:
                for k in list(node_data.keys()):
                    if kind in ('platform', 'root', 'generate', 'group') and k == 'platforms' \
                    or kind == 'platforms':
                        # Nested sections
                        if k == 'platforms':
                            nodes += \
                                self._sch_to_structured(errors, path, node_data[k],
                                                        kind=k, parent=parent, group=group)
                        else:
                            if k not in ('generate', 'group', 'import', 'include'):
                                nodes_kind = 'platform:'+k
                            else:
                                nodes_kind = k
                            nodes += \
                                self._sch_to_structured(errors, path, node_data[k],
                                                        kind=nodes_kind, parent=parent, group=group)
                    del node_data[k]

                # At this point node_data should be clean, check this and raise error if not
                if len(node_data) != 0:
                    errors.append("There is unprocessed data left for '{}' but shouldn't be\n"
                                  "  Data content: {}".format(result['path'], node_data))

                results.append(result)
            if kind == 'platforms':
                platforms = results
                results = []
                for p in platforms:
                    results += p['__nodes__']
        except Exception as e:
            message = "Exception occured while processing description on path {} (item of {})!\n" \
                      "  Exception data: {}".format(path, initial_path, e)
            errors.append(message)
            results = []
        return results

    def to_uml(self, extrapolated=False):
        result = []
        result.append("@startuml")
        objects = []
        relations = []
        groups = {}
        if extrapolated:
            assert self._sch_structure_extrapolated, "Extrapolated structure should exist at this point"
            root = copy.deepcopy(self._sch_structure_extrapolated)
        else:
            assert self._sch_structure, "Description should be loaded and parsed into structure at this point"
            root = copy.deepcopy(self._sch_structure)
        self._structured_to_uml(objects, relations, groups, None, root, None)

        result += objects

        def render_group(output, groups, groups_list, level):
            # groups[group_name]["groups"][name] = {
            #     "kind": meta['kind'],
            #     "print_name": print_name,
            #     "parent_group": group_name,
            #     "package_type": package,
            #     "groups": {},
            #     "objects": []}
            assert level < 1000, "Something is wrong. Possibly infinite recursion"
            for group_name in groups_list:
                group = groups[group_name]
                if level == 0 and group['parent_group'] is not None:
                    continue
                output.append('  '*level + 'package "{}" {} as {}'.format(
                    group['print_name'], group['package_type'], group_name
                ) + "{")
                for record in group["objects"]:
                    output.append('  '*(level+1) + record)
                render_group(output, groups, groups[group_name]["groups"], level+1)
                output.append('  '*level+'}')

        render_group(result, groups, groups.keys(), 0)

        result += relations

        result.append("@enduml")
        result = "\n".join(result)
        return result

    def _structured_to_uml(self, root, relations, groups, group_name, structure, parent):
        assert '__metadata__' in structure
        assert '__nodes__' in structure

        def alpha_numeric(a_string):
            return re.sub(r"[^A-Za-z0-9_]", "_", a_string)

        def kind_to_package(kind):
            map_data = {
                'generate': '<<Node>>',
                'generated': '<<Rectangle>>',
                'group': '<<Folder>>',
                'grouped': '<<Folder>>',
                'import': '<<Frame>>',
                'imported': '<<Frame>>',
                'include': '<<Cloud>>'
            }
            return map_data.get(kind, None)

        def package_object(kind):
            map_data = {
                'generate': 'generate',
                'group': 'group',
                'import': 'import',
                'include': 'include'
            }
            return map_data.get(kind, None)

        # Specials:
        #   # for s in specials:
        #     object "testenv_<name>_<s>" as testenv_<name>_<s>
        #     testenv_<name>_<s> : <generic_name> = value
        #   <objects of platforms>
        #   <content of other objects like generate, group, import, include>
        # Objects, Root:
        #   object "<type>:<name>" as <type>_<name>   # test env object
        #   <type>_<name> : <generic_name> = <value>
        # Generate:
        #   package generate <<Node>> as <path> {
        #     object generics as <path>_generics
        #     <path>_generics : hierarchy_path = <path>
        #     <path>_generics : <generic_name> = value
        #     <generate content>
        #   }
        # Generate result:
        #   package "<path>" <<Rectangle>> as <path> {
        #     <generated content>
        #   }
        # Group:
        #   package group <<Folder>> as <path> {
        #     object generics as <path>_generics
        #     <path>_generics : hierarchy_path = <path>
        #     <path>_generics : <generic_name> = value
        #     <group content>
        #   }
        # Grouped:
        #   package "<path>" <<Folder>> as <path> {
        #     <group content>
        #   }
        # Import:
        #   package "<import_path>" <<Frame>> as <path> {
        #     object generics as <path>_generics
        #     <path>_generics : hierarchy_path = <path>
        #     <path>_generics : <import_generic_name> = <value>
        #   }
        # Imported:
        #   package "<path>" <<Frame>> as <path> {
        #     <imported content>
        #   }
        # Include:
        #   package "<include_path>" <<Cloud>> as <path> {
        #     object generics as <path>_generics
        #     <path>_generics : <include_generic_name> = <value>
        #   }

        # NOTE: "platform" field is skipped as it's shown as relation

        # TODO: Description

        # Into relations:
        #   All except include:
        #     <subject_name> --> <parent> # if subject is within 'platforms' which is within Object or root
        #   Include:
        #     <path> --> <object that is higher at hierarchy> # always

        package = None
        meta = structure['__metadata__']
        nodes = structure['__nodes__']
        used_props = []

        if group_name is not None:
            assert group_name in groups
            objects = groups[group_name]["objects"]
        else:
            objects = root

        name = "{}".format(alpha_numeric(meta['path']))
        if meta['kind'] == 'root':
            print_name = "testenv_{}".format(structure['name'])
            name = "testenv_{}".format(alpha_numeric(print_name))
            used_props.append('name')
        elif meta['kind'] == 'platform':
            print_name = "{}:{}".format(meta['platform_kind'], structure['name'])
            used_props.append('name')
            used_props.append('platform')
            used_props.append('wait')
        elif meta['kind'] == 'special':
            print_name = meta['name']
        elif kind_to_package(meta['kind']) is not None:
            package = kind_to_package(meta['kind'])
            if meta['kind'] == 'generate':
                print_name = "${" + "{}".format(structure['iterator_name']) + \
                             "} in " + "{}".format(structure['iterator'])
                used_props.append('iterator_name')
                used_props.append('iterator')
            elif meta['kind'] in ('import', 'include'):
                print_name = "{}".format(structure['path'])
                used_props.append('path')
            else:
                print_name = "{} generics".format(package_object(meta['kind']))
        else:
            assert False, "Not supported item in schematic description: {}".format(meta)

        if package is not None:
            new_group_name = "group"+name
            assert new_group_name not in groups  # Simple sanity check
            if group_name is not None:
                groups[group_name]["groups"].append(new_group_name)
            groups[new_group_name] = {
                "kind": meta['kind'],
                "print_name": print_name,
                "parent_group": group_name,
                "package_type": package,
                "groups": [],
                "objects": []}
            group_name = new_group_name
            objects = groups[group_name]["objects"]
            if meta['kind'] == 'generate':  # NOTE: nothing left for generate
                print_name = None
        else:
            new_group_name = None

        if print_name is not None:
            objects.append('object "{}" as {}'.format(print_name, name))
            # TODO: set color depending on 'condition'

            skip = tuple(['__metadata__', '__nodes__', 'description'] + used_props)
            for p in structure:
                if p in skip:
                    continue
                objects.append('{}: {} = "{}"'.format(name, alpha_numeric(p),
                                                      [str(structure[p]), p][isinstance(p, (bool, int, float))]))

        if parent is not None:
            relations.append('{} --> {}'.format([name, new_group_name][new_group_name is not None], parent))
        if meta['kind'] == 'platform' and 'wait' in structure:
            wait = structure['wait']
            if not isinstance('wait', (list, tuple)):
                wait = [wait]
            for w in wait:
                relations.append('{} ..> {}'.format(name, w))

        if meta['kind'] == 'platform':
            parent = name
        else:
            parent = None

        for node in nodes:
            self._structured_to_uml(root, relations, groups, group_name, node, parent)

    def extrapolate_structured(self):
        assert self._sch_data is not None, "It's expected that environment description is already loaded at this moment"
        struct = copy.deepcopy(self._sch_structure)

        # Extrapolate generics first
        for p in self._data:
            # NOTE: generics are also allowed to be extrapolated
            # if p == 'generics':
            #    continue
            self._extrapolate_data(p, p, self._data[p], ".{}", generics_only=True)

        # Register all platforms flat (no hierarchy structure) into self._data
        queued_platforms = {}   # Dict of platforms to register. Key is platforms type, value - instances list

        # Extrapolate current and subnodes
        for n in struct['__nodes__']:
            for field in n:
                if field[0] == '_' or field[-1] == '_':
                    continue
                n[field] = self._extrapolate_value()

        # Process generate, include, import, group
        for i in range(0, len(struct['__nodes__'])):
            n = struct['__nodes__'][i]
            if n['kind'] == 'platform':
                continue
            elif n['kind'] == 'generate':
                struct['__nodes__'][i] = generate(n)
            elif n['kind'] == 'group':
                struct['__nodes__'][i] = group()
            elif n['kind'] == 'import':
                struct['__nodes__'][i] = import_structured()
            elif n['kind'] == 'include':
                desc = include()
                struct = parse(desc)
                struct['__nodes__'][i] = extrapolate(struct)
            else:
                assert "Unknown node kind: {} at {}".format(n['kind'], path)

        # Enqueue platforms at last

    def extrapolate_description(self):
        assert self._sch_data is not None, "It's expected that environment description is already loaded at this moment"
        desc = copy.deepcopy(self._sch_data)
        del desc['name']

        # Extrapolate generics first
        for p in self._data:
            # NOTE: generics are also allowed to be extrapolated
            # if p == 'generics':
            #    continue
            self._extrapolate_data(p, p, self._data[p], ".{}", generics_only=True)

        # Register all platforms flat (no hierarchy structure) into self._data
        queued_platforms = {}   # Dict of platforms to register. Key is platforms type, value - instances list

        def enqueue_platforms(obj, root, root_name):
            assert isinstance(root, dict), "Platforms root should be a dict! " \
                                           "Got: {} for platforms of {}".format(root, root_name)
            for p in root:
                if p in obj.specials:
                    continue
                if p == 'generate':
                    if isinstance(root[p], (list, tuple)):
                        for i in range(0, len(root[p])):
                            generate_platforms(obj, root[p][i], "{}/{}[{}]".format(root_name, "generate", i))
                    else:
                        generate_platforms(obj, root[p], "{}/{}".format(root_name, "generate"))
                    continue
                if p == 'platforms':
                    enqueue_platforms(obj, root[p], "{}/{}".format(root_name, p))
                    continue
                else:
                    sp = [root[p]]
                for item in sp:
                    if p not in queued_platforms:
                        queued_platforms[p] = []
                    if not isinstance(item, (list, tuple)):
                        queued_platforms[p] += [item]
                    else:
                        queued_platforms[p] += list(item)

        def generate_platforms(obj, generate_root, root_name):
            assert isinstance(generate_root, dict), "Generate item expected to be a dict! " \
                                                    "Generate item: {}".format(root_name)
            for field in ("iterator", "iterator_name", "platforms"):
                assert field in generate_root, "Field '{}' expected to be in generate item {}".format(field, root_name)
            assert isinstance(generate_root["platforms"], dict), "Field 'platforms' expected to be " \
                                                                 "dict in generate item {}".format(root_name)
            assert isinstance(generate_root["iterator_name"], str) and \
                   re.search(r"^\w+$", generate_root["iterator_name"]) is not None, "Field 'iterator_name' expected " \
                                                                                    "to be " \
                                                                                    "alphanumeric string (\w+)" \
                                                                                    "in generate item" \
                                                                                    " {}".format(root_name)
            iterator = generate_root["iterator"]
            iterator = obj._extrapolate_value("generics", root_name, iterator, generics_only=True)
            iterator = evaluate(iterator)

            for i in iterator:
                platforms_root = copy.deepcopy(generate_root["platforms"])
                platforms_root = re_sub_recursive(
                    re.compile(r"\${"+generate_root["iterator_name"]+"}"), str(i), platforms_root)
                enqueue_platforms(obj, platforms_root, root_name + "/{}[{}]".format(
                    generate_root["iterator_name"], str(i)))

        def re_sub_recursive(regex, rep, data):
            if isinstance(data, str):
                result = re.sub(regex, rep, data)
            elif isinstance(data, (list, tuple)):
                result = []
                for i in range(0, len(data)):
                    result.append(re_sub_recursive(regex, rep, data[i]))
            elif isinstance(data, dict):
                result = {}
                for i in data.keys():
                    if isinstance(i, str):
                        ix = re.sub(regex, rep, i)
                    else:
                        ix = i
                    result[ix] = re_sub_recursive(regex, rep, data[i])
            else:
                result = copy.deepcopy(data)
            return result

        enqueue_platforms(self, desc, "__scheme_root__")

        while len(queued_platforms) > 0:
            t = list(queued_platforms.keys())[0]
            pl = queued_platforms.pop(t)
            for p in pl:
                assert isinstance(p, dict), "Instance description should be a dict! " \
                                            "Check instances of {} kind".format(t)
                assert 'name' in p, "Platform should have a name! " \
                                    "Encountered nameless platform instance of {} kind".format(t)
                assert p['name'] not in self._data, "Encountered multiple platform instances " \
                                                   "with same name: {}".format(p['name'])
                p["base_platform"] = t
                if 'platforms' in p:
                    enqueue_platforms(self, p['platforms'], p['name'])
                    del p['platforms']
                self._data[p['name']] = p

        # Check there is no alias shadowing
        for p in self._data["alias"]:
            assert p not in self._data, "Alias {} shadows environment's data!"

        # Extrapolate data
        for p in self._data:
            # NOTE: generics are also allowed to be extrapolated
            # if p == 'generics':
            #    continue
            self._extrapolate_data(p, p, self._data[p], ".{}")

        # TODO: parse OPTIONS

    @property
    def specials(self):
        return self._specials

    def _extrapolate_data(self, name, path, data, next_path, generics_only=False):
        if isinstance(data, dict):
            keys = data.keys()
        elif isinstance(data, list):
            keys = range(0, len(data))
        else:
            self._extrapolate_value(name, path, data, generics_only)
            return
        for key in keys:
            if isinstance(data[key], (dict, list)):
                self._extrapolate_data(name, path+next_path.format(key), data[key], "[{}]", generics_only)
            else:
                data[key] = self._extrapolate_value(name, path+next_path.format(key), data[key], generics_only)

    def _extrapolate_value(self, name, path, value, generics_only=False):
        if generics_only and name != 'generics':
            return value
        if path in self._extrapolated_values:
            return self._extrapolated_values[path]
        assert self._extrapolation_counter < 1000, "Looks like it's dead loop on values extrapolation of. " \
                                                   "Last item: {}. " \
                                                   "Extrapolated data so far: \n{}" \
                                                   "Extrapolation chain at this moment: \n  {}" \
                                                   "".format(path, pprint.pformat(self._extrapolated_values),
                                                             '\n  '.join(self._extrapolation_chain))
        assert path not in self._extrapolation_chain, "Looks like there is dependency loop in values extrapolation: " \
                                                      "Extrapolated data so far: \n{}" \
                                                      "Extrapolation chain: {}" \
                                                      "".format(pprint.pformat(self._extrapolated_values),
                                                                '\n  '.join(self._extrapolation_chain))
        self._extrapolation_counter += 1
        self._extrapolation_chain.append(path)

        expr = False
        count = 0
        result = [value]
        while True:
            if self._extrapolate_string(name, path, result, expr=expr, types=False):
                expr = False
            elif expr is False:
                expr = True
            else:
                self._extrapolate_string(name, path, result, expr=False, types=True)
                break
            count += 1
            assert count < 100, "Look's like it's extrapolation dead loop on extrapolation of {}".format(path)

        self._extrapolation_counter -= 1
        self._extrapolation_chain.pop(-1)

        if value != result[0]:
            vprint("Extrapolated {}: from '{}' to '{}'".format(path, value, result[0]))
        self._extrapolated_values[path] = result[0]
        return result[0]

    def _extrapolate_string(self, name, path, value, expr, types):
        if not isinstance(value[0], str):
            return False
        data = value[0]
        if not expr:
            if not types:
                m = re.findall(r"\$(s?){(\w+\.?\w+(?:(?:\[\d+\])|(?:\['.+?'\])|(?:\[\".+?\"\]))*)}", data)
                # TODO: avoid escaped chars
            else:
                m = re.findall(r"^\$([bfi]){(.+)}$", data)
        else:
            m = re.findall(r"\$(es?){(.+?)}", data)            # TODO: avoid escaped chars
        if m is None or len(m) == 0:
            return False
        values = {}
        straight = False
        straight_value = None
        for t, k in list(m):
            if k in values:
                continue    # NOTE: it's enough to extrapolate one time
            try:
                if not expr:
                    if not types:
                        tmp = self._get_extrapolated_value(k)
                        # If specified to be string or it's part of value - convert value to string
                        if t == 's' or len(r"$" + t + "{" + k + "}") != len(data) or name in ("alias", ):
                            values[k] = str(tmp)
                        else:
                            straight = True
                            straight_value = tmp
                    else:
                        straight = True
                        if len(k > 2) and (k[0] == "'" and k[-1] == "'" or k[0] == '"' and k[-1] == '"'):
                            vv = k[1:-1]
                        else:
                            vv = k

                        if t == 'b':
                            if vv in ('True', 'False'):
                                straight_value = vv == 'True'
                            else:
                                straight_value = bool(int(vv))
                        elif t == 'f':
                            straight_value = float(vv)
                        else:
                            straight_value = int(vv)
                else:
                    tmp = evaluate(k)
                    if t == 'es' or len(r"$" + t + "{" + k + "}") != len(data) or name in ("alias", ):
                        values[k] = str(tmp)
                    else:
                        straight = True
                        straight_value = tmp
            except Exception as e:
                eprint("Exception occurred while extrapolating {} with value {}."
                       "\n  Failed on {}, exception: {}".format(path, data, k, e))
                exprint()
                raise e
        if straight:
            value[0] = straight_value
        else:
            for t, k in list(m):
                kv = r"\$"+t+"{" + re.escape(k) + "}"
                vprint("Extrapolated {}: {}->{}".format(value[0], kv, values[k]))
                value[0] = re.sub(kv, values[k], value[0])
        return True

    def _get_extrapolated_value(self, path):
        """
        Extrapolates string value
        Replaces \w+ with corresponding generic value
        Replaces (\w+\).(\w+) with argument value (2) of specified platform (1)
          platform generics corresponds to generics also
        :param value: string to extrapolate
        :return: extrapolated string
        """
        if path in self._extrapolated_values:
            return self._extrapolated_values[path]
        m = re.findall(r"^(\w+)\.?(\w+)?", path)
        if m is None or len(m) == 0:
            raise ValueError("Bad format for extrapolated value path")

        generic = False
        if m[0][1] == "":
            generic = True
            p = "generics"
            k = m[0][0]
        else:
            p = m[0][0]
            k = m[0][1]
        if generic:
            path = "generics."+path
            if path in self._extrapolated_values:
                return self._extrapolated_values[path]
        count = 0
        while p in self._data["alias"]:
            if p in self.specials:
                break
            vprint("aliasing {} with {}".format(p, self._data["alias"]))
            p = self._get_extrapolated_value("alias."+p)
            count += 1
            assert count < 100, "Look's like it's aliasing dead loop"
        if p not in self._data:
            raise ValueError("Not found {} within platforms".format(p))
        if k not in self._data[p]:
            raise ValueError("Not found {} within platform's {} generics".format(k, p))
        self._extrapolate_data(p, p+"."+k, self._data[p][k], "[{}]")

        assert path in self._extrapolated_values, "No extrapolated data for {}".format(path)
        return self._extrapolated_values[path]
