// Optional serverless relay: provider owns the mailing list; GitHub owns event review.
// No database, cookies, subscriber files or API credentials in the static website.
const DOMAIN='esrarobotics.eu'
const encoder=new TextEncoder()
const b64=bytes=>btoa(String.fromCharCode(...bytes)).replaceAll('+','-').replaceAll('/','_').replace(/=+$/,'')
const un64=value=>Uint8Array.from(atob(value.replaceAll('-','+').replaceAll('_','/')+'='.repeat((4-value.length%4)%4)),c=>c.charCodeAt(0))
const html=value=>String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;')
async function key(secret){if(!secret||secret.length<32)throw Error('Service not configured');return crypto.subtle.importKey('raw',encoder.encode(secret),{name:'HMAC',hash:'SHA-256'},false,['sign','verify'])}
export async function sign(payload,secret){const data=b64(encoder.encode(JSON.stringify(payload)));return data+'.'+b64(new Uint8Array(await crypto.subtle.sign('HMAC',await key(secret),encoder.encode(data))))}
export async function verify(token,secret,purpose){
  try{
    if(typeof token!=='string'||token.length>14000)throw Error()
    const [data,signature,...rest]=token.split('.')
    if(rest.length||!signature||!await crypto.subtle.verify('HMAC',await key(secret),un64(signature),encoder.encode(data)))throw Error()
    const result=JSON.parse(new TextDecoder().decode(un64(data)))
    if(result.purpose!==purpose||!Number.isFinite(result.expires)||result.expires<=Date.now()/1000)throw Error()
    return result
  }catch{throw Error('This sign-in link is invalid or expired. Request another link.')}
}
function email(value){const result=String(value||'').trim().toLowerCase();if(result.length>254||!/^[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+$/.test(result))throw Error('Enter a valid email address.');return result}
function memberEmail(value){const result=email(value);if(result.split('@')[1]!==DOMAIN)throw Error('Use your @esrarobotics.eu email address.');return result}
function cleanEvent(value){
  const result={}
  for(const [name,min,max] of [['title',1,160],['organiser',1,160],['location',1,160],['description',40,4000],['relevance',30,1500]]){
    const text=String(value[name]||'').trim();if(text.length<min||text.length>max||/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(text))throw Error('Please check '+name+'.');result[name]=text
  }
  if(!['Trips','Hackathons','Workshops','Meetups','Build weeks','Exchanges'].includes(value.type))throw Error('Choose a supported event type.')
  result.type=value.type
  const url=new URL(value.url);if(url.protocol!=='https:'||url.username||url.password||url.href.length>1000)throw Error('Use a public HTTPS event link.');result.url=url.href
  const start=new Date(value.start),end=new Date(value.end)
  if(!Number.isFinite(+start)||!Number.isFinite(+end)||end<start||end-start>366*86400000)throw Error('Please check the event dates.')
  result.start=start.toISOString();result.end=end.toISOString();return result
}
async function provider(env,path,payload){
  const response=await fetch('https://api.brevo.com/v3'+path,{method:'POST',headers:{'api-key':env.BREVO_API_KEY,'Content-Type':'application/json'},body:JSON.stringify(payload)})
  if(!response.ok)throw Error('Email service is temporarily unavailable. Please try again later.')
}
export default {async fetch(request,env){
  const origin=request.headers.get('Origin'),allowed=(env.ALLOWED_ORIGINS||env.SITE_ORIGIN||'').split(',').map(s=>s.trim())
  const headers={'Content-Type':'application/json','Cache-Control':'no-store','Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff','Vary':'Origin'}
  if(allowed.includes(origin))headers['Access-Control-Allow-Origin']=origin
  const reply=(data,status=200)=>new Response(JSON.stringify(data),{status,headers})
  if(!allowed.includes(origin))return reply({error:'Origin not allowed.'},403)
  if(request.method==='OPTIONS')return new Response(null,{status:204,headers:{...headers,'Access-Control-Allow-Methods':'POST, OPTIONS','Access-Control-Allow-Headers':'Content-Type, Authorization'}})
  if(request.method!=='POST')return reply({error:'Method not allowed.'},405)
  // Fail closed. No real mail is sent until the owner enables and configures the service.
  if(env.EMAIL_ENABLED!=='true'||!env.BREVO_API_KEY||!env.RATE_LIMITER||!env.SITE_ORIGIN)return reply({error:'Email signup is being connected. Please try again soon.'},503)
  try{
    const limited=await env.RATE_LIMITER.limit({key:request.headers.get('CF-Connecting-IP')||'unknown'})
    if(!limited.success)return reply({error:'Too many requests. Please try again later.'},429)
    if(request.headers.get('Content-Type')?.split(';')[0]!=='application/json')return reply({error:'Use JSON.'},415)
    const bytes=await request.arrayBuffer();if(bytes.byteLength>16000)return reply({error:'Request too large.'},413)
    const data=JSON.parse(new TextDecoder().decode(bytes)),path=new URL(request.url).pathname
    if(!data||typeof data!=='object'||Array.isArray(data))throw Error('Invalid request.')
    if(path==='/subscribe'){
      if(data.consent!==true)throw Error('Please agree to receive ESRA event updates.')
      if(data.website)return reply({message:'Please check your inbox to confirm your subscription.'},202)
      const address=email(data.email),list=Number(env.BREVO_LIST_ID),template=Number(env.BREVO_DOI_TEMPLATE_ID)
      if(!Number.isInteger(list)||list<=0||!Number.isInteger(template)||template<=0)return reply({error:'Email signup is being connected. Please try again soon.'},503)
      await provider(env,'/contacts/doubleOptinConfirmation',{email:address,includeListIds:[list],templateId:template,redirectionUrl:env.SITE_ORIGIN+'/events/?subscribed=confirmed',contactPixelTrackingConsent:false})
      return reply({message:'Check your inbox and confirm your email to join the European robotics list.'},202)
    }
    if(path==='/organiser/request-link'){
      const address=memberEmail(data.email)
      if(!env.EMAIL_FROM)return reply({error:'Organiser sign-in is being connected.'},503)
      const access=await sign({purpose:'organiser',email:address,expires:Math.floor(Date.now()/1000)+1200,nonce:crypto.randomUUID()},env.ACCESS_SECRET)
      const link=env.SITE_ORIGIN+'/events/submit/#access='+access
      await provider(env,'/smtp/email',{sender:{email:env.EMAIL_FROM,name:'ESRA Events'},to:[{email:address}],subject:'Your ESRA organiser sign-in link',htmlContent:'<html><body style="background:#f3f4f1;color:#222;font-family:Arial;padding:32px"><p>ESRA / ORGANISERS</p><h1>Your next event starts here.</h1><p>Use this private link to submit an event. It expires in 20 minutes.</p><p><a href="'+html(link)+'" style="display:inline-block;background:#fff0b5;padding:16px;color:#222">Open ESRA event submission</a></p><p>If you did not request this, ignore this email.</p></body></html>'})
      return reply({message:'A private sign-in link has been requested for your ESRA inbox.'},202)
    }
    if(path==='/applications/china'){
      // Participant details stay private. Never create a public GitHub issue.
      if(env.APPLICATIONS_ENABLED!=='true'||!env.APPLICATION_REVIEWERS||!env.EMAIL_FROM)return reply({error:'Applications are not open yet. Please check back for updates.'},503)
      if(data.consent!==true)throw Error('Please agree to application review and contact.')
      if(data.website)throw Error('Please check your application.')
      const application={email:email(data.email)}
      for(const [field,min,max] of [['name',1,160],['organisation',1,160],['work',80,3000],['motivation',60,2000],['contribution',60,2000]]){
        const value=String(data[field]||'').trim()
        if(value.length<min||value.length>max||/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(value))throw Error('Please check '+field+'.')
        application[field]=value
      }
      const portfolio=new URL(data.portfolio)
      if(portfolio.protocol!=='https:'||portfolio.username||portfolio.password||portfolio.href.length>1000)throw Error('Use an HTTPS project or portfolio link.')
      application.portfolio=portfolio.href
      const reviewers=env.APPLICATION_REVIEWERS.split(',').map(value=>({email:memberEmail(value)}))
      if(!reviewers.length||reviewers.length>5)throw Error('Application review is not configured.')
      const content=Object.entries(application).map(([field,value])=>'<h2>'+html(field)+'</h2><p style="white-space:pre-wrap">'+html(value)+'</p>').join('')
      await provider(env,'/smtp/email',{sender:{email:env.EMAIL_FROM,name:'ESRA Applications'},to:reviewers,subject:'China delegation 2027: new application',htmlContent:'<html><body style="background:#f3f4f1;color:#222;font-family:Arial;padding:32px"><p>ESRA / PRIVATE APPLICATION REVIEW</p><h1>China robotics delegation</h1>'+content+'<p>Applicant agreed to review and contact about this delegation. A submission does not confirm a place. Handle privately under ESRA’s retention policy.</p></body></html>'})
      return reply({message:'Application submitted for private ESRA review. This does not confirm a place. ESRA will contact you about next steps.'},202)
    }
    const access=request.headers.get('Authorization')?.replace(/^Bearer /,'')
    const identity=await verify(access,env.ACCESS_SECRET,'organiser');memberEmail(identity.email)
    if(path==='/organiser/verify')return reply({eligible:true})
    if(path==='/organiser/submit'){
      if(data.rules!==true)throw Error('Please accept the submission guidelines.')
      if(!env.GITHUB_TOKEN||!env.EVENT_SUBMISSION_SECRET)return reply({error:'Event review is being connected.'},503)
      const event=cleanEvent(data)
      // Public attestation proves ESRA-domain access without exposing the organiser email.
      const proof=await sign({purpose:'event-submission',domain:DOMAIN,event,expires:Math.floor(Date.now()/1000)+7*86400},env.EVENT_SUBMISSION_SECRET)
      const body='### Event details\n\n```json\n'+JSON.stringify(event,null,2)+'\n```\n\n### Review acknowledgement\n\nI am authorised to submit this public event and agree to the ESRA event guidelines.\n\n### ESRA verification\n\n'+proof
      const response=await fetch('https://api.github.com/repos/ESRA-Robotics/website/issues',{method:'POST',headers:{Authorization:'Bearer '+env.GITHUB_TOKEN,'Content-Type':'application/json','User-Agent':'ESRA-Events','X-GitHub-Api-Version':'2022-11-28'},body:JSON.stringify({title:'[Event] '+event.title,body})})
      if(!response.ok)throw Error('Your event could not be submitted. Please try again later.')
      return reply({message:'Submitted for ESRA review. Your event is not published yet.'},202)
    }
    return reply({error:'Not found.'},404)
  }catch(error){return reply({error:error.message||'Please check your request.'},400)}
}}
