"""
Bug-Gira — Database backup management command.

Copyright (c) [2026] [Bidhu Shekhar Tiwari]
Licensed under the MIT License. See LICENSE for details.

Usage:
    python manage.py backup_db
    python manage.py backup_db --keep 14
"""

import os
import subprocess
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create a timestamped PostgreSQL backup and prune old ones."

    def add_arguments(self, parser):
        parser.add_argument(
            "--keep",
            type=int,
            default=7,
            help="Number of recent backups to keep (default: 7).",
        )

    def handle(self, *args, **options):
        keep = options["keep"]

        # Backup directory (created if missing)
        backup_dir = Path(settings.BASE_DIR) / "backups"
        backup_dir.mkdir(exist_ok=True)

        # Read database connection details from Django's settings
        db = settings.DATABASES["default"]
        db_name = db.get("NAME")
        db_user = db.get("USER")
        db_host = db.get("HOST") or "localhost"
        db_port = str(db.get("PORT") or "5432")
        db_password = db.get("PASSWORD")

        if not db_name:
            self.stderr.write(self.style.ERROR("No database name found in settings."))
            return

        # Timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"buggira_{db_name}_{timestamp}.sql"

        # Locate pg_dump (subprocess doesn't always inherit the shell PATH)
        pg_dump_path = self.find_pg_dump()
        if not pg_dump_path:
            self.stderr.write(self.style.ERROR(
                "pg_dump not found. Set PG_DUMP_PATH env var to its full path, "
                "or ensure PostgreSQL client tools are on PATH."
            ))
            return

        # Build the pg_dump command
        cmd = [pg_dump_path, "-h", db_host, "-p", db_port, "-d", db_name, "-f", str(backup_file)]
        if db_user:
            cmd += ["-U", db_user]

        # pg_dump reads the password from the PGPASSWORD environment variable
        env = os.environ.copy()
        if db_password:
            env["PGPASSWORD"] = db_password

        self.stdout.write(f"Creating backup: {backup_file.name} ...")

        try:
            subprocess.run(cmd, env=env, check=True, capture_output=True, text=True)
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(
                "pg_dump not found. Make sure PostgreSQL client tools are installed and on PATH."
            ))
            return
        except subprocess.CalledProcessError as e:
            self.stderr.write(self.style.ERROR(f"Backup failed: {e.stderr}"))
            return

        size_kb = backup_file.stat().st_size / 1024
        self.stdout.write(self.style.SUCCESS(
            f"Backup created: {backup_file.name} ({size_kb:.1f} KB)"
        ))

        # ----- Prune old backups -----
        self.prune_old_backups(backup_dir, keep)

    def find_pg_dump(self):
        """Locate the pg_dump executable reliably."""
        import shutil

        # 1. Explicit override via environment variable (best for production)
        env_path = os.environ.get("PG_DUMP_PATH")
        if env_path and Path(env_path).exists():
            return env_path

        # 2. Standard PATH lookup
        found = shutil.which("pg_dump")
        if found:
            return found

        # 3. Common Postgres.app locations on macOS
        common_paths = [
            "/Applications/Postgres.app/Contents/Versions/latest/bin/pg_dump",
            "/opt/homebrew/bin/pg_dump",
            "/usr/local/bin/pg_dump",
            "/usr/bin/pg_dump",
        ]
        for path in common_paths:
            if Path(path).exists():
                return path

        return None    

    def prune_old_backups(self, backup_dir, keep):
        # All backup files, newest first
        backups = sorted(
            backup_dir.glob("buggira_*.sql"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        old_backups = backups[keep:]  # everything beyond the keep limit
        for old in old_backups:
            old.unlink()
            self.stdout.write(f"Pruned old backup: {old.name}")

        if old_backups:
            self.stdout.write(self.style.SUCCESS(
                f"Pruned {len(old_backups)} old backup(s). Keeping {keep} most recent."
            ))
        else:
            self.stdout.write(f"No pruning needed ({len(backups)} backup(s), keeping up to {keep}).")