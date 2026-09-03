"""Preferences router — GET/PUT user preferences."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.db.models.preference import DEFAULT_PREFS, Preference
from app.schemas.resources import PrefsResponse, PrefsUpdate

router = APIRouter(prefix="/preferences", tags=["preferences"])


@router.get("", response_model=PrefsResponse)
async def get_prefs(user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(Preference).where(Preference.user_id == user.id)
    )
    pref = result.scalar_one_or_none()
    if not pref:
        # Return defaults if no preferences saved yet
        return DEFAULT_PREFS
    return pref.data


@router.put("", response_model=PrefsResponse)
async def update_prefs(body: PrefsUpdate, user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(Preference).where(Preference.user_id == user.id)
    )
    pref = result.scalar_one_or_none()
    if not pref:
        pref = Preference(user_id=user.id, org_id=user.org_id, data=dict(DEFAULT_PREFS))
        db.add(pref)

    update_data = body.model_dump(exclude_unset=True, by_alias=True)
    current = dict(pref.data)
    current.update(update_data)
    pref.data = current
    await db.flush()
    return pref.data
