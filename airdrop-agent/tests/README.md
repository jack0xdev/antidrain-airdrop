# Tests

Offline tests. They use no API key and spend no money: the RPC and the Claude API are mocked.

```bash
docker compose run --rm agent python tests/test_wallet.py      # wallet safety policy
docker compose run --rm agent python tests/test_tg.py          # Telegram approvals / questions
docker compose run --rm agent bash -c "Xvfb :99 & sleep 1; python tests/test_browser.py; python tests/test_runner.py"
```
