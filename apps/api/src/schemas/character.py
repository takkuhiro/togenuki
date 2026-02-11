"""Character schemas for API requests and responses."""

from pydantic import BaseModel


class CharacterResponse(BaseModel):
    """Response model for a single character."""

    id: str
    displayName: str
    description: str


class CharactersListResponse(BaseModel):
    """Response model for GET /api/characters endpoint."""

    characters: list[CharacterResponse]


class UpdateCharacterRequest(BaseModel):
    """Request body for PUT /api/users/character endpoint."""

    characterId: str
