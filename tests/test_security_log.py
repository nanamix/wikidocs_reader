import json
import tempfile
import time
import unittest
from pathlib import Path

from plugins.metadata.wikidocs_reader import wikidocs_reader as security_log


class SecurityLogTests(unittest.TestCase):
    def test_events_are_server_side_and_old_events_are_pruned(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_path = security_log.LOG_PATH
            security_log.LOG_PATH = Path(tmp) / "security.log"
            try:
                security_log.security_event("test_event", error_type="ValueError")
                rows = [json.loads(x) for x in security_log.LOG_PATH.read_text().splitlines()]
                self.assertEqual(rows[0]["event"], "test_event")
                self.assertEqual(rows[0]["error_type"], "ValueError")

                old = {"ts": time.time() - security_log.RETENTION_SECONDS - 1, "event": "old_event"}
                security_log.LOG_PATH.write_text(json.dumps(old) + "\n")
                security_log.security_event("new_event")
                rows = [json.loads(x) for x in security_log.LOG_PATH.read_text().splitlines()]
                self.assertEqual([row["event"] for row in rows], ["new_event"])
            finally:
                security_log.LOG_PATH = old_path


if __name__ == "__main__":
    unittest.main()
