from brms.core.metrics.base import MetricRegistry


class FakeMetric:
    name = "fake"
    requires_history = False

    def compute(self, bank, market_state, history=None):
        return 42


def test_register_and_get():
    reg = MetricRegistry()
    m = FakeMetric()
    reg.register(m)
    assert reg.get("fake") is m


def test_all_metrics():
    reg = MetricRegistry()
    reg.register(FakeMetric())
    assert len(reg.all_metrics()) == 1
