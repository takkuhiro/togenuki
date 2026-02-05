/**
 * Email API functions.
 */

import type { EmailsResponse } from '../types/email';

const API_BASE_URL = '/api';

/**
 * Fetch emails for the authenticated user.
 *
 * @param idToken - Firebase ID token for authentication
 * @returns Promise resolving to EmailsResponse
 * @throws Error if the request fails
 */
export async function fetchEmails(idToken: string): Promise<EmailsResponse> {
  const response = await fetch(`${API_BASE_URL}/emails`, {
    headers: {
      Authorization: `Bearer ${idToken}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.error || 'メールの取得に失敗しました');
  }

  return response.json();
}
