"""Exercise deployment orchestration without touching Docker or public ports."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

ROOT = Path(os.environ.get("MANDI_REPO_ROOT", str(Path(__file__).resolve().parents[2])))


class DeploymentScriptTests(SimpleTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / "scripts", self.root / "scripts")
        shutil.copy(ROOT / ".env.example", self.root / ".env.example")
        shutil.copy(
            ROOT / ".env.production.example", self.root / ".env.production.example"
        )
        (self.root / "deploy").mkdir()
        (self.root / "bin").mkdir()
        self.log = self.root / "commands.log"
        commands = {
            "docker": """#!/usr/bin/env bash
printf '%s\\n' "$*" >> "$COMMAND_LOG"
if [[ "$*" == *"--wait-timeout 240"* && "${FAIL_CANDIDATE:-}" == 1 ]]; then exit 1; fi
if [[ "$*" == *" cp proxy:"* ]]; then
  printf 'test-public-ca' > "${@: -1}"
fi
exit 0
""",
            "curl": '#!/usr/bin/env bash\n[[ "${FAIL_PUBLIC:-}" != 1 ]]\n',
            "git": "#!/usr/bin/env bash\necho abc1234\n",
        }
        for name, content in commands.items():
            path = self.root / "bin" / name
            path.write_text(content)
            path.chmod(0o755)
        self.env = {
            **os.environ,
            "PATH": str(self.root / "bin") + ":" + os.environ["PATH"],
            "COMMAND_LOG": str(self.log),
        }
        self.run_script("setup.sh")
        path = self.root / ".env"
        path.write_text(path.read_text().replace("example.org", "review.invalid"))

    def run_script(self, name, *, check=True, extra_env=None):
        return subprocess.run(
            [str(self.root / "scripts" / name)],
            cwd=self.root,
            env={**self.env, **(extra_env or {})},
            check=check,
            capture_output=True,
            text=True,
        )

    def test_setup_generates_secrets_once_and_never_executes_dotenv(self):
        path = self.root / ".env"
        original = path.read_text()
        self.run_script("setup.sh")
        self.assertEqual(path.read_text(), original)
        for key in (
            "DJANGO_SECRET_KEY",
            "POSTGRES_PASSWORD",
            "ODK_PASSWORD",
            "ODK_ADMIN_PASSWORD",
            "MANDI_ADMIN_PASSWORD",
        ):
            self.assertTrue(
                next(
                    line.partition("=")[2]
                    for line in original.splitlines()
                    if line.startswith(key + "=")
                )
            )
        path.write_text(original + f"UNTRUSTED=$(touch {self.root / 'executed'})\n")
        self.run_script("deploy.sh")
        self.assertFalse((self.root / "executed").exists())

    def test_alternating_slots_and_rollback_preserve_previous_release(self):
        self.run_script("deploy.sh")
        first = (self.root / "deploy/runtime/active").read_text()
        self.assertTrue(first.startswith("blue "))
        self.run_script("deploy.sh")
        self.assertTrue(
            (self.root / "deploy/runtime/active").read_text().startswith("green ")
        )
        self.assertEqual((self.root / "deploy/runtime/previous").read_text(), first)
        self.run_script("rollback.sh")
        self.assertEqual((self.root / "deploy/runtime/active").read_text(), first)
        self.assertEqual(
            (self.root / "deploy/runtime/routes/mandi.caddy").read_text(),
            "reverse_proxy web-blue:80\n",
        )
        log = self.log.read_text()
        self.assertNotIn("down -v", log)
        self.assertLess(log.index("build --pull"), log.index("up -d --wait"))

    def test_failed_candidate_does_not_change_live_route(self):
        self.run_script("deploy.sh")
        active = (self.root / "deploy/runtime/active").read_text()
        route = (self.root / "deploy/runtime/routes/mandi.caddy").read_text()
        result = self.run_script(
            "deploy.sh", check=False, extra_env={"FAIL_CANDIDATE": "1"}
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.root / "deploy/runtime/active").read_text(), active)
        self.assertEqual(
            (self.root / "deploy/runtime/routes/mandi.caddy").read_text(), route
        )

    def test_failed_public_health_restores_previous_route(self):
        self.run_script("deploy.sh")
        active = (self.root / "deploy/runtime/active").read_text()
        result = self.run_script(
            "deploy.sh", check=False, extra_env={"FAIL_PUBLIC": "1"}
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.root / "deploy/runtime/active").read_text(), active)
        self.assertEqual(
            (self.root / "deploy/runtime/routes/mandi.caddy").read_text(),
            "reverse_proxy web-blue:80\n",
        )
