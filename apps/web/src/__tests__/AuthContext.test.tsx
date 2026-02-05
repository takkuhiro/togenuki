/**
 * @vitest-environment jsdom
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthProvider, useAuth } from '../contexts/AuthContext';

// Mock firebase/auth
vi.mock('firebase/auth', () => ({
  getAuth: vi.fn(() => ({})),
  GoogleAuthProvider: vi.fn(() => ({})),
  signInWithPopup: vi.fn(),
  signOut: vi.fn(),
  onAuthStateChanged: vi.fn(),
}));

// Mock firebase/app
vi.mock('firebase/app', () => ({
  initializeApp: vi.fn(() => ({})),
}));

// Mock firebase config
vi.mock('../firebase/config', () => ({
  auth: {},
}));

// Test component to access auth context
function TestComponent() {
  const { user, isLoading, error, isGmailConnected, signInWithGoogle, signOut } = useAuth();

  return (
    <div>
      <div data-testid="loading">{isLoading ? 'loading' : 'not-loading'}</div>
      <div data-testid="user">{user ? user.email : 'no-user'}</div>
      <div data-testid="error">{error ? error : 'no-error'}</div>
      <div data-testid="gmail-connected">{isGmailConnected ? 'connected' : 'not-connected'}</div>
      <button type="button" onClick={signInWithGoogle}>
        Sign In
      </button>
      <button type="button" onClick={signOut}>
        Sign Out
      </button>
    </div>
  );
}

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('AuthProvider', () => {
    it('should render children', async () => {
      const { onAuthStateChanged } = await import('firebase/auth');
      vi.mocked(onAuthStateChanged).mockImplementation((_auth, callback) => {
        (callback as (user: unknown) => void)(null);
        return vi.fn();
      });

      render(
        <AuthProvider>
          <div data-testid="child">Child Content</div>
        </AuthProvider>
      );

      expect(screen.getByTestId('child')).toBeInTheDocument();
    });

    it('should provide initial loading state as true', async () => {
      const { onAuthStateChanged } = await import('firebase/auth');
      vi.mocked(onAuthStateChanged).mockImplementation(() => vi.fn());

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      expect(screen.getByTestId('loading')).toHaveTextContent('loading');
    });

    it('should set loading to false after auth state is determined', async () => {
      const { onAuthStateChanged } = await import('firebase/auth');
      vi.mocked(onAuthStateChanged).mockImplementation((_auth, callback) => {
        (callback as (user: unknown) => void)(null);
        return vi.fn();
      });

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('loading')).toHaveTextContent('not-loading');
      });
    });

    it('should set user when authenticated', async () => {
      const { onAuthStateChanged } = await import('firebase/auth');
      const mockUser = {
        uid: 'test-uid',
        email: 'test@example.com',
        displayName: 'Test User',
        getIdToken: vi.fn().mockResolvedValue('mock-token'),
      };

      vi.mocked(onAuthStateChanged).mockImplementation((_auth, callback) => {
        (callback as (user: unknown) => void)(mockUser);
        return vi.fn();
      });

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('user')).toHaveTextContent('test@example.com');
      });
    });

    it('should set user to null when not authenticated', async () => {
      const { onAuthStateChanged } = await import('firebase/auth');
      vi.mocked(onAuthStateChanged).mockImplementation((_auth, callback) => {
        (callback as (user: unknown) => void)(null);
        return vi.fn();
      });

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('user')).toHaveTextContent('no-user');
      });
    });
  });

  describe('signInWithGoogle', () => {
    it('should call signInWithPopup on sign in', async () => {
      const { onAuthStateChanged, signInWithPopup } = await import('firebase/auth');
      vi.mocked(onAuthStateChanged).mockImplementation((_auth, callback) => {
        (callback as (user: unknown) => void)(null);
        return vi.fn();
      });
      vi.mocked(signInWithPopup).mockResolvedValue({
        user: {
          uid: 'test-uid',
          email: 'test@example.com',
          displayName: 'Test User',
          getIdToken: vi.fn().mockResolvedValue('mock-token'),
        },
      } as never);

      const user = userEvent.setup();
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('loading')).toHaveTextContent('not-loading');
      });

      await user.click(screen.getByText('Sign In'));

      expect(signInWithPopup).toHaveBeenCalled();
    });
  });

  describe('signOut', () => {
    it('should call signOut on sign out', async () => {
      const { onAuthStateChanged, signOut } = await import('firebase/auth');
      vi.mocked(onAuthStateChanged).mockImplementation((_auth, callback) => {
        (callback as (user: unknown) => void)({
          uid: 'test-uid',
          email: 'test@example.com',
          displayName: 'Test User',
          getIdToken: vi.fn().mockResolvedValue('mock-token'),
        });
        return vi.fn();
      });
      vi.mocked(signOut).mockResolvedValue(undefined);

      const user = userEvent.setup();
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('user')).toHaveTextContent('test@example.com');
      });

      await user.click(screen.getByText('Sign Out'));

      expect(signOut).toHaveBeenCalled();
    });
  });
});

describe('useAuth', () => {
  it('should throw error when used outside AuthProvider', () => {
    // Suppress console.error for this test
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => {
      render(<TestComponent />);
    }).toThrow('useAuth must be used within an AuthProvider');

    consoleSpy.mockRestore();
  });
});
