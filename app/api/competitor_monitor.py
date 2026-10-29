from fastapi import APIRouter, Depends

from app.auth.security import get_current_user
from app.services.competitor_monitor_service import analyze_prices, monitoring_dashboard

router = APIRouter(prefix='/competitor-monitor', tags=['competitor-monitor'])


@router.get('')
def get_dashboard(current_user: dict = Depends(get_current_user)):
    return monitoring_dashboard(current_user)


@router.post('/analyze')
def post_analysis(current_user: dict = Depends(get_current_user)):
    return analyze_prices(current_user)
