"""Normalize reverse-engineered API payloads into stable renderer-friendly shapes."""

from __future__ import annotations

from typing import Any


def _published_values(*objects: dict[str, Any]) -> tuple[Any, str]:
    timestamp = None
    text = ""
    for obj in objects:
        timestamp = timestamp or obj.get("time") or obj.get("timestamp") or obj.get("create_time") or obj.get("ctime")
        for tag in obj.get("corner_tag_info", []):
            if isinstance(tag, dict) and tag.get("type") == "publish_time":
                text = str(tag.get("text", ""))
                break
        if timestamp or text:
            break
    return timestamp, text


def _coerce_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return default
    return default


def normalize_user_info(data: dict[str, Any]) -> dict[str, Any]:
    basic = data.get("basic_info", data)
    interactions = data.get("interactions", [])

    stats = {}
    for item in interactions:
        stats[item.get("type", "")] = item.get("count", "0")

    return {
        "nickname": basic.get("nickname", basic.get("nick_name", "Unknown")),
        "red_id": basic.get("red_id", ""),
        "desc": basic.get("desc", ""),
        "ip_location": basic.get("ip_location", ""),
        "user_id": basic.get("user_id", data.get("user_id", "")),
        "gender": basic.get("gender"),
        "stats": stats,
    }


def normalize_note_detail(data: dict[str, Any]) -> dict[str, Any] | None:
    items = data.get("items", [])
    if not items:
        return None

    item = items[0]
    note = item.get("note_card", item.get("note", {}))
    user = note.get("user", {})
    interact = note.get("interact_info", {})
    tags = note.get("tag_list", [])

    published_at, published_at_text = _published_values(note, item)
    return {
        "title": note.get("title", "Untitled"),
        "desc": note.get("desc", ""),
        "author": user.get("nickname", "Unknown"),
        "liked_count": interact.get("liked_count", "0"),
        "collected_count": interact.get("collected_count", "0"),
        "comment_count": interact.get("comment_count", "0"),
        "share_count": interact.get("share_count", "0"),
        "tags": [tag.get("name", "") for tag in tags if tag.get("name")],
        "image_count": len(note.get("image_list", [])),
        "published_at": published_at,
        "published_at_text": published_at_text,
    }


def normalize_note_summary(item: dict[str, Any]) -> dict[str, Any] | None:
    note_card = item.get("note_card", item)
    if not isinstance(note_card, dict):
        return None
    user = note_card.get("user", {})
    interact = note_card.get("interact_info", {})
    published_at, published_at_text = _published_values(note_card, item)
    return {
        "title": str(note_card.get("title", note_card.get("display_title", "")))[:40],
        "author": user.get("nickname", ""),
        "liked": str(interact.get("liked_count", "")),
        "note_type": "video" if note_card.get("type") == "video" else "image",
        "note_id": item.get("id", note_card.get("note_id", "")),
        "xsec_token": item.get("xsec_token", note_card.get("xsec_token", "")),
        "published_at": published_at,
        "published_at_text": published_at_text,
    }


def normalize_search_results(data: dict[str, Any]) -> dict[str, Any]:
    items = [item for item in (normalize_note_summary(item) for item in data.get("items", [])) if item]
    return {
        "items": items,
        "has_more": bool(data.get("has_more", False)),
    }


def normalize_comments(data: dict[str, Any]) -> list[dict[str, Any]]:
    normalized = []
    for comment in data.get("comments", []):
        user = comment.get("user_info", {})
        published_at, _published_at_text = _published_values(comment)
        normalized.append({
            "nickname": user.get("nickname", "Unknown"),
            "content": comment.get("content", ""),
            "like_count": comment.get("like_count", "0"),
            "sub_comment_count": _coerce_int(comment.get("sub_comment_count", 0)),
            "published_at": published_at,
        })
    return normalized


def normalize_feed(data: dict[str, Any]) -> list[dict[str, Any]]:
    normalized = []
    for item in data.get("items", [])[:20]:
        note_card = item.get("note_card", {})
        user = note_card.get("user", {})
        interact = note_card.get("interact_info", {})
        published_at, published_at_text = _published_values(note_card, item)
        normalized.append({
            "title": note_card.get("title", note_card.get("display_title", ""))[:40],
            "author": user.get("nickname", ""),
            "liked": str(interact.get("liked_count", "")),
            "note_id": item.get("id", ""),
            "xsec_token": item.get("xsec_token", note_card.get("xsec_token", "")),
            "published_at": published_at,
            "published_at_text": published_at_text,
        })
    return normalized


