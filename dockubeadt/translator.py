import os,sys
from pathlib import Path

import ruamel.yaml as yaml
import logging

logging.basicConfig(filename="std.log",format='%(asctime)s %(message)s',filemode='w')
logger=logging.getLogger()
logger.setLevel(logging.INFO)

def translate(file):
    type = check_type(file)
    if type == 'manifest':
        translate_manifest(file)
    elif type == 'compose':
        container_name = validate_compose(file)
        convert_doc_to_kube(file,container_name)
        file_name = "{}.yaml".format(container_name)
        translate_manifest(file_name)

def check_type(file):
    """Check whether the given file is a Docker Compose or K8s Manifest

    Args:
        file (string): Path to a docker compose or k8s manifest

    Returns:
        string: compose or manifest
    """ 
    with open(file, "r") as in_file:
        dicts = yaml.safe_load_all(in_file)
        dict = list(dicts)[0]
        if 'kind' in dict:
            type = "manifest"
        elif 'services' in dict:
            type = "compose"    
    return type

def validate_compose(file):
    """Check whether the given file Docker Compose contains more than one containers

    Args:
        file (string): Path to a Docker Compose file

    Returns:
        string: name of the container
    """
    with open(file, "r") as in_file:
        dicts = yaml.safe_load(in_file)
        dict = dicts['services']
        if len(dict) > 1:
            logger.info("Docker compose file can't have more than one containers. Exiting...")
            sys.exit("Docker compose file has more than one container")
        name = next(iter(dict))
        return name

def convert_doc_to_kube(file,container_name):
    """Check whether the given file Docker Compose contains more than one containers

    Args:
        file (string): Path to a Docker Compose file

    Returns:
        string: name of the container
    """
    cmd = "kompose convert -f {} --volumes hostPath".format(file)
    os.system(cmd)
    cmd = "count=0;for file in `ls {}-*`; do if [ $count -eq 0 ]; then cat $file >{}.yaml; count=1; else echo '---'>>{}.yaml; cat $file >>{}.yaml; fi; done".format(container_name,container_name,container_name,container_name)
    os.system(cmd)

def translate_manifest(file):
    """Translates K8s Manifest(s) to a MiCADO ADT

    Args:
        file (string): Path to Kubernetes manifest
    """
    in_path = Path(file)
    adt = _get_default_adt(in_path.name)
    node_templates = adt["topology_template"]["node_templates"]
    logger.info("Translating the file {}".format(file))
    with open(file, "r") as in_file:
        manifests = yaml.safe_load_all(in_file)
        _transform(manifests, in_path.stem, node_templates)

    out_path = Path(f"{os.getcwd()}/adt-{in_path.name}")
    with open(out_path, "w") as out_file:
        yaml.round_trip_dump(adt, out_file)


def _transform(manifests, filename, node_templates):
    """Transforms a single manifest into a node template

    Args:
        manifests (iter): Iterable of k8s manifests
        filename (string): Name of the input file
        node_templates (dict): `node_templates` key of the ADT
    """
    wln = 0
    for ix, manifest in enumerate(manifests):
        name, count = _get_name(manifest)
        if count == 1:
            wln = wln + 1
        if wln > 1:
            logger.info("Manifest file can't have more than one workloads. Exiting ...")
            sys.exit("Manifest file has more than one workload")
        node_name = name or f"{filename}-{ix}"
        node_templates[node_name] = _to_node(manifest)


def _get_name(manifest):
    """Returns the name from the manifest metadata

    Args:
        manifest (dict): K8s manifests

    Returns:
        string: Name of the Kubernetes object, or None
    """
    try:
        count = 0
        name = manifest["metadata"]["name"].lower()
        kind = manifest["kind"].lower()
        if kind in ['deployment','pod','statefulset','daemonset']:
            count = 1
        return f"{name}-{kind}",count
    except KeyError:
        return None,0


def _get_default_adt(filename):
    """Returns the boilerplate for a MiCADO ADT

    Args:
        filename (string): Filename of K8s manifest(s)

    Returns:
        dict: ADT boilerplate
    """
    return {
        "topology_template": {"node_templates": {}},
    }


def _to_node(manifest):
    """Inlines the Kubernetes manifest under node_templates

    Args:
        manifest (dict): K8s manifest

    Returns:
        dict: ADT node_template
    """
    metadata = manifest['metadata']
    metadata.pop('annotations', None)
    metadata.pop('creationTimestamp', None)
    manifest['metadata'] = metadata
    manifest.pop('status', None)
    return {
        "type": "tosca.nodes.MiCADO.Kubernetes",
        "interfaces": {"Kubernetes": {"create": {"inputs": manifest}}},
    }

