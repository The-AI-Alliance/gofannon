#!/usr/bin/env python3
import re
import sys
from datetime import datetime
import os

def read_current_version(pyproject_path="pyproject.toml"):
    """Read the current version from pyproject.toml"""
    try:
        with open(pyproject_path, 'r') as f:
            content = f.read()
            version_match = re.search(r'version\s*=\s*"([^"]+)"', content)
            if version_match:
                return version_match.group(1)
            else:
                print("Could not find version in pyproject.toml")
                return None
    except Exception as e:
        print(f"Error reading pyproject.toml: {e}")
        return None

def generate_new_version():
    """Generate version based on year.week"""
    now = datetime.now()
    year_week = now.strftime("%y.%V")
    return f"0.{year_week}"

def increment_version(current_version, base_new_version):
    """Increment version if needed"""
    # If versions don't match at the base level, use the new base version
    if not current_version.startswith(base_new_version):
        return base_new_version

    # If versions match at the base level, check for point release
    parts = current_version.split('.')
    if len(parts) <= 3:
        # No point release yet, add .1
        return f"{current_version}.1"
    else:
        # Increment the point release
        try:
            point_release = int(parts[3])
            parts[3] = str(point_release + 1)
            return '.'.join(parts)
        except (ValueError, IndexError):
            # If there's any issue parsing, default to adding .1
            return f"{base_new_version}.1"

def main():
    current_version = read_current_version()
    if current_version is None:
        sys.exit(1)

    base_new_version = generate_new_version()
    final_version = increment_version(current_version, base_new_version)

    # Set GitHub Actions environment variables
    with open(os.environ['GITHUB_ENV'], 'a') as f:
        f.write(f"PYPI_VERSION={final_version}\n")
        f.write(f"RELEASE_TAG=v{final_version}\n")

    print(f"Current version: {current_version}")
    print(f"New version: {final_version}")

if __name__ == "__main__":
    main()
