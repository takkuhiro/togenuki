/**
 * @vitest-environment jsdom
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as characterApi from '../api/characters';
import { CharacterSelector } from '../components/CharacterSelector';

// Mock the characters API
vi.mock('../api/characters', () => ({
  fetchCharacters: vi.fn(),
  fetchCurrentCharacter: vi.fn(),
  updateCharacter: vi.fn(),
}));

// Mock AuthContext
vi.mock('../contexts/AuthContext', () => ({
  useAuth: vi.fn(() => ({
    idToken: 'mock-token',
    user: { uid: 'test-uid', email: 'test@example.com' },
    isLoading: false,
  })),
}));

// Mock HTMLAudioElement
const mockPlay = vi.fn().mockResolvedValue(undefined);
const mockPause = vi.fn();
const mockAudioInstances: Array<{
  src: string;
  play: ReturnType<typeof vi.fn>;
  pause: ReturnType<typeof vi.fn>;
  addEventListener: ReturnType<typeof vi.fn>;
  removeEventListener: ReturnType<typeof vi.fn>;
}> = [];

vi.stubGlobal(
  'Audio',
  vi.fn().mockImplementation((src: string) => {
    const instance = {
      src,
      play: mockPlay,
      pause: mockPause,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    };
    mockAudioInstances.push(instance);
    return instance;
  })
);

const mockCharacters = [
  {
    id: 'gyaru',
    displayName: '全肯定お姉さん',
    description: 'ハイテンションでポジティブなお姉さん',
  },
  {
    id: 'senpai',
    displayName: '優しい先輩',
    description: '穏やかで包容力のある先輩',
  },
  {
    id: 'butler',
    displayName: '冷静な執事',
    description: '落ち着いた口調の執事',
  },
];

function getCard(name: string): HTMLElement {
  return screen.getByText(name).closest('[data-testid="character-card"]') as HTMLElement;
}

describe('CharacterSelector', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAudioInstances.length = 0;
  });

  describe('キャラクター一覧表示 (Requirement 5.1, 5.3)', () => {
    it('should display all character cards with name and description', async () => {
      vi.mocked(characterApi.fetchCharacters).mockResolvedValue({
        characters: mockCharacters,
      });
      vi.mocked(characterApi.fetchCurrentCharacter).mockResolvedValue(mockCharacters[0]);

      render(<CharacterSelector />);

      await waitFor(() => {
        expect(screen.getByText('全肯定お姉さん')).toBeInTheDocument();
        expect(screen.getByText('優しい先輩')).toBeInTheDocument();
        expect(screen.getByText('冷静な執事')).toBeInTheDocument();
      });

      // Check descriptions
      expect(screen.getByText(/ハイテンションでポジティブ/)).toBeInTheDocument();
      expect(screen.getByText(/穏やかで包容力/)).toBeInTheDocument();
      expect(screen.getByText(/落ち着いた口調/)).toBeInTheDocument();
    });

    it('should show loading state while fetching', async () => {
      vi.mocked(characterApi.fetchCharacters).mockImplementation(() => new Promise(() => {}));
      vi.mocked(characterApi.fetchCurrentCharacter).mockImplementation(() => new Promise(() => {}));

      render(<CharacterSelector />);

      expect(screen.getByText('読み込み中...')).toBeInTheDocument();
    });
  });

  describe('選択状態のハイライト (Requirement 5.2)', () => {
    it('should highlight the currently selected character', async () => {
      vi.mocked(characterApi.fetchCharacters).mockResolvedValue({
        characters: mockCharacters,
      });
      vi.mocked(characterApi.fetchCurrentCharacter).mockResolvedValue(mockCharacters[1]);

      render(<CharacterSelector />);

      await waitFor(() => {
        expect(getCard('優しい先輩')).toHaveClass('selected');
      });
    });

    it('should not highlight non-selected characters', async () => {
      vi.mocked(characterApi.fetchCharacters).mockResolvedValue({
        characters: mockCharacters,
      });
      vi.mocked(characterApi.fetchCurrentCharacter).mockResolvedValue(mockCharacters[0]);

      render(<CharacterSelector />);

      await waitFor(() => {
        expect(getCard('優しい先輩')).not.toHaveClass('selected');
        expect(getCard('冷静な執事')).not.toHaveClass('selected');
      });
    });
  });

  describe('キャラクター選択・保存 (Requirement 5.2, 5.4)', () => {
    it('should call updateCharacter API when a card is clicked', async () => {
      vi.mocked(characterApi.fetchCharacters).mockResolvedValue({
        characters: mockCharacters,
      });
      vi.mocked(characterApi.fetchCurrentCharacter).mockResolvedValue(mockCharacters[0]);
      vi.mocked(characterApi.updateCharacter).mockResolvedValue(mockCharacters[2]);

      const user = userEvent.setup();
      render(<CharacterSelector />);

      await waitFor(() => {
        expect(screen.getByText('冷静な執事')).toBeInTheDocument();
      });

      await user.click(getCard('冷静な執事'));

      await waitFor(() => {
        expect(characterApi.updateCharacter).toHaveBeenCalledWith('mock-token', 'butler');
      });
    });

    it('should update selection after successful save', async () => {
      vi.mocked(characterApi.fetchCharacters).mockResolvedValue({
        characters: mockCharacters,
      });
      vi.mocked(characterApi.fetchCurrentCharacter).mockResolvedValue(mockCharacters[0]);
      vi.mocked(characterApi.updateCharacter).mockResolvedValue(mockCharacters[2]);

      const user = userEvent.setup();
      render(<CharacterSelector />);

      await waitFor(() => {
        expect(screen.getByText('冷静な執事')).toBeInTheDocument();
      });

      await user.click(getCard('冷静な執事'));

      await waitFor(() => {
        expect(getCard('冷静な執事')).toHaveClass('selected');
      });
    });

    it('should not call API when clicking already selected character', async () => {
      vi.mocked(characterApi.fetchCharacters).mockResolvedValue({
        characters: mockCharacters,
      });
      vi.mocked(characterApi.fetchCurrentCharacter).mockResolvedValue(mockCharacters[0]);

      const user = userEvent.setup();
      render(<CharacterSelector />);

      await waitFor(() => {
        expect(screen.getByText('全肯定お姉さん')).toBeInTheDocument();
      });

      await user.click(getCard('全肯定お姉さん'));

      expect(characterApi.updateCharacter).not.toHaveBeenCalled();
    });

    it('should show saving state while updating', async () => {
      vi.mocked(characterApi.fetchCharacters).mockResolvedValue({
        characters: mockCharacters,
      });
      vi.mocked(characterApi.fetchCurrentCharacter).mockResolvedValue(mockCharacters[0]);
      vi.mocked(characterApi.updateCharacter).mockImplementation(() => new Promise(() => {}));

      const user = userEvent.setup();
      render(<CharacterSelector />);

      await waitFor(() => {
        expect(screen.getByText('冷静な執事')).toBeInTheDocument();
      });

      await user.click(getCard('冷静な執事'));

      await waitFor(() => {
        expect(screen.getByText('保存中...')).toBeInTheDocument();
      });
    });
  });

  describe('ボイスサンプル再生', () => {
    async function renderWithCharacters() {
      vi.mocked(characterApi.fetchCharacters).mockResolvedValue({
        characters: mockCharacters,
      });
      vi.mocked(characterApi.fetchCurrentCharacter).mockResolvedValue(mockCharacters[0]);

      const user = userEvent.setup();
      render(<CharacterSelector />);

      await waitFor(() => {
        expect(screen.getByText('全肯定お姉さん')).toBeInTheDocument();
      });

      return user;
    }

    function getVoiceButtons() {
      return screen.getAllByTestId('voice-play-button');
    }

    it('should render a voice play button for each character', async () => {
      await renderWithCharacters();

      expect(getVoiceButtons()).toHaveLength(3);
    });

    it('should play audio when voice button is clicked', async () => {
      const user = await renderWithCharacters();

      await user.click(getVoiceButtons()[0]);

      expect(Audio).toHaveBeenCalledWith('/gyaru.wav');
      expect(mockPlay).toHaveBeenCalled();
    });

    it('should stop previous audio when playing a different character', async () => {
      const user = await renderWithCharacters();

      // Play gyaru
      await user.click(getVoiceButtons()[0]);
      expect(Audio).toHaveBeenCalledWith('/gyaru.wav');

      // Play senpai - should pause previous
      await user.click(getVoiceButtons()[1]);
      expect(mockPause).toHaveBeenCalled();
      expect(Audio).toHaveBeenCalledWith('/senpai.wav');
    });

    it('should pause audio when clicking the same voice button while playing', async () => {
      const user = await renderWithCharacters();

      // Play
      await user.click(getVoiceButtons()[0]);
      expect(mockPlay).toHaveBeenCalledTimes(1);

      // Pause (click same button again)
      await user.click(getVoiceButtons()[0]);
      expect(mockPause).toHaveBeenCalled();
    });

    it('should not trigger character selection when clicking voice button', async () => {
      const user = await renderWithCharacters();

      // Click voice button for senpai (not currently selected)
      await user.click(getVoiceButtons()[1]);

      // updateCharacter should NOT be called
      expect(characterApi.updateCharacter).not.toHaveBeenCalled();
    });
  });

  describe('エラーハンドリング', () => {
    it('should show error when character save fails', async () => {
      vi.mocked(characterApi.fetchCharacters).mockResolvedValue({
        characters: mockCharacters,
      });
      vi.mocked(characterApi.fetchCurrentCharacter).mockResolvedValue(mockCharacters[0]);
      vi.mocked(characterApi.updateCharacter).mockRejectedValue(new Error('保存に失敗'));

      const user = userEvent.setup();
      render(<CharacterSelector />);

      await waitFor(() => {
        expect(screen.getByText('冷静な執事')).toBeInTheDocument();
      });

      await user.click(getCard('冷静な執事'));

      await waitFor(() => {
        expect(screen.getByText(/エラー/)).toBeInTheDocument();
      });
    });

    it('should show error when fetch fails', async () => {
      vi.mocked(characterApi.fetchCharacters).mockRejectedValue(new Error('Network error'));
      vi.mocked(characterApi.fetchCurrentCharacter).mockRejectedValue(new Error('Network error'));

      render(<CharacterSelector />);

      await waitFor(() => {
        expect(screen.getByText(/エラー/)).toBeInTheDocument();
      });
    });
  });
});
