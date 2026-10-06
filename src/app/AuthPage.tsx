import { FormEvent, useState } from 'react';
import { Eye, EyeOff, Leaf, LoaderCircle, ShieldCheck } from 'lucide-react';
import { api, ApiError, clearAccessToken } from '../services/api';

type Mode = 'login' | 'register';
const usernamePattern = /^[A-Za-z0-9_.-]+$/;

function errorMessage(error: unknown) {
  if (!(error instanceof ApiError)) return 'We could not reach LeafNode. Check the API connection and try again.';
  if (error.status === 401) return 'The username or password is incorrect.';
  if (error.status === 409) return 'That username is already in use.';
  if (error.status === 422) return error.message.replace(/^HTTP 422:\s*/, '') || 'Check the highlighted details and try again.';
  return error.message.replace(/^HTTP \d+:?\s*/, '') || 'Something went wrong. Please try again.';
}

function validate(username: string, password: string, confirmPassword: string, mode: Mode) {
  if (username.length < 3 || username.length > 64 || !usernamePattern.test(username)) {
    return 'Username must be 3-64 characters and use only letters, numbers, underscores, periods, or hyphens.';
  }
  if (password.length < 12 || password.length > 128) return 'Password must be 12-128 characters.';
  if (mode === 'register' && password !== confirmPassword) return 'Passwords do not match.';
  return '';
}

export default function AuthPage({ onAuthenticated }: { onAuthenticated: () => void }) {
  const [mode, setMode] = useState<Mode>('login');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const switchMode = (nextMode: Mode) => {
    setMode(nextMode); setError(''); setNotice(''); setPassword(''); setConfirmPassword('');
  };
  const submit = async (event: FormEvent) => {
    event.preventDefault(); setError(''); setNotice('');
    const validationError = validate(username.trim(), password, confirmPassword, mode);
    if (validationError) { setError(validationError); return; }
    setBusy(true);
    try {
      if (mode === 'register') {
        await api.register({ username: username.trim(), password });
        setMode('login'); setPassword(''); setConfirmPassword('');
        setNotice('Your account is ready. Sign in to open your growing space.');
      } else {
        await api.login({ username: username.trim(), password });
        await api.me();
        onAuthenticated();
      }
    } catch (requestError) {
      clearAccessToken(); setError(errorMessage(requestError));
    } finally { setBusy(false); }
  };

  return <main className="auth-page">
    <div className="auth-atmosphere auth-atmosphere-one" />
    <div className="auth-atmosphere auth-atmosphere-two" />
    <section className="auth-layout" aria-labelledby="auth-title">
      <div className="auth-intro">
        <a className="auth-brand" href="#home" aria-label="LeafNode home"><span className="auth-brand-mark"><Leaf size={23}/></span><span>Leaf<span>Node</span></span></a>
        <div className="auth-intro-copy"><p className="auth-kicker"><span />Connected growing, thoughtfully designed</p><h1 id="auth-title">A clearer view of what your plants need.</h1><p>Bring sensor insight, gentle automation, and plant intelligence into one calm growing space.</p></div>
        <div className="auth-trust"><ShieldCheck size={16}/><span>Your account and session are protected with secure bearer authentication.</span></div>
      </div>
      <div className="auth-card">
        <div className="auth-card-heading"><span className="auth-card-leaf"><Leaf size={18}/></span><div><h2>{mode === 'login' ? 'Welcome back' : 'Create your account'}</h2><p>{mode === 'login' ? 'Sign in to continue tending your growing space.' : 'Start with a secure LeafNode account.'}</p></div></div>
        <div className="auth-tabs" role="tablist" aria-label="Authentication options">
          <button type="button" role="tab" aria-selected={mode === 'login'} className={mode === 'login' ? 'active' : ''} onClick={() => switchMode('login')}>Log in</button>
          <button type="button" role="tab" aria-selected={mode === 'register'} className={mode === 'register' ? 'active' : ''} onClick={() => switchMode('register')}>Create account</button>
        </div>
        <form className="auth-form" onSubmit={submit} noValidate>
          <label htmlFor="auth-username">Username<span aria-hidden="true">*</span></label>
          <input id="auth-username" name="username" autoComplete="username" value={username} onChange={event => setUsername(event.target.value)} disabled={busy} aria-invalid={Boolean(error)} />
          <span className="auth-hint">3-64 characters: letters, numbers, _, ., -</span>
          <label htmlFor="auth-password">Password<span aria-hidden="true">*</span></label>
          <div className="auth-password-field"><input id="auth-password" name="password" type={showPassword ? 'text' : 'password'} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} value={password} onChange={event => setPassword(event.target.value)} disabled={busy} aria-invalid={Boolean(error)} /><button type="button" className="auth-visibility" onClick={() => setShowPassword(value => !value)} aria-label={showPassword ? 'Hide password' : 'Show password'}>{showPassword ? <EyeOff size={17}/> : <Eye size={17}/>}</button></div>
          {mode === 'register' && <><label htmlFor="auth-confirm-password">Confirm password<span aria-hidden="true">*</span></label><input id="auth-confirm-password" name="confirmPassword" type={showPassword ? 'text' : 'password'} autoComplete="new-password" value={confirmPassword} onChange={event => setConfirmPassword(event.target.value)} disabled={busy} aria-invalid={Boolean(error)} /><span className="auth-hint">Use at least 12 characters.</span></>}
          {error && <p className="auth-message auth-error" role="alert">{error}</p>}
          {notice && <p className="auth-message auth-notice" role="status">{notice}</p>}
          <button className="auth-submit" type="submit" disabled={busy}>{busy ? <><LoaderCircle size={17} className="auth-spinner"/> {mode === 'login' ? 'Opening your space…' : 'Creating account…'}</> : mode === 'login' ? 'Log in to LeafNode' : 'Create account'}</button>
        </form>
        <p className="auth-footer">{mode === 'login' ? 'New to LeafNode? ' : 'Already have an account? '}<button type="button" onClick={() => switchMode(mode === 'login' ? 'register' : 'login')}>{mode === 'login' ? 'Create an account' : 'Log in'}</button></p>
      </div>
    </section>
  </main>;
}
