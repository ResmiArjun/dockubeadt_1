import click
import sys

from .translator import translate
from ruamel.yaml.scanner import ScannerError


@click.command()
@click.argument("file")
def main(file):
    """Converts from Docker compose or Kubernetes manifests to a MiCADO ADT

    FILE is the path to a single/multi compose files or K8s manifests (YAML)"""
    try:
        translate(file)
    except ScannerError:
        print("[Errno 1] Not a valid YAML file")
        sys.exit(1)
    except FileNotFoundError as error:
        print(str(error))
        sys.exit(1)


if __name__ == "__main__":
    main()
