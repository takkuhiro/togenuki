/**
 * Character selector component for choosing email conversion character.
 * Requirements: 5.1, 5.2, 5.3, 5.4
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  type Character,
  fetchCharacters,
  fetchCurrentCharacter,
  updateCharacter,
} from '../api/characters';
import { useAuth } from '../contexts/AuthContext';

/**
 * Character selector component that displays character cards
 * and allows the user to select their preferred character.
 */
export function CharacterSelector() {
  const { idToken } = useAuth();
  const [characters, setCharacters] = useState<Character[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [playingVoiceId, setPlayingVoiceId] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Fetch characters list and current selection on mount
  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [charactersRes, currentRes] = await Promise.all([
          fetchCharacters(),
          idToken ? fetchCurrentCharacter(idToken) : Promise.resolve(null),
        ]);

        if (cancelled) return;

        setCharacters(charactersRes.characters);
        if (currentRes) {
          setSelectedId(currentRes.id);
        }
        setError(null);
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : 'エラーが発生しました');
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    load();

    return () => {
      cancelled = true;
    };
  }, [idToken]);

  // Cleanup audio on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
    };
  }, []);

  const handlePlayVoice = useCallback(
    (e: React.MouseEvent, characterId: string) => {
      e.stopPropagation();

      // If same character is playing, pause it
      if (playingVoiceId === characterId && audioRef.current) {
        audioRef.current.pause();
        setPlayingVoiceId(null);
        return;
      }

      // Stop previous audio
      if (audioRef.current) {
        audioRef.current.pause();
      }

      const audio = new Audio(`/${characterId}.wav`);
      audio.addEventListener('ended', () => {
        setPlayingVoiceId(null);
      });
      audioRef.current = audio;
      audio.play();
      setPlayingVoiceId(characterId);
    },
    [playingVoiceId]
  );

  const handleSelect = useCallback(
    async (characterId: string) => {
      if (!idToken || characterId === selectedId || isSaving) return;

      setIsSaving(true);
      setError(null);

      try {
        const updated = await updateCharacter(idToken, characterId);
        setSelectedId(updated.id);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'エラーが発生しました');
      } finally {
        setIsSaving(false);
      }
    },
    [idToken, selectedId, isSaving]
  );

  if (isLoading) {
    return (
      <div className="character-selector-loading">
        <span className="loading-spinner" aria-hidden="true" />
        <p>読み込み中...</p>
      </div>
    );
  }

  if (error && characters.length === 0) {
    return (
      <div className="character-selector-error" role="alert">
        <p>エラー: {error}</p>
      </div>
    );
  }

  return (
    <div className="character-selector">
      {error && (
        <div className="character-selector-error" role="alert">
          <p>エラー: {error}</p>
        </div>
      )}
      {isSaving && <p className="character-saving">保存中...</p>}
      <div className="character-cards">
        {characters.map((character) => {
          return (
            // biome-ignore lint/a11y/useSemanticElements: contains nested voice button
            <div
              key={character.id}
              data-testid="character-card"
              className={`character-card${selectedId === character.id ? ' selected' : ''}`}
              role="button"
              tabIndex={0}
              onClick={() => handleSelect(character.id)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  handleSelect(character.id);
                }
              }}
              aria-pressed={selectedId === character.id}
            >
              <img
                src={`/${character.id}.png`}
                alt={character.displayName}
                className="character-card-image"
              />
              <h4 className="character-card-name">{character.displayName}</h4>
              <p className="character-card-description">{character.description}</p>
              <button
                type="button"
                data-testid="voice-play-button"
                className={`voice-play-button${playingVoiceId === character.id ? ' playing' : ''}`}
                aria-label={`${character.displayName}のボイスを${playingVoiceId === character.id ? '停止' : '再生'}`}
                onClick={(e) => handlePlayVoice(e, character.id)}
              >
                {playingVoiceId === character.id ? <PauseIcon /> : <PlayIcon />}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function PlayIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M8 5v14l11-7z" />
    </svg>
  );
}

function PauseIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
    </svg>
  );
}
