"""Character selection API endpoints.

Provides endpoints for:
- GET /api/characters - List all available characters (public, no auth)
- GET /api/users/character - Get current user's selected character (auth required)
- PUT /api/users/character - Update user's selected character (auth required)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.auth.schemas import FirebaseUser
from src.database import get_db
from src.repositories.email_repository import get_user_by_firebase_uid
from src.schemas.character import (
    CharacterResponse,
    CharactersListResponse,
    UpdateCharacterRequest,
)
from src.services.character_service import get_all_characters, get_character

router = APIRouter()


@router.get("/characters", response_model=CharactersListResponse)
async def list_characters() -> CharactersListResponse:
    """Return all available characters.

    This endpoint is public and does not require authentication.
    """
    characters = get_all_characters()
    return CharactersListResponse(
        characters=[
            CharacterResponse(
                id=c.id,
                displayName=c.display_name,
                description=c.description,
            )
            for c in characters
        ]
    )


@router.get("/users/character", response_model=CharacterResponse)
async def get_user_character(
    current_user: FirebaseUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CharacterResponse:
    """Return the current user's selected character.

    Falls back to default character (gyaru) if no selection.
    """
    user = await get_user_by_firebase_uid(session, current_user.uid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "user_not_found"},
        )

    character = get_character(user.selected_character_id)
    return CharacterResponse(
        id=character.id,
        displayName=character.display_name,
        description=character.description,
    )


@router.put("/users/character", response_model=CharacterResponse)
async def update_user_character(
    request: UpdateCharacterRequest,
    current_user: FirebaseUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CharacterResponse:
    """Update the current user's selected character.

    Returns 400 if the character ID is invalid.
    """
    # Validate character ID
    all_ids = [c.id for c in get_all_characters()]
    if request.characterId not in all_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_character_id"},
        )

    user = await get_user_by_firebase_uid(session, current_user.uid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "user_not_found"},
        )

    user.selected_character_id = request.characterId
    await session.commit()

    character = get_character(request.characterId)
    return CharacterResponse(
        id=character.id,
        displayName=character.display_name,
        description=character.description,
    )
