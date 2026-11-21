const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
  const user = tg.initDataUnsafe?.user;
  if (user?.first_name) document.querySelector(".welcome h1").innerHTML = `Привет, ${escapeHtml(user.first_name)}!<br>Чем помочь?`;
  if (user?.first_name) document.getElementById("avatar").textContent = user.first_name.slice(0,2).toUpperCase();
}
const form = document.getElementById("chatForm");
const input = document.getElementById("messageInput");
const messages = document.getElementById("messages");
function escapeHtml(s){return String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));}
function addBubble(text, who){const el=document.createElement("div");el.className=`bubble ${who}`;el.textContent=text;messages.appendChild(el);messages.scrollTop=messages.scrollHeight;}
document.querySelectorAll(".tile").forEach(btn=>btn.addEventListener("click",()=>{input.value=btn.dataset.prompt;input.focus();}));
form.addEventListener("submit",e=>{e.preventDefault();const text=input.value.trim();if(!text)return;addBubble(text,"user");input.value="";addBubble("Интерфейс готов! На следующем шаге подключим этот чат к нейросети через защищённый сервер. Пока это демонстрационный режим.","bot");});
