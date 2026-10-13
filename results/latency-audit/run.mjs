import fs from 'node:fs';
import path from 'node:path';
import { spawn, execFileSync } from 'node:child_process';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const {chromium} = require(path.join(process.env.TEMP, 'edubourse-latency-tools/node_modules/playwright-core'));
const root = process.cwd();
const out = path.join(root, 'results/latency-audit');
let backendPid = Number(process.argv[2]);
let runLabel;
const sleep = ms => new Promise(r=>setTimeout(r,ms));
const browser = await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true});
const context = await browser.newContext({viewport:{width:1440,height:1000}});
const page = await context.newPage();
page.setDefaultTimeout(15000);
await page.goto('http://localhost:5173/assistant');
await page.locator('#assistant-question').waitFor();
const runtime = await page.evaluate(async()=>{
  const chat = await import('/src/services/chat.ts');
  const voice = await import('/src/services/voice.ts');
  return {frontend_url:location.href,chat_endpoint:chat.CHAT_ENDPOINT,voice_endpoint:voice.voiceSocketUrl(),user_agent:navigator.userAgent};
});
fs.writeFileSync(path.join(out,'runtime.json'),JSON.stringify(runtime,null,2));
console.log('RUNTIME', JSON.stringify(runtime));

async function restart(label) {
  if (process.argv.includes('--verified')) label += '-verified';
  if (backendPid) {
    // Windows venv python.exe spawns a child: stop only the audited listener.
    execFileSync('powershell.exe',['-NoProfile','-Command',
      "$auditProcesses = Get-CimInstance Win32_Process -Filter \"name = 'python.exe'\" | Where-Object { $_.CommandLine -like '*results*latency-audit*serve_audit.py*' }; foreach ($proc in $auditProcesses) { Stop-Process -Id $proc.ProcessId -ErrorAction SilentlyContinue }"
    ],{windowsHide:true});
  }
  await sleep(1000);
  runLabel=label;
  const stdout=fs.openSync(path.join(out,`${label}.stdout.log`),'w');
  const stderr=fs.openSync(path.join(out,`${label}.stderr.log`),'w');
  const start=Date.now();
  const child=spawn(path.join(root,'backend/.venv/Scripts/python.exe'),['-u',path.join(out,'serve_audit.py')],{cwd:path.join(root,'backend'),env:process.env,windowsHide:true,detached:true,stdio:['ignore',stdout,stderr]});
  backendPid=child.pid;
  child.unref();
  fs.closeSync(stdout);fs.closeSync(stderr);
  fs.writeFileSync(path.join(out,'backend-pid.json'),JSON.stringify({pid:backendPid,label,started:new Date(start).toISOString()}));
  for(let i=0;i<240;i++){
    try {const r=await fetch('http://127.0.0.1:8080/health/live',{signal:AbortSignal.timeout(1000)});if(r.ok){console.log('STARTED',label,Date.now()-start);return;}} catch{}
    await sleep(500);
  }
  throw Error('Backend not ready');
}

async function run(id,query,sameThread=false){
  if (process.argv.includes('--verified')) id = 'v2-' + id;
  if(!sameThread) await page.locator('.ap-history-new').click();
  const before=await page.locator('.ap-bubble-bot').count();
  await page.locator('#assistant-question').fill(query);
  console.log('BEGIN',id,new Date().toISOString());
  const clickAt=Date.now();
  const responsePromise=page.waitForResponse(r=>r.url()===runtime.chat_endpoint && r.request().method()==='POST',{timeout:310000});
  await page.locator('.ap-send').click();
  const record={id,query,run:runLabel,click_at:new Date(clickAt).toISOString()};
  try{
    const response=await responsePromise;
    record.headers_received_at=new Date().toISOString();
    await response.finished();
    record.response_received_at=new Date().toISOString();
    record.http_status=response.status();
    record.request_id=(await response.allHeaders())['x-request-id'];
    record.request_body=response.request().postDataJSON();
    record.timing=response.request().timing();
    record.browser_request_start=new Date(record.timing.startTime).toISOString();
    record.browser_response_end=new Date(record.timing.startTime+record.timing.responseEnd).toISOString();
    record.browser_total_ms=record.timing.responseEnd;
    record.body=await response.json();
    await page.waitForFunction(n=>document.querySelectorAll('.ap-bubble-bot').length>n || !!document.querySelector('.ap-bubble-error'),before,{timeout:15000});
    record.rendered_at=new Date().toISOString();
    record.click_to_render_ms=Date.now()-clickAt;
    record.receive_to_render_ms=Date.now()-Date.parse(record.response_received_at);
    await page.screenshot({path:path.join(out,`${id}.png`)});
    console.log('RESULT',id,record.http_status,record.body.route,record.browser_total_ms);
  }catch(e){record.error=e.message;record.elapsed_ms=Date.now()-clickAt;console.log('ERROR',id,e.message);}
  fs.appendFileSync(path.join(out,'browser.jsonl'),JSON.stringify(record)+'\n');
  // Do not let any timed-out backend call overlap the following measurement.
  if(record.error) throw Error(`Stop after incomplete scenario ${id}`);
  await sleep(300);
}

try {
  if (!process.argv.includes('--resume-cisi')) {
  await restart('cold-fr');
  await run('A-cold',"Qu'est-ce qu'une obligation ?");
  await run('A-warm',"Qu'est-ce qu'une obligation ?");
  await restart('cold-quiz');
  await run('J-cold','Je veux un quiz.');
  await run('J-warm','Je veux un quiz.');
  }
  await restart('cold-cisi');
  await run('G-cold','Comment préparer la certification CISI ?');
  await run('G-warm','Comment préparer la certification CISI ?');
  for(const [id,q] of [
    ['B','What is a bond?'],['C','ما هي السندات؟'],['D','chno hiya obligation?'],
    ['E','Je veux suivre une formation pour débuter en Bourse.'],
    ['F','Par où commencer pour apprendre la Bourse ?'],
    ['H','Comment participer au Championnat de la Bourse ?'],
    ['I',"Je n'arrive pas à me connecter à mon compte e-learning."],
    ['K','Quelle action dois-je acheter maintenant ?'],
    ['L','Quelle est la capitale du Japon ?'],
    ['M1',"Qu'est-ce qu'une obligation ?"]]) await run(id,q);
  await run('M2','Et quels sont ses principaux risques ?',true);
  await run('N','Et quels sont ses principaux risques ?');
  console.log('MATRIX_COMPLETE');
} finally {await browser.close();}
