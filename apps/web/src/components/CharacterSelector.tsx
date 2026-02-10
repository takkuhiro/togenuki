/**
 * Character selector component for choosing email conversion character.
 * Requirements: 5.1, 5.2, 5.3, 5.4
 */

import { useCallback, useEffect, useState } from 'react';
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
        {characters.map((character) => (
          <button
            key={character.id}
            type="button"
            data-testid="character-card"
            className={`character-card${selectedId === character.id ? ' selected' : ''}`}
            onClick={() => handleSelect(character.id)}
            aria-pressed={selectedId === character.id}
          >
            <h4 className="character-card-name">{character.displayName}</h4>
            <p className="character-card-description">{character.description}</p>
          </button>
        ))}
      </div>
    </div>
  );
}
