import { createContext, useContext } from 'react';

const STORAGE_KEY = 'currentUserId';

export interface CurrentUserContextValue {
  currentUserId: string | null;
  setCurrentUserId: (id: string | null) => void;
}

export const CurrentUserContext = createContext<
  CurrentUserContextValue | undefined
>(undefined);

export function getStoredUserId(): string | null {
  return localStorage.getItem(STORAGE_KEY);
}

export function setStoredUserId(id: string | null): void {
  if (id === null) {
    localStorage.removeItem(STORAGE_KEY);
  } else {
    localStorage.setItem(STORAGE_KEY, id);
  }
}

export function useCurrentUser(): CurrentUserContextValue {
  const context = useContext(CurrentUserContext);
  if (!context) {
    throw new Error('useCurrentUser must be used within a CurrentUserProvider');
  }
  return context;
}
