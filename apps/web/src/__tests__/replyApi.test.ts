/**
 * @vitest-environment jsdom
 */

import { beforeEach, describe, expect, it, vi } from 'vitest';
import { composeReply, saveDraft, sendReply } from '../api/reply';

const mockFetch = vi.fn();
vi.stubGlobal('fetch', mockFetch);

describe('reply API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('composeReply', () => {
    it('正しいURLとヘッダーでPOSTリクエストを送信する', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            composedBody: '清書されたメール本文',
            composedSubject: 'Re: テスト件名',
          }),
      });

      await composeReply('test-token', 'email-123', { rawText: 'お疲れ様です' });

      expect(mockFetch).toHaveBeenCalledWith('/api/emails/email-123/compose-reply', {
        method: 'POST',
        headers: {
          Authorization: 'Bearer test-token',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ rawText: 'お疲れ様です' }),
      });
    });

    it('清書結果のレスポンスを返す', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            composedBody: '清書されたメール本文',
            composedSubject: 'Re: テスト件名',
          }),
      });

      const result = await composeReply('test-token', 'email-123', {
        rawText: 'お疲れ様です',
      });

      expect(result).toEqual({
        composedBody: '清書されたメール本文',
        composedSubject: 'Re: テスト件名',
      });
    });

    it('APIエラー時にエラーをスローする', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ detail: { error: '清書に失敗しました' } }),
      });

      await expect(composeReply('test-token', 'email-123', { rawText: 'テスト' })).rejects.toThrow(
        '清書に失敗しました'
      );
    });

    it('APIエラーのJSON解析失敗時はデフォルトエラーメッセージをスローする', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.reject(new Error('parse error')),
      });

      await expect(composeReply('test-token', 'email-123', { rawText: 'テスト' })).rejects.toThrow(
        'メールの清書に失敗しました'
      );
    });
  });

  describe('sendReply', () => {
    it('正しいURLとヘッダーでPOSTリクエストを送信する', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            success: true,
            googleMessageId: 'msg-456',
          }),
      });

      await sendReply('test-token', 'email-123', {
        composedBody: '清書されたメール本文',
        composedSubject: 'Re: テスト件名',
      });

      expect(mockFetch).toHaveBeenCalledWith('/api/emails/email-123/send-reply', {
        method: 'POST',
        headers: {
          Authorization: 'Bearer test-token',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          composedBody: '清書されたメール本文',
          composedSubject: 'Re: テスト件名',
        }),
      });
    });

    it('送信結果のレスポンスを返す', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            success: true,
            googleMessageId: 'msg-456',
          }),
      });

      const result = await sendReply('test-token', 'email-123', {
        composedBody: '清書されたメール本文',
        composedSubject: 'Re: テスト件名',
      });

      expect(result).toEqual({
        success: true,
        googleMessageId: 'msg-456',
      });
    });

    it('APIエラー時にエラーをスローする', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ detail: { error: '送信に失敗しました' } }),
      });

      await expect(
        sendReply('test-token', 'email-123', {
          composedBody: '本文',
          composedSubject: '件名',
        })
      ).rejects.toThrow('送信に失敗しました');
    });

    it('APIエラーのJSON解析失敗時はデフォルトエラーメッセージをスローする', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.reject(new Error('parse error')),
      });

      await expect(
        sendReply('test-token', 'email-123', {
          composedBody: '本文',
          composedSubject: '件名',
        })
      ).rejects.toThrow('メールの送信に失敗しました');
    });
  });

  describe('saveDraft', () => {
    it('正しいURLとヘッダーでPOSTリクエストを送信する', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            success: true,
            googleDraftId: 'draft-789',
          }),
      });

      await saveDraft('test-token', 'email-123', {
        composedBody: '清書されたメール本文',
        composedSubject: 'Re: テスト件名',
      });

      expect(mockFetch).toHaveBeenCalledWith('/api/emails/email-123/save-draft', {
        method: 'POST',
        headers: {
          Authorization: 'Bearer test-token',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          composedBody: '清書されたメール本文',
          composedSubject: 'Re: テスト件名',
        }),
      });
    });

    it('下書き保存結果のレスポンスを返す', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            success: true,
            googleDraftId: 'draft-789',
          }),
      });

      const result = await saveDraft('test-token', 'email-123', {
        composedBody: '清書されたメール本文',
        composedSubject: 'Re: テスト件名',
      });

      expect(result).toEqual({
        success: true,
        googleDraftId: 'draft-789',
      });
    });

    it('APIエラー時にエラーをスローする', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ detail: { error: '下書き保存に失敗しました' } }),
      });

      await expect(
        saveDraft('test-token', 'email-123', {
          composedBody: '本文',
          composedSubject: '件名',
        })
      ).rejects.toThrow('下書き保存に失敗しました');
    });

    it('APIエラーのJSON解析失敗時はデフォルトエラーメッセージをスローする', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.reject(new Error('parse error')),
      });

      await expect(
        saveDraft('test-token', 'email-123', {
          composedBody: '本文',
          composedSubject: '件名',
        })
      ).rejects.toThrow('下書きの保存に失敗しました');
    });
  });
});
