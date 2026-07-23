from datetime import datetime, timedelta, timezone

def make_prospect(c,h,name="CRM Prospect"):
    r=c.post("/api/v1/prospects",headers=h,json={"company_name":name}); assert r.status_code==201; return r.json()

def test_default_pipeline_and_stage_history(test_context,auth_headers):
    c=test_context["client"]
    r=c.get("/api/v1/pipeline/stages",headers=auth_headers); assert r.status_code==200
    assert [x["slug"] for x in r.json()]==["nouveau","a_contacter","contacte","rdv_planifie","proposition_envoyee","negociation","gagne","perdu"]
    p=make_prospect(c,auth_headers)
    r=c.post(f"/api/v1/prospects/{p['id']}/stage",headers=auth_headers,json={"pipeline_stage":"contacte","note":"Appel concluant"})
    assert r.status_code==200 and r.json()["pipeline_stage"]=="contacte"
    assert c.get(f"/api/v1/prospects/{p['id']}/stage-history",headers=auth_headers).json()[0]["note"]=="Appel concluant"

def test_activity_creation_completion_and_filter(test_context,auth_headers):
    c=test_context["client"];p=make_prospect(c,auth_headers)
    date=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()
    r=c.post(f"/api/v1/prospects/{p['id']}/activities",headers=auth_headers,json={"activity_type":"call","subject":"Rappeler","scheduled_at":date,"priority":"haute"})
    assert r.status_code==201; a=r.json()
    r=c.post(f"/api/v1/activities/{a['id']}/complete",headers=auth_headers,json={"outcome":"RDV obtenu"})
    assert r.status_code==200 and r.json()["completed_at"] is not None
    assert len(c.get(f"/api/v1/prospects/{p['id']}/activities?status=completed",headers=auth_headers).json())==1

def test_due_activities(test_context,auth_headers):
    c=test_context["client"];p=make_prospect(c,auth_headers)
    past=(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat()
    c.post(f"/api/v1/prospects/{p['id']}/activities",headers=auth_headers,json={"activity_type":"task","subject":"Envoyer devis","scheduled_at":past})
    r=c.get("/api/v1/activities/due?overdue_only=true",headers=auth_headers)
    assert r.status_code==200 and r.json()[0]["subject"]=="Envoyer devis"

def test_unknown_stage_and_invalid_activity_rejected(test_context,auth_headers):
    c=test_context["client"];p=make_prospect(c,auth_headers)
    assert c.post(f"/api/v1/prospects/{p['id']}/stage",headers=auth_headers,json={"pipeline_stage":"inconnue"}).status_code==422
    assert c.post(f"/api/v1/prospects/{p['id']}/activities",headers=auth_headers,json={"activity_type":"sms","subject":"x"}).status_code==422
