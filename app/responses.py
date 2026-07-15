from fastapi import HTTPException


def success(data=None, message=None):
    return {"success": True, "data": data, "message": message}


def fail(status: int, code: str, message: str, details=None):
    raise HTTPException(status_code=status, detail={"code": code, "message": message, "details": details})


def pagination(page: int, size: int, total: int):
    pages = (total + size - 1) // size
    return {"page": page, "size": size, "totalElements": total, "totalPages": pages,
            "hasPrevious": page > 1, "hasNext": page < pages}
