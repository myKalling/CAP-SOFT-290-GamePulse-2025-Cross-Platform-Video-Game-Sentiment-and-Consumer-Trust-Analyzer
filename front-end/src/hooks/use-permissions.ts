import { rolePermissions, useAuth, type Permissions } from '../../authorization/authorization-login';

// used to retrieve and return the current user's permissions based on their role.
export function usePermissions(): Permissions {
  const { role } = useAuth();
  return rolePermissions[role];
}
