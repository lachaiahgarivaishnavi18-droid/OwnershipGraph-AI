import React,{useEffect,useState} from 'react';
import {Link,useLocation} from 'react-router-dom';
import {Network,ArrowRight} from 'lucide-react';
import {api,message} from './api';
import {Notice} from './components';

export function Login({onLogin}){
  const location=useLocation();
  const registering=location.pathname==='/register';
  const [username,setUsername]=useState(registering?'':'analyst');
  const [email,setEmail]=useState('');
  const [password,setPassword]=useState('');
  const [confirmation,setConfirmation]=useState('');
  const [registrationEnabled,setRegistrationEnabled]=useState(false);
  const [configReady,setConfigReady]=useState(false);
  const [error,setError]=useState('');
  const [busy,setBusy]=useState(false);
  useEffect(()=>{
    let live=true;
    (async()=>{
      try{const {data}=await api.get('/auth/config');if(live)setRegistrationEnabled(data.registration_enabled===true);}
      catch{if(live)setRegistrationEnabled(false);}
      finally{if(live)setConfigReady(true);}
    })();
    return()=>{live=false;};
  },[]);
  useEffect(()=>{setError('');setPassword('');setConfirmation('');setUsername(registering?'':'analyst');},[registering]);
  async function submit(event){
    event.preventDefault();setError('');
    if(registering&&password!==confirmation){setError('Passwords do not match.');return;}
    setBusy(true);
    try{
      const endpoint=registering?'/auth/signup':'/auth/login';
      const input=registering?{username,email,password}:{username,password};
      const {data}=await api.post(endpoint,input);
      sessionStorage.setItem('token',data.access_token);onLogin(data.user);
    }catch(exc){
      const details=exc.response?.data?.details;
      setError(details?.length?details.map(d=>`${d.loc.at(-1)}: ${d.msg}`).join(' '):message(exc));
    }finally{setBusy(false);}
  }
  return <div className="login-page">
    <div className="login-story">
      <div className="brand"><div className="brand-symbol"><Network size={28}/></div><span>OwnershipGraph<span className="brand-ai"> AI</span></span></div>
      <div>
        <div className="eyebrow">CONNECTED EVIDENCE. CLEARER DECISIONS.</div>
        <h1>See beyond<br/>the first layer.</h1>
        <p>Discover the people behind corporate structures.<br/>Turn complex networks into explainable investigations.</p>
        <div className="login-network"><div>Aster Maritime</div><span>60% ────────── 30%</span><section><div>Northstar Holdings</div><div>Cedar Capital</div></section><span>│ &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; │</span><section><div>Elena Vale</div><div>Marcus Chen</div></section></div>
      </div>
      <small>Academic research platform · Synthetic demonstration data</small>
    </div>
    <div className="login-form"><form onSubmit={submit}>
      <span className="badge verified">{registering?'CREATE YOUR ANALYST ACCOUNT':'SECURE ANALYST ACCESS'}</span>
      <h2>{registering?'Create your account':'Welcome to your workspace'}</h2>
      <p>{registering?'Start exploring ownership networks and create your own investigations.':'Sign in to continue your investigation.'}</p>
      {registering&&configReady&&!registrationEnabled?<Notice>Account creation is currently disabled. Contact your administrator or <Link to="/login">sign in</Link>.</Notice>:<>
        <label>Username<input autoComplete="username" value={username} onChange={e=>setUsername(e.target.value)} minLength={registering?3:undefined} maxLength={80} pattern={registering?'[A-Za-z0-9_.-]+':undefined} title={registering?'Use letters, numbers, dots, hyphens or underscores.':undefined} required/></label>
        {registering&&<label>Email address<input type="email" autoComplete="email" value={email} onChange={e=>setEmail(e.target.value)} maxLength={254} required/></label>}
        <label>Password<input aria-label="Password" autoComplete={registering?'new-password':'current-password'} type="password" value={password} onChange={e=>setPassword(e.target.value)} minLength={registering?8:undefined} maxLength={128} placeholder={registering?'e.g. demo@2026':undefined} required/>{registering&&<small>Use at least 8 characters, for example demo@2026.</small>}</label>
        {registering&&<label>Confirm password<input autoComplete="new-password" type="password" value={confirmation} onChange={e=>setConfirmation(e.target.value)} minLength={8} maxLength={128} required/></label>}
        {error&&<div className="error" role="alert">{error}</div>}
        <button className="primary full" disabled={busy||(registering&&(!configReady||!registrationEnabled))}>{busy?(registering?'Creating account…':'Signing in…'):(registering?'Create account':'Sign in to workspace')}<ArrowRight size={17}/></button>
      </>}
      <div className="auth-switch">{registering?<><span>Already have an account?</span><Link to="/login">Sign in</Link></>:registrationEnabled?<><span>New to OwnershipGraph AI?</span><Link to="/register">Create account<ArrowRight size={14}/></Link></>:null}</div>
      {!registering&&<p className="login-help">Demo accounts: analyst, reviewer, admin.<br/>Use the configured demo password.</p>}
      <Notice>{registering?'Your account starts with the Analyst role. You can create investigations and submit them for independent review.':'Screening sources are disconnected. All demo entities are synthetic.'}</Notice>
    </form></div>
  </div>;
}
