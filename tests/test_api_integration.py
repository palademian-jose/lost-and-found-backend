import asyncio
import json
import os
import socket
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from uuid import uuid4


ROOT_DIR = Path(__file__).resolve().parents[1]


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _request_json(
    method: str,
    url: str,
    *,
    payload: dict | None = None,
    headers: dict | None = None,
):
    data = None
    request_headers = {"Content-Type": "application/json"}

    if headers:
        request_headers.update(headers)

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url=url,
        method=method,
        data=data,
        headers=request_headers,
    )

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8")
            return response.status, json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        return exc.code, json.loads(body) if body else None


class ApiIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = _find_free_port()
        cls.base_url = f"http://127.0.0.1:{cls.port}"
        cls._ensure_admin_user()
        cls.server = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(cls.port),
            ],
            cwd=ROOT_DIR,
            env={**os.environ, "PYTHONPATH": str(ROOT_DIR)},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        cls._wait_for_server()

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "server") and cls.server.poll() is None:
            cls.server.terminate()
            try:
                cls.server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                cls.server.kill()

    @classmethod
    def _wait_for_server(cls):
        deadline = time.time() + 20
        while time.time() < deadline:
            try:
                status, _ = _request_json("GET", f"{cls.base_url}/openapi.json")
                if status == 200:
                    return
            except Exception:
                pass
            time.sleep(0.5)
        raise RuntimeError("API server did not start in time.")

    @classmethod
    def _ensure_admin_user(cls):
        async def run():
            from app.main import startup
            from app.modules.auth.infrastructure.repositories.user_repo_sql import UserRepository
            from app.modules.auth.infrastructure.security.password import hash_password
            from app.shared.infrastructure.db import AsyncSessionLocal

            await startup()

            async with AsyncSessionLocal() as session:
                repo = UserRepository(session)
                admin = await repo.get_by_email("admin@example.com")
                if admin is None:
                    await repo.create(
                        email="admin@example.com",
                        password_hash=hash_password("123456"),
                        role="ADMIN",
                    )
                    await session.commit()

        asyncio.run(run())

    def _register_user(self, role: str) -> dict:
        suffix = uuid4().hex[:8]
        email = f"{role.lower()}_{suffix}@example.com"
        status, body = _request_json(
            "POST",
            f"{self.base_url}/auth/register",
            payload={
                "email": email,
                "password": "123456",
                "role": role,
            },
        )
        self.assertEqual(status, 201, body)
        return body

    def _login(self, email: str, password: str = "123456") -> str:
        status, body = _request_json(
            "POST",
            f"{self.base_url}/auth/login",
            payload={"email": email, "password": password},
        )
        self.assertEqual(status, 200, body)
        return body["access_token"]

    def test_full_claim_workflow_and_privacy(self):
        owner = self._register_user("MEMBER")
        finder = self._register_user("MEMBER")

        owner_token = self._login(owner["email"])
        finder_token = self._login(finder["email"])

        status, created_item = _request_json(
            "POST",
            f"{self.base_url}/items",
            payload={
                "report_type": "LOST",
                "title": "Lost Headphones",
                "description_public": "Gray headphones near library",
                "category": "Electronics",
                "location_text": "Main Library",
                "happened_at": "2026-04-03T08:30:00Z",
                "verification_questions": [
                    "What brand are they?",
                    "What color is the case?",
                ],
            },
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        self.assertEqual(status, 201, created_item)

        item_id = created_item["item_id"]

        status, public_item = _request_json("GET", f"{self.base_url}/items/{item_id}")
        self.assertEqual(status, 200, public_item)
        self.assertNotIn("verification_questions", public_item)
        self.assertNotIn("active_claim_id", public_item)
        self.assertNotIn("posted_by_user_id", public_item)

        status, claim_questions = _request_json(
            "GET",
            f"{self.base_url}/items/{item_id}/claim-questions",
            headers={"Authorization": f"Bearer {finder_token}"},
        )
        self.assertEqual(status, 200, claim_questions)
        self.assertEqual(len(claim_questions["questions"]), 2)

        status, created_claim = _request_json(
            "POST",
            f"{self.base_url}/items/{item_id}/claims",
            payload={"answers": ["Sony", "Gray"]},
            headers={"Authorization": f"Bearer {finder_token}"},
        )
        self.assertEqual(status, 200, created_claim)

        status, my_claims = _request_json(
            "GET",
            f"{self.base_url}/claims/mine",
            headers={"Authorization": f"Bearer {finder_token}"},
        )
        self.assertEqual(status, 200, my_claims)
        self.assertTrue(any(claim["id"] == created_claim["claim_id"] for claim in my_claims))

        status, managed_item = _request_json(
            "GET",
            f"{self.base_url}/items/{item_id}/manage",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        self.assertEqual(status, 200, managed_item)
        self.assertEqual(managed_item["posted_by_user_id"], owner["user_id"])
        self.assertEqual(len(managed_item["verification_questions"]), 2)

        status, claims = _request_json(
            "GET",
            f"{self.base_url}/items/{item_id}/claims",
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        self.assertEqual(status, 200, claims)
        self.assertEqual(len(claims), 1)

        status, decision = _request_json(
            "POST",
            f"{self.base_url}/claims/{created_claim['claim_id']}/decision",
            payload={"decision": "APPROVE"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        self.assertEqual(status, 200, decision)

        status, item_after_decision = _request_json(
            "GET",
            f"{self.base_url}/items/{item_id}",
        )
        self.assertEqual(status, 200, item_after_decision)
        self.assertEqual(item_after_decision["status"], "RETURNED")

    def test_admin_user_moderation_and_audit_log_access(self):
        admin_token = self._login("admin@example.com")
        finder = self._register_user("MEMBER")

        status, users = _request_json(
            "GET",
            f"{self.base_url}/admin/users?limit=50",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(status, 200, users)
        self.assertTrue(any(user["email"] == finder["email"] for user in users))

        status, updated_user = _request_json(
            "PATCH",
            f"{self.base_url}/admin/users/{finder['user_id']}/status",
            payload={"is_active": False},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(status, 200, updated_user)
        self.assertFalse(updated_user["is_active"])

        status, blocked_login = _request_json(
            "POST",
            f"{self.base_url}/auth/login",
            payload={"email": finder["email"], "password": "123456"},
        )
        self.assertEqual(status, 403, blocked_login)

        status, audit_logs = _request_json(
            "GET",
            f"{self.base_url}/admin/audit-logs?limit=50",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(status, 200, audit_logs)
        self.assertTrue(any(log["action"] == "USER_DEACTIVATED" for log in audit_logs))


if __name__ == "__main__":
    unittest.main()
