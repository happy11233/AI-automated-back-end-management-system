PYTHON ?= $(shell if [ -x .venv/bin/python ]; then echo .venv/bin/python; else echo python3; fi)
VERIFY_API_BASE_URL ?= http://127.0.0.1:8001
DEMO_API_BASE_URL ?= http://127.0.0.1:8001
DEMO_FRONTEND_URL ?= http://127.0.0.1:5173

.PHONY: demo-check verify-quick verify-api verify-release

demo-check:
	$(PYTHON) scripts/verify_demo_readiness.py --api-base-url $(DEMO_API_BASE_URL) --frontend-url $(DEMO_FRONTEND_URL)

verify-quick:
	$(PYTHON) scripts/verify_all.py --profile quick

verify-api:
	VERIFY_API_BASE_URL=$(VERIFY_API_BASE_URL) $(PYTHON) scripts/verify_all.py --profile api

verify-release:
	VERIFY_API_BASE_URL=$(VERIFY_API_BASE_URL) $(PYTHON) scripts/verify_all.py --profile release
