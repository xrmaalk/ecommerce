import base64
from io import BytesIO, StringIO
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from .tax import AvaTaxAdapter, TaxUnavailable
from .tests import AVATAX, FakeHttpResponse


@AVATAX
@override_settings(COMMERCE_TAX_ADAPTER="commerce.tax.AvaTaxAdapter", COMMERCE_ALLOW_ZERO_TAX=False)
class AvaTaxSetupTests(SimpleTestCase):
    def check(self, **options):
        output = StringIO()
        call_command("check_avatax", stdout=output, **options)
        return output.getvalue()

    @patch("commerce.tax.urlopen")
    def test_connection_checks_only_authentication_and_exact_active_company(self, mocked_urlopen):
        mocked_urlopen.side_effect = [
            FakeHttpResponse({"authenticated": True}),
            FakeHttpResponse({"value": [{"companyCode": "ORGANICEMPEROR", "isActive": True}]}),
        ]
        output = self.check()
        self.assertIn("authentication and active company verified", output)
        self.assertIn("No tax transactions were created", output)
        self.assertNotIn("sandbox-license", output)
        self.assertEqual(mocked_urlopen.call_count, 2)
        requests = [call.args[0] for call in mocked_urlopen.call_args_list]
        self.assertEqual(requests[0].full_url, "https://sandbox-rest.avatax.com/api/v2/utilities/ping")
        self.assertEqual(urlsplit(requests[1].full_url).path, "/api/v2/companies")
        self.assertEqual(parse_qs(urlsplit(requests[1].full_url).query)["$filter"], ["companyCode eq 'ORGANICEMPEROR'"])
        expected_auth = "Basic " + base64.b64encode(b"123456:sandbox-license").decode()
        for request in requests:
            self.assertEqual(request.get_method(), "GET")
            self.assertIsNone(request.data)
            self.assertEqual(request.get_header("Authorization"), expected_auth)

    @override_settings(AVATAX_ENVIRONMENT=" Production ")
    @patch("commerce.tax.urlopen")
    def test_production_environment_uses_only_production_host(self, mocked_urlopen):
        mocked_urlopen.side_effect = [
            FakeHttpResponse({"authenticated": True}),
            FakeHttpResponse({"value": [{"companyCode": "ORGANICEMPEROR", "isActive": True}]}),
        ]
        self.check()
        for call in mocked_urlopen.call_args_list:
            self.assertEqual(urlsplit(call.args[0].full_url).netloc, "rest.avatax.com")

    @patch("commerce.tax.urlopen")
    def test_local_only_does_not_claim_authentication_or_make_network_requests(self, mocked_urlopen):
        output = self.check(local_only=True)
        self.assertIn("have not been verified", output)
        mocked_urlopen.assert_not_called()

    @override_settings(
        AVATAX_ACCOUNT_ID="your-sandbox-account-id",
        AVATAX_LICENSE_KEY="your-sandbox-license-key",
        AVATAX_ORIGIN_LINE1="your-ship-from-street",
        AVATAX_ORIGIN_POSTAL_CODE="",
    )
    @patch("commerce.tax.urlopen")
    def test_sample_or_missing_values_are_reported_by_name_without_values(self, mocked_urlopen):
        with self.assertRaises(CommandError) as error:
            self.check()
        message = str(error.exception)
        for name in ("AVATAX_ACCOUNT_ID", "AVATAX_LICENSE_KEY", "AVATAX_ORIGIN_LINE1", "AVATAX_ORIGIN_POSTAL_CODE"):
            self.assertIn(name, message)
        self.assertNotIn("your-sandbox-license-key", message)
        self.assertNotIn("your-ship-from-street", message)
        mocked_urlopen.assert_not_called()

    @override_settings(AVATAX_ENVIRONMENT="prodution")
    @patch("commerce.tax.urlopen")
    def test_invalid_environment_is_rejected_before_any_network_request(self, mocked_urlopen):
        with self.assertRaisesRegex(CommandError, "AVATAX_ENVIRONMENT must be sandbox or production"):
            self.check()
        with self.assertRaises(TaxUnavailable):
            AvaTaxAdapter().calculate(subtotal=10, shipping=0, address={}, items=[])
        mocked_urlopen.assert_not_called()

    @override_settings(AVATAX_ACCOUNT_ID="0", AVATAX_LICENSE_KEY="private key with spaces")
    @patch("commerce.tax.urlopen")
    def test_invalid_credentials_are_rejected_without_disclosing_them(self, mocked_urlopen):
        with self.assertRaises(CommandError) as error:
            self.check()
        self.assertIn("numeric AvaTax account ID", str(error.exception))
        self.assertIn("must not contain whitespace", str(error.exception))
        self.assertNotIn("private key", str(error.exception))
        mocked_urlopen.assert_not_called()

    @override_settings(COMMERCE_TAX_ADAPTER="commerce.tax.UnavailableTaxAdapter")
    @patch("commerce.tax.urlopen")
    def test_command_requires_the_configured_avatax_adapter(self, mocked_urlopen):
        with self.assertRaisesRegex(CommandError, "COMMERCE_TAX_ADAPTER"):
            self.check()
        mocked_urlopen.assert_not_called()

    @override_settings(COMMERCE_ALLOW_ZERO_TAX=True)
    @patch("commerce.tax.urlopen")
    def test_command_flags_zero_tax_configuration(self, mocked_urlopen):
        with self.assertRaisesRegex(CommandError, "COMMERCE_ALLOW_ZERO_TAX=False"):
            self.check()
        mocked_urlopen.assert_not_called()

    @patch("commerce.tax.urlopen")
    def test_http_200_with_failed_authentication_still_fails(self, mocked_urlopen):
        mocked_urlopen.return_value = FakeHttpResponse({"authenticated": False})
        with self.assertRaisesRegex(CommandError, "authentication failed"):
            self.check()
        self.assertEqual(mocked_urlopen.call_count, 1)

    @patch("commerce.tax.urlopen")
    def test_401_does_not_disclose_provider_response_and_does_not_retry(self, mocked_urlopen):
        mocked_urlopen.side_effect = HTTPError(
            "https://sandbox-rest.avatax.com/api/v2/utilities/ping", 401, "Unauthorized", {},
            BytesIO(b'{"private": "sandbox-license"}'),
        )
        with self.assertRaises(CommandError) as error:
            self.check()
        message = str(error.exception)
        self.assertIn("HTTP 401", message)
        self.assertIn("matching environment/account/license key", message)
        self.assertNotIn("sandbox-license", message)
        self.assertEqual(mocked_urlopen.call_count, 1)

    @patch("commerce.tax.urlopen")
    def test_missing_inactive_or_malformed_company_is_not_a_success(self, mocked_urlopen):
        for companies in (
            [], [{"companyCode": "OTHER", "isActive": True}],
            [{"companyCode": "ORGANICEMPEROR", "isActive": False}],
            [{"companyCode": "ORGANICEMPEROR"}], None, [None],
        ):
            with self.subTest(companies=companies):
                mocked_urlopen.side_effect = [
                    FakeHttpResponse({"authenticated": True}), FakeHttpResponse({"value": companies}),
                ]
                with self.assertRaises(CommandError):
                    self.check()

    @override_settings(AVATAX_COMPANY_CODE="OE's & Shop")
    @patch("commerce.tax.urlopen")
    def test_company_code_is_escaped_as_a_filter_literal(self, mocked_urlopen):
        mocked_urlopen.side_effect = [
            FakeHttpResponse({"authenticated": True}),
            FakeHttpResponse({"value": [{"companyCode": "OE's & Shop", "isActive": True}]}),
        ]
        self.check()
        query = parse_qs(urlsplit(mocked_urlopen.call_args.args[0].full_url).query)
        self.assertEqual(query["$filter"], ["companyCode eq 'OE''s & Shop'"])

    @patch("commerce.tax.urlopen")
    def test_unavailable_or_malformed_provider_response_fails_cleanly(self, mocked_urlopen):
        for response in (FakeHttpResponse([]), FakeHttpResponse(None), FakeHttpResponse({})):
            with self.subTest(response=response):
                mocked_urlopen.side_effect = None
                mocked_urlopen.return_value = response
                with self.assertRaises(CommandError):
                    self.check()
        mocked_urlopen.side_effect = URLError("private connection details")
        with self.assertRaises(CommandError) as error:
            self.check()
        self.assertNotIn("private connection details", str(error.exception))
