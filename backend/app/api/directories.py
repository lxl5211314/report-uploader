from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..errors import (
    depth_exceeded,
    directory_name_conflict,
    directory_not_empty,
    not_found,
)
from ..models import DataFile, Directory
from ..schemas import DirectoryCreate, DirectoryRename, TreeOut

router = APIRouter()


@router.get("/directories", response_model=TreeOut)
def list_tree(db: Session = Depends(get_db)) -> dict:
    directories = db.query(Directory).order_by(Directory.id).all()
    files = db.query(DataFile).order_by(DataFile.name).all()

    nodes: dict[int, dict] = {
        d.id: {
            "id": d.id,
            "name": d.name,
            "parent_id": d.parent_id,
            "children": [],
            "files": [],
        }
        for d in directories
    }
    for f in files:
        node = nodes.get(f.directory_id)
        if node is not None:
            node["files"].append(
                {
                    "id": f.id,
                    "name": f.name,
                    "format": f.format.value,
                    "size_bytes": f.size_bytes,
                    "directory_id": f.directory_id,
                    "uploaded_at": f.uploaded_at.isoformat() if f.uploaded_at else None,
                }
            )

    roots = []
    for node in nodes.values():
        parent_id = node["parent_id"]
        if parent_id is None:
            roots.append(node)
        elif parent_id in nodes:
            nodes[parent_id]["children"].append(node)
    return {"tree": roots}


def _depth(db: Session, parent_id: int | None) -> int:
    """深度：顶级目录=1，无父级=0。新建目录深度 = _depth(parent) + 1。"""
    if parent_id is None:
        return 0
    parent = db.get(Directory, parent_id)
    if parent is None:
        raise not_found("DIRECTORY_NOT_FOUND", "父目录不存在")
    return 1 + _depth(db, parent.parent_id)


def _sibling_exists(db: Session, name: str, parent_id: int | None) -> bool:
    q = db.query(Directory).filter(Directory.name == name)
    if parent_id is None:
        q = q.filter(Directory.parent_id.is_(None))
    else:
        q = q.filter(Directory.parent_id == parent_id)
    return q.first() is not None


@router.post("/directories", status_code=201)
def create_directory(body: DirectoryCreate, db: Session = Depends(get_db)) -> dict:
    if body.parent_id is not None and db.get(Directory, body.parent_id) is None:
        raise not_found("DIRECTORY_NOT_FOUND", "父目录不存在")
    if _depth(db, body.parent_id) >= 2:
        raise depth_exceeded()
    if _sibling_exists(db, body.name, body.parent_id):
        raise directory_name_conflict(f"同级已存在同名目录：{body.name}")
    directory = Directory(name=body.name, parent_id=body.parent_id)
    db.add(directory)
    db.commit()
    db.refresh(directory)
    return {"id": directory.id, "name": directory.name, "parent_id": directory.parent_id}


@router.patch("/directories/{directory_id}")
def rename_directory(
    directory_id: int, body: DirectoryRename, db: Session = Depends(get_db)
) -> dict:
    directory = db.get(Directory, directory_id)
    if directory is None:
        raise not_found("DIRECTORY_NOT_FOUND", "目录不存在")
    if body.name != directory.name and _sibling_exists(
        db, body.name, directory.parent_id
    ):
        raise directory_name_conflict(f"同级已存在同名目录：{body.name}")
    directory.name = body.name
    db.commit()
    return {"id": directory.id, "name": directory.name, "parent_id": directory.parent_id}


@router.delete("/directories/{directory_id}", status_code=204)
def delete_directory(directory_id: int, db: Session = Depends(get_db)) -> None:
    directory = db.get(Directory, directory_id)
    if directory is None:
        raise not_found("DIRECTORY_NOT_FOUND", "目录不存在")
    has_children = (
        db.query(Directory).filter(Directory.parent_id == directory_id).first()
        is not None
    )
    has_files = (
        db.query(DataFile).filter(DataFile.directory_id == directory_id).first()
        is not None
    )
    if has_children or has_files:
        raise directory_not_empty()
    db.delete(directory)
    db.commit()
