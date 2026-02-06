/**
 * Contact data types for the frontend application.
 */

/**
 * Contact data transfer object from API.
 */
export interface Contact {
  id: string;
  contactEmail: string;
  contactName: string | null;
  gmailQuery: string | null;
  isLearningComplete: boolean;
  learningFailedAt: string | null;
  createdAt: string;
  status: 'learning_started' | 'learning_complete' | 'learning_failed';
}

/**
 * API response for GET /api/contacts.
 */
export interface ContactsListResponse {
  contacts: Contact[];
  total: number;
}

/**
 * Request body for POST /api/contacts.
 */
export interface ContactCreateRequest {
  contactEmail: string;
  contactName?: string;
  gmailQuery?: string;
}

/**
 * API response for POST /api/contacts.
 */
export interface ContactCreateResponse {
  id: string;
  contactEmail: string;
  contactName: string | null;
  gmailQuery: string | null;
  isLearningComplete: boolean;
  learningFailedAt: string | null;
  createdAt: string;
  status: 'learning_started' | 'learning_complete' | 'learning_failed';
}
