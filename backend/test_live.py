"""Live API test — requires backend running on localhost:8000."""
import httpx
import asyncio
import io
import time


async def main():
    content = "# 退款政策\n客户可在购买后7天内申请全额退款。\n退款需提供购买凭证。".encode("utf-8")
    files = [("files", ("policy.md", io.BytesIO(content), "text/markdown"))]

    async with httpx.AsyncClient(base_url="http://localhost:8000") as c:
        # 1. Upload
        print("1. Uploading document...")
        r = await c.post("/api/documents/upload", files=files, timeout=30)
        print(f"   HTTP {r.status_code}: {r.json()}")

        if r.status_code != 201 or "documents" not in r.json():
            print("   UPLOAD FAILED")
            return

        doc_id = r.json()["documents"][0]["id"]
        print(f"   doc_id = {doc_id}")

        # 2. Wait for indexing
        print("2. Waiting for indexing...")
        status = "pending"
        for _ in range(15):
            await asyncio.sleep(2)
            r = await c.get(f"/api/documents/{doc_id}")
            doc = r.json()
            status = doc["status"]
            print(f"   -> {status}")
            if status == "failed":
                print(f"   ERROR: {doc.get('error_message')}")
                return
            if status == "indexed":
                break

        if status != "indexed":
            print(f"   Document stuck at: {status}")
            return

        # 3. Start a scan
        print("3. Starting conflict scan...")
        r = await c.post("/api/scans/start?threshold=0.85", timeout=10)
        print(f"   HTTP {r.status_code}: {r.json()}")

        # 4. Test QA
        print("4. Testing QA...")
        r = await c.post("/api/qa/sessions", json={"title": "test"})
        sess_id = r.json()["id"]

        r = await c.post(
            f"/api/qa/sessions/{sess_id}/messages",
            json={"content": "退款政策是什么？"},
            timeout=60,
        )
        print(f"   HTTP {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"   Answer: {data['answer']['content'][:300]}")
            if data["answer"].get("conflict_warning"):
                print(f"   CONFLICT: {data['answer']['conflict_warning']}")
        else:
            print(f"   ERROR: {r.text}")


if __name__ == "__main__":
    asyncio.run(main())
