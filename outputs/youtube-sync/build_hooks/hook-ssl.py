"""Include optional trust data required by the Python runtime's SSL module."""

from pathlib import Path
import ssl

trust_data = Path(ssl.__file__).with_name("codex-rejected-cas.pem")
datas = [(str(trust_data), ".")] if trust_data.is_file() else []
