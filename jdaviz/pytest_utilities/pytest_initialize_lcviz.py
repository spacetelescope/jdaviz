from importlib.metadata import distribution
import requests
from packaging.requirements import Requirement
from packaging.version import parse as parse_version


def _get_jdaviz_requirement_spec():
    """
    Get the jdaviz version requirement specifier from lcviz's installed package metadata.

    Returns:
        SpecifierSet: The version specifier for jdaviz (e.g., ">=5.0.1,<5.1").
    """
    dist = distribution("lcviz")
    requires_dist = dist.metadata.get_all("Requires-Dist") or []

    req = None
    for req_str in requires_dist:
        if req_str.startswith("jdaviz"):
            req = Requirement(req_str).specifier

    return req


def _get_latest_jdaviz_version():
    """
    Get the latest jdaviz version available on PyPI that matches lcviz's version requirement.

    Returns:
        str: The latest version string that satisfies the lcviz jdaviz requirement,
             or None if no matching versions are found.
    """
    try:
        specifier = _get_jdaviz_requirement_spec()
        if specifier is None:
            raise Exception('Could not find jdaviz dependency in lcviz package metadata')

        # Query PyPI for all available versions
        response = requests.get("https://pypi.org/pypi/jdaviz/json", timeout=10)
        response.raise_for_status()
        all_versions = response.json()["releases"].keys()

        # Filter to versions that match the specifier
        matching = [v for v in all_versions if parse_version(v) in specifier]

        if not matching:
            raise Exception('No jdaviz versions found matching the lcviz requirement')

        # Sort by version (newest first) and return the latest
        matching.sort(key=parse_version, reverse=True)

        return matching[0]

    except Exception as e:
        return f'Error determining latest jdaviz version: {str(e)}'


if __name__ == "__main__":
    # Determine the latest jdaviz version matching lcviz's requirement
    latest_version = _get_latest_jdaviz_version()
    print(f"Latest matching jdaviz version: {latest_version}")