def normalize_user_posts(notes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for note in notes:
        interact = note.get("interact_info", {})
        published_at, published_at_text = _published_values(note)
        normalized.append({
            "title": note.get("display_title", "")[:40],
            "liked": str(interact.get("liked_count", note.get("liked_count", ""))),
            "note_type": "video" if note.get("type") == "video" else "image",
            "note_id": note.get("note_id", ""),
            "published_at": published_at,
            "published_at_text": published_at_text,
        })
    return normalized


def normalize_topics(data: Any) -> list[dict[str, Any]]:
    topics = data if isinstance(data, list) else data.get("topic_info_dtos", [])
    return [
        {
            "name": topic.get("name", ""),
            "view_num": topic.get("view_num", 0),
            "topic_id": topic.get("id", ""),
        }
        for topic in topics
    ]


def normalize_users(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        users = data
    elif isinstance(data, dict):
        users = data.get("user_info_dtos") or data.get("users") or data.get("items") or []
    else:
        users = []

    normalized = []
    for user in users:
        base = user.get("user_base_dto", user)
        normalized.append({
            "nickname": base.get("user_nickname", base.get("nickname", base.get("nick_name", ""))),
            "red_id": base.get("red_id", ""),
            "fans": user.get("fans_total", base.get("fans", base.get("fansCount", 0))),
            "user_id": base.get("user_id", base.get("id", "")),
        })
    return normalized


def normalize_creator_notes(data: Any) -> list[dict[str, Any]]:
    notes = data if isinstance(data, list) else data.get("notes", data.get("note_list", []))
    normalized = []
    for note in notes:
        interact = note.get("interact_info", {})
        published_at, published_at_text = _published_values(note)
        normalized.append({
            "title": note.get("title", note.get("display_title", ""))[:40],
            "liked": str(note.get("liked_count", interact.get("liked_count", ""))),
            "comment_count": str(note.get("comment_count", interact.get("comment_count", ""))),
            "status": note.get("status"),
            "note_id": note.get("note_id", note.get("id", "")),
            "published_at": published_at,
            "published_at_text": published_at_text,
        })
    return normalized


def normalize_hydrated_note(data: dict[str, Any], *, note_id: str, url: str) -> dict[str, Any]:
    """Normalize a note detail response for the stable hydrate command."""
    items = data.get("items", [])
    item = items[0] if items else {}
    note = item.get("note_card", item.get("note", {})) if isinstance(item, dict) else {}
    user = note.get("user", {}) if isinstance(note, dict) else {}
    interact = note.get("interact_info", {}) if isinstance(note, dict) else {}
    tags = note.get("tag_list", []) if isinstance(note, dict) else []
    images = note.get("image_list", []) if isinstance(note, dict) else []
    published_at, published_at_text = _published_values(note, item)

    image_urls = []
    for image in images:
        if not isinstance(image, dict):
            continue
        candidates = [image.get("url_default"), image.get("url_pre"), image.get("url")]
        candidates.extend(info.get("url") for info in image.get("info_list", []) if isinstance(info, dict))
        value = next((str(candidate) for candidate in candidates if candidate), "")
        if value and value not in image_urls:
            image_urls.append(value)

    return {
        "id": note_id,
        "url": url,
        "title": note.get("title", note.get("display_title", "")),
        "body": note.get("desc", ""),
        "author": {"id": user.get("user_id", ""), "name": user.get("nickname", "")},
        "note_type": "video" if note.get("type") == "video" else "image",
        "liked_count": interact.get("liked_count", "0"),
        "collected_count": interact.get("collected_count", "0"),
        "comment_count": interact.get("comment_count", "0"),
        "share_count": interact.get("share_count", "0"),
        "tags": [tag.get("name", "") for tag in tags if isinstance(tag, dict) and tag.get("name")],
        "images": image_urls,
        "image_count": len(images),
        "published_at": published_at,
        "published_at_text": published_at_text,
    }


def normalize_notifications(data: dict[str, Any]) -> list[dict[str, Any]]:
    normalized = []
    for message in data.get("message_list", []):
        user = message.get("user_info", {}) or {}
        item = message.get("item_info", {}) or {}
        normalized.append({
            "nickname": user.get("nickname", ""),
            "title": message.get("title", ""),
            "note_content": item.get("content", ""),
            "time": message.get("time", 0),
        })
    return normalized
