# Namespace package for myfy
# See PEP 420 - Implicit Namespace Packages
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
