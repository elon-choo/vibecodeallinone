# React Test Templates

## React Component Test Template

```typescript
// ═══════════════════════════════════════════════════════════════
// React Component Test Template
// File: src/components/UserCard.test.tsx
// ═══════════════════════════════════════════════════════════════

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { UserCard } from './UserCard';
import { User } from '@/types';

describe('UserCard', () => {
  // ─────────────────────────────────────────────────────────────
  // Test Data
  // ─────────────────────────────────────────────────────────────

  const mockUser: User = {
    id: '1',
    name: 'John Doe',
    email: 'john@example.com',
    role: 'admin',
    avatar: 'https://example.com/avatar.jpg',
  };

  const mockOnEdit = jest.fn();
  const mockOnDelete = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  // ─────────────────────────────────────────────────────────────
  // Rendering Tests
  // ─────────────────────────────────────────────────────────────

  describe('rendering', () => {
    it('should render user name', () => {
      render(<UserCard user={mockUser} />);

      expect(screen.getByText('John Doe')).toBeInTheDocument();
    });

    it('should render user email', () => {
      render(<UserCard user={mockUser} />);

      expect(screen.getByText('john@example.com')).toBeInTheDocument();
    });

    it('should render user role with correct styling', () => {
      render(<UserCard user={mockUser} />);

      const roleBadge = screen.getByText('admin');
      expect(roleBadge).toBeInTheDocument();
      expect(roleBadge).toHaveClass('badge-admin');
    });

    it('should render avatar image', () => {
      render(<UserCard user={mockUser} />);

      const avatar = screen.getByRole('img', { name: /john doe/i });
      expect(avatar).toHaveAttribute('src', mockUser.avatar);
    });

    it('should render fallback avatar when no avatar provided', () => {
      const userWithoutAvatar = { ...mockUser, avatar: undefined };
      render(<UserCard user={userWithoutAvatar} />);

      const fallback = screen.getByTestId('avatar-fallback');
      expect(fallback).toHaveTextContent('JD'); // Initials
    });
  });

  // ─────────────────────────────────────────────────────────────
  // Interaction Tests
  // ─────────────────────────────────────────────────────────────

  describe('interactions', () => {
    it('should call onEdit when edit button clicked', async () => {
      const user = userEvent.setup();
      render(
        <UserCard
          user={mockUser}
          onEdit={mockOnEdit}
        />
      );

      await user.click(screen.getByRole('button', { name: /edit/i }));

      expect(mockOnEdit).toHaveBeenCalledTimes(1);
      expect(mockOnEdit).toHaveBeenCalledWith(mockUser);
    });

    it('should call onDelete when delete button clicked', async () => {
      const user = userEvent.setup();
      render(
        <UserCard
          user={mockUser}
          onDelete={mockOnDelete}
        />
      );

      await user.click(screen.getByRole('button', { name: /delete/i }));

      expect(mockOnDelete).toHaveBeenCalledTimes(1);
      expect(mockOnDelete).toHaveBeenCalledWith(mockUser.id);
    });

    it('should show confirmation dialog before delete', async () => {
      const user = userEvent.setup();
      render(
        <UserCard
          user={mockUser}
          onDelete={mockOnDelete}
          confirmDelete
        />
      );

      await user.click(screen.getByRole('button', { name: /delete/i }));

      expect(screen.getByRole('dialog')).toBeInTheDocument();
      expect(screen.getByText(/are you sure/i)).toBeInTheDocument();

      await user.click(screen.getByRole('button', { name: /confirm/i }));

      expect(mockOnDelete).toHaveBeenCalledWith(mockUser.id);
    });
  });

  // ─────────────────────────────────────────────────────────────
  // Accessibility Tests
  // ─────────────────────────────────────────────────────────────

  describe('accessibility', () => {
    it('should have accessible name for edit button', () => {
      render(<UserCard user={mockUser} onEdit={mockOnEdit} />);

      expect(
        screen.getByRole('button', { name: /edit john doe/i })
      ).toBeInTheDocument();
    });

    it('should be keyboard navigable', async () => {
      const user = userEvent.setup();
      render(<UserCard user={mockUser} onEdit={mockOnEdit} />);

      await user.tab();
      expect(screen.getByRole('button', { name: /edit/i })).toHaveFocus();

      await user.keyboard('{Enter}');
      expect(mockOnEdit).toHaveBeenCalled();
    });
  });

  // ─────────────────────────────────────────────────────────────
  // Edge Cases
  // ─────────────────────────────────────────────────────────────

  describe('edge cases', () => {
    it('should handle very long names with ellipsis', () => {
      const longNameUser = {
        ...mockUser,
        name: 'A'.repeat(100),
      };
      render(<UserCard user={longNameUser} />);

      const nameElement = screen.getByTestId('user-name');
      expect(nameElement).toHaveClass('truncate');
    });

    it('should handle missing optional props', () => {
      render(<UserCard user={mockUser} />);

      expect(screen.queryByRole('button', { name: /edit/i })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /delete/i })).not.toBeInTheDocument();
    });
  });
});
```

