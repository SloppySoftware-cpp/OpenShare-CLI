import unittest
from usage_report import report

class UsageReportTests(unittest.TestCase):
    def row(self):
        return {"actor":{"type":"user_actor","email_address":"demo@example.com"},
            "core_metrics":{"num_sessions":2},
            "model_breakdown":[{"tokens":{"input":100,"output":50},
                "estimated_cost":{"currency":"USD","amount":"125"}}]}

    def test_pagination_and_aggregation(self):
        def reader(day,cursor,key):
            return {"data":[self.row()], "has_more":cursor is None,
                "next_page":"second" if cursor is None else None}
        result=report("2026-11-25","test",reader)
        self.assertIsNone(result["remaining_quota"])
        row=result["rows"][0]
        self.assertEqual((row["sessions"],row["input_tokens"],row["output_tokens"]),(4,200,100))
        self.assertEqual(row["estimated_cost_usd"],"2.50")

    def test_empty_is_not_quota(self):
        r=report("2026-11-25","test",lambda *_:{"data":[],"has_more":False})
        self.assertEqual(r["rows"],[])
        self.assertIsNone(r["remaining_quota"])

    def test_repeated_cursor_rejected(self):
        with self.assertRaises(ValueError):
            report("2026-11-25","test",lambda *_:{"data":[],"has_more":True,"next_page":"same"})

if __name__=="__main__":
    unittest.main()
