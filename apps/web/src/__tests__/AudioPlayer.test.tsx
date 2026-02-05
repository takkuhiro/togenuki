/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AudioPlayer } from "../components/AudioPlayer";

// Mock HTMLMediaElement
const mockPlay = vi.fn(() => Promise.resolve());
const mockPause = vi.fn();
let mockAudioElement: Partial<HTMLAudioElement>;

beforeEach(() => {
  mockAudioElement = {
    play: mockPlay,
    pause: mockPause,
    currentTime: 0,
    duration: 100,
    paused: true,
    addEventListener: vi.fn((event: string, handler: EventListener) => {
      if (event === "ended") {
        // Store the handler to call it later
        (mockAudioElement as { _onEndedHandler?: EventListener })._onEndedHandler = handler;
      }
    }),
    removeEventListener: vi.fn(),
  };

  vi.stubGlobal("Audio", vi.fn(() => mockAudioElement));
});

describe("AudioPlayer", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPlay.mockClear();
    mockPause.mockClear();
  });

  describe("再生ボタンクリック (Requirement 5.1)", () => {
    it("should load and play audio when play button is clicked", async () => {
      const user = userEvent.setup();

      render(<AudioPlayer audioUrl="https://example.com/audio.mp3" emailId="1" />);

      const playButton = screen.getByRole("button", { name: /再生|やさしく聴く/ });
      await user.click(playButton);

      expect(mockPlay).toHaveBeenCalled();
    });

    it("should not show play button when audioUrl is null", () => {
      render(<AudioPlayer audioUrl={null} emailId="1" />);

      expect(
        screen.queryByRole("button", { name: /再生|やさしく聴く/ })
      ).not.toBeInTheDocument();
    });
  });

  describe("再生中の表示変更 (Requirement 5.2)", () => {
    it("should show pause button while audio is playing", async () => {
      const user = userEvent.setup();

      render(<AudioPlayer audioUrl="https://example.com/audio.mp3" emailId="1" />);

      const playButton = screen.getByRole("button", { name: /再生|やさしく聴く/ });
      await user.click(playButton);

      await waitFor(() => {
        expect(screen.getByRole("button", { name: /停止|一時停止/ })).toBeInTheDocument();
      });
    });
  });

  describe("停止ボタンクリック (Requirement 5.3)", () => {
    it("should stop audio when stop button is clicked", async () => {
      const user = userEvent.setup();

      render(<AudioPlayer audioUrl="https://example.com/audio.mp3" emailId="1" />);

      // Start playing
      const playButton = screen.getByRole("button", { name: /再生|やさしく聴く/ });
      await user.click(playButton);

      await waitFor(() => {
        expect(screen.getByRole("button", { name: /停止|一時停止/ })).toBeInTheDocument();
      });

      // Stop
      const stopButton = screen.getByRole("button", { name: /停止|一時停止/ });
      await user.click(stopButton);

      expect(mockPause).toHaveBeenCalled();
    });
  });

  describe("再生完了時の状態変更 (Requirement 5.4)", () => {
    it("should show play button again after playback ends", async () => {
      const user = userEvent.setup();

      render(<AudioPlayer audioUrl="https://example.com/audio.mp3" emailId="1" />);

      // Start playing
      const playButton = screen.getByRole("button", { name: /再生|やさしく聴く/ });
      await user.click(playButton);

      await waitFor(() => {
        expect(screen.getByRole("button", { name: /停止|一時停止/ })).toBeInTheDocument();
      });

      // Simulate playback ended
      const onEndedHandler = (mockAudioElement as { _onEndedHandler?: EventListener })._onEndedHandler;
      if (onEndedHandler) {
        onEndedHandler(new Event("ended"));
      }

      await waitFor(() => {
        expect(screen.getByRole("button", { name: /再生|もう一度聴く/ })).toBeInTheDocument();
      });
    });
  });

  describe("読み込みエラー時のエラーメッセージ (Requirement 5.5)", () => {
    it("should display error message when audio fails to load", async () => {
      mockPlay.mockRejectedValueOnce(new Error("Failed to load audio"));
      const user = userEvent.setup();

      render(<AudioPlayer audioUrl="https://example.com/audio.mp3" emailId="1" />);

      const playButton = screen.getByRole("button", { name: /再生|やさしく聴く/ });
      await user.click(playButton);

      await waitFor(() => {
        expect(screen.getByText(/エラー|音声の読み込みに失敗/)).toBeInTheDocument();
      });
    });
  });
});