## React Hook Test Template

```typescript
// ═══════════════════════════════════════════════════════════════
// React Hook Test Template
// File: src/hooks/useUsers.test.ts
// ═══════════════════════════════════════════════════════════════

import { renderHook, act, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useUsers, useCreateUser, useDeleteUser } from './useUsers';
import { api } from '@/lib/api';
import { User } from '@/types';

jest.mock('@/lib/api');
const mockedApi = api as jest.Mocked<typeof api>;

describe('useUsers hooks', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
    jest.clearAllMocks();
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );

  // ─────────────────────────────────────────────────────────────
  // useUsers Tests
  // ─────────────────────────────────────────────────────────────

  describe('useUsers', () => {
    const mockUsers: User[] = [
      { id: '1', name: 'User 1', email: 'user1@test.com' },
      { id: '2', name: 'User 2', email: 'user2@test.com' },
    ];

    it('should fetch users successfully', async () => {
      mockedApi.get.mockResolvedValue({ data: mockUsers });

      const { result } = renderHook(() => useUsers(), { wrapper });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.data).toEqual(mockUsers);
      expect(result.current.data).toHaveLength(2);
      expect(result.current.error).toBeNull();
    });

    it('should handle fetch error', async () => {
      const error = new Error('Network error');
      mockedApi.get.mockRejectedValue(error);

      const { result } = renderHook(() => useUsers(), { wrapper });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toEqual(error);
      expect(result.current.data).toBeUndefined();
    });

    it('should handle empty response', async () => {
      mockedApi.get.mockResolvedValue({ data: [] });

      const { result } = renderHook(() => useUsers(), { wrapper });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.data).toEqual([]);
      expect(result.current.data).toHaveLength(0);
    });
  });

  // ─────────────────────────────────────────────────────────────
  // useCreateUser Tests
  // ─────────────────────────────────────────────────────────────

  describe('useCreateUser', () => {
    const newUser = { name: 'New User', email: 'new@test.com' };
    const createdUser = { id: '3', ...newUser };

    it('should create user successfully', async () => {
      mockedApi.post.mockResolvedValue({ data: createdUser });

      const { result } = renderHook(() => useCreateUser(), { wrapper });

      await act(async () => {
        await result.current.mutateAsync(newUser);
      });

      expect(mockedApi.post).toHaveBeenCalledWith('/users', newUser);
      expect(result.current.data).toEqual(createdUser);
    });

    it('should handle creation error', async () => {
      const error = new Error('Validation failed');
      mockedApi.post.mockRejectedValue(error);

      const { result } = renderHook(() => useCreateUser(), { wrapper });

      await act(async () => {
        try {
          await result.current.mutateAsync(newUser);
        } catch (e) {
          // Expected
        }
      });

      expect(result.current.error).toEqual(error);
    });
  });
});
```
