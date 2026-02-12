/**
 * @vitest-environment jsdom
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fetchCharacters, fetchCurrentCharacter, updateCharacter } from '../../api/characters';

const API_BASE_URL = '/api';

describe('characters API', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  describe('fetchCharacters', () => {
    it('should send GET request to characters endpoint without auth', async () => {
      const mockResponse = {
        characters: [
          { id: 'gyaru', displayName: '全肯定お姉さん', description: 'desc1' },
          { id: 'senpai', displayName: '優しい先輩', description: 'desc2' },
          { id: 'butler', displayName: '冷静な執事', description: 'desc3' },
        ],
      };

      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      } as Response);

      const result = await fetchCharacters();

      expect(fetchSpy).toHaveBeenCalledWith(`${API_BASE_URL}/characters`, {
        headers: {
          'Content-Type': 'application/json',
        },
      });
      expect(result).toEqual(mockResponse);
    });

    it('should throw error on fetch failure', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValue({
        ok: false,
        status: 500,
        json: () => Promise.resolve({}),
      } as unknown as Response);

      await expect(fetchCharacters()).rejects.toThrow('キャラクター一覧の取得に失敗しました');
    });
  });

  describe('fetchCurrentCharacter', () => {
    it('should send GET request with auth header', async () => {
      const mockResponse = { id: 'gyaru', displayName: '全肯定お姉さん', description: 'desc1' };

      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      } as Response);

      const result = await fetchCurrentCharacter('mock-token');

      expect(fetchSpy).toHaveBeenCalledWith(`${API_BASE_URL}/users/character`, {
        headers: {
          Authorization: 'Bearer mock-token',
          'Content-Type': 'application/json',
        },
      });
      expect(result).toEqual(mockResponse);
    });

    it('should throw error when unauthorized', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValue({
        ok: false,
        status: 401,
        json: () => Promise.resolve({ detail: { error: 'unauthorized' } }),
      } as unknown as Response);

      await expect(fetchCurrentCharacter('bad-token')).rejects.toThrow('unauthorized');
    });
  });

  describe('updateCharacter', () => {
    it('should send PUT request with characterId in body', async () => {
      const mockResponse = { id: 'butler', displayName: '冷静な執事', description: 'desc3' };

      const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockResponse),
      } as Response);

      const result = await updateCharacter('mock-token', 'butler');

      expect(fetchSpy).toHaveBeenCalledWith(`${API_BASE_URL}/users/character`, {
        method: 'PUT',
        headers: {
          Authorization: 'Bearer mock-token',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ characterId: 'butler' }),
      });
      expect(result).toEqual(mockResponse);
    });

    it('should throw error for invalid character ID', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValue({
        ok: false,
        status: 400,
        json: () => Promise.resolve({ detail: { error: 'invalid_character_id' } }),
      } as unknown as Response);

      await expect(updateCharacter('mock-token', 'invalid')).rejects.toThrow(
        'invalid_character_id'
      );
    });

    it('should throw default error when JSON parsing fails', async () => {
      vi.spyOn(globalThis, 'fetch').mockResolvedValue({
        ok: false,
        status: 500,
        json: () => Promise.reject(new Error('parse error')),
      } as unknown as Response);

      await expect(updateCharacter('mock-token', 'butler')).rejects.toThrow(
        'キャラクターの更新に失敗しました'
      );
    });
  });
});
