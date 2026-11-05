import {createClient} from '@supabase/supabase-js';
const url=import.meta.env.VITE_SUPABASE_URL;const key=import.meta.env.VITE_SUPABASE_ANON_KEY;
export const supabase=url&&key?createClient(url,key):null;
export const API=import.meta.env.VITE_API_URL||'http://localhost:8000';
export async function api(path,options={}){const session=supabase?(await supabase.auth.getSession()).data.session:null;const headers={...(options.body instanceof FormData?{}:{'Content-Type':'application/json'}),...(session?{Authorization:`Bearer ${session.access_token}`}:{}) ,...(options.headers||{})};const res=await fetch(`${API}${path}`,{...options,headers});if(!res.ok){const data=await res.json().catch(()=>({detail:'Request failed'}));throw new Error(data.detail||'Request failed')}return res.headers.get('content-type')?.includes('application/pdf')?res.blob():res.json()}
