(() => {
  let ready=false, busy=false, currentGroup=null, state=null, generation=0;
  function render() {
    const subtitle=document.getElementById("chatPresenceStatus");
    if(subtitle)subtitle.textContent=state ? `${state.filter(user=>user.online).length}/${state.length} th\u00e0nh vi\u00ean online` : "\u0110ang ki\u1ec3m tra tr\u1ea1ng th\u00e1i...";
    document.querySelectorAll("[data-presence-user]").forEach(node=>{
      const user=state?.find(user=>user.user_id===Number(node.dataset.presenceUser));
      let badge=node.querySelector(".presence-indicator");
      if(!badge){badge=document.createElement("span");badge.className="presence-indicator";node.append(badge);}
      const online=Boolean(user?.online);
      badge.classList.toggle("online",online);badge.classList.toggle("unknown",!user);
      const text=!user?"Ch\u01b0a x\u00e1c \u0111\u1ecbnh":online?"\u0110ang online":"Offline";
      badge.title=text;badge.setAttribute("role","img");badge.setAttribute("aria-label",text);
    });
  }
  async function update() {
    if(!ready||busy||document.hidden)return;
    busy=true;const version=generation,group=currentGroup;
    try {
      const beat=await fetch("/api/auth/presence",{method:"POST",cache:"no-store"});
      if(beat.status===401){ready=false;state=null;render();return;}
      if(!beat.ok)throw new Error("heartbeat failed");
      if(group){
        const response=await fetch(`/api/groups/${group.id}/presence`,{cache:"no-store"});
        if(version!==generation)return;
        const next=response.ok?await response.json():null;
        if(version!==generation)return;
        state=next;render();
      }
    } catch(_){if(version===generation){state=null;render();}}
    finally{busy=false;if(version!==generation)update();}
  }
  document.addEventListener("account-ready",()=>{ready=true;currentGroup=selectedGroup();generation++;update();});
  document.addEventListener("family-ledger-changed",event=>{currentGroup=event.detail;generation++;state=null;render();update();});
  for(const event of ["family-members-rendered","chat-messages-rendered"])document.addEventListener(event,render);
  document.addEventListener("visibilitychange",()=>{if(!document.hidden)update();});
  setInterval(update,30000);
})();
