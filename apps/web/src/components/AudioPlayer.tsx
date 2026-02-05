/**
 * Audio player component for playing email voice recordings.
 * Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
 */

import { useCallback, useEffect, useRef, useState } from 'react';

interface AudioPlayerProps {
  audioUrl: string | null;
  emailId?: string;
}

/**
 * Audio player component that handles playback of converted email audio.
 *
 * Features:
 * - Play/pause toggle
 * - Error handling for failed audio loads
 * - Automatic state reset on playback end
 */
export function AudioPlayer({ audioUrl }: AudioPlayerProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasPlayed, setHasPlayed] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, []);

  const handlePlayPause = useCallback(async () => {
    if (!audioUrl) return;

    try {
      if (isPlaying && audioRef.current) {
        // Pause
        audioRef.current.pause();
        setIsPlaying(false);
        return;
      }

      // Play
      setIsLoading(true);
      setError(null);

      if (!audioRef.current) {
        // Create new audio element
        const audio = new Audio(audioUrl);

        // Handle playback end
        audio.addEventListener('ended', () => {
          setIsPlaying(false);
          setHasPlayed(true);
        });

        // Handle errors
        audio.addEventListener('error', () => {
          setError('音声の読み込みに失敗しました');
          setIsLoading(false);
          setIsPlaying(false);
        });

        audioRef.current = audio;
      }

      await audioRef.current.play();
      setIsPlaying(true);
      setHasPlayed(true);
    } catch {
      setError('音声の読み込みに失敗しました');
      setIsPlaying(false);
    } finally {
      setIsLoading(false);
    }
  }, [audioUrl, isPlaying]);

  // Don't render if no audio URL
  if (!audioUrl) {
    return null;
  }

  const getButtonLabel = () => {
    if (isLoading) return '読み込み中...';
    if (isPlaying) return '一時停止';
    if (hasPlayed) return 'もう一度聴く';
    return 'とげぬき再生';
  };

  return (
    <div className="audio-player">
      <button
        type="button"
        onClick={handlePlayPause}
        disabled={isLoading}
        aria-label={getButtonLabel()}
        className="audio-player-button"
      >
        {isLoading ? (
          <span className="loading-spinner">読み込み中...</span>
        ) : isPlaying ? (
          <>
            <PauseIcon />
            一時停止
          </>
        ) : (
          <>
            <PlayIcon />
            {hasPlayed ? 'もう一度聴く' : 'とげぬき再生'}
          </>
        )}
      </button>

      {error && (
        <p className="audio-error" role="alert">
          エラー: {error}
        </p>
      )}
    </div>
  );
}

// Simple icon components
function PlayIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M8 5v14l11-7z" />
    </svg>
  );
}

function PauseIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
    </svg>
  );
}
