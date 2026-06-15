from fastapi import APIRouter, Request

from mechabellum_replay_parser.events.schemas import SupplyResponseBody

router = APIRouter(prefix="/ui")


@router.post("/supply-response", status_code=204)
async def supply_response(body: SupplyResponseBody, request: Request) -> None:
    pending: dict = request.app.state.pending_supplies
    future = pending.get(body.recommendation_id)
    if future is None or future.done():
        return
    supply_value = None if body.cancelled else body.supply
    future.set_result(supply_value)
