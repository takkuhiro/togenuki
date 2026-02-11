/**
 * Characters API functions.
 */

const API_BASE_URL = '/api';

/**
 * Character data from API.
 */
export interface Character {
  id: string;
  displayName: string;
  description: string;
}

/**
 * API response for GET /api/characters.
 */
export interface CharactersListResponse {
  characters: Character[];
}

/**
 * Fetch all available characters (no auth required).
 *
 * @returns Promise resolving to CharactersListResponse
 * @throws Error if the request fails
 */
export async function fetchCharacters(): Promise<CharactersListResponse> {
  const response = await fetch(`${API_BASE_URL}/characters`, {
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.error || 'キャラクター一覧の取得に失敗しました');
  }

  return response.json();
}

/**
 * Fetch current user's selected character.
 *
 * @param idToken - Firebase ID token for authentication
 * @returns Promise resolving to Character
 * @throws Error if the request fails
 */
export async function fetchCurrentCharacter(idToken: string): Promise<Character> {
  const response = await fetch(`${API_BASE_URL}/users/character`, {
    headers: {
      Authorization: `Bearer ${idToken}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.error || '現在のキャラクターの取得に失敗しました');
  }

  return response.json();
}

/**
 * Update user's selected character.
 *
 * @param idToken - Firebase ID token for authentication
 * @param characterId - ID of the character to select
 * @returns Promise resolving to updated Character
 * @throws Error if the request fails
 */
export async function updateCharacter(idToken: string, characterId: string): Promise<Character> {
  const response = await fetch(`${API_BASE_URL}/users/character`, {
    method: 'PUT',
    headers: {
      Authorization: `Bearer ${idToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ characterId }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.error || 'キャラクターの更新に失敗しました');
  }

  return response.json();
}
