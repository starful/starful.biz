import os

from fastapi import APIRouter, HTTPException, Request
from firebase_admin import firestore
from starlette.concurrency import run_in_threadpool

from app.dependencies import db as firestore_db
from app.utils.http import get_client_ip

router = APIRouter()
COLLECTION_NAME = os.getenv("REACTIONS_COLLECTION", "starful_biz")


def sync_process_reaction(db_client, collection_name, slug, safe_ip, new_type):
    post_ref = db_client.collection(collection_name).document(slug)
    reaction_ref = post_ref.collection("reactions").document(safe_ip)

    reaction_doc = reaction_ref.get()
    likes_inc, dislikes_inc = 0, 0
    batch = db_client.batch()

    if not reaction_doc.exists:
        if new_type == "like":
            likes_inc = 1
        else:
            dislikes_inc = 1
        batch.set(reaction_ref, {"type": new_type})
        current_type = None
    else:
        current_type = reaction_doc.to_dict().get("type")
        if current_type == new_type:
            if new_type == "like":
                likes_inc = -1
            else:
                dislikes_inc = -1
            batch.delete(reaction_ref)
        else:
            if new_type == "like":
                likes_inc = 1
                dislikes_inc = -1
            else:
                likes_inc = -1
                dislikes_inc = 1
            batch.update(reaction_ref, {"type": new_type})

    batch.set(
        post_ref,
        {
            "likes_count": firestore.Increment(likes_inc),
            "dislikes_count": firestore.Increment(dislikes_inc),
        },
        merge=True,
    )
    batch.commit()
    action_result = "added" if (not reaction_doc.exists) or current_type != new_type else "removed"
    updated_doc = post_ref.get()
    return action_result, updated_doc.to_dict() or {}


@router.get("/reactions/{slug}")
async def get_reactions(slug: str):
    if firestore_db is None:
        return {"likes": 0, "dislikes": 0, "error": "Database not connected"}
    try:
        doc_ref = firestore_db.collection(COLLECTION_NAME).document(slug)
        doc = await run_in_threadpool(doc_ref.get)
        if doc.exists:
            data = doc.to_dict()
            return {
                "likes": data.get("likes_count", 0),
                "dislikes": data.get("dislikes_count", 0),
            }
    except Exception as e:
        print(f"Read Error: {e}")
    return {"likes": 0, "dislikes": 0}


async def process_reaction(request: Request, slug: str, reaction_type: str):
    if firestore_db is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    safe_ip = get_client_ip(request).replace(".", "_").replace(":", "_")
    try:
        result, data = await run_in_threadpool(
            sync_process_reaction, firestore_db, COLLECTION_NAME, slug, safe_ip, reaction_type
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Reaction processing failed")

    return {
        "status": "success",
        "action": result,
        "likes": data.get("likes_count", 0),
        "dislikes": data.get("dislikes_count", 0),
        "current_type": reaction_type if result == "added" else None,
    }


@router.post("/like/{slug}")
async def like_post(request: Request, slug: str):
    return await process_reaction(request, slug, "like")


@router.post("/dislike/{slug}")
async def dislike_post(request: Request, slug: str):
    return await process_reaction(request, slug, "dislike")
