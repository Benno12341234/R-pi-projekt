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

### Cost guard

`ModelRouter` refuses to make more than `MODEL_ROUTER_RATE_LIMIT_MAX_REQUESTS`
API calls per `MODEL_ROUTER_RATE_LIMIT_WINDOW_SECONDS` (default: 60 per hour)
and raises `RateLimitExceeded` instead. This caps what a stuck loop, or a
crash-restart on the Pi, can cost you - even before the provider is asked.
Tune it via those two env vars, or pass `max_requests=`/`window_seconds=`
to `ModelRouter()` directly.

### Running as a systemd service (autostart on the Pi)

```bash
cp .env.example .env        # then fill in your API key(s)
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

sudo cp systemd/model-router.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now model-router.service

# check it's running / see logs
systemctl status model-router.service
journalctl -u model-router.service -f
```

`systemd/model-router.service` assumes user `pi` and the project checked
out at `/home/pi/R-pi-projekt` - adjust `User=`, `WorkingDirectory=`, and
`ExecStart=` if yours differs. It restarts the service on crash
(`Restart=on-failure`), but gives up after 5 restarts within 10 minutes
(`StartLimitBurst`/`StartLimitIntervalSec`) so a broken deploy can't turn
into an endless, paid, restart loop. `ExecStart` currently points at the
demo script - swap it for your real entrypoint once you have one.
