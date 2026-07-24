PYTHON ?= $(shell if [ -x .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi)
VERIFY_API_BASE_URL ?= http://127.0.0.1:8001

.PHONY: verify-quick verify-api verify-release

verify-quick:
	$(PYTHON) scripts/verify_all.py --profile quick

verify-api:
	VERIFY_API_BASE_URL=$(VERIFY_API_BASE_URL) $(PYTHON) scripts/verify_all.py --profile api

verify-release:
	VERIFY_API_BASE_URL=$(VERIFY_API_BASE_URL) $(PYTHON) scripts/verify_all.py --profile release
