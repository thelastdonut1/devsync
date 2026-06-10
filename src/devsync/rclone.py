"""
rclone command construction and execution.

One function builds a sync/copy command with the shared filter file and the
.backupignore-all marker; another runs it with real-time output streaming so
progress is visible in logs. Both legs (local mirror and cloud) use this.
"""

import logging
import subprocess
from pathlib import Path
