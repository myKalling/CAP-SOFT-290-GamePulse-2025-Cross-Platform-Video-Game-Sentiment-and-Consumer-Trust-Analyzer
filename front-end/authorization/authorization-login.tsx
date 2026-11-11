import React, { createContext, useContext, useState } from 'react';

export type Role = 'guest' | 'user' | 'admin';

export interface Permissions {
  canAddReview: boolean;
}

export const rolePermissions: Record<Role, Permissions> = {
  guest: { canAddReview: false },
  user: { canAddReview: true },
  admin: { canAddReview: true },
};

interface AuthContextType {
  role: Role;
  username: string | null;
  setRole: (role: Role) => void;
  signIn: (username: string) => void;
  signOut: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [role, setRole] = useState<Role>('guest');
  const [username, setUsername] = useState<string | null>(null);

  const signIn = (name: string) => {
    setUsername(name);
    setRole('user');
  };

  const signOut = () => {
    setUsername(null);
    setRole('guest');
  };

  return (
    <AuthContext.Provider value={{ role, username, setRole, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const auth = useContext(AuthContext);
  if (!auth) throw new Error('useAuth must be used within AuthProvider');
  return auth;
}
