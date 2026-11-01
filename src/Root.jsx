import { useState } from 'react';
import App from './App.jsx';
import Home from './Home.jsx';
import Login from './Login.jsx';

const KEY = 'formax_token';
const read = () => { try { return sessionStorage.getItem(KEY); } catch { return null; } };

// Decides which screen to show: home -> login -> workspace.
export default function Root() {
  const [token, setToken] = useState(read);
  const [view, setView] = useState('home');

  const signIn = (t) => { try { sessionStorage.setItem(KEY, t); } catch { /* storage blocked */ } setToken(t); };
  const signOut = () => { try { sessionStorage.removeItem(KEY); } catch { /* ignore */ } setToken(null); setView('home'); };

  if (token) return <App onLogout={signOut} />;
  if (view === 'login') return <Login onSuccess={signIn} onBack={() => setView('home')} />;
  return <Home onSignIn={() => setView('login')} />;
}
