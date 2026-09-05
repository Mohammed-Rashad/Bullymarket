from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.bets.router import router as bets_router
from app.modules.groups.router import router as groups_router
from app.modules.house.router import router as house_router
from app.modules.leaderboard.router import router as leaderboard_router
from app.modules.media.router import router as media_router
from app.modules.notifications.router import router as notifications_router
from app.modules.resolution.router import router as resolution_router
from app.modules.trading.router import router as trading_router
from app.modules.users.router import router as users_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(groups_router)
api_router.include_router(house_router)
api_router.include_router(bets_router)
api_router.include_router(trading_router)
api_router.include_router(resolution_router)
api_router.include_router(leaderboard_router)
api_router.include_router(notifications_router)
api_router.include_router(media_router)
