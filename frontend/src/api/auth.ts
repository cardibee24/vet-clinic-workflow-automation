import { API_BASE_URL } from "../config";

export interface Token {
  access_token: string;
  token_type: string;
}

export interface CurrentUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
}

export async function login(email: string, password: string): Promise<Token> {
  const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!response.ok) {
    throw new Error("Incorrect email or password");
  }
  return response.json();
}

export async function fetchCurrentUser(accessToken: string): Promise<CurrentUser> {
  const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!response.ok) {
    throw new Error("Session expired, please log in again");
  }
  return response.json();
}
