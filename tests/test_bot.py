from main import build_application


def test_build_application():
    app = build_application()
    assert app is not None
