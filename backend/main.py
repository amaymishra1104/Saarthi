from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from backend.config import settings
from backend.db.session import init_db
from backend.api.routes import router as api_router
from backend.mock_payments.service import mock_payments_service
from backend.mock_payments.models import ReversalRequest

app = FastAPI(
    title="SAARTHI Backend API",
    description="Autonomous AI teammate turning payment complaints into verified, resolved cases.",
    version="1.0.0"
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    init_db()

# Mount Main Application API
app.include_router(api_router, prefix="/api")

# ---------------------------------------------------------------------------
# Simulated Connected System: Payments Core API
# (Built as an authentic API surface with key authentication)
# ---------------------------------------------------------------------------
def verify_payments_key(x_api_key: str = Header(None)):
    if x_api_key != settings.PAYMENTS_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid Payments Core API Key")

@app.get("/payments-core/transactions/{txn_id}")
async def core_get_transaction(txn_id: str, _=Depends(verify_payments_key)):
    txn = await mock_payments_service.get_transaction(txn_id)
    return txn.model_dump()

@app.get("/payments-core/transactions")
async def core_search_transactions(
    customer_id: str = None,
    amount: float = None,
    date: str = None,
    _=Depends(verify_payments_key)
):
    txns = await mock_payments_service.search_transactions(customer_id, amount, date)
    return [t.model_dump() for t in txns]

@app.get("/payments-core/transactions/{txn_id}/status")
async def core_check_status(txn_id: str, _=Depends(verify_payments_key)):
    return await mock_payments_service.check_transaction_status(txn_id)

@app.post("/payments-core/transactions/{txn_id}/reversal")
async def core_initiate_reversal(
    txn_id: str,
    req: ReversalRequest,
    idempotency_key: str = Header(None, alias="Idempotency-Key"),
    _=Depends(verify_payments_key)
):
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key header is strictly required.")
    res = await mock_payments_service.initiate_reversal(
        txn_id=txn_id,
        idempotency_key=idempotency_key,
        reason=req.reason,
        requested_by=req.requested_by
    )
    return res.model_dump()

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "SAARTHI",
        "mock_llm": settings.MOCK_LLM,
        "auto_limit": settings.AUTO_ACTION_LIMIT
    }

