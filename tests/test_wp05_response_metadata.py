"""WP-05 image API response summaries must never store raw base64 or secrets."""
import unittest
from ucscene.provider import _safe_image_response_summary

class TestImageResponseSummary(unittest.TestCase):
    def test_safe_summary_whitelists_only_metadata(self):
        raw={'id':'img-123','created':100,
             'usage':{'input_tokens':50,'output_tokens':30,'total_tokens':80,'secret':'DO_NOT_SAVE'},
             'data':[{'b64_json':'SENSITIVE_IMAGE_PAYLOAD'}],
             'api_key':'DO_NOT_SAVE'}
        value=_safe_image_response_summary(raw)
        self.assertEqual(value['response_id'],'img-123')
        self.assertEqual(value['image_items_returned'],1)
        self.assertEqual(value['usage'],{'input_tokens':50,'output_tokens':30,'total_tokens':80})
        self.assertNotIn('DO_NOT_SAVE',repr(value))
        self.assertNotIn('SENSITIVE_IMAGE_PAYLOAD',repr(value))
    def test_absent_provider_fields_stay_null(self):
        value=_safe_image_response_summary({'data':[{}]})
        self.assertIsNone(value['response_id'])
        self.assertIsNone(value['created_unix'])
        self.assertIsNone(value['usage'])

if __name__=='__main__':unittest.main()
