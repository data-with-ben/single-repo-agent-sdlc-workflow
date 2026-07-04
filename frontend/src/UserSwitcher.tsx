import { useEffect, useState } from 'react';
import { apiFetch } from './api';
import { useCurrentUser } from './currentUserContext';

interface ApiUser {
  id: number;
  display_name: string;
  roles: string[];
}

function UserSwitcher() {
  const [users, setUsers] = useState<ApiUser[]>([]);
  const { currentUserId, setCurrentUserId } = useCurrentUser();

  useEffect(() => {
    let cancelled = false;

    apiFetch('/users')
      .then((response) => response.json())
      .then((data: ApiUser[]) => {
        if (!cancelled) {
          setUsers(data);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <label>
      Current user:
      <select
        value={currentUserId ?? ''}
        onChange={(event) => setCurrentUserId(event.target.value || null)}
      >
        <option value="">Select a user</option>
        {users.map((user) => (
          <option key={user.id} value={user.id}>
            {user.display_name} ({user.roles.join(', ')})
          </option>
        ))}
      </select>
    </label>
  );
}

export default UserSwitcher;
