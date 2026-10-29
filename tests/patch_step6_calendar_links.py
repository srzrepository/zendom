"""Step 6: "Add to my calendar" on saved events: Google Calendar link, Outlook on the web links, and a .ics file.
No stored-data change. Usage: python3 patch_step6_calendar_links.py file.html"""
import sys
p = sys.argv[1]; s = open(p).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, (s.count(old), old[:90])
    s = s.replace(old, new)

CODE = r'''
/* ---- "Add to my calendar": one-time copies into Google, Outlook or any calendar app ----
   Timed events last an hour. Google and the .ics file keep weekly/monthly/yearly repeats; Outlook's link can't. */
const CAL_RRULE = {weekly:"FREQ=WEEKLY", monthly:"FREQ=MONTHLY", yearly:"FREQ=YEARLY"};
function calTimes(e){
  if(!e.time) return {allDay:true, start:e.date, end:addDays(e.date, 1)};
  const [y, m, d] = e.date.split("-").map(Number), [hh, mm] = e.time.split(":").map(Number);
  const a = new Date(y, m - 1, d, hh, mm), b = new Date(a.getTime() + 3600000);
  return {allDay:false, a, b};
}
const calZ = dt => dt.toISOString().replace(/\.\d{3}Z$/, "Z");                    // 2026-10-29T17:30:00Z
const calCompact = s => s.replace(/[-:]/g, "");                                    // 20261029T173000Z
function calDetails(e){ return [e.note, "From zen·dom"].filter(Boolean).join("\n\n"); }
function googleCalUrl(e){
  const t = calTimes(e), q = new URLSearchParams({action:"TEMPLATE", text:e.title, details:calDetails(e)});
  q.set("dates", t.allDay ? `${t.start.replace(/-/g, "")}/${t.end.replace(/-/g, "")}` : `${calCompact(calZ(t.a))}/${calCompact(calZ(t.b))}`);
  if(CAL_RRULE[e.repeat]) q.set("recur", "RRULE:" + CAL_RRULE[e.repeat]);
  return "https://calendar.google.com/calendar/render?" + q.toString();
}
function outlookCalUrl(e, host){
  const t = calTimes(e), q = new URLSearchParams({path:"/calendar/action/compose", rru:"addevent", subject:e.title, body:calDetails(e)});
  if(t.allDay){ q.set("startdt", t.start); q.set("enddt", t.end); q.set("allday", "true"); }
  else { q.set("startdt", calZ(t.a)); q.set("enddt", calZ(t.b)); q.set("allday", "false"); }
  return `https://${host}/calendar/0/deeplink/compose?` + q.toString();
}
function icsText(e){
  const t = calTimes(e), esc = v => String(v).replace(/\\/g, "\\\\").replace(/;/g, "\\;").replace(/,/g, "\\,").replace(/\r?\n/g, "\\n");
  const fold = line => { const out = []; let cur = ""; for(const ch of line){ if(new TextEncoder().encode(cur + ch).length > 74){ out.push(cur); cur = " " + ch; } else cur += ch; } out.push(cur); return out.join("\r\n"); };
  const lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//zen-dom//household app//EN", "CALSCALE:GREGORIAN", "BEGIN:VEVENT",
    `UID:${e.id}@zendom`, `DTSTAMP:${calCompact(calZ(new Date()))}`,
    t.allDay ? `DTSTART;VALUE=DATE:${t.start.replace(/-/g, "")}` : `DTSTART:${calCompact(calZ(t.a))}`,
    t.allDay ? `DTEND;VALUE=DATE:${t.end.replace(/-/g, "")}` : `DTEND:${calCompact(calZ(t.b))}`,
    `SUMMARY:${esc(e.title)}`, `DESCRIPTION:${esc(calDetails(e))}`];
  if(CAL_RRULE[e.repeat]) lines.push("RRULE:" + CAL_RRULE[e.repeat]);
  lines.push("END:VEVENT", "END:VCALENDAR");
  return lines.map(fold).join("\r\n") + "\r\n";
}
function calLinksHTML(e){
  const rep = e.repeat !== "none";
  return `<div class="field"><span class="lab">Add to my calendar</span>
    <div class="seg">
      <a class="chip" href="${esc(googleCalUrl(e))}" target="_blank" rel="noopener">Google Calendar</a>
      <a class="chip" href="${esc(outlookCalUrl(e, "outlook.office.com"))}" target="_blank" rel="noopener">Outlook (work or school)</a>
      <a class="chip" href="${esc(outlookCalUrl(e, "outlook.live.com"))}" target="_blank" rel="noopener">Outlook.com</a>
      <button type="button" class="chip" data-act="icsFile" data-id="${e.id}">Calendar file (.ics)</button>
    </div>
    <span class="hint">A one-time copy of the saved details: later changes here won't update it.${rep ? " Outlook's links can't repeat; use the calendar file for that." : ""}</span></div>`;
}
'''
rep('''function eventForm(id, date){''', CODE + '''function eventForm(id, date){''')
rep('''    ${footer(e ? "delEvent:" + e.id : "")}`,
  form => {
    const title = val(form,"etitle")''', '''    ${e ? calLinksHTML(e) : ""}
    ${footer(e ? "delEvent:" + e.id : "")}`,
  form => {
    const title = val(form,"etitle")''')
rep('''  editEvent: id => eventForm(id)''', '''  editEvent: id => eventForm(id),
  icsFile: id => { const e = state.events.find(x => x.id === id); if(!e) return;
    try {
      const url = URL.createObjectURL(new Blob([icsText(e)], {type:"text/calendar"}));
      const a = document.createElement("a"); a.href = url; a.download = (e.title.replace(/[^\\w ]+/g, "").trim() || "event").slice(0, 40) + ".ics";
      document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 30000);
      toast("Calendar file made. Open it to add the event.");
    } catch(err){ toast("This browser couldn't make the file."); } }''')
open(p, 'w').write(s)
print("patched", p)
