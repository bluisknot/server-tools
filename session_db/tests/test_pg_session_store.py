from unittest import mock

import psycopg2

from odoo.http import OpenERPSession
from odoo.tests.common import TransactionCase
from odoo.tools import config

from odoo.addons.session_db.pg_session_store import PGSessionStore


class TestPGSessionStore(TransactionCase):
    def setUp(self):
        super().setUp()
        self.session_store = PGSessionStore(
            config["db_name"], session_class=OpenERPSession
        )

    def test_session_crud(self):
        session = self.session_store.new()
        session["test"] = "test"
        self.session_store.save(session)
        assert session.sid is not None
        assert self.session_store.get(session.sid)["test"] == "test"
        self.session_store.delete(session)
        assert self.session_store.get(session.sid).get("test") is None

    def test_retry(self):
        """Test that session operations are retried before failing"""
        with mock.patch("odoo.sql_db.Cursor.execute") as mock_execute:
            mock_execute.side_effect = psycopg2.OperationalError()
            with self.assertRaises(psycopg2.OperationalError):
                self.session_store.get("abc")
            assert mock_execute.call_count == 5
        # when the error is resolved, it works again
        self.session_store.get("abc")

    def test_retry_connect_fail(self):
        with mock.patch("odoo.sql_db.Cursor.execute") as mock_execute, mock.patch(
            "odoo.sql_db.db_connect"
        ) as mock_db_connect:
            mock_execute.side_effect = psycopg2.OperationalError()
            mock_db_connect.side_effect = RuntimeError("connection failed")
            # get fails, and a RuntimeError is raised when trying to reconnect
            with self.assertRaises(RuntimeError):
                self.session_store.get("abc")
            assert mock_execute.call_count == 1
        # when the error is resolved, it works again
        self.session_store.get("abc")
