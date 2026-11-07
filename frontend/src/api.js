import axios from 'axios';
export const api=axios.create({baseURL:'/api',timeout:120000});
api.interceptors.request.use(config=>{const token=sessionStorage.getItem('token');if(token) config.headers.Authorization=`Bearer ${token}`;return config;});
api.interceptors.response.use(r=>r,error=>{if(error.response?.status===401 && !error.config.url.includes('/auth/login')){sessionStorage.removeItem('token');window.location.assign('/login');}return Promise.reject(error);});
export const message=e=>e.response?.data?.error||e.message||'Request failed';
export async function downloadReport(caseId,format){const {data}=await api.post(`/reports/generate/${caseId}`,{format});const result=await api.get(data.download_url.replace('/api',''),{responseType:'blob'});const url=URL.createObjectURL(result.data);const a=document.createElement('a');a.href=url;a.download=`ownershipgraph-${caseId}.${format}`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
