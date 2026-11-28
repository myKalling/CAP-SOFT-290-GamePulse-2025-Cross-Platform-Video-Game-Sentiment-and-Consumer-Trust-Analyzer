import React, { createContext, useContext, useEffect, useState } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';

export type Role = 'guest' | 'user' | 'admin';

export interface Permissions {
  canAddReview: boolean;
}

export async function storeToken(token: string) {
  await AsyncStorage.setItem('token', token);
}

const generateUserID = (username: string): number => {
  let hash = 0;
  const name = username.trim().toLowerCase();

  for (const char of name) {
    hash = (hash << 5) - hash + char.charCodeAt(0);
    hash |= 0;
  }

  return (hash & 0x7fffffff) || 1;
};

export const rolePermissions: Record<Role, Permissions> = {
  guest: { canAddReview: false },
  user: { canAddReview: true },
  admin: { canAddReview: true },
};

interface AuthContextType {
  role: Role;
  username: string | null;
  userID: number | null;
  setRole: (role: Role) => void;
  isLoading: boolean;
  storageError: string | null;
  signIn: (username: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [role, setRole] = useState<Role>('guest');
  const [username, setUsername] = useState<string | null>(null);
  const [userID, setUserID] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [storageError, setStorageError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function restoreUsername() {
      try {
        const savedName = await AsyncStorage.getItem('username');
        if (active && savedName) {
          setUsername(savedName);
          setUserID(generateUserID(savedName));
          setRole('user');
        }
      } catch (error) {
        console.error('Unable to restore the saved username:', error);
        if (active) {
          setStorageError('Unable to load your saved account. Please restart the app and try again.');
        }
      } finally {
        if (active) setIsLoading(false);
      }
    }

    void restoreUsername();
    return () => { active = false; };
  }, []);

  const signIn = async (name: string) => {
    await AsyncStorage.setItem('username', name);
    setUsername(name);
    setUserID(generateUserID(name));
    setRole('user');
  };

  const signOut = async () => {
    await AsyncStorage.removeItem('username');
    setUsername(null);
    setUserID(null);
    setRole('guest');
  };

  return (
    <AuthContext.Provider value={{ role, username, userID, setRole, isLoading, storageError, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

const fallbackAuth: AuthContextType = {
  role: 'guest',
  username: null,
  userID: null,
  setRole: () => { },
  isLoading: false,
  storageError: null,
  signIn: async (name: string) => {
    await AsyncStorage.setItem('username', name);
  },
  signOut: async () => {
    await AsyncStorage.removeItem('username');
  },
};

export function useAuth() {
  return useContext(AuthContext) ?? fallbackAuth;
}
