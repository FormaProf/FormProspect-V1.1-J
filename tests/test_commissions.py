import sqlite3
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from core.sqlite_utils import connect_database
from core.database import init_database
from services.commission_service import CommissionService


class CommissionServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name) / "project.db"
        init_database(self.db)
        with connect_database(self.db) as conn:
            conn.execute("INSERT INTO prospects(entreprise) VALUES ('Client Test')")
        self.service = CommissionService(self.db)

    def tearDown(self):
        self.temp.cleanup()

    def test_default_offers_and_commissions(self):
        offers = self.service.list_offers()
        self.assertEqual(len(offers), 3)
        expected = {
            "Formation Classic BTP": 25_500,
            "Formation Pro BTP": 50_000,
            "Formation Pro+ BTP": 87_500,
        }
        for offer in offers:
            self.service.create_sale(
                prospect_id=1,
                offer_id=offer["id"],
                commercial_user_id=7,
                commercial_name="Commercial Test",
                signed_at=date(2026, 7, 10),
            )
            sale = self.service.list_sales(year=2026, month=7, commercial_user_id=7)[0]
            self.assertEqual(sale["commission_cents"], expected[offer["name"]])

        summary = self.service.monthly_summary(year=2026, month=7, commercial_user_id=7)
        self.assertEqual(summary["contracts"], 3)
        self.assertEqual(summary["revenue_cents"], 770_000)
        self.assertEqual(summary["commission_cents"], 163_000)


    def test_future_signature_date_is_rejected(self):
        offer = self.service.list_offers()[0]
        future_date = date.today() + timedelta(days=1)

        with self.assertRaisesRegex(
            ValueError,
            "La date de signature ne peut pas être postérieure à la date du jour",
        ):
            self.service.create_sale(
                prospect_id=1,
                offer_id=offer["id"],
                commercial_user_id=11,
                commercial_name="Commercial Test",
                signed_at=future_date,
            )

        summary = self.service.monthly_summary(
            year=future_date.year,
            month=future_date.month,
            commercial_user_id=11,
        )
        self.assertEqual(summary["contracts"], 0)
        self.assertEqual(summary["commission_cents"], 0)

    def test_cancelled_sale_is_excluded_from_summary(self):
        offer = self.service.list_offers()[0]
        sale_id = self.service.create_sale(
            prospect_id=1,
            offer_id=offer["id"],
            commercial_user_id=9,
            commercial_name="Commercial Test",
            signed_at="2026-07-11",
        )
        self.service.cancel_sale(sale_id)
        summary = self.service.monthly_summary(year=2026, month=7, commercial_user_id=9)
        self.assertEqual(summary["contracts"], 0)
        self.assertEqual(summary["commission_cents"], 0)


if __name__ == "__main__":
    unittest.main()
