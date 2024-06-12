from allauth.account.utils import Login
from allauth.socialaccount.models import SocialLogin
from allauth.socialaccount.providers.saml.views import (
    AuthError,
    AuthProcess,
    LoginSession,
    OneLogin_Saml2_Error,
    SAMLViewMixin,
    binascii,
    build_auth,
    complete_social_login,
    decode_relay_state,
    httpkit,
    render_authentication_error,
)
from django.http import HttpRequest, HttpResponseRedirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View
from rest_framework.views import csrf_exempt

from pprint import pprint

import structlog

from iam.models import User
from iam.utils import generate_token

logger = structlog.get_logger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class ACSView(SAMLViewMixin, View):
    def dispatch(self, request, organization_slug):
        url = reverse(
            "saml_finish_acs",
            kwargs={"organization_slug": organization_slug},
        )
        response = HttpResponseRedirect(url)
        acs_session = LoginSession(request, "saml_acs_session", "saml-acs-session")
        acs_session.store.update({"request": httpkit.serialize_request(request)})
        acs_session.save(response)
        return response


class FinishACSView(SAMLViewMixin, View):
    def dispatch(self, request, organization_slug):
        provider = self.get_provider(organization_slug)
        acs_session = LoginSession(request, "saml_acs_session", "saml-acs-session")
        acs_request = None
        acs_request_data = acs_session.store.get("request")
        if acs_request_data:
            acs_request = httpkit.deserialize_request(acs_request_data, HttpRequest())
        acs_session.delete()
        if not acs_request:
            logger.error("Unable to finish login, SAML ACS session missing")
            return render_authentication_error(request, provider)

        auth = build_auth(acs_request, provider)
        error_reason = None
        errors = []
        try:
            # We're doing the check for a valid `InResponeTo` ourselves later on
            # (*) by checking if there is a matching state stashed.
            auth.process_response(request_id=None)
        except binascii.Error:
            errors = ["invalid_response"]
            error_reason = "Invalid response"
        except OneLogin_Saml2_Error as e:
            errors = ["error"]
            error_reason = str(e)
        if not errors:
            errors = auth.get_errors()
        if errors:
            # e.g. ['invalid_response']
            error_reason = auth.get_last_error_reason() or error_reason
            logger.error(
                "Error processing SAML ACS response: %s: %s"
                % (", ".join(errors), error_reason)
            )
            return render_authentication_error(
                request,
                provider,
                extra_context={
                    "saml_errors": errors,
                    "saml_last_error_reason": error_reason,
                },
            )
        if not auth.is_authenticated():
            return render_authentication_error(
                request, provider, error=AuthError.CANCELLED
            )
        login: SocialLogin = provider.sociallogin_from_response(request, auth)
        # (*) If we (the SP) initiated the login, there should be a matching
        # state.
        state_id = auth.get_last_response_in_response_to()
        if state_id:
            login.state = provider.unstash_redirect_state(request, state_id)
        else:
            # IdP initiated SSO
            reject = provider.app.settings.get("advanced", {}).get(
                "reject_idp_initiated_sso", True
            )
            if reject:
                logger.error("IdP initiated SSO rejected")
                return render_authentication_error(request, provider)
            next_url = decode_relay_state(acs_request.POST.get("RelayState"))
            login.state["process"] = AuthProcess.LOGIN
            if next_url:
                login.state["next"] = next_url
        print("LOGIN STATE", login.state)
        email = auth._nameid
        user = User.objects.get(email=email)
        token = generate_token(user)
        login.state["next"] += f"sso/authenticate/{token}"
        return complete_social_login(request, login)
