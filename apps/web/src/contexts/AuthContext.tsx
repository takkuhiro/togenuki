/**
 * Authentication context for managing Firebase Auth state.
 */

import {
  signOut as firebaseSignOut,
  GoogleAuthProvider,
  onAuthStateChanged,
  signInWithPopup,
  type User,
} from 'firebase/auth';
import { createContext, type ReactNode, useCallback, useContext, useEffect, useState } from 'react';
import { auth } from '../firebase/config';

/**
 * Firebase user information.
 */
export interface FirebaseUser {
  uid: string;
  email: string | null;
  displayName: string | null;
}

/**
 * Authentication error types.
 */
export type AuthError = 'auth_failed' | 'sign_out_failed' | 'unknown';

/**
 * Authentication state.
 */
interface AuthState {
  user: FirebaseUser | null;
  idToken: string | null;
  isGmailConnected: boolean;
  isLoading: boolean;
  error: AuthError | null;
}

/**
 * Authentication context value.
 */
interface AuthContextValue extends AuthState {
  signInWithGoogle: () => Promise<void>;
  signOut: () => Promise<void>;
  refreshToken: () => Promise<string | null>;
  connectGmail: () => Promise<void>;
  checkGmailStatus: () => Promise<boolean>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

/**
 * Authentication provider component.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    idToken: null,
    isGmailConnected: false,
    isLoading: true,
    error: null,
  });

  // Update ID token when user changes
  const updateIdToken = useCallback(async (user: User | null) => {
    if (user) {
      try {
        const token = await user.getIdToken();
        setState((prev) => ({ ...prev, idToken: token }));
      } catch {
        setState((prev) => ({ ...prev, idToken: null }));
      }
    } else {
      setState((prev) => ({ ...prev, idToken: null }));
    }
  }, []);

  // Listen for auth state changes
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      if (user) {
        const firebaseUser: FirebaseUser = {
          uid: user.uid,
          email: user.email,
          displayName: user.displayName,
        };
        setState((prev) => ({
          ...prev,
          user: firebaseUser,
          isLoading: false,
          error: null,
        }));
        await updateIdToken(user);
      } else {
        setState((prev) => ({
          ...prev,
          user: null,
          idToken: null,
          isGmailConnected: false,
          isLoading: false,
          error: null,
        }));
      }
    });

    return () => unsubscribe();
  }, [updateIdToken]);

  // Sign in with Google
  const signInWithGoogle = useCallback(async () => {
    try {
      setState((prev) => ({ ...prev, isLoading: true, error: null }));
      const provider = new GoogleAuthProvider();
      await signInWithPopup(auth, provider);
    } catch {
      setState((prev) => ({
        ...prev,
        error: 'auth_failed',
        isLoading: false,
      }));
    }
  }, []);

  // Sign out
  const signOut = useCallback(async () => {
    try {
      setState((prev) => ({ ...prev, isLoading: true, error: null }));
      await firebaseSignOut(auth);
    } catch {
      setState((prev) => ({
        ...prev,
        error: 'sign_out_failed',
        isLoading: false,
      }));
    }
  }, []);

  // Refresh ID token
  const refreshToken = useCallback(async () => {
    const user = auth.currentUser;
    if (user) {
      try {
        const token = await user.getIdToken(true);
        setState((prev) => ({ ...prev, idToken: token }));
        return token;
      } catch {
        return null;
      }
    }
    return null;
  }, []);

  // Check Gmail connection status
  const checkGmailStatus = useCallback(async () => {
    if (!state.idToken) return false;

    try {
      const response = await fetch('/api/auth/gmail/status', {
        headers: {
          Authorization: `Bearer ${state.idToken}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        const connected = data.connected === true;
        setState((prev) => ({ ...prev, isGmailConnected: connected }));
        return connected;
      }
      return false;
    } catch {
      return false;
    }
  }, [state.idToken]);

  // Connect Gmail account
  const connectGmail = useCallback(async () => {
    if (!state.idToken) return;

    try {
      const response = await fetch('/api/auth/gmail/url', {
        headers: {
          Authorization: `Bearer ${state.idToken}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        // Redirect to Google OAuth consent screen
        window.location.href = data.url;
      }
    } catch {
      setState((prev) => ({ ...prev, error: 'unknown' }));
    }
  }, [state.idToken]);

  const value: AuthContextValue = {
    ...state,
    signInWithGoogle,
    signOut,
    refreshToken,
    connectGmail,
    checkGmailStatus,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/**
 * Hook to access authentication context.
 */
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
