# R-Pi-Projekt

Raspberry Pi Projekt.

## AI Model Routing

`model_router/` routes a prompt to the cheapest model tier that can plausibly
handle it (`simple` / `standard` / `complex`, picked by a lightweight
heuristic in `complexity.py`), and falls back to the next configured
provider if one fails or has no API key set.

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...   # and/or
export OPENAI_API_KEY=...
python examples/model_routing_demo.py
```

```python
from model_router import ModelRouter

router = ModelRouter()
result = router.route("Explain what a Kalman filter does.")
print(result.provider, result.model, result.tier)
print(result.text)
```

Which models back each tier is defined in `model_router/config.py`
(`DEFAULT_TIERS`) - update it when a provider ships a new model.
