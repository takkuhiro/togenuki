/**
 * Email data types for the frontend application.
 */

/**
 * Email data transfer object from API.
 */
export interface Email {
  id: string;
  senderName: string | null;
  senderEmail: string;
  subject: string | null;
  convertedBody: string | null;
  audioUrl: string | null;
  isProcessed: boolean;
  receivedAt: string | null;
  repliedAt: string | null;
  replyBody: string | null;
  replySubject: string | null;
}

/**
 * API response for GET /api/emails.
 */
export interface EmailsResponse {
  emails: Email[];
  total: number;
}
