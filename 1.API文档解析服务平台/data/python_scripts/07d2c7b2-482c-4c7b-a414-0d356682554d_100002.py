import pytest
import requests
import allure
from allure_commonsSteps import step
import json

@pytest.mark.allure
def test_login_response():
    @allure.title("Validating login response")
    @allure.description("Test if login returns correct token")
    try:
        response = requests.post(
            "http://api.example.com/login",
            json={"username": "testuser", "password": "securepass"}
        )
        response.raise_for_status()
        assert response.status_code == 200
        expected_response = {"token": "valid_token_123"}
        assert json.loads(response.text) == expected_response
    except requests.exceptions.RequestException as e:
        allure.step("Encountered request error")
        allure.attach(str(e), "error details")
        pytest.fail("Request failed: " + str(e))

@pytest.mark.allure
def test_userlistGET():
    @allure.title("Validating user list retrieval")
    @allure.description("Test if GET /users returns valid JSON array")
    try:
        response = requests.get("http://api.example.com/users")
        response.raise_for_status()
        assert response.status_code == 200
        expected_response = [{"id": 1, "name": "John Doe"}, {"id": 2, "name": "Jane Smith"}]
        assert json.loads(response.text) == expected_response
    except requests.exceptions.RequestException as e:
        allure.step("Encountered request error")
        allure.attach(str(e), "error details")
        pytest.fail("Request failed: " + str(e))

@pytest.mark.allure
def test_userpatch():
    @allure.title("Validating user update")
    @allure.description("Test if PATCH /users/1 updates user details")
    try:
        response = requests.patch(
            "http://api.example.com/users/1",
            json={"new_name": "John Doe Updated"}
        )
        response.raise_for_status()
        assert response.status_code == 200
        assert "new_name" in response.json()
    except requests.exceptions.RequestException as e:
        allure.step("Encountered request error")
        allure.attach(str(e), "error details")
        pytest.fail("Request failed: " + str(e))

if __name__ == "__main__":
    # 执行测试
    pass
