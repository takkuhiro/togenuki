const API_BASE_URL = '/api';

export interface ComposeReplyRequest {
  rawText: string;
}

export interface ComposeReplyResponse {
  composedBody: string;
  composedSubject: string;
}

export interface SendReplyRequest {
  composedBody: string;
  composedSubject: string;
}

export interface SendReplyResponse {
  success: boolean;
  googleMessageId: string;
}

export interface SaveDraftRequest {
  composedBody: string;
  composedSubject: string;
}

export interface SaveDraftResponse {
  success: boolean;
  googleDraftId: string;
}

export async function composeReply(
  idToken: string,
  emailId: string,
  request: ComposeReplyRequest
): Promise<ComposeReplyResponse> {
  const response = await fetch(`${API_BASE_URL}/emails/${emailId}/compose-reply`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${idToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.error || 'メールの清書に失敗しました');
  }

  return response.json();
}

export async function sendReply(
  idToken: string,
  emailId: string,
  request: SendReplyRequest
): Promise<SendReplyResponse> {
  const response = await fetch(`${API_BASE_URL}/emails/${emailId}/send-reply`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${idToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.error || 'メールの送信に失敗しました');
  }

  return response.json();
}

export async function saveDraft(
  idToken: string,
  emailId: string,
  request: SaveDraftRequest
): Promise<SaveDraftResponse> {
  const response = await fetch(`${API_BASE_URL}/emails/${emailId}/save-draft`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${idToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail?.error || '下書きの保存に失敗しました');
  }

  return response.json();
}
