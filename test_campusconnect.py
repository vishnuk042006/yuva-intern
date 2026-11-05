"""
CampusConnect AI - automated tests (pytest)

Run from your project folder:
    pip install pytest
    pytest -v

BEFORE RUNNING: edit the CONFIG section so the names match your project.
Tests whose function/route does not exist are skipped, not failed.
"""
import pytest

# ----------------------------- CONFIG ---------------------------------------
APP_MODULE = "app"                 # file containing your Flask app  (app.py)
APP_OBJECT = "app"                 # the Flask object inside it      (app = Flask(...))

SUBMIT_ROUTE = "/submit"           # route that receives the issue form (POST)
STATUS_ROUTE = "/status/{id}"      # route that shows one issue's status (GET)
FIELD_TITLE = "title"              # form field names
FIELD_DESC = "description"

NLP_MODULE = "nlp"                 # file with your NLP functions (nlp.py)
FN_PREPROCESS = "preprocess_text"  # text -> cleaned text
FN_CLASSIFY = "classify_issue"     # text -> category / department
FN_PRIORITY = "suggest_priority"   # text -> "High" / "Medium" / "Low"
# ----------------------------------------------------------------------------


# ------------------------------ fixtures ------------------------------------
@pytest.fixture(scope="module")
def client():
    mod = pytest.importorskip(APP_MODULE)
    flask_app = getattr(mod, APP_OBJECT)
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as c:
        yield c


def nlp_fn(name):
    mod = pytest.importorskip(NLP_MODULE)
    fn = getattr(mod, name, None)
    if fn is None:
        pytest.skip(f"{NLP_MODULE}.{name} not found - update CONFIG")
    return fn


def post_issue(client, title="Water leakage", desc="Water leakage in hostel block A"):
    return client.post(SUBMIT_ROUTE, data={FIELD_TITLE: title, FIELD_DESC: desc},
                       follow_redirects=True)


# ------------------------------ UNIT TESTS ----------------------------------
def test_tc05_classifier_known_issue():
    result = nlp_fn(FN_CLASSIFY)("Water leakage in hostel block")
    assert result  # should return a category / department, not empty
    assert "maint" in str(result).lower() or "hostel" in str(result).lower()


def test_tc06_classifier_unknown_text_does_not_crash():
    result = nlp_fn(FN_CLASSIFY)("asdf qwerty zzzz")
    assert result is not None  # fallback such as 'General' is fine


def test_tc07_urgent_issue_gets_high_priority():
    result = nlp_fn(FN_PRIORITY)("Fire hazard and exposed wires near the lab, urgent danger")
    assert str(result).lower() == "high"


def test_preprocess_cleans_text():
    cleaned = nlp_fn(FN_PREPROCESS)("  HELLO, World!!!  ")
    assert cleaned == cleaned.lower()
    assert "!" not in cleaned


# -------------------------- EDGE CASES / VALIDATION -------------------------
def test_tc01_valid_submission(client):
    r = post_issue(client)
    assert r.status_code == 200


def test_tc02_empty_description_rejected(client):
    r = post_issue(client, desc="")
    assert r.status_code in (200, 400, 422)
    assert r.status_code != 500  # must never crash


def test_tc03_very_long_text_handled(client):
    r = post_issue(client, desc="leak " * 2000)
    assert r.status_code != 500


def test_tc04_html_is_not_executed(client):
    r = post_issue(client, desc="<script>alert('x')</script> broken fan")
    assert r.status_code != 500
    assert b"<script>alert('x')</script>" not in r.data  # must be escaped


def test_missing_fields_do_not_crash(client):
    r = client.post(SUBMIT_ROUTE, data={})
    assert r.status_code != 500


# ------------------------------ INTEGRATION ---------------------------------
def test_tc09_status_page_loads(client):
    r = client.get(STATUS_ROUTE.format(id=1))
    assert r.status_code in (200, 302, 403, 404)  # any handled response, no 500


def test_invalid_issue_id_handled(client):
    r = client.get(STATUS_ROUTE.format(id=999999))
    assert r.status_code in (302, 403, 404)


# -------------------------------- SYSTEM ------------------------------------
def test_tc12_full_flow_submit_then_view(client):
    r = post_issue(client, "Projector broken", "Projector not working in room 204")
    assert r.status_code == 200
    r2 = client.get("/")
    assert r2.status_code == 200
