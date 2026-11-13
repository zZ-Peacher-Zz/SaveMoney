(() => {
  const panel = document.getElementById("familyChat");
  const log = document.getElementById("chatMessages");
  const form = document.getElementById("chatForm");
  const input = document.getElementById("chatInput");
  const send = document.getElementById("chatSend");
  const older = document.getElementById("chatOlder");
  const status = document.getElementById("chatStatus");
  let group = null, generation = 0, messages = new Map(), polling = false, sending = false;
  let receivedId = 0, loaded = false;
  const drafts = new Map();
  const time = new Intl.DateTimeFormat("vi-VN", {day:"2-digit",month:"2-digit",hour:"2-digit",minute:"2-digit"});
  async function request(url, options={}) {
    const response = await fetch(url, {cache:"no-store", ...options, headers:{"Content-Type":"application/json"}});
    if (!response.ok) {
      const error = new Error(response.status===404 ? "B\u1ea1n kh\u00f4ng c\u00f2n quy\u1ec1n truy c\u1eadp nh\u00f3m n\u00e0y." : "Kh\u00f4ng th\u1ec3 k\u1ebft n\u1ed1i. Vui l\u00f2ng th\u1eed l\u1ea1i.");
      error.code=response.status;throw error;
    }
    return response.json();
  }
  function endpoint(id) {return `/api/groups/${id}/messages`;}
  function merge(items, forceBottom=false) {
    if (!items.length && messages.size) return;
    const bottom=forceBottom || log.scrollHeight-log.scrollTop-log.clientHeight<60;
    const existing=new Set(messages.keys());
    for (const message of items) messages.set(message.id,message);
    if (!messages.size) {log.textContent="Ch\u01b0a c\u00f3 tin nh\u1eafn. G\u1eedi l\u1eddi ch\u00e0o cho c\u1ea3 nh\u00e0 nh\u00e9!";return;}
    // Append new messages as text nodes, never render message content as HTML.
    if (!existing.size) log.replaceChildren();
    for (const message of items) {
      if (existing.has(message.id)) continue;
      const bubble=document.createElement("article");bubble.className="chat-bubble"+(message.is_mine?" mine":"");bubble.dataset.messageId=message.id;
      const author=document.createElement("strong");author.textContent=message.username;
      const text=document.createElement("p");text.textContent=message.content;
      const stamp=document.createElement("time");stamp.dateTime=new Date(message.created_at).toISOString();stamp.textContent=time.format(new Date(message.created_at));
      bubble.append(author,text,stamp);
      const next=[...log.children].find(node=>Number(node.dataset.messageId)>message.id);
      log.insertBefore(bubble,next||null);
    }
    if (bottom) log.scrollTop=log.scrollHeight;
  }
  function handleError(error, token) {
    if (token!==generation) return;
    status.textContent=error.message;
    if (error.code===404||error.code===401) {
      messages.clear();log.replaceChildren();input.disabled=true;send.disabled=true;older.classList.add("hidden");group=null;
    }
  }
  async function poll() {
    if (!group || polling || document.hidden) return;
    const token=generation,id=group.id;
    polling=true;
    try {
      const latest=receivedId;
      const data=await request(endpoint(id)+(latest?`?after_id=${latest}`:""));
      if (token!==generation) return;
      merge(data.messages);
      if (!loaded) older.classList.toggle("hidden",!data.has_more);
      loaded=true;
      if(data.messages.length) receivedId=Math.max(receivedId,...data.messages.map(item=>item.id));
      status.textContent="";
    } catch(error) {handleError(error,token);}
    finally {if(token===generation)polling=false;}
  }
  function selectGroup(next) {
    if (group?.id===next?.id) return;
    if (group) drafts.set(group.id,input.value);
    generation++;group=next;messages=new Map();receivedId=0;loaded=false;polling=false;sending=false;
    panel.classList.toggle("hidden",!group);log.replaceChildren();status.textContent="";
    input.disabled=false;input.readOnly=false;send.disabled=false;older.disabled=false;older.classList.add("hidden");
    input.value=group?(drafts.get(group.id)||""):"";
    if (!group) return;
    document.getElementById("chatGroupName").textContent=group.name;
    status.textContent="\u0110ang t\u1ea3i tin nh\u1eafn...";
    poll();
  }
  document.addEventListener("family-ledger-changed",event=>selectGroup(event.detail));
  document.addEventListener("account-ready",()=>selectGroup(selectedGroup()));
  older.addEventListener("click",async()=>{
    if (!group || !messages.size) return;
    const token=generation,id=group.id,previous=log.scrollHeight;older.disabled=true;
    try {
      const data=await request(endpoint(id)+`?before_id=${Math.min(...messages.keys())}`);
      if(token!==generation)return;
      merge(data.messages);log.scrollTop=log.scrollHeight-previous;
      older.classList.toggle("hidden",!data.has_more);
    } catch(error){handleError(error,token);}
    finally {if(token===generation)older.disabled=false;}
  });
  form.addEventListener("submit",async event=>{
    event.preventDefault();
    if (!FieldErrors.validate(form)) return;
    FieldErrors.clear(input);
    const content=input.value.trim();if(!group||sending)return;
    if(!content){FieldErrors.set(input,"Tin nh\u1eafn kh\u00f4ng \u0111\u01b0\u1ee3c \u0111\u1ec3 tr\u1ed1ng.");input.focus();return;}
    const token=generation,id=group.id;
    sending=true;send.disabled=true;input.readOnly=true;status.textContent="\u0110ang g\u1eedi...";
    try {
      const message=await request(endpoint(id),{method:"POST",body:JSON.stringify({content})});
      if(token!==generation)return;
      merge([message],true);input.value="";drafts.delete(id);status.textContent="\u0110\u00e3 g\u1eedi.";
    } catch(error){if(token===generation)FieldErrors.set(input,error.message);handleError(error,token);}
    finally {if(token===generation){sending=false;input.readOnly=false;send.disabled=!group;}}
  });
  setInterval(poll,3000);
  document.addEventListener("visibilitychange",()=>{if(!document.hidden)poll();});
})();
