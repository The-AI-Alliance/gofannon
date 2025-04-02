from gofannon.open_notify_space.iss_locator import IssLocator
import requests_mock
from http import HTTPStatus
import json

error_response_string = "Error: The ISS endpoint returned an error. No location for the ISS can be determined"
perfect_response_string = f"According to OpenNotify.org, the International Space Station can be found at (lat, long) (-50.0654, -11.6885)"

perfect_response_json = {
    "message": "success",
    "timestamp": 1739999640,
    "iss_position": {"longitude": "-11.6885", "latitude": "-50.0654"},
}

error_response_json = {
    "message": "failure",
    "error": "Error: The ISS endpoint returned an error. No location for the ISS can be determined",
}


def test_iss_locator_string_perfect_case():
    with requests_mock.Mocker() as mock:
        mock.get("http://api.open-notify.org/iss-now.json", json=perfect_response_json)
        test = IssLocator(format_json=False)
        results = test.fn()
        assert results == perfect_response_string


def test_iss_locator_string_http_error():
    http_error_status_codes = [
        HTTPStatus.BAD_REQUEST,  # 400
        HTTPStatus.UNAUTHORIZED,  # 401
        HTTPStatus.FORBIDDEN,  # 403
        HTTPStatus.NOT_FOUND,  # 404
        HTTPStatus.INTERNAL_SERVER_ERROR,  # 500
        HTTPStatus.BAD_GATEWAY,  # 502
        HTTPStatus.SERVICE_UNAVAILABLE,  # 503
        HTTPStatus.GATEWAY_TIMEOUT,  # 504
    ]

    for error_status_code in http_error_status_codes:
        with requests_mock.Mocker() as mock:
            mock.get(
                "http://api.open-notify.org/iss-now.json", status_code=error_status_code
            )
            test = IssLocator(format_json=False)
            results = test.fn()
            assert results == error_response_string


def test_iss_locator_string_malformed_response():
    malformed_responses = [
        {"message": "some junk"},
        {},
        "SOME REAL JUNK!",
        {
            "message": "failure",
            "timestamp": 1739999640,
            "iss_position": {"longitude": "-11.6885", "latitude": "-50.0654"},
        },
        {"message": "success"},
        {
            "message": "success",
            "timestamp": 1739999640,
            "iss_position": {"longitude": "ABC", "latitude": "-50.0654"},
        },
        {
            "message": "success",
            "timestamp": 1739999640,
            "iss_position": {"longitude": "-11.6885", "latitude": "ABC"},
        },
        {
            "message": "success",
            "timestamp": 1739999640,
            "iss_position": {"longitude": "450", "latitude": "-50.0654"},
        },
        {
            "message": "success",
            "timestamp": 1739999640,
            "iss_position": {"longitude": "-11.6885", "latitude": "980"},
        },
        {"message": "success", "timestamp": 1739999640},
        {
            "message": "success",
            "timestamp": 1739999640,
            "iss_position": {"latitude": "-50.0654"},
        },
        {
            "message": "success",
            "timestamp": 1739999640,
            "iss_position": {"longitude": "-11.6885"},
        },
    ]

    for malformed_response in malformed_responses:
        with requests_mock.Mocker() as mock:
            mock.get("http://api.open-notify.org/iss-now.json", json=malformed_response)
            test = IssLocator(format_json=False)
            results = test.fn()
            assert results == error_response_string


def test_iss_locator_json_perfect_case():
    with requests_mock.Mocker() as mock:
        mock.get("http://api.open-notify.org/iss-now.json", json=perfect_response_json)
        test = IssLocator()
        results = test.fn()
        assert results == json.dumps(perfect_response_json)


def test_iss_locator_json_http_error():
    http_error_status_codes = [
        HTTPStatus.BAD_REQUEST,  # 400
        HTTPStatus.UNAUTHORIZED,  # 401
        HTTPStatus.FORBIDDEN,  # 403
        HTTPStatus.NOT_FOUND,  # 404
        HTTPStatus.INTERNAL_SERVER_ERROR,  # 500
        HTTPStatus.BAD_GATEWAY,  # 502
        HTTPStatus.SERVICE_UNAVAILABLE,  # 503
        HTTPStatus.GATEWAY_TIMEOUT,  # 504
    ]

    for error_status_code in http_error_status_codes:
        with requests_mock.Mocker() as mock:
            mock.get(
                "http://api.open-notify.org/iss-now.json", status_code=error_status_code
            )
            test = IssLocator(format_json=True)
            results = test.fn()
            assert results == json.dumps(error_response_json)


def test_iss_locator_json_malformed_response():
    malformed_responses = [
        {"message": "some junk"},
        {},
        "SOME REAL JUNK!",
        {
            "message": "failure",
            "timestamp": 1739999640,
            "iss_position": {"longitude": "-11.6885", "latitude": "-50.0654"},
        },
        {"message": "success"},
        {
            "message": "success",
            "timestamp": 1739999640,
            "iss_position": {"longitude": "ABC", "latitude": "-50.0654"},
        },
        {
            "message": "success",
            "timestamp": 1739999640,
            "iss_position": {"longitude": "-11.6885", "latitude": "ABC"},
        },
        {
            "message": "success",
            "timestamp": 1739999640,
            "iss_position": {"longitude": "450", "latitude": "-50.0654"},
        },
        {
            "message": "success",
            "timestamp": 1739999640,
            "iss_position": {"longitude": "-11.6885", "latitude": "980"},
        },
        {"message": "success", "timestamp": 1739999640},
        {
            "message": "success",
            "timestamp": 1739999640,
            "iss_position": {"latitude": "-50.0654"},
        },
        {
            "message": "success",
            "timestamp": 1739999640,
            "iss_position": {"longitude": "-11.6885"},
        },
    ]

    for malformed_response in malformed_responses:
        with requests_mock.Mocker() as mock:
            mock.get("http://api.open-notify.org/iss-now.json", json=malformed_response)
            test = IssLocator()
            results = test.fn()
            assert results == json.dumps(error_response_json)
