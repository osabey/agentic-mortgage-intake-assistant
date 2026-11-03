import unittest
from app import validate

class ValidationTests(unittest.TestCase):
    def test_complete(self):
        record = {"applicant":"Demo", "annual_income":1, "loan_amount":1, "documents":["photo_id","pay_stub","bank_statement","tax_return"]}
        self.assertEqual(validate(record)["status"], "ready_for_human_review")

    def test_missing_document_and_field(self):
        record = {"applicant":"Demo", "annual_income":None, "loan_amount":1, "documents":[]}
        result = validate(record)
        self.assertIn("annual_income", result["missing_fields"])
        self.assertIn("pay_stub", result["missing_documents"])
        self.assertEqual(result["status"], "needs_review")

if __name__ == "__main__": unittest.main()
