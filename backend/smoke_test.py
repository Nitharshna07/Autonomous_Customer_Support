import time
import os
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def run_tests():
    print("=" * 60)
    print("STARTING BACKEND API ENDPOINTS SMOKE TEST")
    print("=" * 60)

    # 1. Health check
    r = requests.get(f"{BASE_URL}/")
    assert r.status_code == 200, f"Root endpoint failed: {r.text}"
    print("[OK] Health Check Passed")

    # 2. Signup or Login Admin User
    admin_credentials = {
        "email": "admin@supportcopilot.com",
        "password": "AdminPassword123!"
    }
    r = requests.post(f"{BASE_URL}/auth/signup", json=admin_credentials)
    if r.status_code != 200:
        # User exists, login instead
        r = requests.post(f"{BASE_URL}/auth/login", json=admin_credentials)
        assert r.status_code == 200, f"Admin login failed: {r.text}"
    
    admin_token = r.json()["access_token"]
    assert r.json()["user"]["role"] == "admin", "User role should be admin"
    print(f"[OK] Admin Auth & Role Verification Passed (User: {r.json()['user']['email']}, Role: {r.json()['user']['role']})")

    # 3. Signup Customer User
    ts = int(time.time())
    customer_signup = {
        "email": f"customer_{ts}@supportcopilot.com",
        "password": "CustomerPassword123!"
    }
    r = requests.post(f"{BASE_URL}/auth/signup", json=customer_signup)
    assert r.status_code == 200, f"Customer signup failed: {r.text}"
    customer_token = r.json()["access_token"]
    assert r.json()["user"]["role"] == "customer", "Second user should be customer"
    print("[OK] Customer Signup & Role Verification Passed")

    # 4. Login Check
    r = requests.post(f"{BASE_URL}/auth/login", json=admin_credentials)
    assert r.status_code == 200, f"Login failed: {r.text}"
    print("[OK] Authentication Login Passed")

    # 5. Auth /me check
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    headers_customer = {"Authorization": f"Bearer {customer_token}"}

    r = requests.get(f"{BASE_URL}/auth/me", headers=headers_admin)
    assert r.status_code == 200 and r.json()["role"] == "admin"
    print("[OK] GET /auth/me Passed")

    # 6. Upload Knowledge Base Document (Admin Only)
    kb_content = (
        "AUTONOMOUS COPILOT SUPPORT FAQ AND POLICIES\n"
        "Pricing Policy:\n"
        "Our standard tier costs $29 per month per user. The enterprise tier costs $99 per month.\n"
        "All plans come with a 14-day money back guarantee and 24/7 automated support.\n"
        "To upgrade your tier, navigate to Account Settings > Billing > Upgrade.\n"
        "Refund Policy:\n"
        "Refunds are processed within 5 business days upon request if within the 14-day trial window.\n"
    )
    files = {"file": ("support_policy.txt", kb_content.encode("utf-8"), "text/plain")}
    r = requests.post(f"{BASE_URL}/kb/upload", headers=headers_admin, files=files)
    assert r.status_code == 200, f"KB Upload failed: {r.text}"
    kb_doc = r.json()
    assert kb_doc["chunk_count"] > 0
    print(f"[OK] KB Upload Passed (Document ID: {kb_doc['id']}, Chunks: {kb_doc['chunk_count']})")

    # 7. Verify KB document listing
    r = requests.get(f"{BASE_URL}/kb/documents", headers=headers_admin)
    assert r.status_code == 200 and len(r.json()) > 0
    print("[OK] GET /kb/documents Passed")

    # 8. Normal Question (RAG Retrieval, No Escalation)
    q1 = {"content": "What is the price of the standard tier?"}
    r = requests.post(f"{BASE_URL}/chat/message", headers=headers_customer, json=q1)
    assert r.status_code == 200, f"Chat message failed: {r.text}"
    res1 = r.json()
    conv_id = res1["conversation_id"]
    bot_msg1 = res1["bot_message"]
    assert bot_msg1["rag_grounded"] is True, "Query should be RAG grounded"
    assert bot_msg1["escalated"] is False, "Normal query should not escalate"
    print(f"[OK] Normal RAG Chat Message Passed (Conv #{conv_id}, Response time: {bot_msg1['response_time_ms']}ms)")

    # 9. Complaint Question (High Priority Intent -> Auto-Escalate & Create Ticket)
    q2 = {"conversation_id": conv_id, "content": "This service is a scam, refund my money immediately! Terrible service!"}
    r = requests.post(f"{BASE_URL}/chat/message", headers=headers_customer, json=q2)
    assert r.status_code == 200, f"Complaint message failed: {r.text}"
    res2 = r.json()
    bot_msg2 = res2["bot_message"]
    assert bot_msg2["escalated"] is True, "Complaint message should trigger escalation"
    assert bot_msg2["intent"] == "complaint"
    print(f"[OK] Complaint Auto-Escalation Passed (Intent: {bot_msg2['intent']}, Reason: {bot_msg2['escalation_reason']})")

    # 10. Message Feedback
    fb_req = {"message_id": bot_msg1["id"], "feedback": 1}
    r = requests.post(f"{BASE_URL}/chat/feedback", headers=headers_customer, json=fb_req)
    assert r.status_code == 200 and r.json()["feedback"] == 1
    print("[OK] Message Thumbs-Up Feedback Passed")

    # 11. Admin Metrics Summary
    r = requests.get(f"{BASE_URL}/metrics/summary", headers=headers_admin)
    assert r.status_code == 200, f"Metrics failed: {r.text}"
    metrics = r.json()
    assert metrics["total_conversations"] >= 1
    assert metrics["open_tickets_count"] >= 1
    print(f"[OK] GET /metrics/summary Passed (Conversations: {metrics['total_conversations']}, CSAT: {metrics['satisfaction_score']}%)")

    # 12. Get Escalation Tickets (Admin Only)
    r = requests.get(f"{BASE_URL}/tickets", headers=headers_admin)
    assert r.status_code == 200 and len(r.json()) >= 1
    ticket_id = r.json()[0]["id"]
    print(f"[OK] GET /tickets Passed (Found {len(r.json())} tickets)")

    # 13. Patch Ticket Status
    r = requests.patch(f"{BASE_URL}/tickets/{ticket_id}/status", headers=headers_admin, json={"status": "in_progress"})
    assert r.status_code == 200 and r.json()["status"] == "in_progress"
    print("[OK] PATCH /tickets/{{id}}/status Passed")

    # 14. Mark Conversation Resolved
    r = requests.post(f"{BASE_URL}/chat/resolve/{conv_id}", headers=headers_customer)
    assert r.status_code == 200
    print("[OK] POST /chat/resolve/{{id}} Passed")

    print("=" * 60)
    print("ALL BACKEND SMOKE TESTS COMPLETED SUCCESSFULLY WITH 100% PASS RATE!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
