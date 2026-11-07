import React from 'react';
import {it,expect,vi,beforeEach,afterEach} from 'vitest';
import {render,screen,fireEvent,waitFor,cleanup} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {Login} from './AuthScreen';
import {api} from './api';
vi.mock('./api',()=>({api:{get:vi.fn(),post:vi.fn()},message:e=>e.message}));
beforeEach(()=>{vi.clearAllMocks();sessionStorage.clear();api.get.mockResolvedValue({data:{registration_enabled:true}});});
afterEach(cleanup);
it('offers create account from the sign-in screen',async()=>{
  render(<MemoryRouter><Login onLogin={vi.fn()}/></MemoryRouter>);
  fireEvent.click(await screen.findByRole('link',{name:'Create account'}));
  expect(await screen.findByRole('heading',{name:'Create your account'})).toBeInTheDocument();
  expect(screen.getByLabelText('Email address')).toBeInTheDocument();
});
function fill(password='demo@2026',confirmation=password){
  fireEvent.change(screen.getByLabelText('Username'),{target:{value:'new_analyst'}});
  fireEvent.change(screen.getByLabelText('Email address'),{target:{value:'new@example.invalid'}});
  fireEvent.change(screen.getByLabelText('Password',{exact:true}),{target:{value:password}});
  fireEvent.change(screen.getByLabelText('Confirm password'),{target:{value:confirmation}});
}
it('creates an account with demo@2026 and opens the authenticated workspace',async()=>{
  const onLogin=vi.fn();api.post.mockResolvedValue({data:{access_token:'new-token',user:{username:'new_analyst',role:'analyst'}}});
  render(<MemoryRouter initialEntries={['/register']}><Login onLogin={onLogin}/></MemoryRouter>);
  await waitFor(()=>expect(screen.getByRole('button',{name:'Create account'})).toBeEnabled());fill();
  fireEvent.click(screen.getByRole('button',{name:'Create account'}));
  await waitFor(()=>expect(api.post).toHaveBeenCalledWith('/auth/signup',{username:'new_analyst',email:'new@example.invalid',password:'demo@2026'}));
  expect(onLogin).toHaveBeenCalledWith({username:'new_analyst',role:'analyst'});
});
it('requires matching password confirmation',async()=>{
  render(<MemoryRouter initialEntries={['/register']}><Login onLogin={vi.fn()}/></MemoryRouter>);
  await waitFor(()=>expect(screen.getByRole('button',{name:'Create account'})).toBeEnabled());fill('demo@2026','different-password');
  fireEvent.click(screen.getByRole('button',{name:'Create account'}));
  expect(await screen.findByRole('alert')).toHaveTextContent('Passwords do not match');
  expect(api.post).not.toHaveBeenCalled();
});
