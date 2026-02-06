/**
 * Contacts API functions.
 */

import type {
  ContactCreateRequest,
  ContactCreateResponse,
  ContactsListResponse,
} from '../types/contact';

const API_BASE_URL = '/api';

/**
 * Fetch contacts for the authenticated user.
 *
 * @param idToken - Firebase ID token for authentication
 * @returns Promise resolving to ContactsListResponse
 * @throws Error if the request fails
 */
export async function fetchContacts(idToken: string): Promise<ContactsListResponse> {
  const response = await fetch(`${API_BASE_URL}/contacts`, {
    headers: {
      Authorization: `Bearer ${idToken}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.error || '連絡先の取得に失敗しました');
  }

  return response.json();
}

/**
 * Create a new contact.
 *
 * @param idToken - Firebase ID token for authentication
 * @param request - Contact creation request data
 * @returns Promise resolving to ContactCreateResponse
 * @throws Error if the request fails
 */
export async function createContact(
  idToken: string,
  request: ContactCreateRequest
): Promise<ContactCreateResponse> {
  const response = await fetch(`${API_BASE_URL}/contacts`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${idToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      contact_email: request.contactEmail,
      contact_name: request.contactName,
      gmail_query: request.gmailQuery,
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    if (response.status === 409) {
      throw new Error('この連絡先は既に登録されています');
    }
    throw new Error(error.detail?.error || '連絡先の登録に失敗しました');
  }

  return response.json();
}

/**
 * Delete a contact.
 *
 * @param idToken - Firebase ID token for authentication
 * @param contactId - ID of the contact to delete
 * @throws Error if the request fails
 */
export async function deleteContact(idToken: string, contactId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/contacts/${contactId}`, {
    method: 'DELETE',
    headers: {
      Authorization: `Bearer ${idToken}`,
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    if (response.status === 404) {
      throw new Error('連絡先が見つかりません');
    }
    if (response.status === 403) {
      throw new Error('この連絡先を削除する権限がありません');
    }
    throw new Error(error.detail?.error || '連絡先の削除に失敗しました');
  }
}
