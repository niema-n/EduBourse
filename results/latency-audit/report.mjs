import fs from 'node:fs';
import path from 'node:path';
const dir=path.dirname(new URL(import.meta.url).pathname).replace(/^\/([A-Za-z]:)/,'$1');
const rows=JSON.parse(fs.readFileSync(path.join(dir,'measurements.json'),'utf8'));
const main=rows.filter(r=>r.scenario.startsWith('v2-'));
const pilot=rows.filter(r=>!r.scenario.startsWith('v2-'));
const n=v=>v==null?'N/A':typeof v==='number'?v.toFixed(2):String(v);
const table=(headers,data)=>['| '+headers.join(' | ')+' |','| '+headers.map(()=>'---').join(' | ')+' |',...data.map(r=>'| '+r.map(n).join(' | ')+' |')].join('\n');
const get=id=>main.find(r=>r.scenario==='v2-'+id);
const max=key=>Math.max(...rows.map(r=>r[key]??0));
const min=key=>Math.min(...rows.map(r=>r[key]).filter(v=>v!=null));
const descriptions={'A-cold':'Pédagogie FR froid','A-warm':'Pédagogie FR chaud','J-cold':'Quiz froid','J-warm':'Quiz chaud','G-cold':'CISI froid','G-warm':'CISI chaud',B:'Pédagogie EN',C:'Pédagogie AR',D:'Pédagogie ARY',E:'Formation',F:'Orientation',H:'Championnat',I:'Support',K:'Sécurité',L:'Hors domaine',M1:'Mémoire tour 1',M2:'Mémoire tour 2',N:'Contrôle nouveau fil'};
const matrix=table(['Scénario','Route','RAG','Azure','Retries','Backend ms¹','Browser ms','Classe','Goulot'],main.map(r=>[descriptions[r.scenario.slice(3)],r.route,r.rag_used?'oui':'non',r.composer_status==='bypassed_quiz'?'bypass':r.composer_status,r.total_retries,r.backend_ms,r.browser_ms,r.classification,r.bottleneck]));
const cold=table(['Parcours','Froid ms','Chaud ms','Écart ms','Initialisation RAG ms','Avant compteur business ms'],['A','J','G'].map(id=>{const c=get(id+'-cold'),w=get(id+'-warm');return [id,c?.browser_ms,w?.browser_ms,c&&w?c.browser_ms-w.browser_ms:null,c?.init_ms,c?.pre_business_ms]}));
const providers=table(['Scénario','Groq appels / ms','Azure tentatives / HTTP / ms HTTP','Azure composer ms','Gemini HTTP','Statut métier'],main.map(r=>[r.scenario.slice(3),`${r.providers.groq.calls} / ${n(r.providers.groq.total_ms)}`,`${r.azure_logical_attempts} / ${r.providers.azure.calls} / ${n(r.providers.azure.total_ms)}`,r.azure_ms,r.providers.gemini.calls,r.response_status]));
const retryRows=rows.filter(r=>r.total_retries>0 || r.validation?.some(a=>!a.accepted));
const retryTable=table(['Scénario','Reprises','Faits observés','Temps perdu observé ms','Résultat'],retryRows.map(r=>[r.scenario,r.total_retries,r.providers.groq.attempts.filter(a=>a.status_code>=400).map(a=>`Groq ${a.status_code} (${n(a.duration_ms)} ms)`).join('; ') || JSON.stringify(r.validation),r.observed_retry_waste_ms,r.response_status]));
const slow=table(['Scénario','Browser ms','Classe'],rows.filter(r=>r.browser_ms>30000).map(r=>[r.scenario,r.browser_ms,r.classification]));
const fastest=table(['Scénario chaud','Browser ms'],main.filter(r=>!r.scenario.endsWith('cold')).sort((a,b)=>a.browser_ms-b.browser_ms).slice(0,5).map(r=>[r.scenario,r.browser_ms]));
const checks=table(['Scénario','Langue','Grounded','Citations','Quiz interne','Quiz exposé JSON','Statut'],main.map(r=>[r.scenario,r.language,r.grounded,r.citations,r.quiz_internal,r.quiz_present,r.response_status]));
const report=`# Audit de latence frontend EduBourse — 19 septembre 2026

Verdict : **${main.length===18?'FRONTEND_LATENCY_MATRIX_READY':'FRONTEND_LATENCY_DIAG_INCOMPLETE'}**.

Diagnostic uniquement. Aucun code de production, fichier .env, configuration Docker ou index RAG modifié. Seuls des scripts et résultats de diagnostic ont été créés dans ce dossier. Les requêtes réelles ont produit des conversations de test et l’indexation mémoire normale de l’application ; aucune réindexation RAG ni suppression de données n’a été demandée par l’audit.

## 1. Runtime réellement utilisé

- FRONTEND_URL = http://localhost:5173/assistant
- FRONTEND_API_BASE = http://localhost:8080
- CHAT_ENDPOINT = http://localhost:8080/api/v1/chat
- VOICE_ENDPOINT = ws://localhost:8080/api/v1/voice/live
- TARGET_BACKEND_RUNTIME = backend **hôte Windows**, Python du venv backend, Uvicorn sur 127.0.0.1:8080, configuration chargée depuis le .env racine.
- Frontend = Vite local, PID initial 20616. Backend initial = PID 23104, commande : python -m uvicorn app.main:app --env-file ../.env --host 127.0.0.1 --port 8080.
- Docker ne servait aucun backend. PostgreSQL, ChromaDB, MCP et n8n étaient actifs ; PostgreSQL joint sur 127.0.0.1:5432. Le RAG applicatif ouvre son index persistant local, pas le serveur Chroma Docker pour ces requêtes.
- Configuration effective : PERSISTENCE_ENABLED=true, RELEVANT_MEMORY_ENABLED=true (défaut), RAG_WARMUP_ENABLED=false (défaut), FINANCIAL_EXPERT_FALLBACK_ENABLED=false (défaut), FINAL_RESPONSE_PROVIDER=azure_openai, max_output_tokens=4096.
- Cette configuration diffère de Compose : mémoire pertinente désactivée et préchauffage RAG activé par défaut dans Compose. L’audit mesure le runtime que le frontend appelle, sans changer ces réglages.

Preuve navigateur : [runtime.json](runtime.json). Chromium réel headless 153, Windows, viewport 1440×1000 ; clics dans le formulaire React, aucun appel direct d’un client HTTP à la place des parcours utilisateur.

## 2. Méthode et limites

${rows.length} requêtes mesurées, deux passes de 18. Chaque passe comporte trois paires froid/chaud (FR, quiz, CISI), puis EN, AR, ARY, formation, orientation, championnat, support, sécurité, hors domaine, mémoire deux tours et contrôle neuf. Chaque requête emploie un nouveau thread, sauf M2 qui reprend exclusivement M1. Les répétitions chaud ne réutilisent pas le contexte conversationnel.

Le backend hôte a été relancé avec le même environnement et le même code via [serve_audit.py](serve_audit.py). Les wrappers temporaires ne changent ni réponses, ni timeout, ni retry : ils chronomètrent HTTPX (Groq), HTTPX2 (OpenAI), validation Azure et sous-étapes de persistance. Le premier lot n’instrumentait pas HTTPX2 : ses compteurs de tentatives logiques et temps composer restent mesurés, mais pas sa durée réseau Azure isolée. La seconde passe fournit ces mesures complètes, sans remplacer ou cacher le premier lot.

Froid = premier POST chat après disponibilité de /health/live sur un nouveau processus ; pas un redémarrage Windows ni une purge du cache disque. Aucun warm-up artificiel. Une tentative de redémarrage du harnais a rencontré un port encore occupé, corrigée avant toute mesure CISI ; aucune mesure issue de ce démarrage rejeté n’est incluse.

Browser ms provient du timing réseau Chromium (request start → response end, corps reçu). Le rendu est contrôlé séparément par apparition du message dans le DOM React ; ce contrôle Playwright fournit une borne supérieure, pas un timestamp exact de peinture écran. Les captures sont des preuves d’interface, pas des traces vidéo. Les horloges navigateur et backend sont celles du même hôte, en UTC.

Échantillonnage court, non un p95/p99 de production. Machine : i5-1335U, 12 processeurs logiques, environ 7,64 Gio de RAM visible ; un instantané pendant l’audit montrait environ 0,58 Gio libres. BGE-M3 utilise le CPU. Pression mémoire plausible, **pagination disque non mesurée** : ne pas lui attribuer une durée exacte.

## 3. Matrice principale — seconde passe instrumentée

${matrix}

¹ Backend ms = compteur request.completed existant. **Il exclut la résolution des dépendances FastAPI et l’initialisation du graphe/RAG avant process_text_message.** La différence à froid n’est pas un délai de rendu frontend. Les nombres proches de 60 000 ms sont classés avant arrondi.

Tous les timings des deux passes, étapes, horodatages et request_id/trace_id sont dans [tables.md](tables.md), [timings.csv](timings.csv) et [measurements.json](measurements.json). Les entrées brutes navigateur sont dans [browser.jsonl](browser.jsonl).

## 4. Froid contre chaud

${cold}

Première passe indépendante : FR 65 566,10 → 18 617,80 ms ; quiz 40 274,21 → 4 723,46 ms ; CISI 43 553,09 → 3 096,08 ms. La variation entre passages interdit d’attribuer toute la différence à BGE seul.

Cause confirmée : [get_chat_graph](../../backend/app/api/chat.py) construit systématiquement _create_grounded_service avant de router, même pour quiz et CISI. [get_retrieval_service](../../backend/app/rag/runtime.py) charge BGE-M3 une fois par processus. Ce coût atteint ${n(max('init_ms'))} ms dans les mesures. Le préchauffage n’est pas activé dans le runtime hôte.

## 5. Frontend contre backend

Fin backend → fin réception navigateur : ${n(min('browser_after_backend_ms'))} à ${n(max('browser_after_backend_ms'))} ms sur les ${rows.length} requêtes. Aucune différence supérieure à 1 000 ms observée. Réception → contrôle du message DOM : maximum ${n(max('receive_to_render_ms'))} ms.

Le navigateur ne reste pas Pending plusieurs secondes après request.completed. [AssistantPage](../../frontend/src/pages/AssistantPage.tsx) ajoute le message dès résolution de sendChatMessage ; refreshHistory(true) est lancé sans await et ne bloque pas l’affichage. Pas de polling ni d’attente WebSocket sur le chat texte. [chat.ts](../../frontend/src/services/chat.ts) fixe un timeout à 300 000 ms, qui est une limite, pas une temporisation volontaire. Son requestDurationMs s’arrête après fetch, avant raw.json ; les mesures Chromium de cet audit incluent la fin du corps et le rendu est contrôlé à part.

## 6. Fournisseurs, retries et erreurs métier

${providers}

Nombre de tentatives HTTP réellement mesuré pour la seconde passe, dont éventuels retries SDK ; Azure composer inclut aussi initialisation du client et validation. Aucun appel Gemini observé dans ces chemins texte. Quiz/formation/orientation avec quiz = zéro Azure. Sécurité = zéro Groq Supervisor et zéro RAG.

${retryTable}

Le M2 de la première passe a subi deux HTTP 429 sur la génération RAG : 193,73 ms + attente déclarée 8 000 ms + 299,82 ms = **8 493,55 ms directement attribuables à cet échec et sa reprise**, hors environ 8,81 ms d’overhead dans le bloc génération mesuré à 8 502,36 ms. Réponse totale 12 642,06 ms, HTTP 200 mais status=error, grounded=false, zéro citation. Le compositeur Azure a ensuite reformulé le message d’indisponibilité en 2 645,04 ms. C’est une erreur fonctionnelle, pas une réponse financière réussie.

Le compteur generation_provider_calls de rag.stages vaut 1 pour ce cas malgré deux tentatives HTTP : c’est un compteur logique, insuffisant seul pour auditer les retries. Pas de ConnectionTimeout/APIConnectionError/attente de connexion DB anormale observée sur ces essais. Les reprises Azure et raisons de validation mesurées sont conservées dans measurements.json ; aucune raison ne doit être inférée lorsque la trace ne la donne pas.

Sur la matrice mesurée : zéro reprise Azure et zéro rejet wrong_language. Sur la seconde passe, les tentatives SDK Azure portent toutes sdk_retry=0 et sont acceptées. Ces constats ne contredisent pas la trace antérieure de fallback décrite plus bas : elle appartient à une autre requête.

## 7. Conformité des parcours

${checks}

FR/EN/AR/ARY : vérifier grounded et citations dans le tableau, et non simplement HTTP 200. Formation et orientation gardent leur route initiale tout en déclenchant le quiz interne ; composer_status=bypassed_quiz le confirme. Le code ne prend ce chemin que si quiz_session existe dans le résultat du graphe.

**Écart au contrat demandé : quiz_session n’est pas exposé dans le JSON ChatResponse.** Il existe en interne (preuve par la condition de bypass), mais le schéma [ChatResponse](../../backend/app/schemas/chat.py) ne contient pas ce champ. Aucune modification effectuée.

M1/M2 utilisent le même thread ; N utilise un nouveau thread. M2 est routé pedagogie, N out_of_domain. La mémoire ne doit donc pas être comparée en supposant un même parcours métier ; ses temps sont explicitement séparés dans tables.md.

Seconde passe : memory_context = ${n(get('M1')?.memory_ms)} ms au tour 1, ${n(get('M2')?.memory_ms)} ms au tour 2, ${n(get('N')?.memory_ms)} ms pour le contrôle neuf. Le quiz chaud (${n(get('J-warm')?.browser_ms)} ms) est environ ${n(get('A-warm')?.browser_ms/get('J-warm')?.browser_ms)} fois plus rapide que FR chaud avec Azure ; la sécurité peut le devancer puisqu’elle saute Supervisor.

## 8. Trois composants les plus coûteux

Classement par maximum mesuré sur les deux passes, hors totaux imbriqués :

1. Initialisation BGE-M3/RAG : **${n(max('init_ms'))} ms**, avant le compteur request.completed. Coût payé même par les routes sans RAG à froid.
2. Compositeur final Azure : **${n(max('azure_ms'))} ms**, incluant initialisation SDK, réseau et validation. Le temps HTTP isolé peut être nettement inférieur au bloc composer au premier appel.
3. Persistance historique + indexation mémoire synchrone : **${n(max('persistence_ms'))} ms**. Sur la seconde passe la sous-instrumentation sépare SQL, index et embedding ; ne pas attribuer ce bloc entier à PostgreSQL.

Détail de la seconde passe : SQL append au maximum ${n(Math.max(...main.map(r=>r.sql_ms??0)))} ms ; index mémoire au maximum ${n(Math.max(...main.map(r=>r.memory_index_ms??0)))} ms. Le coût majoritaire après réponse générée est l’encodage BGE des messages, dans [index_canonical_messages](../../backend/app/memory/shared_context.py), appelé synchroniquement depuis chat.py avant le retour HTTP.

## 9. Requêtes >30 s, >60 s et parcours rapides

${slow}

>60 s : ${rows.filter(r=>r.browser_ms>60000).map(r=>r.scenario+' = '+n(r.browser_ms)+' ms').join('; ')||'aucune'}.

${fastest}

L’ordre observé à chaud est globalement cohérent : quiz/fixes et agents spécialisés précèdent pédagogie avec RAG. Formation/orientation peuvent être plus rapides qu’un quiz direct ; les coûts réseau et l’indexation varient. Pas de règle de classement strict déduite d’un seul échantillon.

## 10. Les réponses d’environ trois minutes

**Non reproduites : maximum navigateur ${n(max('browser_ms'))} ms. La cause exacte d’un ancien tour à ~180 000 ms n’est donc pas établie.** Ne pas présenter les timeouts possibles comme un incident mesuré.

Une trace antérieure déjà présente dans backend-local.stdout.log (request_id d1120054-d7df-4dda-806b-0077d3f00711) montre BGE/RAG initialisé en 34 254,45 ms, puis pipeline 40 035,67 ms incluant composer Azure 22 192,88 ms avec une reprise et fallback. Elle n’a pas de mesure navigateur et ne prouve pas trois minutes ; les raisons exactes de rejet Azure n’y sont pas journalisées.

Risque de longues attentes confirmé par le code, **pas par reproduction de 180 s** : Supervisor Groq a timeout=60 s et max_retries=2 ; une série de trois timeouts peut approcher 180 s plus backoff. Azure configure timeout=120 s, garde deux retries SDK par défaut et possède deux tentatives de validation applicative. Ces limites se cumulent et ne constituent pas un budget end-to-end. Le frontend attend jusqu’à 300 s. Un timeout est par opération réseau, pas une garantie de durée totale. Il faut une trace corrélée d’un tour lent réel pour trancher entre réseau/reprises, démarrage et charge machine.

## 11. Recommandations minimales — aucune appliquée

| Priorité | Cause / action proposée | Temps actuel observé | Gain attendu (hypothèse à valider) | Fichier / composant | Risque |
| --- | --- | --- | --- | --- | --- |
| P0 | Sortir le chargement BGE de la première requête de toutes les routes : préparer réellement le runtime choisi et contrôler sa readiness ; rendre le RAG paresseux pour routes sans RAG | Initialisation jusqu’à ${n(max('init_ms'))} ms ; premier FR >60 s au pilote | Déplacer ~18–26,5 s hors chemin utilisateur ; gain non garanti si machine saturée | api/chat.py:get_chat_graph, rag/runtime.py, rag/warmup.py ; stratégie de lancement hôte | RAM/CPU au démarrage, concurrence de warm-up, readiness ne doit pas annoncer trop tôt |
| P0 | Mettre un budget global cohérent aux fournisseurs/retries et capturer le prochain tour à 180 s | Aucun 180 s observé ; limites Supervisor 60 s × jusqu’à 3, Azure 120 s et reprises imbriquées | Borner les futurs cas >60 s ; gain nominal non mesuré | llm/groq_provider.py, graph/final_response_composer.py, frontend/services/chat.ts | Réponses/fallback plus précoces ; ne pas simplement augmenter le timeout navigateur |
| P0 | Traiter les 429 comme une indisponibilité métier avec observabilité dédiée, vérifier capacité/quota et pertinence du retry | M2 pilote : 8 493,55 ms perdus, status=error malgré HTTP 200 | Éviter le retry futile peut économiser ~8,3 s sur cet incident ; rétablir une réponse exige capacité fournisseur | rag/grounded_generation.py, API métier et métriques | Réduire les retries peut abandonner un incident transitoire récupérable |
| P1 | Découpler l’indexation sémantique mémoire de la réponse, ou évaluer le mode sans mémoire pertinente pour la démo en conservant historique SQL | Persistance jusqu’à ${n(max('persistence_ms'))} ms ; index mesuré séparément jusqu’à ${n(Math.max(...main.map(r=>r.memory_index_ms??0)))} ms | Récupérer la durée d’indexation sur le chemin visible, pas forcément tout le bloc persistance | api/chat.py, memory/shared_context.py, memory/embeddings.py | Cohérence éventuelle, perte temporaire de rappel sémantique ; conserver écriture canonique avant réponse |
| P1 | Préparer le client final et mesurer/limiter son coût sans retirer les validations de langue | Composer jusqu’à ${n(max('azure_ms'))} ms | Réduire coût de première construction et générations/reprises ; estimation réseau non garantie | graph/final_response_composer.py | Régression langue/fidélité si budgets trop faibles |
| P1 | Unifier la mesure end-to-end serveur, y compris dépendances avant process_text_message | Jusqu’à ${n(max('pre_business_ms'))} ms actuellement absents du total business | Aucun gain de latence direct ; évite mauvais diagnostic frontend | observability/logging.py, api/chat.py | Faible ; attention aux données sensibles et durées imbriquées |
| P2 | Décomposer durablement SQL/index/embedding et compter tentatives transport, pas seulement appels logiques | SQL bien inférieur au bloc persistance ; 1 appel RAG logique peut produire 2 HTTP | Gain d’observabilité, pas d’accélération garantie | observability, memory, SDK | Faible surcoût ; ne pas journaliser clés/prompts |
| P2 | Mesurer fin du corps et rendu dans le frontend, et montrer clairement status=error | Après backend : max ${n(max('browser_after_backend_ms'))} ms ; pas de blocage frontend prouvé | Précision UX et diagnostic, gain performance non établi | services/chat.ts, pages/AssistantPage.tsx | Faible ; préserver le contrat de réponse |

## 12. Voix

STT_MS=N/A ; TEXT_PIPELINE_AFTER_STT_MS=N/A. Aucun appel vocal ou TTS effectué. Le parcours WebSocket envoie response.text puis appelle immédiatement tts_provider.synthesize ; aucun paramètre public « sans TTS » trouvé. Fermer le socket après response.text ne garantit pas que la synthèse ne commence pas. Sans modifier le code ni consommer du quota TTS, cet essai optionnel a été omis.

## 13. Artefacts et état final

- [tables.md](tables.md) : tous les parcours, timings d’étapes, horodatages UTC, provider calls et request_id/trace_id.
- [timings.csv](timings.csv) : mesures plates exportables, deux passes.
- [measurements.json](measurements.json) : métriques et événements corrélés, avec sous-timings et reprises.
- [browser.jsonl](browser.jsonl) : données réseau Chromium et réponses de test.
- Fichiers *.stdout.log / *.stderr.log : traces des processus de diagnostic ; *.png : captures navigateur.
- Le script run.mjs et le lanceur serve_audit.py sont uniquement des outils de diagnostic ; aucune optimisation livrée.
- Après les mesures, le backend normal a été relancé sans wrappers (PID 3996). Backend /health/live et frontend /assistant vérifiés HTTP 200. Les traces de cette restauration sont restored.stdout.log et restored.stderr.log.

La matrice est complète ; l’incident spécifique d’environ trois minutes reste **non reproduit**, pas expliqué artificiellement. Les conversations de test restent dans l’historique, conformément à l’absence de nettoyage destructif dans cet audit.
`;
fs.writeFileSync(path.join(dir,'REPORT.md'),report);
console.log('Report generated:',main.length,'main scenarios;',rows.length,'total requests');
