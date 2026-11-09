import test from 'node:test'
import assert from 'node:assert/strict'
import worker,{sign,verify} from './worker.mjs'
const secret='test-only-secret-with-more-than-32-characters'
const env={EMAIL_ENABLED:'true',SITE_ORIGIN:'https://esrarobotics.eu',BREVO_API_KEY:'stub',BREVO_LIST_ID:'3',BREVO_DOI_TEMPLATE_ID:'4',EMAIL_FROM:'events@esrarobotics.eu',ACCESS_SECRET:secret,EVENT_SUBMISSION_SECRET:secret,GITHUB_TOKEN:'stub',RATE_LIMITER:{limit:async()=>({success:true})}}
const request=(path,data,token,origin=env.SITE_ORIGIN)=>new Request('https://mail.example'+path,{method:'POST',headers:{Origin:origin,'Content-Type':'application/json',...(token?{Authorization:'Bearer '+token}:{})},body:JSON.stringify(data)})
test('signup requires consent, allowed origin and enabled service; sends provider double opt-in only',async t=>{
 const calls=[];t.mock.method(globalThis,'fetch',async(url,options)=>{calls.push({url,body:JSON.parse(options.body)});return new Response('{}',{status:201})})
 assert.equal((await worker.fetch(request('/subscribe',{email:'a@example.com'}),env)).status,400)
 assert.equal((await worker.fetch(request('/subscribe',{email:'a@example.com',consent:true},null,'https://bad.example'),env)).status,403)
 assert.equal((await worker.fetch(request('/subscribe',{}),{...env,EMAIL_ENABLED:'false'})).status,503)
 assert.equal(calls.length,0)
 assert.equal((await worker.fetch(request('/subscribe',{email:'a@example.com',consent:true}),env)).status,202)
 assert.equal(calls[0].url,'https://api.brevo.com/v3/contacts/doubleOptinConfirmation')
 assert.deepEqual(calls[0].body.includeListIds,[3]);assert.equal(calls[0].body.contactPixelTrackingConsent,false)
})
test('provider failure and rate limiting never return a saved-subscription success',async t=>{
 t.mock.method(globalThis,'fetch',async()=>new Response('{}',{status:500}))
 assert.equal((await worker.fetch(request('/subscribe',{email:'a@example.com',consent:true}),env)).status,400)
 assert.equal((await worker.fetch(request('/subscribe',{}),{...env,RATE_LIMITER:{limit:async()=>({success:false})}})).status,429)
})
test('only exact ESRA domain can request a signed inbox link',async t=>{
 const calls=[];t.mock.method(globalThis,'fetch',async(url,options)=>{calls.push(JSON.parse(options.body));return new Response('{}',{status:201})})
 for(const email of ['a@example.com','a@esrarobotics.eu.attacker.com','a@attacker-esrarobotics.eu'])assert.equal((await worker.fetch(request('/organiser/request-link',{email}),env)).status,400)
 assert.equal(calls.length,0)
 assert.equal((await worker.fetch(request('/organiser/request-link',{email:'A@ESRAROBOTICS.EU'}),env)).status,202)
 const token=calls[0].htmlContent.match(/#access=([\w.-]+)/)[1]
 assert.equal((await verify(token,secret,'organiser')).email,'a@esrarobotics.eu')
 assert.equal((await worker.fetch(request('/organiser/verify',{},token),env)).status,200)
})
test('expired, altered, wrong-purpose and absent credentials cannot submit',async()=>{
 for(const token of [undefined,await sign({purpose:'organiser',email:'a@esrarobotics.eu',expires:1},secret),await sign({purpose:'other',expires:Date.now()/1000+60},secret),'invalid.token'])assert.equal((await worker.fetch(request('/organiser/submit',{},token),env)).status,400)
})
test('verified submission creates a signed public issue without private email or Original privilege',async t=>{
 let issue;t.mock.method(globalThis,'fetch',async(url,options)=>{assert.match(url,/api.github.com/);issue=JSON.parse(options.body);return new Response('{}',{status:201})})
 const access=await sign({purpose:'organiser',email:'private@esrarobotics.eu',expires:Date.now()/1000+60},secret)
 const event={title:'Robot workshop',organiser:'Member club',location:'Munich',description:'A practical student robotics workshop with technical exchange.',relevance:'Connect student robotics teams across Europe.',type:'Workshops',url:'https://example.com/event',start:'2027-04-02T12:00:00Z',end:'2027-04-02T14:00:00Z',rules:true,original:true,email:'private@esrarobotics.eu'}
 assert.equal((await worker.fetch(request('/organiser/submit',event,access),env)).status,202)
 assert.ok(!issue.body.includes('private@'))
 const proof=await verify(issue.body.split('### ESRA verification\n\n')[1],secret,'event-submission')
 assert.equal(proof.domain,'esrarobotics.eu');assert.equal(proof.event.original,undefined);assert.equal(proof.event.rules,undefined)
})
