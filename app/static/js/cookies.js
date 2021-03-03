'use strict';

function gtag() {
    window.dataLayer.push(arguments)
}

var setCookies = function () {
    window.dataLayer = window.dataLayer || [];

    gtag('js', new Date());
    gtag(
        'config',
        'UA-161400643-2',
        {
            'anonymize_ip': true,
            'allowAdFeatures': false
        }
    );
    window.ga('create', 'UA-145652997-1', 'auto', 'govuk_shared', { 'allowLinker': true });
    window.ga('govuk_shared.require', 'linker');
    window.ga('govuk_shared.set', 'anonymizeIp', true);
    window.ga('govuk_shared.set', 'allowAdFeatures', false);
    window.ga('govuk_shared.linker:autoLink', ['www.gov.uk']);
    window.ga('send', 'pageview');
    window.ga('govuk_shared.send', 'pageview');
};

var determineCookieState = function () {
    var cookies = document.cookie.split(';');
    var cookiePreferences = cookies.find(c => c.trim().startsWith('cookies_preferences_set_21_3'));

    if ( !cookiePreferences || cookiePreferences.split('=')[1] !== 'true' ) {
        var cookieBanner = document.querySelector("#cookie-banner");
        cookieBanner.style.display = 'block';
        cookieBanner.style.visibility = 'visible';
    }
};

function runCookieJobs() {
    document.querySelector("#accept-cookies").onclick = function () {
        var today = new Date();
        var year = today.getFullYear();
        var month = today.getMonth();
        var day = today.getDate();
        var cookieExpiryDate = new Date(year, month + 1, day).toUTCString();

        document.cookie = `cookies_policy_21_3=${ encodeURIComponent('{"essential":true,"usage":true}') }; expires=${ cookieExpiryDate };`;
        setCookies();

        document.cookie = `cookies_preferences_set_21_3=true; expires=${ cookieExpiryDate };`;

        var cookieDecisionBanner = document.querySelector('#global-cookie-message');
        cookieDecisionBanner.style.display = 'block';
        cookieDecisionBanner.style.visibility = 'visible';

        var cookieBanner = document.querySelector("#cookie-banner");
        cookieBanner.style.display = 'none';
        cookieBanner.style.visibility = 'hidden';

        document.querySelector("#hide-cookie-decision").onclick = function () {
            cookieDecisionBanner.style.display = 'none';
            cookieDecisionBanner.style.visibility = 'hidden';
        };
    };

    determineCookieState();
}

document.readyState !== 'loading'
    ? runCookieJobs()
    : document.addEventListener('DOMContentLoaded', runCookieJobs);