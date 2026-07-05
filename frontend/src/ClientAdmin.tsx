import { useEffect, useState, useCallback } from 'react';
import { apiFetch } from './api';
import { useCurrentUser } from './currentUserContext';

interface ApiClient {
  id: number;
  name: string;
  status: 'active' | 'archived';
}

interface ApiUser {
  id: number;
  display_name: string;
  roles: string[];
}

interface Assignment {
  consultant_id: number;
  display_name: string;
  start_date: string;
}

function ClientAdmin() {
  const { currentUserId } = useCurrentUser();
  const [clients, setClients] = useState<ApiClient[]>([]);
  const [users, setUsers] = useState<ApiUser[]>([]);
  const [selectedClientId, setSelectedClientId] = useState<number | null>(null);
  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [newClientName, setNewClientName] = useState('');

  const isAdmin = users
    .find((u) => String(u.id) === currentUserId)
    ?.roles.includes('admin');

  const loadClients = useCallback(() => {
    apiFetch('/clients')
      .then((response) => (response.ok ? response.json() : []))
      .then(setClients);
  }, []);

  useEffect(() => {
    apiFetch('/users')
      .then((response) => response.json())
      .then(setUsers);
    loadClients();
  }, [loadClients]);

  useEffect(() => {
    if (selectedClientId === null || !isAdmin) {
      return;
    }
    apiFetch(`/clients/${selectedClientId}/assignments`)
      .then((response) => response.json())
      .then(setAssignments);
  }, [selectedClientId, isAdmin]);

  const handleAddClient = async () => {
    if (!newClientName.trim()) return;
    await apiFetch('/clients', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: newClientName }),
    });
    setNewClientName('');
    loadClients();
  };

  const handleArchive = async (clientId: number) => {
    await apiFetch(`/clients/${clientId}/archive`, { method: 'POST' });
    loadClients();
  };

  const handleAssign = async (consultantId: number) => {
    if (selectedClientId === null) return;
    await apiFetch(`/clients/${selectedClientId}/assignments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ consultant_id: consultantId }),
    });
    const response = await apiFetch(`/clients/${selectedClientId}/assignments`);
    setAssignments(await response.json());
  };

  const handleRemove = async (consultantId: number) => {
    if (selectedClientId === null) return;
    await apiFetch(`/clients/${selectedClientId}/assignments/${consultantId}`, {
      method: 'DELETE',
    });
    const response = await apiFetch(`/clients/${selectedClientId}/assignments`);
    setAssignments(await response.json());
  };

  const selectedClient = clients.find((c) => c.id === selectedClientId);
  const assignedIds = new Set(assignments.map((a) => a.consultant_id));
  const unassignedConsultants = users.filter(
    (u) => u.roles.includes('consultant') && !assignedIds.has(u.id),
  );

  return (
    <section>
      <h2>Clients and assignments</h2>
      <div style={{ display: 'flex', gap: '2rem' }}>
        <div>
          <ul>
            {clients.map((c) => (
              <li key={c.id}>
                <button type="button" onClick={() => setSelectedClientId(c.id)}>
                  {c.name} {c.status === 'archived' ? '(archived)' : ''}
                </button>
                {isAdmin && c.status === 'active' && (
                  <button type="button" onClick={() => handleArchive(c.id)}>
                    Archive
                  </button>
                )}
              </li>
            ))}
          </ul>
          {isAdmin && (
            <div>
              <input
                aria-label="New client name"
                value={newClientName}
                onChange={(e) => setNewClientName(e.target.value)}
              />
              <button type="button" onClick={handleAddClient}>
                + Add client
              </button>
            </div>
          )}
        </div>

        {selectedClient && isAdmin && (
          <div>
            <h3>{selectedClient.name} — assigned consultants</h3>
            <ul>
              {assignments.map((a) => (
                <li key={a.consultant_id}>
                  {a.display_name}
                  <button
                    type="button"
                    aria-label={`Remove ${a.display_name}`}
                    onClick={() => handleRemove(a.consultant_id)}
                  >
                    ×
                  </button>
                </li>
              ))}
            </ul>
            {unassignedConsultants.length > 0 && (
              <select
                aria-label="Assign consultant"
                value=""
                onChange={(e) => handleAssign(Number(e.target.value))}
              >
                <option value="">Assign…</option>
                {unassignedConsultants.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.display_name}
                  </option>
                ))}
              </select>
            )}
          </div>
        )}
      </div>
    </section>
  );
}

export default ClientAdmin;
