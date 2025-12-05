import os
from typing import Any, Dict, Optional


class Config:
    """
    Lightweight .env loader.

    - Parses KEY=VALUE pairs from a .env file
    - Ignores empty lines and comments starting with '#'
    - Supports optional quotes around values (single or double)
    - Falls back to os.environ if a key is not present in the file
    """

    def __init__(self, env_file: str = ".env", encoding: str = "utf-8") -> None:
        self.env_file = env_file
        self.encoding = encoding
        self._values: Dict[str, str] = {}
        self.load()

    def load(self) -> None:
        """(Re)load values from the .env file into memory."""
        values: Dict[str, str] = {}
        try:
            with open(self.env_file, "r", encoding=self.encoding) as f:
                for raw_line in f:
                    line = raw_line.strip()
                    if not line or line.startswith("#"):
                        continue

                    if line.startswith("export "):
                        line = line[len("export ") :].strip()

                    if "=" not in line:
                        # Skip malformed lines
                        continue

                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()

                    # Remove surrounding quotes if present
                    if value and len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                        value = value[1:-1]
                    else:
                        # Trim inline comments that start after a space (e.g., VALUE # comment)
                        if " #" in value:
                            value = value.split(" #", 1)[0].strip()

                    # Interpret common escapes (e.g., \n, \t)
                    try:
                        value = bytes(value, "utf-8").decode("unicode_escape")
                    except Exception:
                        pass

                    if key:
                        values[key] = value

        except FileNotFoundError:
            values = {}

        self._values = values

    def get(self, key: str, default: Optional[Any] = None) -> Optional[str]:
        """
        Get a value for `key` from the loaded .env values, falling
        back to process environment variables, or `default` if not found.
        """
        if key in self._values:
            return self._values[key]
        return os.environ.get(key, default)  # type: ignore[return-value]

    def as_dict(self) -> Dict[str, str]:
        """Return a merged dict of env file values overlaid on os.environ."""
        merged = dict(os.environ)
        merged.update(self._values)
        return merged


__all__ = ["Config"]
