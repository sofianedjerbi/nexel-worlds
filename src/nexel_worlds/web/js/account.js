// Who you are, in a world that asks (the server's --accounts; a world that does not, and the demo, never come here):
// your email, a six-digit code mailed to it, and you are in for thirty days. The account service (account/service.py)
// is apart from the world: the world only ever gets a ticket saying "this account may enter", never your email.
// The first screen shows one step at a time (title.js): your email, then the code, then who you are.

const ACCOUNT = {url: document.body.dataset.accounts || "", session: localStorage.getItem("megastructure-session") || "",
  email: localStorage.getItem("megastructure-email") || "", named: null, busy: false};
const ACCOUNT_SAYS = {bad_email: "That does not look like an email.", too_many: "Too many tries. Wait a little, then ask again.",
  mail_down: "The mail could not be sent. Try again in a moment.", bad_code: "That is not the code. Look at the mail again, or start over.",
  offline: "The account service does not answer.", no_session: "You were logged out. Log in again."};
async function accountAsk(path, body) {
  try { return await (await fetch(ACCOUNT.url + path, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)})).json(); }
  catch (e) { return {ok: false, error: "offline"}; }
}
function accountStep() { return !ACCOUNT.url || ACCOUNT.session ? "me" : ACCOUNT.sent ? "code" : "mail"; }
function accountNeed(id, why) { $(id).classList.add("need"); $(id).focus(); if (why) toast(ACCOUNT_SAYS[why] || why, true); }
async function accountCode() {                                // step one: mail me a code
  const email = $("email").value.trim();
  if (!/^\S+@\S+\.\S+$/.test(email)) return accountNeed("email", email ? "bad_email" : "");
  if (ACCOUNT.busy) return; ACCOUNT.busy = true;
  const r = await accountAsk("/code", {email}); ACCOUNT.busy = false;
  if (!r.ok) return accountNeed("email", r.error);
  ACCOUNT.email = email; ACCOUNT.sent = true; $("code").value = ""; titleStep();
  toast("A code is on its way to " + email + ".");
}
async function accountLogin() {                               // step two: the code
  const code = $("code").value.replace(/\D/g, "");
  if (code.length !== 6) return accountNeed("code", "");
  if (ACCOUNT.busy) return; ACCOUNT.busy = true;
  const r = await accountAsk("/login", {email: ACCOUNT.email, code}); ACCOUNT.busy = false;
  if (!r.ok) { $("code").value = ""; return accountNeed("code", r.error); }
  ACCOUNT.session = r.session; ACCOUNT.sent = false;
  localStorage.setItem("megastructure-session", r.session); localStorage.setItem("megastructure-email", ACCOUNT.email);
  titleStep(); accountWho();
}
function accountOver() { ACCOUNT.sent = false; titleStep(); }  // back to the email: another one, or a new code
function accountDrop() {                                      // this browser is nobody again
  ACCOUNT.session = ""; ACCOUNT.sent = false; ACCOUNT.named = null; localStorage.removeItem("megastructure-session");
  $("name").readOnly = false; titleStep();
}
function accountOut() { accountAsk("/logout", {session: ACCOUNT.session}); accountDrop(); }
async function accountTicket() {                              // what the world's door asks for: good for this world, two minutes
  const r = await accountAsk("/ticket", {session: ACCOUNT.session, world: location.host});
  if (r.ok) return r.ticket;
  if (r.error === "no_session") accountDrop();
  toast(ACCOUNT_SAYS[r.error] || r.error, true);
  return null;
}
async function accountWho() {                                 // has this account a character here already? the world says
  if (!ACCOUNT.url || !ACCOUNT.session) return;
  const ticket = await accountTicket();
  if (!ticket) return;
  const ask = () => spec && spec.readyState === 1 ? sendSpec({op: "who", ticket}) : setTimeout(ask, 200);   // (the socket may still be opening)
  ask();
}
function accountNamed(name) {                                 // (state.js: the world's answer) yours is yours: the name is not asked again
  ACCOUNT.named = name;
  if (name) { $("name").value = name; $("name").classList.remove("need"); }
  $("name").readOnly = !!name;
}
