import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import App from "./App";
import { AuthProvider } from "./contexts/AuthContext";

// Mock firebase/auth
vi.mock("firebase/auth", () => ({
  getAuth: vi.fn(() => ({})),
  GoogleAuthProvider: vi.fn(() => ({})),
  signInWithPopup: vi.fn(),
  signOut: vi.fn(),
  onAuthStateChanged: vi.fn((_auth, callback) => {
    // Simulate no user logged in
    callback(null);
    return vi.fn();
  }),
}));

// Mock firebase/app
vi.mock("firebase/app", () => ({
  initializeApp: vi.fn(() => ({})),
}));

// Mock firebase config
vi.mock("./firebase/config", () => ({
  auth: {},
}));

const renderWithAuth = (component: React.ReactElement) => {
  return render(<AuthProvider>{component}</AuthProvider>);
};

describe("App", () => {
  it("renders TogeNuki title", () => {
    renderWithAuth(<App />);
    const titleElement = screen.getByText(/TogeNuki/i);
    expect(titleElement).toBeInTheDocument();
  });

  it("renders subtitle", () => {
    renderWithAuth(<App />);
    const subtitleElement = screen.getByText(/メールストレス軽減AIツール/i);
    expect(subtitleElement).toBeInTheDocument();
  });

  it("renders login button when not authenticated", () => {
    renderWithAuth(<App />);
    const loginButton = screen.getByText(/Googleでログイン/i);
    expect(loginButton).toBeInTheDocument();
  });
});
