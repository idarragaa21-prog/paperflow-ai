import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import LoginPage from '../pages/LoginPage';
import SignupPage from '../pages/SignupPage';
import { useAuthStore } from '../store/authStore';

vi.mock('../services/api', () => ({
  api: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

vi.mock('../i18n', () => ({
  useI18n: () => ({
    t: {
      auth: {
        signingIn: 'Signing in',
        signIn: 'Sign in',
        forgotPassword: 'Forgot password',
        noAccount: 'No account?',
        signUp: 'Sign up',
        tagline: 'Tagline',
        createAccountTitle: 'Create account',
        createAccountSubtitle: 'Create your account',
        fullName: 'Full name',
        fullNamePlaceholder: 'Your name',
        email: 'Email',
        emailPlaceholder: 'you@example.com',
        password: 'Password',
        passwordPlaceholder: '••••••••',
        confirmPassword: 'Confirm password',
        passwordMinLength: 'Password too short',
        passwordMismatch: 'Passwords do not match',
        creatingAccount: 'Creating account',
        hasAccount: 'Already have an account?',
      },
    },
  }),
}));

import { api } from '../services/api';

function renderAuth(initialEntry: '/login' | '/signup') {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/dashboard" element={<div>Dashboard Home</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('Auth pages', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({
      user: null,
      loading: false,
      initialized: true,
      error: null,
    });
  });

  it('redirects to the dashboard after a successful login', async () => {
    vi.mocked(api.post).mockResolvedValue({ data: {} });
    vi.mocked(api.get).mockResolvedValue({
      data: { id: 'user-1', email: 'user@example.com', full_name: 'Dr. Vega' },
    });

    renderAuth('/login');

    await userEvent.type(screen.getByPlaceholderText('you@example.com'), 'user@example.com');
    await userEvent.type(screen.getByPlaceholderText('••••••••'), 'correct-password');
    fireEvent.click(screen.getByRole('button', { name: 'Sign in →' }));

    await waitFor(() => {
      expect(screen.getByText('Dashboard Home')).toBeInTheDocument();
    });
  });

  it('shows an error for incorrect login credentials', async () => {
    vi.mocked(api.post).mockRejectedValue({
      response: { data: { detail: 'Credenciales inválidas' } },
    });

    renderAuth('/login');

    await userEvent.type(screen.getByPlaceholderText('you@example.com'), 'user@example.com');
    await userEvent.type(screen.getByPlaceholderText('••••••••'), 'wrong-password');
    fireEvent.click(screen.getByRole('button', { name: 'Sign in →' }));

    await waitFor(() => {
      expect(screen.getByText('Credenciales inválidas')).toBeInTheDocument();
    });
  });

  it('creates the user on signup and redirects to login', async () => {
    vi.mocked(api.post).mockResolvedValue({
      data: { id: 'user-2', email: 'new@example.com', full_name: 'New User' },
    });

    renderAuth('/signup');

    await userEvent.type(screen.getByPlaceholderText('Your name'), 'New User');
    await userEvent.type(screen.getByPlaceholderText('you@example.com'), 'new@example.com');
    const passwordInputs = screen.getAllByPlaceholderText('••••••••');
    await userEvent.type(passwordInputs[0], 'secure-pass');
    await userEvent.type(passwordInputs[1], 'secure-pass');
    fireEvent.click(screen.getByRole('button', { name: 'Sign up →' }));

    await waitFor(() => {
      expect(api.post).toHaveBeenCalledWith('/auth/register', {
        email: 'new@example.com',
        password: 'secure-pass',
        full_name: 'New User',
      });
      expect(screen.getByText('Welcome back')).toBeInTheDocument();
    });
  });
});
