/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within, fireEvent } from "@testing-library/react";
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
    it("should show loading indicator for unprocessed emails when expanded", async () => {
      vi.mocked(emailApi.fetchEmails).mockResolvedValue({
        emails: mockEmails,
        total: 2,
      });

      render(<EmailList />);

      await waitFor(() => {
        // Find the card for佐藤課長 (unprocessed)
        const unprocessedCard = screen.getByText("佐藤課長").closest("article");
        expect(unprocessedCard).toBeInTheDocument();
      });

      // Click to expand the unprocessed email card
      const unprocessedCard = screen.getByText("佐藤課長").closest("article");
      const header = unprocessedCard?.querySelector(".email-card-header");
      if (header) {
        fireEvent.click(header);
      }

      await waitFor(() => {
        if (unprocessedCard) {
          expect(within(unprocessedCard).getByText("処理中...")).toBeInTheDocument();
        }
      });
    });
  });

  describe("トグル形式", () => {
    it("should expand email card on header click", async () => {
      vi.mocked(emailApi.fetchEmails).mockResolvedValue({
        emails: mockEmails,
        total: 2,
      });

      render(<EmailList />);

      await waitFor(() => {
        expect(screen.getByText("田中部長")).toBeInTheDocument();
      });

      // Initially, converted body should not be visible
      expect(screen.queryByText("変換後テキスト1")).not.toBeInTheDocument();

      // Click to expand the first email card
      const processedCard = screen.getByText("田中部長").closest("article");
      const header = processedCard?.querySelector(".email-card-header");
      if (header) {
        fireEvent.click(header);
      }

      // After expansion, converted body should be visible
      await waitFor(() => {
        expect(screen.getByText("変換後テキスト1")).toBeInTheDocument();
      });
    });

    it("should collapse email card when clicking header again", async () => {
      vi.mocked(emailApi.fetchEmails).mockResolvedValue({
        emails: mockEmails,
        total: 2,
      });

      render(<EmailList />);

      await waitFor(() => {
        expect(screen.getByText("田中部長")).toBeInTheDocument();
      });

      const processedCard = screen.getByText("田中部長").closest("article");
      const header = processedCard?.querySelector(".email-card-header");

      // Click to expand
      if (header) {
        fireEvent.click(header);
      }

      await waitFor(() => {
        expect(screen.getByText("変換後テキスト1")).toBeInTheDocument();
      });

      // Click again to collapse
      if (header) {
        fireEvent.click(header);
      }

      await waitFor(() => {
        expect(screen.queryByText("変換後テキスト1")).not.toBeInTheDocument();
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
