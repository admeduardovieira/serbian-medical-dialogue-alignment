import os

# Torch may call getpass in containers whose UID has no passwd entry.
os.environ.setdefault("USER", "researcher")
