from fastapi import APIRouter
from mechabellum_replay_parser.events.schemas import SupplyResponseBody

router = APIRouter(prefix="/ui")


@router.post("/supply-response", status_code=204)
async def supply_response(body: SupplyResponseBody) -> None:
    # Phase 3 will wire this into the coach pipeline via recommendation_id
    pass
