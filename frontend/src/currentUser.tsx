import { useState, type ReactNode } from 'react';
import {
  CurrentUserContext,
  getStoredUserId,
  setStoredUserId,
} from './currentUserContext';

export function CurrentUserProvider({ children }: { children: ReactNode }) {
  const [currentUserId, setCurrentUserIdState] = useState<string | null>(
    getStoredUserId(),
  );

  const setCurrentUserId = (id: string | null) => {
    setStoredUserId(id);
    setCurrentUserIdState(id);
  };

  return (
    <CurrentUserContext.Provider value={{ currentUserId, setCurrentUserId }}>
      {children}
    </CurrentUserContext.Provider>
  );
}
