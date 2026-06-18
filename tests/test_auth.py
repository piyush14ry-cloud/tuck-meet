from app.models import User


def _register(client, email="alice@tuck.dartmouth.edu", pw="longenoughpw1"):
    return client.post(
        "/register",
        data={"name": "Alice Adams", "email": email, "password": pw, "confirm": pw},
        follow_redirects=True,
    )


def test_rejects_non_tuck_email(client, db):
    resp = client.post(
        "/register",
        data={"name": "Bob", "email": "bob@gmail.com",
              "password": "longenoughpw1", "confirm": "longenoughpw1"},
        follow_redirects=True,
    )
    assert b"email address" in resp.data
    assert User.query.count() == 0


def test_rejects_short_password(client, db):
    resp = client.post(
        "/register",
        data={"name": "Bob", "email": "bob@tuck.dartmouth.edu",
              "password": "short", "confirm": "short"},
        follow_redirects=True,
    )
    assert b"at least 12 characters" in resp.data
    assert User.query.count() == 0


def test_register_creates_unverified_user_and_hashes_password(client, db):
    _register(client)
    user = User.query.filter_by(email="alice@tuck.dartmouth.edu").first()
    assert user is not None
    assert user.email_verified is False
    assert user.password_hash != "longenoughpw1"
    assert user.check_password("longenoughpw1")


def test_unverified_user_cannot_login(client, db):
    _register(client)
    resp = client.post(
        "/login",
        data={"email": "alice@tuck.dartmouth.edu", "password": "longenoughpw1"},
        follow_redirects=True,
    )
    assert b"verify your email" in resp.data.lower()


def test_verified_user_can_login(client, db):
    _register(client)
    user = User.query.filter_by(email="alice@tuck.dartmouth.edu").first()
    user.email_verified = True
    db.session.commit()
    resp = client.post(
        "/login",
        data={"email": "alice@tuck.dartmouth.edu", "password": "longenoughpw1"},
        follow_redirects=True,
    )
    assert b"Dashboard" in resp.data
