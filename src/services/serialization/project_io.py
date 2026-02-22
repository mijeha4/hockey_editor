from __future__ import annotations

import json
import zipfile
from pathlib import Path
from datetime import datetime
from typing import Optional

from models.domain.project import Project


class ProjectIO:
    """Service for saving/loading .hep projects (ZIP archive)."""

    HEP_VERSION = "1.0"
    MANIFEST_FILE = "project.json"

    @staticmethod
    def save_project(project: Project, filepath: str) -> bool:
        try:
            file_path = Path(filepath)
            if file_path.suffix.lower() != ".hep":
                file_path = file_path.with_suffix(".hep")

            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Update modification timestamp only (dirty flag is handled by ProjectController)
            try:
                project.modified_at = datetime.now().isoformat()
            except Exception:
                # If modified_at becomes read-only later, don't crash
                pass

            manifest = {
                "version": ProjectIO.HEP_VERSION,
                "project": project.to_dict(),
            }

            with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as hep:
                hep.writestr(
                    ProjectIO.MANIFEST_FILE,
                    json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8"),
                )

            return True

        except Exception as e:
            print(f"Error saving project: {e}")
            return False

    @staticmethod
    def load_project(filepath: str) -> Optional[Project]:
        try:
            file_path = Path(filepath)
            if not file_path.exists():
                raise FileNotFoundError(f"Project file not found: {filepath}")

            with zipfile.ZipFile(file_path, "r") as hep:
                try:
                    manifest_bytes = hep.read(ProjectIO.MANIFEST_FILE)
                except KeyError:
                    raise ValueError(f"Invalid .hep file: missing {ProjectIO.MANIFEST_FILE}")

            # Parse JSON
            try:
                manifest = json.loads(manifest_bytes.decode("utf-8"))
            except Exception as e:
                raise ValueError(f"Invalid project manifest JSON: {e}")

            version = str(manifest.get("version", "1.0"))
            if version != ProjectIO.HEP_VERSION:
                print(f"Warning: Project version {version} may not be fully compatible with {ProjectIO.HEP_VERSION}")

            project_data = manifest.get("project", {})
            project = Project.from_dict(project_data)
            return project

        except Exception as e:
            print(f"Error loading project: {e}")
            return None