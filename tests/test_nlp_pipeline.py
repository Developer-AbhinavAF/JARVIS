from jarvis.ai_os.nlp.pipeline import NLPPipeline
import jarvis.router_service as rs


def test_detect_intent_monkeypatch():
    # Monkeypatch the router_client.chat to return a predictable result
    original = rs.router_client.chat

    try:
        rs.router_client.chat = lambda messages, **kwargs: "greet"
        pipeline = NLPPipeline()
        intent = pipeline.detect_intent("hello there")
        assert "greet" in intent.lower()
    finally:
        rs.router_client.chat = original
