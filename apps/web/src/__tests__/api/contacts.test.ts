/**
 * @vitest-environment jsdom
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';
import { instructContact, relearnContact } from '../../api/contacts';

const API_BASE_URL = '/api';

describe('relearnContact', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('should send POST request to relearn endpoint and return updated contact', async () => {
    const mockContact = {
      id: '1',
      contactEmail: 'tanaka@example.com',
      contactName: '田中部長',
      gmailQuery: 'from:tanaka@example.com',
      isLearningComplete: false,
      learningFailedAt: null,
      createdAt: '2024-01-15T10:30:00+00:00',
      status: 'learning_started' as const,
    };

    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockContact),
    } as Response);

    const result = await relearnContact('mock-token', '1');

    expect(fetchSpy).toHaveBeenCalledWith(`${API_BASE_URL}/contacts/1/relearn`, {
      method: 'POST',
      headers: {
        Authorization: 'Bearer mock-token',
        'Content-Type': 'application/json',
      },
    });
    expect(result).toEqual(mockContact);
  });

  it('should throw error with message when 409 Conflict', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 409,
      json: () => Promise.resolve({ detail: { error: 'not_completed' } }),
    } as unknown as Response);

    await expect(relearnContact('mock-token', '1')).rejects.toThrow('この連絡先は現在学習中です');
  });

  it('should throw error with message when 404 Not Found', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 404,
      json: () => Promise.resolve({ detail: { error: 'not_found' } }),
    } as unknown as Response);

    await expect(relearnContact('mock-token', '1')).rejects.toThrow('連絡先が見つかりません');
  });

  it('should throw generic error for other failures', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 500,
      json: () => Promise.resolve({}),
    } as unknown as Response);

    await expect(relearnContact('mock-token', '1')).rejects.toThrow('再学習に失敗しました');
  });
});

describe('instructContact', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('should send POST request to instruct endpoint and return updated contact', async () => {
    const mockContact = {
      id: '1',
      contactEmail: 'tanaka@example.com',
      contactName: '田中部長',
      gmailQuery: 'from:tanaka@example.com',
      isLearningComplete: true,
      learningFailedAt: null,
      createdAt: '2024-01-15T10:30:00+00:00',
      status: 'learning_complete' as const,
    };

    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockContact),
    } as Response);

    const result = await instructContact('mock-token', '1', "文章の最後には'田中より'と追加して");

    expect(fetchSpy).toHaveBeenCalledWith(`${API_BASE_URL}/contacts/1/instruct`, {
      method: 'POST',
      headers: {
        Authorization: 'Bearer mock-token',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ instruction: "文章の最後には'田中より'と追加して" }),
    });
    expect(result).toEqual(mockContact);
  });

  it('should throw error with message when 404 Not Found', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 404,
      json: () => Promise.resolve({ detail: { error: 'not_found' } }),
    } as unknown as Response);

    await expect(instructContact('mock-token', '1', 'test')).rejects.toThrow(
      '連絡先が見つかりません'
    );
  });

  it('should throw error with message when 409 Conflict', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 409,
      json: () => Promise.resolve({ detail: { error: 'not_completed' } }),
    } as unknown as Response);

    await expect(instructContact('mock-token', '1', 'test')).rejects.toThrow(
      'この連絡先は学習が完了していません'
    );
  });

  it('should throw generic error for other failures', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 500,
      json: () => Promise.resolve({}),
    } as unknown as Response);

    await expect(instructContact('mock-token', '1', 'test')).rejects.toThrow(
      '指示の送信に失敗しました'
    );
  });
});
