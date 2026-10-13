import fs from 'node:fs';
import path from 'node:path';
const dir=path.dirname(new URL(import.meta.url).pathname).replace(/^\/([A-Za-z]:)/,'$1');
const parseLines=file=>fs.readFileSync(file,'utf8').split(/\r?\n/).flatMap(line=>{try{return [JSON.parse(line)]}catch{return []}});
const browser=parseLines(path.join(dir,'browser.jsonl'));
const allEvents=fs.readdirSync(dir).filter(f=>f.endsWith('.stdout.log')).flatMap(f=>parseLines(path.join(dir,f)));
const rows=browser.map(b=>{
  const events=allEvents.filter(e=>e.request_id===b.request_id);
  const last=name=>events.filter(e=>e.event===name).at(-1);
  const dur=name=>last(name)?.duration_ms??null;
  const rag=last('rag.stages');
  const end=last('request.completed');
  const compose=last('final_response.composed');
  const validation=last('audit.composer.validation');
  const attempts=events.filter(e=>e.event==='audit.provider.attempt');
  const providers=Object.fromEntries(['groq','azure','gemini'].map(provider=>{
    const list=attempts.filter(e=>e.provider===provider);
    return [provider,{calls:list.length,total_ms:Math.round(list.reduce((s,e)=>s+e.duration_ms,0)*100)/100,attempts:list}];
  }));
  const completed=end?.timestamp;
  const started=last('request.started')?.timestamp;
  const total=b.browser_total_ms;
  const row={scenario:b.id,route:b.body?.route,language:b.body?.language,http_status:b.http_status,response_status:b.body?.status,
    request_id:b.request_id,trace_id:end?.trace_id,thread_id:b.body?.thread_id,
    backend_ms:dur('request.completed'),browser_ms:total,
    language_ms:dur('language.completed'),security_ms:dur('security.completed'),memory_ms:dur('memory.context.completed'),
    supervisor_ms:dur('supervisor.provider.completed'),routing_ms:dur('routing.completed'),
    rag_retrieval_ms:rag?.retrieval_ms??null,rag_generation_ms:rag?.generation_provider_ms??null,
    graph_ms:dur('graph.completed'),azure_ms:validation?compose?.latency_ms:null,
    persistence_ms:dur('persistence.history.completed'),init_ms:dur('rag.retrieval_service.created'),
    sql_ms:dur('audit.history.sql'),memory_index_ms:dur('audit.memory.index'),
    memory_embedding_ms:dur('audit.memory.embedding_passages'),
    rag_used:!!last('rag.completed'),grounded:b.body?.grounded,citations:b.body?.citations?.length,
    quiz_present:!!b.body?.quiz_session,quiz_internal:compose?.composer_status==='bypassed_quiz',composer_status:compose?.composer_status,
    azure_logical_attempts:validation?.attempts?.length??0,composer_retries:compose?.retry_count??0,
    total_retries:(compose?.retry_count??0)+events.filter(e=>e.event==='rag.generation.retry').length+attempts.filter(e=>Number(e.sdk_retry)>0).length,
    observed_retry_waste_ms:attempts.filter(e=>e.error_type || (e.status_code??0)>=400).reduce((s,e)=>s+e.duration_ms,0)+events.filter(e=>e.event==='rag.generation.retry').reduce((s,e)=>s+(e.delay_ms??0),0),
    validation:validation?.attempts,providers,
    retry_events:events.filter(e=>/retry|failed/.test(e.event)),
    browser_request_start:b.browser_request_start,browser_response_end:b.browser_response_end,
    backend_started_at:started,backend_completed_at:completed,
    browser_after_backend_ms:completed?Date.parse(b.browser_response_end)-Date.parse(completed):null,
    pre_business_ms:started?Date.parse(started)-Date.parse(b.browser_request_start):null,
    receive_to_render_ms:b.receive_to_render_ms,click_to_render_ms:b.click_to_render_ms,
    classification:total<10000?'FAST':total<30000?'ACCEPTABLE':total<=60000?'SLOW':'DEMO_BLOCKING',events};
  const components=[['Azure composer',row.azure_ms],['RAG retrieval',row.rag_retrieval_ms],['RAG generation',row.rag_generation_ms],['Persistence + memory index',row.persistence_ms],['Cold initialization',row.pre_business_ms],['Memory context',row.memory_ms],['Supervisor',row.supervisor_ms]];
  row.bottleneck=components.sort((a,b)=>(b[1]??0)-(a[1]??0))[0][0];
  return row;
});
fs.writeFileSync(path.join(dir,'measurements.json'),JSON.stringify(rows,null,2));
const flatKeys=['scenario','route','language','http_status','request_id','trace_id','thread_id','backend_ms','browser_ms','language_ms','security_ms','memory_ms','supervisor_ms','routing_ms','rag_retrieval_ms','rag_generation_ms','graph_ms','azure_ms','persistence_ms','init_ms','sql_ms','memory_index_ms','memory_embedding_ms','rag_used','grounded','citations','quiz_present','composer_status','azure_logical_attempts','composer_retries','browser_request_start','browser_response_end','backend_started_at','backend_completed_at','browser_after_backend_ms','pre_business_ms','receive_to_render_ms','click_to_render_ms','classification','bottleneck'];
flatKeys.push('response_status','quiz_internal','total_retries','observed_retry_waste_ms');
const csv=v=>JSON.stringify(v??'N/A');
fs.writeFileSync(path.join(dir,'timings.csv'),[flatKeys.join(','),...rows.map(r=>flatKeys.map(k=>csv(r[k])).join(','))].join('\n'));
const n=v=>v===null||v===undefined?'N/A':typeof v==='number'?String(Math.round(v)):String(v);
const table=(headers,data)=>['| '+headers.join(' | ')+' |','| '+headers.map(()=>'---').join(' | ')+' |',...data.map(r=>'| '+r.map(n).join(' | ')+' |')].join('\n');
const summary=table(['Scénario','Route','RAG','Azure','Retries totaux','Backend ms¹','Navigateur ms','Classe','Goulot'],rows.map(r=>[r.scenario,r.route,r.rag_used,r.composer_status,r.total_retries,r.backend_ms,r.browser_ms,r.classification,r.bottleneck]));
const stages=table(['Scénario','Langue','Langue ms','Sécurité','Mémoire','Supervisor','Routing²','RAG retrieval','RAG generation','Graph²','Azure','Persistance³','Initialisation RAG⁴'],rows.map(r=>[r.scenario,r.language,r.language_ms,r.security_ms,r.memory_ms,r.supervisor_ms,r.routing_ms,r.rag_retrieval_ms,r.rag_generation_ms,r.graph_ms,r.azure_ms,r.persistence_ms,r.init_ms]));
const clocks=table(['Scénario','Request start UTC','Backend completed UTC','Response end UTC','Après backend ms','Avant business ms','Réception → rendu ms','HTTP'],rows.map(r=>[r.scenario,r.browser_request_start,r.backend_completed_at,r.browser_response_end,r.browser_after_backend_ms,r.pre_business_ms,r.receive_to_render_ms,r.http_status]));
const providerTable=table(['Scénario','Groq HTTP appels/ms','Azure tentatives logiques','Azure HTTP appels/ms','Azure total composer ms','Gemini HTTP appels','Raisons rejet'],rows.map(r=>[r.scenario,`${r.providers.groq.calls} / ${n(r.providers.groq.total_ms)}`,r.azure_logical_attempts,r.azure_logical_attempts&&!r.providers.azure.calls?'Non instrumenté (premier lot)':`${r.providers.azure.calls} / ${n(r.providers.azure.total_ms)}`,r.azure_ms,r.providers.gemini.calls,(r.validation??[]).flatMap(a=>a.reasons??[]).join(', ')||'Aucune']));
const persistence=table(['Scénario','Persistance totale ms','SQL append ms','Index mémoire ms','Embedding mémoire ms'],rows.map(r=>[r.scenario,r.persistence_ms,r.sql_ms,r.memory_index_ms,r.memory_embedding_ms]));
fs.writeFileSync(path.join(dir,'tables.md'),[
'# Mesures détaillées — EduBourse',
'Toutes les durées sont en millisecondes. N/A signifie étape non exécutée, sauf colonnes de sous-instrumentation SQL/index du premier lot (non mesurées séparément).',
'## Matrice',summary,
'¹ Le compteur backend commence après résolution des dépendances FastAPI : il exclut notamment le chargement initial du graphe/RAG. Ne pas interpréter navigateur − backend comme du rendu frontend.',
'## Étapes',stages,
'² Étapes imbriquées : routing contient Supervisor et réhydratation ; graph contient sécurité, mémoire, routage et agent/RAG. Ne pas additionner ces colonnes ensemble. ³ Inclut indexation mémoire synchrone après écriture SQL. ⁴ Initialisation hors compteur request.completed.',
'## Horodatages et rendu',clocks,
'## Fournisseurs et retries',providerTable,
'Les appels HTTP observés incluent les retries SDK. Les tentatives logiques Azure correspondent aux essais du compositeur. Le temps du compositeur inclut SDK, validation et éventuelles reprises, pas seulement le réseau. Le compteur Gemini couvre les transports HTTPX instrumentés ; aucun parcours vocal/TTS appelé.',
'## Persistance : décomposition',persistence,
'## Identifiants de corrélation',table(['Scénario','request_id','trace_id'],rows.map(r=>[r.scenario,r.request_id,r.trace_id]))
].join('\n\n'));
console.log(JSON.stringify(rows.map(r=>({id:r.scenario,route:r.route,browser:r.browser_ms,backend:r.backend_ms,azure:r.azure_ms,index:r.memory_index_ms,retries:r.composer_retries,azure_http:r.providers.azure.calls,post:r.browser_after_backend_ms})),null,2));
