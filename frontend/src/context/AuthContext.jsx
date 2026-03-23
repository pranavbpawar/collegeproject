/**
 * TBAPS — Auth Context
 * Manages role-aware authentication state for all user types (Admin, Manager, HR).
 * Stores token, user profile, role, and permissions globally.
 *
 * Usage:
 *   const { user, isAdmin, hasPermission, logout } = useAuth();
 */

import React, { createContext, useContext, useState, useCallback } from 'react';

const AuthContext = createContext(null);

const TOKEN_KEY = 'tbaps_token';
const USER_KEY  = 'tbaps_user';

function loadFromStorage() {
    try {
        const token = localStorage.getItem(TOKEN_KEY);
        const user  = JSON.parse(localStorage.getItem(USER_KEY) || 'null');
        return { token, user };
    } catch {
        return { token: null, user: null };
    }
}

export function AuthProvider({ children }) {
    const [state, setState] = useState(() => loadFromStorage());

    const login = useCallback((token, userData) => {
        localStorage.setItem(TOKEN_KEY, token);
        localStorage.setItem(USER_KEY, JSON.stringify(userData));
        setState({ token, user: userData });
    }, []);

    const logout = useCallback(() => {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
        // Also clear legacy key
        localStorage.removeItem('tbaps_admin_token');
        setState({ token: null, user: null });
    }, []);

    // Role helpers
    const isAdmin   = () => state.user?.role === 'admin';
    const isManager = () => state.user?.role === 'manager';
    const isHR      = () => state.user?.role === 'hr';

    // Permission helper
    const hasPermission = (perm) =>
        Array.isArray(state.user?.permissions) && state.user.permissions.includes(perm);

    // HTTP helper — always include Bearer token
    const authHeaders = () => ({
        'Content-Type': 'application/json',
        ...(state.token ? { Authorization: `Bearer ${state.token}` } : {}),
    });

    return (
        <AuthContext.Provider value={{
            token:      state.token,
            user:       state.user,
            isAdmin,
            isManager,
            isHR,
            hasPermission,
            authHeaders,
            login,
            logout,
        }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const ctx = useContext(AuthContext);
    if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
    return ctx;
}
