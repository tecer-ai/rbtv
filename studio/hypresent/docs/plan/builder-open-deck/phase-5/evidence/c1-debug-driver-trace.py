"""
c1-debug-driver-trace.py — Replays the VERIFIER's positional-targeting gesture sequence
(cv_b15 style: slow_mo, query_selector_all([n]) snapshots, drag row[1] over row[0]) while
capturing the /api/deck-save payload AND the model state right before each remove/duplicate.

Goal: show WHY the verifier driver yields [1,1,1,...] (sec0 absent, sec1 x3) — i.e. the
positional row snapshot the driver clicks diverges from the row it logs, after the drag.

Usage: python c1-debug-driver-trace.py <server_base> <owner_deck_copy> <evidence_dir>
"""
import os, sys, json, time, hashlib, tempfile
SERVER=sys.argv[1]; DECK=sys.argv[2]; EVDIR=sys.argv[3] if len(sys.argv)>3 else "."
os.makedirs(EVDIR, exist_ok=True)
from playwright.sync_api import sync_playwright
LOG=[]
def log(m):
    print(m,flush=True); LOG.append(str(m))

def dom_rows(page):
    return page.evaluate("""()=>Array.from(document.querySelectorAll('#tray-list .tray-row')).map((r,i)=>({
        i,uid:r.dataset.uid,slideId:r.dataset.slideId}))""")

CAP={"items":None}
def run():
    save_dir=tempfile.mkdtemp(); save_path=os.path.join(save_dir,"trace-saved.html")
    with sync_playwright() as p:
        # Match verifier exactly: headed + slow_mo=300
        browser=p.chromium.launch(headless=False, slow_mo=300)
        page=browser.new_context().new_page()
        def route(r):
            if r.request.method=="POST" and "/api/deck-save" in r.request.url:
                try: CAP["items"]=r.request.post_data_json.get("items")
                except Exception: CAP["items"]=r.request.post_data
            r.continue_()
        page.route("**/api/deck-save", route)
        page.request.post(SERVER+"/api/_test/set-dialog",
            data=json.dumps({"path":DECK}), headers={"Content-Type":"application/json"})
        page.goto(SERVER+"/app/builder.html"); page.wait_for_load_state("networkidle",timeout=8000)
        page.click("#open-deck-btn")
        page.wait_for_function("()=>document.querySelectorAll('#tray-list .tray-row').length>0",timeout=15000)
        page.wait_for_timeout(1500)
        log("OPEN: "+json.dumps(dom_rows(page)[:4]))

        # REORDER — verifier exact math
        rows=page.query_selector_all("#tray-list .tray-row")
        row0=rows[0].bounding_box(); row1=rows[1].bounding_box()
        grip1=rows[1].query_selector(".grip").bounding_box()
        sx=grip1["x"]+grip1["width"]/2; sy=grip1["y"]+grip1["height"]/2
        tx=row0["x"]+row0["width"]/2; ty=row0["y"]-4
        page.mouse.move(sx,sy); page.mouse.down(); time.sleep(0.25)
        for st in range(13):
            t=st/12; page.mouse.move(sx+(tx-sx)*t, sy+(ty-sy)*t); time.sleep(0.03)
        time.sleep(0.15); page.mouse.up(); time.sleep(0.8)
        log("AFTER REORDER: "+json.dumps(dom_rows(page)[:4]))

        # REMOVE — verifier: rows_now=query_selector_all; rows_now[2]
        rows_now=page.query_selector_all("#tray-list .tray-row")
        rm=rows_now[2]
        log(f"REMOVE click target snapshot: pos2 uid={rm.get_attribute('data-uid')} slideId={rm.get_attribute('data-slide-id')}")
        rm.query_selector(".tray-remove").click(); time.sleep(0.6)
        log("AFTER REMOVE: "+json.dumps(dom_rows(page)[:4]))

        # DUPLICATE — verifier: rows_now2=query_selector_all; rows_now2[0]
        rows_now2=page.query_selector_all("#tray-list .tray-row")
        dp=rows_now2[0]
        log(f"DUP click target snapshot: pos0 uid={dp.get_attribute('data-uid')} slideId={dp.get_attribute('data-slide-id')}")
        dp.query_selector(".tray-duplicate").click(); time.sleep(0.6)
        log("AFTER DUP: "+json.dumps(dom_rows(page)[:5]))

        page.click("#add-blank-btn"); time.sleep(0.5)

        page.request.post(SERVER+"/api/_test/set-dialog",
            data=json.dumps({"path":save_path}), headers={"Content-Type":"application/json"})
        page.click("#save-new-btn"); page.wait_for_timeout(2500)
        browser.close()
    log("PAYLOAD items indices: "+json.dumps([it.get("index","-") for it in (CAP["items"] or [])]))
    with open(os.path.join(EVDIR,"c1-debug-driver-trace-log.txt"),"w",encoding="utf-8") as f:
        f.write("\n".join(LOG))
    with open(os.path.join(EVDIR,"c1-debug-driver-trace-payload.json"),"w",encoding="utf-8") as f:
        json.dump(CAP["items"], f, indent=2)
    log("wrote trace log + payload")

if __name__=="__main__": run()
