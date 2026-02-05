/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import { EmailList } from "../components/EmailList";
import * as emailApi from "../api/emails";

// Mock the email API
vi.mock("../api/emails", () => ({
  fetchEmails: vi.fn(),
}));

// Mock AuthContext
vi.mock("../contexts/AuthContext", () => ({
  useAuth: vi.fn(() => ({
    idToken: "mock-token",
    user: { uid: "test-uid", email: "test@example.com" },
    isLoading: false,
  })),
}));

const mockEmails = [
  {
    id: "1",
    senderName: "田中部長",
    senderEmail: "tanaka@example.com",
    subject: "重要：プロジェクト進捗報告",
    convertedBody: "変換後テキスト1",
    audioUrl: "https://example.com/audio1.mp3",
    isProcessed: true,
    receivedAt: "2024-01-15T10:30:00+00:00",
  },
  {
    id: "2",
    senderName: "佐藤課長",
    senderEmail: "sato@example.com",
    subject: "週報提出のお願い",
    convertedBody: null,
    audioUrl: null,
    isProcessed: false,
    receivedAt: "2024-01-14T09:00:00+00:00",
  },
];

describe("EmailList", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("メール一覧表示 (Requirement 4.3, 4.4)", () => {
    it("should display email list with sender name, subject, and converted text", async () => {
      vi.mocked(emailApi.fetchEmails).mockResolvedValue({
        emails: mockEmails,
        total: 2,
      });

      render(<EmailList />);

      await waitFor(() => {
        expect(screen.getByText("田中部長")).toBeInTheDocument();
        expect(screen.getByText("重要：プロジェクト進捗報告")).toBeInTheDocument();
      });
    });

    it("should display emails in card format", async () => {
      vi.mocked(emailApi.fetchEmails).mockResolvedValue({
        emails: mockEmails,
        total: 2,
      });

      render(<EmailList />);

      await waitFor(() => {
        // Each email should be in a card
        const cards = screen.getAllByRole("article");
        expect(cards).toHaveLength(2);
      });
    });

    it("should show loading state while fetching", async () => {
      vi.mocked(emailApi.fetchEmails).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );

      render(<EmailList />);

      expect(screen.getByText("読み込み中...")).toBeInTheDocument();
    });
  });

  describe("処理中メールのローディング表示 (Requirement 4.5)", () => {
    it("should show loading indicator for unprocessed emails", async () => {
      vi.mocked(emailApi.fetchEmails).mockResolvedValue({
        emails: mockEmails,
        total: 2,
      });

      render(<EmailList />);

      await waitFor(() => {
        // Find the card for佐藤課長 (unprocessed)
        const unprocessedCard = screen.getByText("佐藤課長").closest("article");
        expect(unprocessedCard).toBeInTheDocument();
        if (unprocessedCard) {
          expect(within(unprocessedCard).getByText("処理中...")).toBeInTheDocument();
        }
      });
    });
  });

  describe("空リスト", () => {
    it("should display empty state when no emails", async () => {
      vi.mocked(emailApi.fetchEmails).mockResolvedValue({
        emails: [],
        total: 0,
      });

      render(<EmailList />);

      await waitFor(() => {
        expect(screen.getByText("メールがありません")).toBeInTheDocument();
      });
    });
  });

  describe("エラーハンドリング", () => {
    it("should display error message on fetch failure", async () => {
      vi.mocked(emailApi.fetchEmails).mockRejectedValue(
        new Error("Network error")
      );

      render(<EmailList />);

      await waitFor(() => {
        expect(screen.getByText(/エラー/)).toBeInTheDocument();
      });
    });
  });
});
